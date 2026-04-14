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


def is_postgresql_url(url: str) -> bool:
    url_l = (url or "").strip().lower()
    return url_l.startswith("postgres:") or url_l.startswith("postgresql:") or url_l.startswith("postgresql+")

def database_engine_kwargs(db_url: str) -> dict[str, object]:
    kwargs: dict[str, object] = {"future": True}
    if is_sqlite_url(db_url):
        kwargs["connect_args"] = {"timeout": 30}
        return kwargs

    kwargs["pool_pre_ping"] = True
    kwargs["pool_recycle"] = 3600
    return kwargs

def database_url(default_sqlite_path: Path) -> str:
    explicit = (os.environ.get("DATABASE_URL") or "").strip()
    if explicit:
        return explicit

    backend = (os.environ.get("DB_BACKEND") or "sqlite").strip().lower()
    if backend in {"sqlite", "sqlite3"}:
        return f"sqlite:///{default_sqlite_path}"

    if backend in {"postgres", "postgresql"}:
        host = (os.environ.get("POSTGRES_HOST") or "").strip()
        if not host:
            raise RuntimeError("POSTGRES_HOST is required when DB_BACKEND=postgresql")

        port_raw = (os.environ.get("POSTGRES_PORT") or "").strip()
        port = int(port_raw) if port_raw.isdigit() else 5432

        database = (os.environ.get("POSTGRES_DATABASE") or os.environ.get("POSTGRES_DB") or "").strip()
        if not database:
            raise RuntimeError("POSTGRES_DATABASE is required when DB_BACKEND=postgresql")

        username = (os.environ.get("POSTGRES_USER") or "").strip() or None
        password = os.environ.get("POSTGRES_PASSWORD")

        driver = (os.environ.get("POSTGRES_DRIVER") or "psycopg2").strip().lower()
        dialect = f"postgresql+{driver}" if driver else "postgresql"

        return str(
            URL.create(
                dialect,
                username=username,
                password=password,
                host=host,
                port=port,
                database=database,
            )
        )

    raise RuntimeError(f"Unsupported DB_BACKEND: {backend}")
