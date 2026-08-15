import os
from pathlib import Path

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://devops@localhost:5432/devops_lab")
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "db" / "migrations"


def main():
    engine = create_engine(DATABASE_URL, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )

        applied = {
            row[0]
            for row in conn.execute(text("SELECT version FROM schema_migrations")).all()
        }

        migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        for migration_file in migration_files:
            version = migration_file.name
            if version in applied:
                continue
            sql = migration_file.read_text(encoding="utf-8")
            conn.execute(text(sql))
            conn.execute(
                text("INSERT INTO schema_migrations(version) VALUES (:version)"),
                {"version": version},
            )
            print(f"Applied {version}")


if __name__ == "__main__":
    main()
