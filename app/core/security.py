from datetime import datetime, timedelta
from typing import Optional
import secrets
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings
from app.models.rbac import UserSession
from app.models.user import User
from sqlalchemy.orm import Session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password[:72])

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password[:72], hashed_password)
    
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def verify_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None

# --- Session Management ---
def create_session(user: User, db: Session, access_token_expiry: int, refresh_token_expiry: int):
    access_token = create_access_token({"sub": user.username}, expires_delta=timedelta(minutes=access_token_expiry))
    refresh_token = secrets.token_urlsafe(32)

    session = UserSession(
        user_id=user.id,
        session_token=access_token,
        refresh_token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(minutes=access_token_expiry),
        is_active=True,
        revoked=False
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

def create_refresh_token(user: User, db: Session, refresh_token_expiry: int):
    refresh_token = secrets.token_urlsafe(64)
    session = UserSession(
        user_id=user.id,
        session_token=None,  # created later in login
        refresh_token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=refresh_token_expiry),
        is_active=True,
        revoked=False
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return refresh_token

def create_id_token(user, expires_delta: timedelta | None = None, aud: str | None = None):
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    role_names = [role.name for role in user.roles]
    to_encode = {
        "sub": str(user.id),
        "name": user.full_name,
        "email": user.email,
        "roles": role_names,          # custom claim
        "iss": settings.issuer,
        "aud": aud or settings.default_aud,
        "iat": datetime.utcnow(),
        "exp": expire
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

def verify_refresh_token(token: str, db: Session) -> Optional[User]:
    session = db.query(Session).filter(
        Session.refresh_token == token,
        Session.revoked == False,
        Session.is_active == True
    ).first()
    if not session or session.expires_at < datetime.utcnow():
        return None
    return session.user
