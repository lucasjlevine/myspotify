"""Load Spotify Extended Streaming History into the local plays database.

Usage (from backend/):
    uv run python -m app.import_history
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app import repositories
from app.config import DATA_DIR
from app.database import init_db, session_scope
from app.spotify.export_history import DEFAULT_EXPORT_DIR, load_plays_from_export


def import_history(
    export_dir: Path | None = None,
    *,
    min_ms_played: int = 0,
) -> dict:
    init_db()
    directory = export_dir or DEFAULT_EXPORT_DIR
    plays = load_plays_from_export(directory, min_ms_played=min_ms_played)

    with session_scope() as session:
        before = repositories.count_plays(session)
        inserted, skipped = repositories.upsert_plays(session, plays)
        after = before + inserted

    return {
        "export_dir": str(directory),
        "parsed": len(plays),
        "inserted": inserted,
        "skipped": skipped,
        "plays_before": before,
        "plays_after": after,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import Spotify Extended Streaming History into plays.db"
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=DEFAULT_EXPORT_DIR,
        help=f"Export directory (default: {DEFAULT_EXPORT_DIR})",
    )
    parser.add_argument(
        "--min-ms",
        type=int,
        default=0,
        help="Skip plays shorter than this many milliseconds (default: 0)",
    )
    args = parser.parse_args()

    summary = import_history(args.dir, min_ms_played=args.min_ms)
    print(
        f"Parsed {summary['parsed']} track plays from {summary['export_dir']}\n"
        f"Inserted {summary['inserted']}, skipped {summary['skipped']} duplicates\n"
        f"plays.db: {summary['plays_before']} -> {summary['plays_after']}"
    )
    print(f"Database: {DATA_DIR / 'plays.db'}")


if __name__ == "__main__":
    main()
