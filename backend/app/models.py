from sqlalchemy import Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Token(Base):
    __tablename__ = "tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[float] = mapped_column(Float, nullable=False)


class Play(Base):
    __tablename__ = "plays"
    __table_args__ = (Index("idx_plays_played_at", "played_at"),)

    played_at: Mapped[str] = mapped_column(String(64), primary_key=True)
    track_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    track_name: Mapped[str] = mapped_column(Text, nullable=False)
    artist_names: Mapped[str] = mapped_column(Text, nullable=False)
    album_name: Mapped[str] = mapped_column(Text, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    context_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    collected_at: Mapped[str] = mapped_column(Text, nullable=False)
