"""CLI: backfill album images for tracks missing art (most-played first).

Usage (from backend/):
    uv run python -m app.enrich_images
    uv run python -m app.enrich_images --batches 40
"""

from __future__ import annotations

import argparse
import time

from app.database import init_db, session_scope
from app import repositories
from app.spotify import tracks as spotify_tracks


def enrich(*, batches: int, limit: int, sleep_s: float) -> None:
    init_db()
    total_fetched = 0
    total_updated = 0

    for i in range(batches):
        with session_scope() as session:
            missing = repositories.track_ids_missing_images(
                session, limit=limit, prioritize="plays"
            )
            coverage = repositories.image_coverage(session)
        if not missing:
            print(f"Done — coverage {coverage['with_image']}/{coverage['unique_tracks']}")
            break

        mapping = spotify_tracks.fetch_track_images(missing)
        with session_scope() as session:
            updated = repositories.apply_album_images(session, mapping)
            coverage = repositories.image_coverage(session)

        total_fetched += len(mapping)
        total_updated += updated
        print(
            f"[{i + 1}/{batches}] fetched={len(mapping)} updated={updated} "
            f"coverage={coverage['with_image']}/{coverage['unique_tracks']} "
            f"(missing {coverage['missing']})"
        )
        if sleep_s > 0 and i + 1 < batches:
            time.sleep(sleep_s)

    print(f"Total fetched={total_fetched} updated={total_updated}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill album artwork")
    parser.add_argument("--batches", type=int, default=40, help="API rounds (50 ids each)")
    parser.add_argument("--limit", type=int, default=50, help="Ids per Spotify request")
    parser.add_argument("--sleep", type=float, default=0.15, help="Seconds between batches")
    args = parser.parse_args()
    enrich(batches=args.batches, limit=min(args.limit, 50), sleep_s=args.sleep)


if __name__ == "__main__":
    main()
