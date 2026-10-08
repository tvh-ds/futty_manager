from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import JSON, DateTime, Float, ForeignKey, ForeignKeyConstraint, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from scout.contracts import DatasetRelease, PlayerStint, Team


class Base(DeclarativeBase):
    pass


class ReleaseRow(Base):
    __tablename__ = "releases"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    manifest: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class PlayerRow(Base):
    __tablename__ = "player_stints"
    release_id: Mapped[str] = mapped_column(ForeignKey("releases.id"), primary_key=True)
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    team_id: Mapped[str] = mapped_column(String(100), index=True)
    league: Mapped[str] = mapped_column(String(50), index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class TeamRow(Base):
    __tablename__ = "teams"
    release_id: Mapped[str] = mapped_column(ForeignKey("releases.id"), primary_key=True)
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)


class ActiveRelease(Base):
    __tablename__ = "active_release"
    slot: Mapped[str] = mapped_column(String(20), primary_key=True)
    release_id: Mapped[str] = mapped_column(ForeignKey("releases.id"))


class EvidenceImport(Base):
    __tablename__ = "evidence_imports"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    manifest: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class SourceRecord(Base):
    """A provider aggregate, explicitly not a canonical player-team stint."""
    __tablename__ = "source_records"
    import_id: Mapped[str] = mapped_column(ForeignKey("evidence_imports.id"), primary_key=True)
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    provider: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    league: Mapped[str] = mapped_column(String(50), index=True)
    season: Mapped[str] = mapped_column(String(10))
    payload: Mapped[dict] = mapped_column(JSON)


class SourceFeature(Base):
    __tablename__ = "source_features"
    import_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    record_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (ForeignKeyConstraint(
        ["import_id", "record_id"], ["source_records.import_id", "source_records.id"]),)


class IdentityLink(Base):
    __tablename__ = "evidence_identity_links"
    import_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    record_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    canonical_id: Mapped[str] = mapped_column(String(100), index=True)
    review: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (ForeignKeyConstraint(
        ["import_id", "record_id"], ["source_records.import_id", "source_records.id"]),)


class ActiveEvidence(Base):
    __tablename__ = "active_evidence"
    slot: Mapped[str] = mapped_column(String(20), primary_key=True)
    import_id: Mapped[str] = mapped_column(ForeignKey("evidence_imports.id"))


class CatalogueRelease(Base):
    __tablename__ = "catalogue_releases"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    import_id: Mapped[str] = mapped_column(ForeignKey("evidence_imports.id"))
    manifest: Mapped[dict] = mapped_column(JSON)


class CataloguePlayer(Base):
    __tablename__ = "catalogue_players"
    catalogue_id: Mapped[str] = mapped_column(ForeignKey("catalogue_releases.id"), primary_key=True)
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    league: Mapped[str] = mapped_column(String(50), index=True)
    team: Mapped[str] = mapped_column(String(200), index=True)
    position: Mapped[str] = mapped_column(String(20), index=True)
    overall: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class ActiveCatalogue(Base):
    __tablename__ = "active_catalogue"
    slot: Mapped[str] = mapped_column(String(20), primary_key=True)
    catalogue_id: Mapped[str] = mapped_column(ForeignKey("catalogue_releases.id"))


def connect(url: str):
    if url.startswith("sqlite:///./"):
        Path(url.removeprefix("sqlite:///./")).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url, pool_pre_ping=True,
                         connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})


def load_active(engine):
    with Session(engine) as session:
        active = session.get(ActiveRelease, "main")
        if not active:
            return None
        release = session.get(ReleaseRow, active.release_id)
        players = session.scalars(select(PlayerRow).where(PlayerRow.release_id == active.release_id)).all()
        teams = session.scalars(select(TeamRow).where(TeamRow.release_id == active.release_id)).all()
        import hashlib

        from scout.releases import serialized
        payload = {"release": release.manifest,
                   "players": [row.payload for row in sorted(players, key=lambda row: row.id)],
                   "teams": [row.payload for row in sorted(teams, key=lambda row: row.id)]}
        if hashlib.sha256(serialized(payload)).hexdigest() != release.checksum:
            raise ValueError("Serving snapshot checksum mismatch")
        return (DatasetRelease.model_validate(release.manifest),
                [PlayerStint.model_validate(row.payload) for row in players],
                [Team.model_validate(row.payload) for row in teams])
