"""Track catalog enrichment: Spotify genres + ReccoBeats audio features.

Spotify's /audio-features returns 403 for many apps (deprecated). ReccoBeats
exposes compatible feature vectors keyed by Spotify track id.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import requests
from fastapi import HTTPException

from app.spotify.auth import get_access_token

logger = logging.getLogger(__name__)

TRACKS_URL = "https://api.spotify.com/v1/tracks"
ARTISTS_URL = "https://api.spotify.com/v1/artists"
RECCOBEATS_FEATURES_URL = "https://api.reccobeats.com/v1/audio-features"

AUDIO_KEYS = (
    "acousticness",
    "danceability",
    "energy",
    "instrumentalness",
    "liveness",
    "loudness",
    "speechiness",
    "tempo",
    "valence",
)


def fetch_track_artist_ids(track_ids: list[str]) -> dict[str, list[str]]:
    """track_id -> list of Spotify artist ids."""
    if not track_ids:
        return {}
    access_token = get_access_token()
    mapping: dict[str, list[str]] = {}
    for start in range(0, len(track_ids), 50):
        batch = track_ids[start : start + 50]
        response = requests.get(
            TRACKS_URL,
            params={"ids": ",".join(batch)},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json() if response.content else response.text,
            )
        for track in response.json().get("tracks") or []:
            if not track:
                continue
            tid = track.get("id")
            if not tid:
                continue
            mapping[tid] = [
                a["id"] for a in (track.get("artists") or []) if a.get("id")
            ]
    return mapping


def fetch_artist_genres(artist_ids: list[str]) -> dict[str, list[str]]:
    if not artist_ids:
        return {}
    access_token = get_access_token()
    mapping: dict[str, list[str]] = {}
    unique = list(dict.fromkeys(artist_ids))
    for start in range(0, len(unique), 50):
        batch = unique[start : start + 50]
        response = requests.get(
            ARTISTS_URL,
            params={"ids": ",".join(batch)},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json() if response.content else response.text,
            )
        for artist in response.json().get("artists") or []:
            if not artist:
                continue
            aid = artist.get("id")
            if aid:
                mapping[aid] = list(artist.get("genres") or [])
    return mapping


def fetch_audio_features(track_ids: list[str]) -> dict[str, dict[str, float]]:
    """Fetch audio features via ReccoBeats (Spotify endpoint is often 403)."""
    if not track_ids:
        return {}
    mapping: dict[str, dict[str, float]] = {}
    for start in range(0, len(track_ids), 40):
        batch = track_ids[start : start + 40]
        payload = None
        for attempt in range(3):
            try:
                response = requests.get(
                    RECCOBEATS_FEATURES_URL,
                    params={"ids": ",".join(batch)},
                    timeout=60,
                )
            except requests.exceptions.RequestException as exc:
                logger.warning(
                    "reccobeats request error (attempt %s): %s", attempt + 1, exc
                )
                time.sleep(0.8 * (attempt + 1))
                continue
            if response.status_code != 200:
                logger.warning(
                    "reccobeats features failed: %s %s",
                    response.status_code,
                    response.text[:200],
                )
                break
            payload = response.json()
            break
        if payload is None:
            continue
        items = payload.get("content") if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            continue
        # ReccoBeats returns its own UUID id but href embeds the Spotify track id.
        # Match order: request ids ↔ content order when possible.
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            href = item.get("href") or ""
            spotify_id = None
            if "/track/" in href:
                spotify_id = href.rsplit("/track/", 1)[-1].split("?")[0]
            if not spotify_id and i < len(batch):
                spotify_id = batch[i]
            if not spotify_id:
                continue
            feats: dict[str, float] = {}
            for key in AUDIO_KEYS:
                val = item.get(key)
                if val is None:
                    continue
                try:
                    feats[key] = float(val)
                except (TypeError, ValueError):
                    continue
            if feats:
                mapping[spotify_id] = feats
        time.sleep(0.08)
    return mapping


def mood_phrases_from_features(feats: dict[str, float] | None) -> list[str]:
    """Turn numeric features into searchable mood language for embeddings."""
    if not feats:
        return []
    tags: list[str] = []
    energy = feats.get("energy")
    valence = feats.get("valence")
    acoustic = feats.get("acousticness")
    dance = feats.get("danceability")
    instrumental = feats.get("instrumentalness")
    tempo = feats.get("tempo")
    speech = feats.get("speechiness")

    if acoustic is not None and acoustic >= 0.55:
        tags.extend(["acoustic", "soft", "intimate", "stripped back"])
    if energy is not None:
        if energy < 0.35:
            tags.extend(["calm", "mellow", "quiet", "low energy", "chill"])
        elif energy > 0.7:
            tags.extend(["energetic", "intense", "high energy", "workout"])
    if valence is not None:
        if valence < 0.35:
            tags.extend(["melancholy", "sad", "somber", "rainy", "heartbreak"])
        elif valence > 0.65:
            tags.extend(["happy", "bright", "uplifting", "feel good"])
    if dance is not None and dance >= 0.65:
        tags.extend(["danceable", "groove", "party"])
    if instrumental is not None and instrumental >= 0.5:
        tags.extend(["instrumental", "ambient", "focus"])
    if tempo is not None:
        if tempo < 90:
            tags.extend(["slow tempo", "ballad"])
        elif tempo > 130:
            tags.extend(["fast tempo", "upbeat"])
    if speech is not None and speech >= 0.33:
        tags.append("spoken word")
    # Seasonal / weather-ish composites for prompt search
    if (
        acoustic is not None
        and energy is not None
        and valence is not None
        and acoustic > 0.45
        and energy < 0.45
        and valence < 0.5
    ):
        tags.extend(
            [
                "rainy day",
                "rainy fall day",
                "autumn",
                "fall evening",
                "cozy",
                "sunday morning",
            ]
        )
    if energy is not None and valence is not None and energy > 0.65 and valence > 0.55:
        tags.extend(["summer", "drive", "road trip"])
    return tags


def build_track_document(
    *,
    name: str,
    artist: str,
    album: str,
    genres: str | None = None,
    features: dict[str, float] | None = None,
) -> str:
    parts = [
        (name or "").strip(),
        (artist or "").strip(),
        (album or "").strip(),
    ]
    base = " — ".join(p for p in parts if p)
    genre_text = (genres or "").strip()
    moods = mood_phrases_from_features(features)
    # Lead with genres/moods so free-text prompts align to descriptors, not titles
    lead: list[str] = []
    if genre_text:
        lead.append(f"Genres: {genre_text}. Style: {genre_text}.")
    if moods:
        mood_line = ", ".join(dict.fromkeys(moods))
        lead.append(f"Mood: {mood_line}. Feels like: {mood_line}.")
    if lead:
        return " ".join(lead) + f" Track: {base}."
    return base


def audio_feature_vector(feats: dict[str, float] | None) -> list[float]:
    """Fixed-order numeric vector; missing values → neutral midpoints."""
    defaults = {
        "acousticness": 0.5,
        "danceability": 0.5,
        "energy": 0.5,
        "instrumentalness": 0.0,
        "liveness": 0.2,
        "loudness": -10.0,  # will normalize
        "speechiness": 0.1,
        "tempo": 120.0,
        "valence": 0.5,
    }
    raw = {**defaults, **(feats or {})}
    # Normalize loudness (-60..0 → 0..1) and tempo (0..200 → 0..1)
    loudness_n = max(0.0, min(1.0, (raw["loudness"] + 60.0) / 60.0))
    tempo_n = max(0.0, min(1.0, raw["tempo"] / 200.0))
    return [
        float(raw["acousticness"]),
        float(raw["danceability"]),
        float(raw["energy"]),
        float(raw["instrumentalness"]),
        float(raw["liveness"]),
        loudness_n,
        float(raw["speechiness"]),
        tempo_n,
        float(raw["valence"]),
    ]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
