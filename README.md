# Guarde

Веб‑приложение на Flask для сайта и обработки заявок техподдержки. Хранение данных — SQLite (`site.db`), загружаемые файлы — `static/uploads/`.

## Локальный запуск (для проверки)

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

Открыть: `http://127.0.0.1:5000/`

## Развёртывание на SpaceWeb

На виртуальном хостинге SpaceWeb (тарифы под PHP) Python/WSGI обычно недоступен. Для этого проекта нужен VPS/VDS на SpaceWeb.

Ниже — схема “VPS + Nginx + Gunicorn + systemd”.

### 1) Подготовка VPS

1. Закажите VPS/VDS в SpaceWeb и установите Ubuntu 22.04/24.04.
2. В панели домена добавьте DNS запись:
   - `A` → ваш домен → IP вашего VPS.
3. Подключитесь по SSH:

```bash
ssh root@YOUR_SERVER_IP
```

Обновите систему и установите зависимости:

```bash
apt update && apt -y upgrade
apt -y install python3 python3-venv python3-pip nginx sqlite3 git
```

### 2) Размещение проекта

Создайте отдельного пользователя и каталог приложения:

```bash
adduser --disabled-password --gecos "" guarde
mkdir -p /var/www/guarde
chown -R guarde:guarde /var/www/guarde
```

Склонируйте репозиторий (или загрузите файлы любым удобным способом) и установите зависимости:

```bash
sudo -u guarde bash -lc "cd /var/www/guarde && git clone https://github.com/majormguarde-bit/guarde.git ."
sudo -u guarde bash -lc "cd /var/www/guarde && python3 -m venv .venv"
sudo -u guarde bash -lc "cd /var/www/guarde && . .venv/bin/activate && pip install -r requirements.txt gunicorn"
```

### 3) Переменные окружения (секреты)

Создайте файл окружения:

```bash
nano /etc/guarde.env
```

Пример содержимого:

```ini
FLASK_SECRET_KEY=REPLACE_WITH_LONG_RANDOM_SECRET
MAX_UPLOAD_MB=512

# Cloudflare Turnstile (необязательно)
# TURNSTILE_SITE_KEY=...
# TURNSTILE_SECRET_KEY=...
```

Права на файл:

```bash
chmod 600 /etc/guarde.env
```

### Хранилище файлов (локально или S3-совместимое)

По умолчанию приложение сохраняет загружаемые файлы на диск сервера в `static/uploads/`.
Чтобы не расходовать дисковое пространство хостинга, можно включить хранение в облаке (S3-совместимый Object Storage).

#### Режим 1: локальное хранение (по умолчанию)

Ничего настраивать не нужно:
- `STORAGE_BACKEND` не задан или равен `local`.
- Файлы сохраняются в `/var/www/guarde/static/uploads/` (внутри проекта).

#### Режим 2: S3-совместимое хранилище (рекомендуется)

Подходит для:
- Yandex Cloud Object Storage
- VK Cloud / Selectel / S3-compatible провайдеров
- MinIO (для своей инфраструктуры)

1) Включите backend:

```ini
STORAGE_BACKEND=s3
```

2) Задайте параметры подключения:

```ini
S3_BUCKET=your-bucket-name
S3_PREFIX=guarde
S3_ENDPOINT_URL=https://storage.yandexcloud.net
S3_REGION=ru-central1
S3_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID
S3_SECRET_ACCESS_KEY=YOUR_SECRET_ACCESS_KEY
```

Пояснения:
- `S3_BUCKET` — имя бакета (обязательно).
- `S3_PREFIX` — префикс “папки” в бакете (необязательно). Если задан, файлы будут храниться внутри `S3_PREFIX/...`.
- `S3_ENDPOINT_URL` — endpoint провайдера (для Yandex Cloud: `https://storage.yandexcloud.net`).
- `S3_REGION` — регион (для Yandex Cloud чаще всего `ru-central1`).
- `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` — ключи доступа к бакету.

