# app/core/security.py
from datetime import datetime, timedelta
from typing import Optional, Tuple
import secrets
import hashlib
import os

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session as OrmSession

from app.config import settings
from app.models.rbac import UserSession
from app.models.user import User
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

# --- password helpers (unchanged) ---
def hash_password(password: str) -> str:
    return pwd_context.hash(password[:72])

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password[:72], hashed_password)

# --- access / id token helpers (HS256) ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def create_id_token(user: User, expires_delta: Optional[timedelta] = None, aud: Optional[str] = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    role_names = [role.name for role in user.roles]
    to_encode = {
        "sub": str(user.id),
        "name": user.full_name,
        "email": user.email,
        "roles": role_names,
        "iss": settings.issuer,
        "aud": aud or settings.default_aud,
        "iat": datetime.utcnow(),
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None

# --- refresh token helpers (secure) ---
def generate_refresh_token(length: int = 48) -> str:
    """Return a URL-safe cryptographically-secure refresh token (raw)."""
    return secrets.token_urlsafe(length)

def _hash_refresh_token(raw: str) -> str:
    """Return hex SHA-256 of the refresh token for storage/lookup."""
    h = hashlib.sha256()
    h.update(raw.encode("utf-8"))
    return h.hexdigest()

def _is_session_expired(session: UserSession) -> bool:
    if session.expires_at is None:
        return False
    return session.expires_at < datetime.utcnow()

# --- session management (DB helpers) ---
def create_session(user: User, db: OrmSession, access_expire_minutes: int, refresh_expire_days: int):
    """Create a new session with access & refresh token."""
    
    # Generate tokens
    refresh_token = secrets.token_urlsafe(64)
    refresh_hash = hash_refresh_token(refresh_token)

    access_token = create_access_token(
        {"sub": user.username, "roles": [r.name for r in user.roles]},
        expires_delta=timedelta(minutes=access_expire_minutes),
    )

    # Store session
    session = UserSession(
        user_id=user.id,
        session_token=access_token,
        refresh_token_hash=refresh_hash,
        expires_at=datetime.utcnow() + timedelta(days=refresh_expire_days),
        is_active=True,
        revoked=False,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return session, refresh_token, access_token

def rotate_refresh_session(session: UserSession, db: OrmSession):
    """Revoke old refresh token and generate a new one."""
    old_refresh_token_hash = session.refresh_token_hash
    new_refresh_token = secrets.token_urlsafe(64)
    session.refresh_token_hash = hash_refresh_token(new_refresh_token)
    db.commit()
    return new_refresh_token


def verify_refresh_token(raw_token: str, db: OrmSession) -> Optional[UserSession]:
    """
    Given a raw refresh token from client, find the active session and validate.
    Returns the UserSession if valid, otherwise None.
    """
    refresh_hash = _hash_refresh_token(raw_token)
    session = db.query(UserSession).filter(
        UserSession.refresh_token == refresh_hash
    ).first()

    if not session:
        return None
    if session.revoked or not session.is_active:
        return None
    if _is_session_expired(session):
        # defensively revoke it
        session.revoked = True
        session.is_active = False
        db.add(session)
        db.commit()
        return None
    return session

def revoke_session(session: UserSession, db: OrmSession):
    """Revoke a user session (logout)."""
    session.revoked = True
    session.is_active = False
    db.commit()

def rotate_keys(private_key_path: str, public_key_path: str):

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    # Write new private key
    with open(private_key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Write new public key
    with open(public_key_path, "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))

    return True

