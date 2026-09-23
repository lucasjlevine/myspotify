"""Spotify Web API helpers beyond recently-played."""

from __future__ import annotations

import logging

import requests
from fastapi import HTTPException

from app.spotify.auth import get_access_token

logger = logging.getLogger(__name__)

TRACKS_URL = "https://api.spotify.com/v1/tracks"


def pick_album_image(images: list[dict] | None) -> str | None:
    if not images:
        return None
    # Prefer mid-size (~300px), else largest available
    sorted_imgs = sorted(
        images,
        key=lambda img: int(img.get("height") or img.get("width") or 0),
    )
    mid = sorted_imgs[len(sorted_imgs) // 2] if sorted_imgs else None
    url = (mid or sorted_imgs[-1]).get("url") if sorted_imgs else None
    return url if isinstance(url, str) and url else None


def fetch_track_images(track_ids: list[str]) -> dict[str, str]:
    """Return track_id -> album image URL for up to 50 ids per Spotify call."""
    if not track_ids:
        return {}

    access_token = get_access_token()
    mapping: dict[str, str] = {}

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
            album = track.get("album") or {}
            url = pick_album_image(album.get("images"))
            if tid and url:
                mapping[tid] = url

    return mapping
