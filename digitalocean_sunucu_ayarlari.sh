#!/usr/bin/env bash
# DigitalOcean Ubuntu - Sunucu: 157.230.16.7
set -euo pipefail

# ---------------------------------------- Bilgiler ----------------------------------------
SERVER_IP="157.230.16.7"
GITHUB_HESAP="mpiriyilmaz"
GITHUB_REPO="aras_test_v12"
DB_NAME="arasomtest"
DB_USER="postgres"
DB_PASSWORD="oms123456"
DJANGO_PROJE_ADI="core"

# ---------------------------------------- Sistem Paketleri ----------------------------------------
sudo apt update
python3 --version || true
sudo apt install -y git curl ca-certificates python3-venv python3-pip nginx iproute2
sudo apt install -y build-essential libpq-dev || true

# ---------------------------------------- SSH key ----------------------------------------
mkdir -p ~/.ssh
chmod 700 ~/.ssh
ssh-keygen -t ed25519 -C "server-key" -f ~/.ssh/id_ed25519 || true
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub
ssh-keyscan -H github.com >> ~/.ssh/known_hosts 2>/dev/null || true

echo "==== PUBLIC KEY ===="
cat ~/.ssh/id_ed25519.pub || true
echo "===================="

# (Key eklenmeden bu test başarısız olabilir, script durmasın)
ssh -T git@github.com || true

# ---------------------------------------- Repo ----------------------------------------
set -euo pipefail
cd /opt

if [ ! -d "/opt/aras_test_v12/.git" ]; then
  echo "[INFO] SSH ile klon deneniyor..."
  if git clone git@github.com:mpiriyilmaz/aras_test_v12.git; then
    :
  else
    echo "[WARN] SSH klon başarısız. HTTPS fallback denenecek."
    if [ -n "${GITHUB_PAT:-}" ]; then
      git clone https://mpiriyilmaz:${GITHUB_PAT}@github.com/mpiriyilmaz/aras_test_v12.git
    else
      echo "[ERROR] Repo klonlanamadı. Deploy key ekleyin ya da GITHUB_PAT ortam değişkeni verin."
      exit 1
    fi
  fi
else
  echo "[INFO] Repo mevcut, güncelleniyor…"
  git -C "/opt/aras_test_v12" pull --rebase || true
fi

git config --global --add safe.directory /opt/aras_test_v12 || true

# manage.py artık repo kökünde
ls -la "/opt/aras_test_v12/manage.py" || true

# ---------------------------------------- venv & paketler ----------------------------------------
cd /opt/aras_test_v12
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel

# manage.py repo kökünde
cd /opt/aras_test_v12

if [ -f requirements.txt ]; then
  pip install -r requirements.txt
else
  pip install "Django>=5.2,<5.3" django-environ gunicorn psycopg2-binary
fi

# ---------------------------------------- .env ----------------------------------------
cd /opt/aras_test_v12

SECRET_KEY=$(python3 - <<'PY'
import secrets
print('django-insecure-' + secrets.token_urlsafe(50))
PY
)

cat > .env <<EOF
DEBUG=False
SECRET_KEY=$SECRET_KEY
ALLOWED_HOSTS=157.230.16.7,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://157.230.16.7,https://157.230.16.7,http://157.230.16.7:8000
DATABASE_URL=postgres://postgres:oms123456@localhost:5432/arasomtest
DJANGO_ADMIN_USERNAME=piri
DJANGO_ADMIN_EMAIL=piri@arasedas.com
DJANGO_ADMIN_PASSWORD=arAs*+1981
EOF

chmod 600 .env
echo ".env olusturuldu:"
cat .env

# ---------------------------------------- PostgreSQL ----------------------------------------
dpkg -l | grep postgresql || true
sudo apt update
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable --now postgresql

# Kullanıcı yoksa oluştur, varsa şifre ver
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname = 'postgres'" | grep -q 1           || sudo -u postgres psql -c "CREATE USER postgres WITH PASSWORD 'oms123456';"
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'oms123456';"

