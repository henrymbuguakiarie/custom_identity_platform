from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Body, Form
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.crud import user_crud
from app.config import settings
from app.schemas.user import UserCreate, UserOut, RefreshTokenRequest
from app.core.dependencies import get_current_user
from app.core.security import create_session, create_access_token, create_id_token, verify_refresh_token, rotate_refresh_session
from app.models.rbac import UserSession
from app.models.user import User
from app.core.utils import verify_code_challenge
from app.crud.oauth_crud import consume_authorization_code, get_client_by_client_id

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/token")
def token_endpoint(
    grant_type: str = Form(...),
    code: str | None = Form(None),
    redirect_uri: str | None = Form(None),
    client_id: str | None = Form(None),
    code_verifier: str | None = Form(None),
    form_data: OAuth2PasswordRequestForm = Depends(),  # password grant
    db: Session = Depends(get_db),
):
    """
    Token endpoint supporting:
    - Password Grant
    - Authorization Code Grant (with PKCE)
    """

    # -------------------------------
    # 1️⃣ Authorization Code + PKCE
    # -------------------------------
    if grant_type == "authorization_code":
        if not code or not client_id or not redirect_uri:
            raise HTTPException(400, "Missing required OAuth parameters")

        client = get_client_by_client_id(db, client_id)
        if not client:
            raise HTTPException(400, "Invalid client_id")
        if redirect_uri not in client.redirect_uri_list():
            raise HTTPException(400, "Invalid redirect_uri")

        auth_code = consume_authorization_code(db, code)
        if not auth_code:
            raise HTTPException(400, "Invalid or expired authorization code")

        if auth_code.client_id != client.id or auth_code.redirect_uri != redirect_uri:
            raise HTTPException(400, "Authorization code mismatch")

        if auth_code.code_challenge:
            if not code_verifier:
                raise HTTPException(400, "Missing code_verifier")
            if not verify_code_challenge(code_verifier, auth_code.code_challenge, auth_code.code_challenge_method):
                raise HTTPException(400, "Invalid code_verifier")

        user = auth_code.user

        # Create session
        session, refresh_token, access_token = create_session(
            user,
            db,
            settings.access_token_expire_minutes,
            settings.refresh_token_expire_days,
        )

        id_token = create_id_token(user, expires_delta=timedelta(minutes=settings.access_token_expire_minutes), aud=client.client_id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "id_token": id_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
        }

    # -------------------------------
    # 2️⃣ Password Grant
    # -------------------------------
    if grant_type == "password":
        user = user_crud.authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")

        session, refresh_token, access_token = create_session(
            user,
            db,
            settings.access_token_expire_minutes,
            settings.refresh_token_expire_days,
        )

        id_token = create_id_token(user, expires_delta=timedelta(minutes=settings.access_token_expire_minutes))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "id_token": id_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
        }

    # -------------------------------
    # 3️⃣ Unsupported grant
    # -------------------------------
    raise HTTPException(400, "Unsupported grant_type")


# --- Refresh Token Endpoint ---
@router.post("/token/refresh")
def refresh_token(
    refresh_token: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Rotate the refresh token and issue a new access token + id token.
    """
    session = verify_refresh_token(refresh_token, db)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = session.user

    # rotate - old session revoked & new created
    new_session, raw_refresh = rotate_refresh_session(db, session, settings.refresh_token_expire_days)

    # create new access token and id token
    access_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token({"sub": user.username, "roles": [r.name for r in user.roles]}, expires_delta=access_expires)
    id_token = create_id_token(user, expires_delta=access_expires)

    # link access token optionally to session
    new_session.session_token = access_token
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "id_token": id_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
    }


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

# --- revoke (user or admin) ---
@router.post("/token/revoke")
def revoke_token(
    refresh_token: str | None = Form(None),
    session_id: int | None = Form(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not refresh_token and not session_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide refresh_token or session_id")

    target = None
    if refresh_token:
        session = verify_refresh_token(refresh_token, db)
        # If verify_refresh_token returns None, try to find a session by hash to allow revocation of expired/revoked tokens
        from app.core.security import _hash_refresh_token
        refresh_hash = _hash_refresh_token(refresh_token)
        target = db.query(UserSession).filter_by(refresh_token=refresh_hash).first()
    else:
        target = db.query(UserSession).filter_by(id=session_id).first()

    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # authorization: owner or admin
    if target.user_id != current_user.id:
        user_roles = {r.name for r in current_user.roles}
        if "Admin" not in user_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    target.revoked = True
    target.is_active = False
    db.add(target)
    db.commit()
    return {"detail": "Session revoked"}
