from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.crud import user_crud
from app.core.security import create_access_token, decode_access_token
from app.config import settings
from app.schemas.user import UserCreate, UserOut, RefreshTokenRequest
from app.core.dependencies import get_current_user
from app.core.security import create_session, create_access_token, verify_access_token
from app.models.rbac import UserSession
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = user_crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    refresh_token_expires = settings.refresh_token_expire_days

    # Create session (with refresh token)
    session = create_session(user, db, settings.access_token_expire_minutes, refresh_token_expires)

    access_token = create_access_token(
        {"sub": user.username, "roles": [role.name for role in user.roles]},
        expires_delta=access_token_expires
    )

    # Link access token to session
    session.session_token = access_token
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": session.refresh_token,
        "token_type": "bearer",
    }


# --- Refresh Token Endpoint ---
@router.post("/token/refresh")
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    refresh_token = request.refresh_token
    session = db.query(UserSession).filter_by(refresh_token=refresh_token, is_active=True, revoked=False).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    
    # Optional: check if expired
    if session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")
    
    # Generate new access token
    access_token = create_access_token({"sub": session.user.username})
    
    # Update session token
    session.session_token = access_token
    db.commit()
    db.refresh(session)
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/me")
def protected_endpoint(current_user = Depends(get_current_user)):
    return current_user


@router.post("/register", response_model=UserOut)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    existing_user = user_crud.get_user_by_username(db, user_in.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    user = user_crud.create_user(db, user_in.username, user_in.email, user_in.password)
    return user

@router.post("/logout")
def logout(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    refresh_token = request.refresh_token
    session = db.query(UserSession).filter(UserSession.refresh_token == refresh_token).first()
    if session:
        session.revoked = True
        session.is_active = False
        db.commit()
    return {"message": "Successfully logged out"}


@router.get("/userinfo", response_model=UserOut)
def userinfo(current_user: UserOut = Depends(get_current_user)):
    """
    Return user claims for the authenticated user.
    Access token must be provided in the Authorization header.
    """
    return current_user
