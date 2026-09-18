from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    spotify_state: str
    spotify_client_id: str
    spotify_client_secret: str
    spotify_redirect_uri: str
    spotify_api_scope: str
    spotify_refresh_token: str = ""

    database_url: str = f"sqlite:///{DATA_DIR / 'plays.db'}"
    poll_interval_seconds: int = 15 * 60
    token_expiry_skew_seconds: int = 60

    spotify_authorize_url: str = "https://accounts.spotify.com/authorize"
    spotify_token_url: str = "https://accounts.spotify.com/api/token"
    spotify_recently_played_url: str = (
        "https://api.spotify.com/v1/me/player/recently-played"
    )


settings = Settings()
