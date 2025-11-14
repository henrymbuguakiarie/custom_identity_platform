from datetime import datetime, timedelta
import secrets
from sqlalchemy.orm import Session
from app.models.oauth import AuthorizationCode, OAuthClient

def get_client_by_client_id(db: Session, client_id: str) -> OAuthClient:
    return db.query(OAuthClient).filter(OAuthClient.client_id == client_id).first()

def create_authorization_code(
    db: Session,
    user_id: int,
    client_id: int,
    redirect_uri: str,
    code_challenge: str | None,
    code_challenge_method: str | None,
    scope: str | None,
    expires_in: int = 600
) -> AuthorizationCode:
    code = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    auth_code = AuthorizationCode(
        code=code,
        user_id=user_id,
        client_id=client_id,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        scope=scope,
        expires_at=expires_at,
        used=False
    )
    db.add(auth_code)
    db.commit()
    db.refresh(auth_code)
    return auth_code

def consume_authorization_code(db: Session, code_str: str) -> AuthorizationCode | None:
    auth_code = db.query(AuthorizationCode).filter(
        AuthorizationCode.code == code_str,
        AuthorizationCode.used == False,
        AuthorizationCode.expires_at > datetime.utcnow()
    ).first()
    if auth_code:
        auth_code.used = True
        db.commit()
        db.refresh(auth_code)
        return auth_code
    return None

