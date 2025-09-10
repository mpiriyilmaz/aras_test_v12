from pathlib import Path
from textwrap import dedent


class SunucuAyar:
    def __init__(
        self,
        ip: str,
        github_hesap_adi: str,
        github_repo_adi: str,
        db_adi: str,
        db_kullanici_adi: str,
        db_sifre: str,
        django_proje_adi: str,
    ):
        self.ip = ip
        self.github_hesap_adi = github_hesap_adi
        self.github_repo_adi = github_repo_adi
        self.db_adi = db_adi
        self.db_kullanici_adi = db_kullanici_adi
        self.db_sifre = db_sifre
        self.django_proje_adi = django_proje_adi
        self.cizgi = "-" * 40

    # 1) Temel paketler
    def django_kurulumu(self, include_shebang: bool = True) -> str:
        shebang = "#!/usr/bin/env bash\n" if include_shebang else ""
        return shebang + dedent(
            f"""\
        # DigitalOcean Ubuntu - Sunucu: {self.ip}
        set -euo pipefail

        # {self.cizgi} Bilgiler {self.cizgi}
        SERVER_IP="{self.ip}"
        GITHUB_HESAP="{self.github_hesap_adi}"
        GITHUB_REPO="{self.github_repo_adi}"
        DB_NAME="{self.db_adi}"
        DB_USER="{self.db_kullanici_adi}"
        DB_PASSWORD="{self.db_sifre}"
        DJANGO_PROJE_ADI="{self.django_proje_adi}"

        # {self.cizgi} Sistem Paketleri {self.cizgi}
        sudo apt update
        python3 --version || true
        sudo apt install -y git curl ca-certificates python3-venv python3-pip nginx iproute2
        sudo apt install -y build-essential libpq-dev || true
        """
        )  # Django, venv içinde pip ile kurulacak.

    # 2) SSH key
    def sshkeygen_uret(self, include_shebang: bool = False) -> str:
        shebang = "#!/usr/bin/env bash\n" if include_shebang else ""
        return shebang + dedent(
            """\
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
        """
        )

    # 3) Repo klonla/güncelle (SSH başarısızsa HTTPS fallback: GITHUB_PAT ile)
    def github_repo_klonla(self, include_shebang: bool = False) -> str:
        shebang = "#!/usr/bin/env bash\n" if include_shebang else ""
        return shebang + dedent(
            f"""\
        set -euo pipefail
        cd /opt

        if [ ! -d "/opt/{self.github_repo_adi}/.git" ]; then
          echo "[INFO] SSH ile klon deneniyor..."
          if git clone git@github.com:{self.github_hesap_adi}/{self.github_repo_adi}.git; then
            :
          else
            echo "[WARN] SSH klon başarısız. HTTPS fallback denenecek."
            if [ -n "${{GITHUB_PAT:-}}" ]; then
              git clone https://{self.github_hesap_adi}:${{GITHUB_PAT}}@github.com/{self.github_hesap_adi}/{self.github_repo_adi}.git
            else
              echo "[ERROR] Repo klonlanamadı. Deploy key ekleyin ya da GITHUB_PAT ortam değişkeni verin."
              exit 1
            fi
          fi
        else
          echo "[INFO] Repo mevcut, güncelleniyor…"
          git -C "/opt/{self.github_repo_adi}" pull --rebase || true
        fi

        git config --global --add safe.directory /opt/{self.github_repo_adi} || true

        # manage.py artık repo kökünde
        ls -la "/opt/{self.github_repo_adi}/manage.py" || true
        """
        )

    # 4) venv + paketler
    def sanalortam_python_paketleri_kurulumu(
        self, include_shebang: bool = False
    ) -> str:
        shebang = "#!/usr/bin/env bash\n" if include_shebang else ""
        return shebang + dedent(
            f"""\
        cd /opt/{self.github_repo_adi}
        python3 -m venv .venv
        source .venv/bin/activate
        pip install --upgrade pip setuptools wheel

        # manage.py repo kökünde
        cd /opt/{self.github_repo_adi}

        if [ -f requirements.txt ]; then
          pip install -r requirements.txt
        else
          pip install "Django>=5.2,<5.3" django-environ gunicorn psycopg2-binary
        fi
        """
        )

    # 5) .env (manage.py ile aynı dizin: repo kökü)
    def env_kurulumu(self, include_shebang: bool = False) -> str:
        shebang = "#!/usr/bin/env bash\n" if include_shebang else ""
        return shebang + dedent(
            f"""\
        cd /opt/{self.github_repo_adi}

        SECRET_KEY=$(python3 - <<'PY'
        import secrets
        print('django-insecure-' + secrets.token_urlsafe(50))
        PY
        )

        cat > .env <<EOF
        DEBUG=False
        SECRET_KEY=$SECRET_KEY
        ALLOWED_HOSTS={self.ip},localhost,127.0.0.1
        CSRF_TRUSTED_ORIGINS=http://{self.ip},https://{self.ip},http://{self.ip}:8000
        DATABASE_URL=postgres://{self.db_kullanici_adi}:{self.db_sifre}@localhost:5432/{self.db_adi}
        DJANGO_ADMIN_USERNAME=piri
        DJANGO_ADMIN_EMAIL=piri@arasedas.com
        DJANGO_ADMIN_PASSWORD=arAs*+1981
        EOF

        chmod 600 .env
        echo ".env olusturuldu:"
        cat .env
        """
        )

    # 6) PostgreSQL
    def postgre_kurulumu(self, include_shebang: bool = False) -> str:
        shebang = "#!/usr/bin/env bash\n" if include_shebang else ""
        return shebang + dedent(
            f"""\
        dpkg -l | grep postgresql || true
        sudo apt update
        sudo apt install -y postgresql postgresql-contrib
        sudo systemctl enable --now postgresql

        # Kullanıcı yoksa oluştur, varsa şifre ver
        sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname = '{self.db_kullanici_adi}'" | grep -q 1 \
          || sudo -u postgres psql -c "CREATE USER {self.db_kullanici_adi} WITH PASSWORD '{self.db_sifre}';"
        sudo -u postgres psql -c "ALTER USER {self.db_kullanici_adi} WITH PASSWORD '{self.db_sifre}';"

        # DB yoksa oluştur ve owner yap
        sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = '{self.db_adi}'" | grep -q 1 \
          || sudo -u postgres createdb -O {self.db_kullanici_adi} {self.db_adi}

        # Test
        PGPASSWORD='{self.db_sifre}' psql "host=localhost dbname={self.db_adi} user={self.db_kullanici_adi}" -c "select current_database(), current_user;"
        """
        )

    # 7) migrate / superuser / static
    def django_migrate_superuser(self, include_shebang: bool = False) -> str:
        shebang = "#!/usr/bin/env bash\n" if include_shebang else ""
        return shebang + dedent(
            f"""\
        cd /opt/{self.github_repo_adi}
        source .venv/bin/activate
        cd /opt/{self.github_repo_adi}

        # Migrasyonlar
        python manage.py migrate --noinput

        # Superuser / staff kullanıcı oluştur ya da düzelt
        python - <<'PY'
        import os, django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', '{self.django_proje_adi}.settings')
        django.setup()

        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group

        User = get_user_model()
        username = os.environ.get('DJANGO_ADMIN_USERNAME', 'admin')
        email    = os.environ.get('DJANGO_ADMIN_EMAIL',    'admin@arasedas.com')
        password = os.environ.get('DJANGO_ADMIN_PASSWORD', 'sifre1234')

        u, created = User.objects.get_or_create(
            username=username,
            defaults={{'email': email, 'is_active': True, 'is_staff': True, 'is_superuser': True}}
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
        """
        )

    # 8) Dev server (opsiyonel)
    def hizli_test(self, include_shebang: bool = False) -> str:
        shebang = "#!/usr/bin/env bash\n" if include_shebang else ""
        return shebang + dedent(
            f"""\
        cd /opt/{self.github_repo_adi}
        source .venv/bin/activate
        cd /opt/{self.github_repo_adi}
        python manage.py runserver 0.0.0.0:8000
        # http://{self.ip}:8000
        """
        )

    # 9) Gunicorn + systemd (manage.py repo kökünde)
    def gunicorn_kurulumu(self, include_shebang: bool = False) -> str:
        shebang = "#!/usr/bin/env bash\n" if include_shebang else ""
        return shebang + dedent(
            f"""\
        cd /opt/{self.github_repo_adi}
        source .venv/bin/activate

        cat > /etc/systemd/system/gunicorn_v1.service <<'EOF'
        [Unit]
        Description=Gunicorn for {self.github_repo_adi}
        After=network-online.target
        Wants=network-online.target

        [Service]
        User=root
        Group=www-data
        WorkingDirectory=/opt/{self.github_repo_adi}
        Environment="PATH=/opt/{self.github_repo_adi}/.venv/bin"
        Environment="DJANGO_SETTINGS_MODULE={self.django_proje_adi}.settings"
        ExecStart=/opt/{self.github_repo_adi}/.venv/bin/gunicorn --workers 3 --timeout 120 --umask 007 --bind unix:/run/gunicorn_v1/gunicorn.sock {self.django_proje_adi}.wsgi:application
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
        """
        )

    # 10) Nginx (conf.d)
    def nginx_kurulumu(self, include_shebang: bool = False) -> str:
        shebang = "#!/usr/bin/env bash\n" if include_shebang else ""
        return shebang + dedent(
            f"""\
        if ! grep -q "include /etc/nginx/conf.d/*.conf;" /etc/nginx/nginx.conf; then
          sudo sed -i '/http \\{{/a \\    include /etc/nginx/conf.d/*.conf;' /etc/nginx/nginx.conf
        fi

        sudo tee /etc/nginx/conf.d/{self.github_repo_adi}.conf > /dev/null <<'NGINX'
        server {{
            listen 80 default_server;
            listen [::]:80 default_server;
            server_name _;

            client_max_body_size 20m;

            # STATIC_ROOT: /opt/{self.github_repo_adi}/staticfiles/
            location /static/ {{
                alias /opt/{self.github_repo_adi}/staticfiles/;
                access_log off;
                expires 30d;
            }}

            location / {{
                proxy_http_version 1.1;
                proxy_set_header Host $host;
                proxy_set_header X-Forwarded-Host $host;
                proxy_set_header X-Forwarded-Proto $scheme;
                proxy_set_header X-Real-IP $remote_addr;
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                proxy_pass http://unix:/run/gunicorn_v1/gunicorn.sock;
            }}
        }}
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
        """
        )

    # 11) UFW
    def guvenlik_duvari(self, include_shebang: bool = False) -> str:
        shebang = "#!/usr/bin/env bash\n" if include_shebang else ""
        return shebang + dedent(
            """\
        ufw allow OpenSSH
        ufw allow 'Nginx Full'
        ufw --force enable
        ufw status
        """
        )

    # 12) Son doğrulamalar
    def dogrulama_testleri(self, include_shebang: bool = False) -> str:
        shebang = "#!/usr/bin/env bash\n" if include_shebang else ""
        return shebang + dedent(
            f"""\
        echo "== Durum Kontrolleri =="
        systemctl is-active nginx || true
        systemctl is-active gunicorn_v1 || true
        ss -ltnp | grep ':80' || true
        ls -l /run/gunicorn_v1/gunicorn.sock || true
        curl -I http://127.0.0.1 || true
        """
        )

    # Tüm akış
    def tam_skript(self, include_shebang: bool = True) -> str:
        parts = [
            self.django_kurulumu(include_shebang),  # 1
            f"\n# {self.cizgi} SSH key {self.cizgi}\n",
            self.sshkeygen_uret(False),  # 2
            f"\n# {self.cizgi} Repo {self.cizgi}\n",
            self.github_repo_klonla(False),  # 3
            f"\n# {self.cizgi} venv & paketler {self.cizgi}\n",
            self.sanalortam_python_paketleri_kurulumu(False),  # 4
            f"\n# {self.cizgi} .env {self.cizgi}\n",
            self.env_kurulumu(False),
            f"\n# {self.cizgi} PostgreSQL {self.cizgi}\n",
            self.postgre_kurulumu(False),  # 5
            f"\n# {self.cizgi} migrate/superuser/static {self.cizgi}\n",
            self.django_migrate_superuser(False),  # 7
            f"\n# {self.cizgi} Gunicorn (systemd) {self.cizgi}\n",
            self.gunicorn_kurulumu(False),  # 9
            f"\n# {self.cizgi} Nginx {self.cizgi}\n",
            self.nginx_kurulumu(False),  # 10
            f"\n# {self.cizgi} UFW {self.cizgi}\n",
            self.guvenlik_duvari(False),  # 11
            f"\n# {self.cizgi} Doğrulamalar {self.cizgi}\n",
            self.dogrulama_testleri(False),  # 12
        ]
        return "".join(parts)

    def kaydet(self, yol: str = "sunucu_ayarlari.sh", mod: str = "full") -> Path:
        content_map = {
            "full": self.tam_skript(True),
            "django": self.django_kurulumu(True),
            "ssh": self.sshkeygen_uret(True),
            "clone": self.github_repo_klonla(True),
            "venv": self.sanalortam_python_paketleri_kurulumu(True),
            "postgres": self.postgre_kurulumu(True),
            "env": self.env_kurulumu(True),
            "migrate": self.django_migrate_superuser(True),
            "serve": self.hizli_test(True),
            "gunicorn": self.gunicorn_kurulumu(True),
            "nginx": self.nginx_kurulumu(True),
            "ufw": self.guvenlik_duvari(True),
            "check": self.dogrulama_testleri(True),
        }
        p = Path(yol)
        p.write_text(content_map[mod], encoding="utf-8")
        try:
            p.chmod(0o755)
        except Exception:
            pass
        return p


if __name__ == "__main__":
    sa = SunucuAyar(
        ip="157.230.16.7",
        github_hesap_adi="mpiriyilmaz",
        github_repo_adi="aras_test_v12",
        db_adi="arasomtest",
        db_kullanici_adi="postgres",
        db_sifre="oms123456",
        django_proje_adi="core",
    )
    print(sa.tam_skript())
    sa.kaydet("sunucu_ayarlari.sh", "full")