Поведение в S3 режиме:
- Все новые загрузки пишутся в бакет.
- Скачивание/просмотр файлов идёт через временную presigned-ссылку (редирект), срок действия 15 минут.

Важно:
- Рекомендуется держать бакет приватным, доступ выдаётся только presigned-ссылками.
- Если у вас уже есть файлы в `static/uploads/`, их нужно перенести в бакет (см. ниже).

#### Перенос существующих файлов в S3

Если раньше использовалось локальное хранение, перенесите содержимое `static/uploads/` в бакет с сохранением путей.

Пример через AWS CLI (работает и для S3-compatible при указании endpoint):

```bash
aws s3 sync /var/www/guarde/static/uploads "s3://your-bucket-name/guarde" --endpoint-url https://storage.yandexcloud.net
```

После переноса:
- включите `STORAGE_BACKEND=s3`,
- перезапустите сервис (`systemctl restart guarde`).

Примечание про Яндекс.Диск:
- Яндекс.Диск не является S3-совместимым Object Storage. Для него нужна отдельная реализация (OAuth/WebDAV/REST) и другая схема выдачи файлов.

### 4) systemd (Gunicorn)

Создайте unit:

```bash
nano /etc/systemd/system/guarde.service
```

Содержимое:

```ini
[Unit]
Description=Guarde (Flask via Gunicorn)
After=network.target

[Service]
User=guarde
Group=guarde
WorkingDirectory=/var/www/guarde
EnvironmentFile=/etc/guarde.env
ExecStart=/var/www/guarde/.venv/bin/gunicorn -w 2 -b 127.0.0.1:8000 app:app
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
```

Запуск:

```bash
systemctl daemon-reload
systemctl enable --now guarde
systemctl status guarde --no-pager
```

### 5) Nginx (прокси на Gunicorn)

Создайте конфиг сайта:

```bash
nano /etc/nginx/sites-available/guarde
```

Пример:

```nginx
server {
  listen 80;
  server_name example.com www.example.com;

  client_max_body_size 512m;

  location /static/ {
    alias /var/www/guarde/static/;
    expires 7d;
    add_header Cache-Control "public";
  }

  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

Важно: не добавляйте отдельный `location /uploads/` через `alias`.
Файлы выдаются приложением (в том числе с проверками доступа для некоторых категорий), а при `STORAGE_BACKEND=s3` `/uploads/...` будет перенаправлять на presigned-ссылки.

Активируйте сайт:

```bash
ln -s /etc/nginx/sites-available/guarde /etc/nginx/sites-enabled/guarde
nginx -t
systemctl reload nginx
```

### 6) HTTPS (Let’s Encrypt)

Если на VPS доступен 80 порт и DNS уже указывает на сервер:

```bash
apt -y install certbot python3-certbot-nginx
certbot --nginx -d example.com -d www.example.com
```

### 7) Первичная настройка админки

1. Откройте сайт в браузере.
2. Если администратор ещё не создан — откройте:
   - `https://example.com/setup`
3. Создайте логин/пароль (пароль минимум 8 символов).
4. Админка:
   - `https://example.com/admin`

В “Тексты” можно редактировать блоки сайта, включая текст модального окна согласия:
- `consent_title`
- `consent_body`

## Обновление приложения

```bash
sudo -u guarde bash -lc "cd /var/www/guarde && git pull"
sudo -u guarde bash -lc "cd /var/www/guarde && . .venv/bin/activate && pip install -r requirements.txt gunicorn"
systemctl restart guarde
```

## Бэкапы

Сохраняйте минимум:
- `/var/www/guarde/site.db` (SQLite база)
- Если `STORAGE_BACKEND=local`: `/var/www/guarde/static/uploads/` (загруженные файлы)
- Если `STORAGE_BACKEND=s3`: делайте бэкапы/версии на стороне Object Storage (бакет), локальная папка с файлами не используется
