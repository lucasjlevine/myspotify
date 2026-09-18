"""SQLite persistence for Spotify tokens and accumulated play history."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DATA_DIR / "plays.db"


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tokens (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                access_token TEXT NOT NULL,
                refresh_token TEXT NOT NULL,
                expires_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS plays (
                played_at TEXT NOT NULL,
                track_id TEXT NOT NULL,
                track_name TEXT NOT NULL,
                artist_names TEXT NOT NULL,
                album_name TEXT NOT NULL,
                duration_ms INTEGER NOT NULL,
                context_uri TEXT,
                collected_at TEXT NOT NULL,
                PRIMARY KEY (played_at, track_id)
            );

            CREATE INDEX IF NOT EXISTS idx_plays_played_at ON plays (played_at DESC);
            """
        )


def save_tokens(access_token: str, refresh_token: str, expires_at: float) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO tokens (id, access_token, refresh_token, expires_at)
            VALUES (1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                access_token = excluded.access_token,
                refresh_token = excluded.refresh_token,
                expires_at = excluded.expires_at
            """,
            (access_token, refresh_token, expires_at),
        )


def get_tokens() -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute("SELECT * FROM tokens WHERE id = 1").fetchone()


def upsert_plays(plays: list[dict]) -> tuple[int, int]:
    """Insert plays; return (inserted, skipped)."""
    if not plays:
        return 0, 0

    inserted = 0
    skipped = 0
    collected_at = datetime.now(timezone.utc).isoformat()

    with connect() as conn:
        for play in plays:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO plays (
                    played_at, track_id, track_name, artist_names,
                    album_name, duration_ms, context_uri, collected_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    play["played_at"],
                    play["track_id"],
                    play["track_name"],
                    play["artist_names"],
                    play["album_name"],
                    play["duration_ms"],
                    play.get("context_uri"),
                    collected_at,
                ),
            )
            if cursor.rowcount:
                inserted += 1
            else:
                skipped += 1

    return inserted, skipped


def list_plays(limit: int = 50) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT played_at, track_id, track_name, artist_names,
                   album_name, duration_ms, context_uri, collected_at
            FROM plays
            ORDER BY played_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
