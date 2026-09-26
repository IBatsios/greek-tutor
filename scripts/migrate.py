"""Apply pending SQL migrations in order, then re-apply the seeds.

    python scripts/migrate.py              # migrate + seed (what the Docker `migrate` service runs)
    python scripts/migrate.py --no-seed    # migrations only
    python scripts/migrate.py --baseline   # record every migration as applied WITHOUT running it

Reads DATABASE_URL from the environment. Applied migrations are recorded in
`schema_migrations`, so re-running is a no-op apart from the seeds, which are
written to be idempotent (ON CONFLICT ...).

--baseline exists for a database that was built by hand with psql before this
script existed: it marks 001..NNN as done so they are not re-run on top of
existing tables. The script refuses to guess — if it finds the app's tables but
no migration history, it stops and tells you to baseline.

Each migration file manages its own BEGIN/COMMIT; the history row is written
right after the file succeeds. A pg advisory lock stops two migrators racing.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

import asyncpg

ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS = ROOT / "migrations"
SEEDS = [ROOT / "seed" / "lessons_a1.sql", ROOT / "seed" / "harada.sql"]
LOCK_KEY = 0x6772_6B74  # "grkt" — arbitrary, just unique to this app

_HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename    TEXT PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""


def _migration_files() -> list[Path]:
    return sorted(p for p in MIGRATIONS.glob("*.sql") if p.name[:3].isdigit())


async def _run(conn: asyncpg.Connection, baseline: bool, seed: bool) -> None:
    await conn.execute("CREATE EXTENSION IF NOT EXISTS citext")
    await conn.execute(_HISTORY_DDL)
    applied = {r["filename"] for r in await conn.fetch("SELECT filename FROM schema_migrations")}
    has_app_tables = await conn.fetchval("SELECT to_regclass('public.users') IS NOT NULL")

    if not applied and has_app_tables and not baseline:
        sys.exit(
            "migrate: found existing tables but no migration history.\n"
            "  This database was set up by hand. If every file in migrations/ has already\n"
            "  been applied, run once with --baseline, then run normally."
        )

    pending = [p for p in _migration_files() if p.name not in applied]
    for path in pending:
        if baseline:
            print(f"baseline  {path.name}")
        else:
            print(f"apply     {path.name}")
            await conn.execute(path.read_text(encoding="utf-8"))
        await conn.execute("INSERT INTO schema_migrations (filename) VALUES ($1)", path.name)
    if not pending:
        print("migrations up to date")

    if seed and not baseline:
        for path in SEEDS:
            print(f"seed      {path.name}")
            await conn.execute(path.read_text(encoding="utf-8"))


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--baseline", action="store_true",
                        help="record migrations as applied without running them")
    parser.add_argument("--no-seed", action="store_true", help="skip the seed files")
    args = parser.parse_args()

    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("migrate: DATABASE_URL is not set")

    conn = await asyncpg.connect(url)
    try:
        await conn.execute("SELECT pg_advisory_lock($1)", LOCK_KEY)
        try:
            await _run(conn, baseline=args.baseline, seed=not args.no_seed)
        finally:
            await conn.execute("SELECT pg_advisory_unlock($1)", LOCK_KEY)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
