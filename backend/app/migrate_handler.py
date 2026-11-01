"""Run database migrations (and optionally seed reference data).

Locally:   python -m app.migrate_handler [--seed]
On AWS:    invoke the MigrationFunction Lambda with {"seed": true|false}
           (it runs inside the VPC, so RDS never needs to be publicly reachable).
"""
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

BACKEND_DIR = Path(__file__).resolve().parent.parent


def run_migrations() -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    command.upgrade(cfg, "head")


def handler(event, _context):
    run_migrations()
    seeded = False
    if (event or {}).get("seed"):
        from app.seed import seed

        seed(include_demo_users=bool(event.get("demo_users", False)))
        seeded = True
    return {"migrated": True, "seeded": seeded}


if __name__ == "__main__":
    run_migrations()
    if "--seed" in sys.argv:
        from app.seed import seed

        seed(include_demo_users=True)
    print("Database is up to date.")
