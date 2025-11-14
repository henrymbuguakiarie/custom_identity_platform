from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Body, Form
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.crud import user_crud
from app.config import settings
from app.schemas.user import UserCreate, UserOut, RefreshTokenRequest
from app.core.dependencies import get_current_user
from app.core.security import create_session, create_access_token, create_id_token
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
    Combined token endpoint supporting:
    - Password Grant
    - Authorization Code Grant (with PKCE)
    """

    # ----------------------------------------------------------
    # 1️⃣ AUTHORIZATION CODE FLOW + PKCE
    # ----------------------------------------------------------
    if grant_type == "authorization_code":

        # Basic parameter validation
        if not code or not client_id or not redirect_uri:
            raise HTTPException(
                status_code=400, detail="Missing required OAuth parameters"
            )

        # Validate client
        client = get_client_by_client_id(db, client_id)
        if not client:
            raise HTTPException(status_code=400, detail="Invalid client_id")

        if redirect_uri not in client.redirect_uri_list():
            raise HTTPException(status_code=400, detail="Invalid redirect_uri")

        # Fetch and consume authorization code
        auth_code = consume_authorization_code(db, code)
        if not auth_code:
            raise HTTPException(status_code=400, detail="Invalid or expired authorization code")

        # Ensure auth code belongs to this client + matching redirect_uri
        if auth_code.client_id != client.id or auth_code.redirect_uri != redirect_uri:
            raise HTTPException(status_code=400, detail="Authorization code mismatch")

        # ----- PKCE Validation (required for public clients) ------
        if auth_code.code_challenge:
            if not code_verifier:
                raise HTTPException(status_code=400, detail="Missing code_verifier")

            if not verify_code_challenge(
                code_verifier,
                auth_code.code_challenge,
                auth_code.code_challenge_method,
            ):
                raise HTTPException(status_code=400, detail="Invalid code_verifier")

        # Issue tokens for authorized user
        user = auth_code.user

        # Create session (with refresh token)
        session = create_session(
            user,
            db,
            settings.access_token_expire_minutes,
            settings.refresh_token_expire_days,
        )

        # Generate ACCESS TOKEN
        access_token = create_access_token(
            {"sub": user.username, "roles": [r.name for r in user.roles]},
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        )

        # Attach access token to session
        session.session_token = access_token
        db.commit()

        # Generate ID TOKEN (OIDC)
        id_token = create_id_token(
            user,
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
            aud=client.client_id,  # REQUIRED for OIDC compliance
        )

        return {
            "access_token": access_token,
            "refresh_token": session.refresh_token,
            "id_token": id_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
        }

    # ----------------------------------------------------------
    # 2️⃣ PASSWORD GRANT (Existing Flow)
    # ----------------------------------------------------------
    if grant_type == "password":

        # Authenticate user
        user = user_crud.authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        # Token expirations
        access_exp = timedelta(minutes=settings.access_token_expire_minutes)
        refresh_days = settings.refresh_token_expire_days

        # Create session
        session = create_session(user, db, settings.access_token_expire_minutes, refresh_days)

        # Access token
        access_token = create_access_token(
            {"sub": user.username, "roles": [role.name for role in user.roles]},
            expires_delta=access_exp,
        )

        session.session_token = access_token
        db.commit()

        # ID Token for OIDC
        id_token = create_id_token(user, expires_delta=access_exp)

        return {
            "access_token": access_token,
            "refresh_token": session.refresh_token,
            "id_token": id_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
        }

    # ----------------------------------------------------------
    # 3️⃣ UNSUPPORTED GRANT TYPE
    # ----------------------------------------------------------
    raise HTTPException(status_code=400, detail="Unsupported grant_type")

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
