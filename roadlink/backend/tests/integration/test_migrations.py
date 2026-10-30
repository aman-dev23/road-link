"""Verify Alembic can build the complete schema in a fresh SQLite database."""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from sqlalchemy.engine import URL


def test_sqlite_migrations_create_complete_schema(tmp_path: Path):
    backend_dir = Path(__file__).resolve().parents[2]
    database_path = tmp_path / "roadlink_migrations.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = URL.create(
        "sqlite+aiosqlite",
        database=str(database_path),
    ).render_as_string(hide_password=False)

    def run_alembic(*arguments: str) -> None:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "-c",
                "alembic.ini",
                *arguments,
            ],
            cwd=backend_dir,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    run_alembic("upgrade", "head")

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {
            "users",
            "user_profiles",
            "user_skills",
            "refresh_tokens",
            "user_locations",
            "sos_requests",
            "chat_messages",
            "notification_events",
            "alembic_version",
        } <= tables
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone() == ("003",)

    run_alembic("downgrade", "base")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert not {
            "users",
            "user_profiles",
            "user_skills",
            "refresh_tokens",
            "user_locations",
            "sos_requests",
            "chat_messages",
            "notification_events",
        } & tables

    run_alembic("upgrade", "head")
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone() == ("003",)
