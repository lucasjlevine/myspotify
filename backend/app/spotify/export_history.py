"""Import Spotify Extended Streaming History privacy export into plays."""

from __future__ import annotations

import json
from pathlib import Path

from app.config import DATA_DIR

TRACK_URI_PREFIX = "spotify:track:"
DEFAULT_EXPORT_DIR = DATA_DIR / "Spotify Extended Streaming History"


def track_id_from_uri(uri: str | None) -> str | None:
    if not uri or not uri.startswith(TRACK_URI_PREFIX):
        return None
    track_id = uri.removeprefix(TRACK_URI_PREFIX).strip()
    return track_id or None


def normalize_export_row(row: dict, *, min_ms_played: int = 0) -> dict | None:
    """Map one Extended Streaming History row to a Play dict."""
    track_id = track_id_from_uri(row.get("spotify_track_uri"))
    played_at = row.get("ts")
    track_name = row.get("master_metadata_track_name")
    if not track_id or not played_at or not track_name:
        return None

    ms_played = int(row.get("ms_played") or 0)
    if ms_played < min_ms_played:
        return None

    return {
        "played_at": played_at,
        "track_id": track_id,
        "track_name": track_name,
        "artist_names": row.get("master_metadata_album_artist_name") or "",
        "album_name": row.get("master_metadata_album_album_name") or "",
        # Export exposes listen duration, not official track length.
        "duration_ms": ms_played,
        "context_uri": None,
    }


def iter_export_files(export_dir: Path) -> list[Path]:
    return sorted(export_dir.glob("Streaming_History_*.json"))


def load_plays_from_export(
    export_dir: Path | None = None,
    *,
    min_ms_played: int = 0,
) -> list[dict]:
    directory = export_dir or DEFAULT_EXPORT_DIR
    if not directory.is_dir():
        raise FileNotFoundError(f"Export directory not found: {directory}")

    plays: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for path in iter_export_files(directory):
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            raise ValueError(f"Expected a JSON array in {path}")

        for row in rows:
            play = normalize_export_row(row, min_ms_played=min_ms_played)
            if play is None:
                continue
            key = (play["played_at"], play["track_id"])
            if key in seen:
                continue
            seen.add(key)
            plays.append(play)

    return plays
