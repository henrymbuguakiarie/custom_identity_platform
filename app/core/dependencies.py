from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.crud import user_crud
from app.core.security import decode_access_token
from app.schemas.user import UserOut
from app.models.rbac import UserSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload["sub"]
    user = user_crud.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # --- New session validation ---
    session = db.query(UserSession).filter_by(session_token=token, is_active=True, revoked=False).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session is inactive or revoked")

    return UserOut.from_orm(user)