# DB yoksa oluştur ve owner yap
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = 'arasomtest'" | grep -q 1           || sudo -u postgres createdb -O postgres arasomtest

# Test
PGPASSWORD='oms123456' psql "host=localhost dbname=arasomtest user=postgres" -c "select current_database(), current_user;"

# ---------------------------------------- migrate/superuser/static ----------------------------------------
cd /opt/aras_test_v12
source .venv/bin/activate
cd /opt/aras_test_v12

# Migrasyonlar
python manage.py migrate --noinput

# Superuser / staff kullanıcı oluştur ya da düzelt
python - <<'PY'
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()
username = os.environ.get('DJANGO_ADMIN_USERNAME', 'admin')
email    = os.environ.get('DJANGO_ADMIN_EMAIL',    'admin@arasedas.com')
password = os.environ.get('DJANGO_ADMIN_PASSWORD', 'sifre1234')

u, created = User.objects.get_or_create(
    username=username,
    defaults={'email': email, 'is_active': True, 'is_staff': True, 'is_superuser': True}
)

if created:
    u.set_password(password)
    u.save()
    print("Superuser created.")
else:
    changed = False
    if not u.is_active:
        u.is_active = True; changed = True
    if not u.is_staff:
        u.is_staff = True; changed = True
    if not u.is_superuser:
        u.is_superuser = True; changed = True
    if changed:
        u.save(); print("User elevated to staff/superuser.")
    else:
        print("Superuser already exists.")

try:
    g = Group.objects.get(name='Admin')
    g.user_set.add(u)
except Group.DoesNotExist:
    pass
PY

# Statikler
python manage.py collectstatic --noinput || true

# ---------------------------------------- Gunicorn (systemd) ----------------------------------------
cd /opt/aras_test_v12
source .venv/bin/activate

cat > /etc/systemd/system/gunicorn_v1.service <<'EOF'
[Unit]
Description=Gunicorn for aras_test_v12
After=network-online.target
Wants=network-online.target

[Service]
User=root
Group=www-data
WorkingDirectory=/opt/aras_test_v12
Environment="PATH=/opt/aras_test_v12/.venv/bin"
Environment="DJANGO_SETTINGS_MODULE=core.settings"
ExecStart=/opt/aras_test_v12/.venv/bin/gunicorn --workers 3 --timeout 120 --umask 007 --bind unix:/run/gunicorn_v1/gunicorn.sock core.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
KillMode=mixed

RuntimeDirectory=gunicorn_v1
RuntimeDirectoryMode=0755

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now gunicorn_v1
systemctl status gunicorn_v1 --no-pager || true

ls -l /run/gunicorn_v1/gunicorn.sock || (echo "[ERROR] Gunicorn soketi oluşmadı." && exit 1)

# ---------------------------------------- Nginx ----------------------------------------
if ! grep -q "include /etc/nginx/conf.d/*.conf;" /etc/nginx/nginx.conf; then
  sudo sed -i '/http \{/a \    include /etc/nginx/conf.d/*.conf;' /etc/nginx/nginx.conf
fi

sudo tee /etc/nginx/conf.d/aras_test_v12.conf > /dev/null <<'NGINX'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    client_max_body_size 20m;

    # STATIC_ROOT: /opt/aras_test_v12/staticfiles/
    location /static/ {
        alias /opt/aras_test_v12/staticfiles/;
        access_log off;
        expires 30d;
    }

    location / {
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_pass http://unix:/run/gunicorn_v1/gunicorn.sock;
    }
}
NGINX

sudo rm -f /etc/nginx/sites-enabled/default || true

sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx

if ! ss -ltnp | grep -q ':80'; then
  echo "[ERROR] Nginx 80 portunu dinlemiyor!"
  sudo tail -n 100 /var/log/nginx/error.log || true
  exit 1
fi

curl --unix-socket /run/gunicorn_v1/gunicorn.sock http://localhost -I || true

