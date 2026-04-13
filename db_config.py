from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.engine import URL


def _strip_quotes(value: str) -> str:
    v = (value or "").strip()
    if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
        return v[1:-1]
    return v


def _load_env_file(path: Path) -> None:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in raw.splitlines():
        s = (line or "").strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            continue
        key, value = s.split("=", 1)
        key = (key or "").strip()
        if not key:
            continue
        if key in os.environ:
            continue
        os.environ[key] = _strip_quotes(value)


_load_env_file(Path(__file__).resolve().parent / ".env")


def is_sqlite_url(url: str) -> bool:
    return (url or "").strip().lower().startswith("sqlite:")


def database_url(default_sqlite_path: Path) -> str:
    explicit = (os.environ.get("DATABASE_URL") or "").strip()
    if explicit:
        return explicit

    backend = (os.environ.get("DB_BACKEND") or "sqlite").strip().lower()
    if backend in {"sqlite", "sqlite3"}:
        return f"sqlite:///{default_sqlite_path}"

    if backend in {"mysql", "mariadb"}:
        host = (os.environ.get("MYSQL_HOST") or "").strip()
        if not host:
            raise RuntimeError("MYSQL_HOST is required when DB_BACKEND=mysql")

        port_raw = (os.environ.get("MYSQL_PORT") or "").strip()
        port = int(port_raw) if port_raw.isdigit() else 3306

        database = (os.environ.get("MYSQL_DATABASE") or os.environ.get("MYSQL_DB") or "").strip()
        if not database:
            raise RuntimeError("MYSQL_DATABASE is required when DB_BACKEND=mysql")

        username = (os.environ.get("MYSQL_USER") or "").strip() or None
        password = os.environ.get("MYSQL_PASSWORD")

        driver = (os.environ.get("MYSQL_DRIVER") or "pymysql").strip().lower()
        dialect = driver if driver.startswith("mysql") else f"mysql+{driver}"

        charset = (os.environ.get("MYSQL_CHARSET") or "utf8mb4").strip() or "utf8mb4"

        return str(
            URL.create(
                dialect,
                username=username,
                password=password,
                host=host,
                port=port,
                database=database,
                query={"charset": charset},
            )
        )

    raise RuntimeError(f"Unsupported DB_BACKEND: {backend}")
