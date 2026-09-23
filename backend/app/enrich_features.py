"""CLI: enrich track genres (Spotify) + audio features (ReccoBeats).

Usage (from backend/):
    uv run python -m app.enrich_features
    uv run python -m app.enrich_features --batches 20
"""

from __future__ import annotations

import argparse
import time

from app.database import init_db, session_scope
from app import repositories
from app.spotify import catalog


def enrich_batch(track_ids: list[str]) -> int:
    if not track_ids:
        return 0

    artist_map = catalog.fetch_track_artist_ids(track_ids)
    all_artist_ids = [aid for aids in artist_map.values() for aid in aids]
    genre_map = catalog.fetch_artist_genres(all_artist_ids)
    features_map = catalog.fetch_audio_features(track_ids)

    rows: list[dict] = []
    for tid in track_ids:
        artist_ids = artist_map.get(tid) or []
        genres: list[str] = []
        for aid in artist_ids:
            genres.extend(genre_map.get(aid) or [])
        # Preserve order, unique
        genres = list(dict.fromkeys(genres))
        feats = features_map.get(tid) or {}
        row: dict = {
            "track_id": tid,
            "artist_ids": ",".join(artist_ids) if artist_ids else None,
            "genres": ", ".join(genres) if genres else None,
            "enriched_at": catalog.now_iso(),
        }
        for key in catalog.AUDIO_KEYS:
            row[key] = feats.get(key)
        rows.append(row)

    with session_scope() as session:
        return repositories.upsert_track_meta(session, rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich genres + audio features")
    parser.add_argument("--batches", type=int, default=20)
    parser.add_argument("--limit", type=int, default=40, help="Tracks per batch")
    parser.add_argument("--sleep", type=float, default=0.2)
    args = parser.parse_args()

    init_db()
    total = 0
    for i in range(args.batches):
        with session_scope() as session:
            missing = repositories.track_ids_missing_meta(session, limit=args.limit)
            coverage = repositories.meta_coverage(session)
        if not missing:
            print(f"Done — features {coverage['with_features']}/{coverage['unique_tracks']}")
            break
        try:
            written = enrich_batch(missing)
        except Exception as exc:  # noqa: BLE001 — keep batching through transient API errors
            print(f"[{i + 1}/{args.batches}] batch failed: {exc}")
            time.sleep(max(args.sleep, 1.0))
            continue
        total += written
        with session_scope() as session:
            coverage = repositories.meta_coverage(session)
        print(
            f"[{i + 1}/{args.batches}] enriched={written} "
            f"features={coverage['with_features']}/{coverage['unique_tracks']} "
            f"genres={coverage['with_genres']}"
        )
        if args.sleep > 0:
            time.sleep(args.sleep)
    print(f"Total enriched rows={total}")


if __name__ == "__main__":
    main()