# ---------------------------------------- UFW ----------------------------------------
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable
ufw status

# ---------------------------------------- Doğrulamalar ----------------------------------------
echo "== Durum Kontrolleri =="
systemctl is-active nginx || true
systemctl is-active gunicorn_v1 || true
ss -ltnp | grep ':80' || true
ls -l /run/gunicorn_v1/gunicorn.sock || true
curl -I http://127.0.0.1 || true

# ---------------------------------------- Deploy script ----------------------------------------
# Repo köküne bir deploy.sh bırak
cat > /opt/aras_test_v12/deploy.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/aras_test_v12"
BRANCH="${1:-$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)}"

echo "[INFO] Deploy başlıyor: $REPO_DIR (branch: $BRANCH)"
git -C "$REPO_DIR" fetch --all --prune
# Tercihen reset --hard; olmazsa ff-only pull
git -C "$REPO_DIR" reset --hard "origin/$BRANCH" || git -C "$REPO_DIR" pull --ff-only origin "$BRANCH"

# Sanal ortam + bağımlılıklar (varsa)
source "$REPO_DIR/.venv/bin/activate"
[ -f "$REPO_DIR/requirements.txt" ] && pip install -r "$REPO_DIR/requirements.txt"

# Django işlemleri
cd "$REPO_DIR"
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Uygulamayı yeniden yükle
systemctl reload gunicorn_v1 || systemctl restart gunicorn_v1

echo "[OK] Deploy tamamlandı."
SH

chmod +x /opt/aras_test_v12/deploy.sh

# Kısa yol (isteğe bağlı)
ln -sf /opt/aras_test_v12/deploy.sh /usr/local/bin/aras_test_v12_update || true

echo "Kullanım: sudo /opt/aras_test_v12/deploy.sh  [opsiyonel-branch]"
echo "Kısayol: sudo aras_test_v12_update"

# ---------------------------------------- DB RESET + SUPERUSER (opsiyonel: DB_RESET=1) ----------------------------------------
# Opsiyonel güvenlik: DB_RESET=1 değilse atla
if [ "${DB_RESET:-0}" != "1" ]; then
  echo "[SKIP] DB reset atlandı (DB_RESET=1 değil)."
  exit 0
fi

set -euo pipefail
echo "[WARN] Veritabanı SIFIRLANACAK: arasomtest"

# DB kullanıcısı garanti
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname = 'postgres'" | grep -q 1           || sudo -u postgres psql -c "CREATE USER postgres WITH PASSWORD 'oms123456';"
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'oms123456';"

# Drop + Create
sudo -u postgres dropdb --if-exists arasomtest
sudo -u postgres createdb -O postgres arasomtest

# Django migrate + superuser
cd /opt/aras_test_v12
source .venv/bin/activate
python manage.py migrate --noinput

# .env'deki DJANGO_ADMIN_* değerlerini ortam değişkenine taşı ve superuser oluştur
python - <<'PY'
import os, django, pathlib
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

env_file = pathlib.Path('/opt/aras_test_v12/.env')
if env_file.exists():
    for line in env_file.read_text(encoding='utf-8', errors='ignore').splitlines():
        s = line.strip()
        if s and not s.startswith('#') and '=' in s:
            k, v = s.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()

username = os.environ.get('DJANGO_ADMIN_USERNAME', 'admin')
email    = os.environ.get('DJANGO_ADMIN_EMAIL',    'admin@example.com')
password = os.environ.get('DJANGO_ADMIN_PASSWORD', 'sifre1234')

u, created = User.objects.get_or_create(
    username=username,
    defaults={'email': email}
)
u.is_active = True
u.is_staff = True
u.is_superuser = True
u.email = email
u.set_password(password)
u.save()
print(f"[OK] Superuser: {username} (şifre .env veya varsayılan)")
PY

python manage.py collectstatic --noinput || true
systemctl reload gunicorn_v1 || systemctl restart gunicorn_v1

echo "[OK] DB reset + superuser tamam."
