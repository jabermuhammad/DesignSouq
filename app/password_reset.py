from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, func, insert, select, update
from sqlalchemy.orm import Session

from app.database import engine

metadata = MetaData()

password_reset_tokens = Table(
    "password_reset_tokens",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_type", String(32), nullable=False),
    Column("user_id", Integer, nullable=False),
    Column("token_hash", String(128), nullable=False, unique=True),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("used_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


def ensure_password_reset_table() -> None:
    metadata.create_all(bind=engine, tables=[password_reset_tokens], checkfirst=True)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_password_reset_token(
    db: Session,
    user_type: str,
    user_id: int,
    minutes: int = 30,
) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    expires_at = _utc_now() + timedelta(minutes=minutes)

    db.execute(
        insert(password_reset_tokens).values(
            user_type=user_type,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
    )
    db.commit()
    return token


def validate_password_reset_token(db: Session, token: str) -> tuple[str, int] | None:
    token_hash = _hash_token(token)
    now = _utc_now()

    row = db.execute(
        select(password_reset_tokens.c.user_type, password_reset_tokens.c.user_id)
        .where(password_reset_tokens.c.token_hash == token_hash)
        .where(password_reset_tokens.c.used_at.is_(None))
        .where(password_reset_tokens.c.expires_at >= now)
        .order_by(password_reset_tokens.c.id.desc())
        .limit(1)
    ).first()

    if not row:
        return None

    return str(row.user_type), int(row.user_id)


def consume_password_reset_token(db: Session, token: str) -> bool:
    token_hash = _hash_token(token)
    now = _utc_now()

    row = db.execute(
        select(password_reset_tokens.c.id)
        .where(password_reset_tokens.c.token_hash == token_hash)
        .where(password_reset_tokens.c.used_at.is_(None))
        .where(password_reset_tokens.c.expires_at >= now)
        .order_by(password_reset_tokens.c.id.desc())
        .limit(1)
    ).first()

    if not row:
        return False

    db.execute(
        update(password_reset_tokens)
        .where(password_reset_tokens.c.id == int(row.id))
        .values(used_at=now)
    )
    db.commit()
    return True
