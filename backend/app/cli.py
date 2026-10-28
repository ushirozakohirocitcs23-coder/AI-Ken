"""AI-KEN management commands.

  python -m app.cli init                 create tables and seed the knowledge base
  python -m app.cli create-admin         create an administrator (interactive or with flags)
  python -m app.cli reindex              re-embed all documents, forms and dictionary entries
  python -m app.cli export-schema        write the PostgreSQL DDL to ../docs/schema.sql
"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

from sqlalchemy import func, select


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    ca = sub.add_parser("create-admin")
    ca.add_argument("--email")
    ca.add_argument("--name", default="AI-KEN Administrator")
    ca.add_argument("--password", help="omit to be prompted securely")
    sub.add_parser("reindex")
    sub.add_parser("export-schema")
    args = parser.parse_args(argv)

    from .database import Base, SessionLocal, engine
    from .models import User
    from .security import PASSWORD_RULE, hash_password, password_ok
    from .services.audit import audit
    from .services.knowledge import reprocess_all, seed

    if args.cmd == "export-schema":
        from sqlalchemy.dialects import postgresql
        from sqlalchemy.schema import CreateIndex, CreateTable
        dialect = postgresql.dialect()
        out = ["-- AI-KEN database schema (PostgreSQL). Generated from app/models.py.\n"]
        for table in Base.metadata.sorted_tables:
            out.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ";\n")
            for idx in table.indexes:
                out.append(str(CreateIndex(idx).compile(dialect=dialect)).strip() + ";")
            out.append("")
        path = Path(__file__).resolve().parents[2] / "docs" / "schema.sql"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(out), encoding="utf-8")
        print(f"Wrote {path}")
        return 0

    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if args.cmd == "init":
            print("Seeded:", seed(db))
            return 0
        if args.cmd == "reindex":
            seed(db)
            print("Reindexed:", reprocess_all(db))
            return 0
        if args.cmd == "create-admin":
            email = (args.email or input("Admin email: ")).strip().lower()
            password = args.password or getpass.getpass("Admin password: ")
            if not args.password and getpass.getpass("Confirm password: ") != password:
                print("Passwords do not match.")
                return 1
            if not password_ok(password):
                print(PASSWORD_RULE)
                return 1
            user = db.scalar(select(User).where(func.lower(User.email) == email))
            if user:
                user.role, user.status = "admin", "active"
                user.password_hash = hash_password(password)
                print(f"Existing account {email} promoted to administrator.")
            else:
                user = User(full_name=args.name, email=email, password_hash=hash_password(password), role="admin")
                db.add(user)
                print(f"Administrator {email} created.")
            db.commit()
            audit(db, "system.cli_admin_created", None, f"user:{user.id}", {"email": email})
            return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
