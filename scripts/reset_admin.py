from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="", help="Path to SQLite DB file (site.db)")
    parser.add_argument("--db-url", default="", help="SQLAlchemy database URL (overrides env/config)")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admin123")
    args = parser.parse_args()

    project_dir = Path(__file__).resolve().parents[1]
    default_db_path = project_dir / "site.db"
    db_path: Path | None = None

    sys.path.insert(0, str(project_dir))
    from db_config import database_url, is_sqlite_url
    from models import AdminUser

    db_url = (args.db_url or "").strip()
    if not db_url:
        if args.db:
            db_path = Path(args.db).expanduser().resolve()
            db_url = f"sqlite:///{db_path}"
        else:
            db_url = database_url(default_db_path)
            if is_sqlite_url(db_url):
                db_path = default_db_path

    engine_kwargs: dict[str, object] = {"future": True}
    if is_sqlite_url(db_url):
        engine_kwargs["connect_args"] = {"timeout": 30}
        if db_path is not None and not db_path.exists():
            raise SystemExit(f"DB not found: {db_path}")
    else:
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_recycle"] = 3600

    engine = create_engine(db_url, **engine_kwargs)

    new_username = (args.username or "").strip()
    new_password = args.password or ""
    if not new_username:
        raise SystemExit("username is empty")
    if len(new_password) < 8:
        raise SystemExit("password must be at least 8 characters")

    password_hash = generate_password_hash(new_password)

    with Session(engine) as session:
        user = session.scalar(
            select(AdminUser).where(func.lower(AdminUser.username) == new_username.lower())
        )
        if user is None:
            user = session.scalar(select(AdminUser).order_by(AdminUser.id.asc()).limit(1))

        action = "updated"
        if user is None:
            user = AdminUser(username=new_username, password_hash=password_hash)
            session.add(user)
            action = "created"
        else:
            user.username = new_username
            user.password_hash = password_hash

        session.commit()

    safe_db_url = make_url(db_url).render_as_string(hide_password=True)
    print(
        f"Admin credentials {action}. username={new_username} password={new_password} db={safe_db_url}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
