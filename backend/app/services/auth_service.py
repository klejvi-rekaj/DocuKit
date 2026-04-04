import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from passlib.context import CryptContext
from sqlalchemy import delete, select
from sqlalchemy.orm import joinedload

from app.config import settings
from app.database import SessionLocal
from app.models.db_models import Conversation, Notebook, User, UserSession

PASSWORD_CONTEXT = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    email: str
    display_name: Optional[str]
    theme_preference: Optional[str]
    has_password: bool


@dataclass(frozen=True)
class SessionLookupResult:
    user: AuthenticatedUser
    session_id: str


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_email(email: str) -> bool:
    return bool(EMAIL_PATTERN.match(normalize_email(email)))


def validate_password(password: str) -> bool:
    return len(password) >= 8


def hash_password(password: str) -> str:
    return PASSWORD_CONTEXT.hash(password)


def verify_password(password: str, password_hash: Optional[str]) -> bool:
    if not password_hash:
        return False
    return PASSWORD_CONTEXT.verify(password, password_hash)


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def build_session_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.session_max_age_days)


def _ensure_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _user_to_dataclass(user: User) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=user.id,
        email=user.email or "",
        display_name=user.display_name,
        theme_preference=user.theme_preference,
        has_password=bool(user.password_hash),
    )


def get_user_by_email(email: str) -> Optional[AuthenticatedUser]:
    normalized = normalize_email(email)
    with SessionLocal() as session:
        user = session.execute(select(User).where(User.email == normalized)).scalar_one_or_none()
        return _user_to_dataclass(user) if user else None


def create_user(email: str, display_name: Optional[str], password: str) -> AuthenticatedUser:
    normalized = normalize_email(email)
    with SessionLocal() as session:
        existing = session.execute(select(User).where(User.email == normalized)).scalar_one_or_none()
        if existing:
            raise ValueError("An account with that email already exists.")

        user = User(
            email=normalized,
            display_name=display_name.strip() if display_name else None,
            password_hash=hash_password(password),
            theme_preference=None,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return _user_to_dataclass(user)


def authenticate_user(email: str, password: str) -> Optional[AuthenticatedUser]:
    normalized = normalize_email(email)
    with SessionLocal() as session:
        user = session.execute(select(User).where(User.email == normalized)).scalar_one_or_none()
        if not user or not verify_password(password, user.password_hash):
            return None
        return _user_to_dataclass(user)


def get_user_by_id(user_id: str) -> Optional[AuthenticatedUser]:
    with SessionLocal() as session:
        user = session.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        return _user_to_dataclass(user) if user else None


def update_user_profile(user_id: str, *, display_name: str, email: str) -> AuthenticatedUser:
    normalized_email = normalize_email(email)
    normalized_name = display_name.strip()

    with SessionLocal() as session:
        user = session.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if not user:
            raise ValueError("User not found.")

        existing = session.execute(select(User).where(User.email == normalized_email, User.id != user_id)).scalar_one_or_none()
        if existing:
            raise ValueError("An account with that email already exists.")

        user.display_name = normalized_name or None
        user.email = normalized_email
        session.commit()
        session.refresh(user)
        return _user_to_dataclass(user)


def update_user_theme_preference(user_id: str, theme_preference: str) -> AuthenticatedUser:
    with SessionLocal() as session:
        user = session.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if not user:
            raise ValueError("User not found.")

        user.theme_preference = theme_preference
        session.commit()
        session.refresh(user)
        return _user_to_dataclass(user)


def change_user_password(user_id: str, *, current_password: str, new_password: str) -> None:
    with SessionLocal() as session:
        user = session.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if not user:
            raise ValueError("User not found.")

        if not user.password_hash:
            raise ValueError("This account cannot update its password with a local password flow.")

        if not verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect.")

        if not validate_password(new_password):
            raise ValueError("Password must be at least 8 characters.")

        user.password_hash = hash_password(new_password)
        session.commit()


def create_user_session(user_id: str, raw_token: str, user_agent: Optional[str] = None) -> None:
    with SessionLocal() as session:
        session.add(
            UserSession(
                user_id=user_id,
                token_hash=hash_session_token(raw_token),
                expires_at=build_session_expiry(),
                last_seen_at=datetime.now(timezone.utc),
                user_agent=(user_agent or "")[:512] or None,
            )
        )
        session.commit()


def get_session_user(raw_token: str) -> Optional[SessionLookupResult]:
    token_hash = hash_session_token(raw_token)
    now = datetime.now(timezone.utc)

    with SessionLocal() as session:
        user_session = session.execute(
            select(UserSession)
            .options(joinedload(UserSession.user))
            .where(UserSession.token_hash == token_hash)
        ).unique().scalar_one_or_none()

        if not user_session:
            return None

        expires_at = _ensure_utc_datetime(user_session.expires_at)

        if expires_at <= now:
            session.delete(user_session)
            session.commit()
            return None

        user_session.last_seen_at = now
        session.commit()

        if not user_session.user or not user_session.user.email:
            return None

        return SessionLookupResult(
            user=_user_to_dataclass(user_session.user),
            session_id=user_session.id,
        )


def delete_user_session(raw_token: str) -> None:
    token_hash = hash_session_token(raw_token)
    with SessionLocal() as session:
        session.execute(delete(UserSession).where(UserSession.token_hash == token_hash))
        session.commit()


def claim_legacy_notebooks_for_user(user_id: str) -> None:
    """
    One-time localhost migration helper so notebooks created before auth are not stranded.

    This only claims notebooks that do not already belong to anyone.
    """
    with SessionLocal() as session:
        unowned_notebooks = session.execute(select(Notebook).where(Notebook.user_id.is_(None))).scalars().all()
        if not unowned_notebooks:
            return

        for notebook in unowned_notebooks:
            notebook.user_id = user_id

        session.flush()

        conversations = session.execute(
            select(Conversation)
            .join(Notebook, Conversation.notebook_id == Notebook.id)
            .where(Notebook.user_id == user_id, Conversation.user_id.is_(None))
        ).scalars().all()

        for conversation in conversations:
            conversation.user_id = user_id

        session.commit()
