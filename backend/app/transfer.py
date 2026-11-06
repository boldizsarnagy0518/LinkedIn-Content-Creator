"""Copy the local ContentOps workspace (SQLite) into the production database once.

Run from backend/ after the Supabase storage schema exists:
  uv run python -m app.transfer --target-env ../deploy/backend.env.local --dry-run
  uv run python -m app.transfer --target-env ../deploy/backend.env.local

The connection string is read from the env file and never printed.
"""

import argparse
from pathlib import Path

from dotenv import dotenv_values

from app.config import DEFAULT_CONTENTOPS_DB_PATH
from app.content.repository import ConflictError, PostgresContentRepository, SQLiteContentRepository
from app.content.transfer import count_rows, transfer_workspace


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, default=DEFAULT_CONTENTOPS_DB_PATH, help="Local SQLite database.")
    parser.add_argument("--target-env", type=Path, required=True, help="Env file with CONTENTOPS_DATABASE_URL.")
    parser.add_argument("--dry-run", action="store_true", help="Only count the rows that would be copied.")
    args = parser.parse_args()

    if not args.source.is_file():
        print(f"FAIL: local database not found: {args.source}")
        return 1
    target_url = dict(dotenv_values(args.target_env, interpolate=False)).get("CONTENTOPS_DATABASE_URL") or ""
    if not target_url.startswith(("postgresql://", "postgres://")) or "REPLACE" in target_url:
        print("FAIL: the env file has no real PostgreSQL CONTENTOPS_DATABASE_URL.")
        return 1

    source = SQLiteContentRepository(args.source)
    if args.dry_run:
        for table, total in count_rows(source).items():
            print(f"{table}: {total}")
        print("Dry run: nothing was copied and the target was not contacted.")
        return 0

    try:
        copied = transfer_workspace(source, PostgresContentRepository(target_url))
    except ConflictError as error:
        print(f"FAIL: {error}")
        return 1
    for table, total in copied.items():
        print(f"{table}: {total}")
    print("PASS: the local workspace was copied. Keep the local database as a backup.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
