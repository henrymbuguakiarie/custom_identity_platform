from typing import List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.rbac import Session as UserSession
from app.database import SessionLocal

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def role_required(required_roles: List[str]):
    """
    Dependency for FastAPI endpoints to enforce role-based access.
    Usage:
        @router.get("/admin")
        def admin_dashboard(current_user=Depends(role_required(["Admin"]))):
            ...
    """
    def dependency(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
        # Fetch session by token
        session = db.query(UserSession).filter_by(session_token=token, is_active=True).first()
        if not session or session.revoked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or revoked session"
            )

        # Check if session has expired
        if session.expires_at and session.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Session expired"
            )

        user_roles = {role.name.lower() for role in session.user.roles}
        required_roles_set = {r.lower() for r in required_roles}

        # Check role intersection
        if not user_roles.intersection(required_roles_set):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {required_roles}"
            )

        return session.user  # Return user object for endpoint usage

    return dependency
