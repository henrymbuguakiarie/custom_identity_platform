from fastapi import APIRouter, Depends, status, HTTPException
from app.utils.auth import role_required
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from app.models.audit import AuditLog
from app.utils.auth import role_required
from typing import List, Optional
from app.models.user import User
from app.models.rbac import Role, UserSession
from app.schemas.user import UserOut


router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/dashboard")
def admin_dashboard(current_user=Depends(role_required(["Admin"]))):
    return {"message": f"Welcome, {current_user.username}! Access granted."}

@router.get("/audit-logs")
def get_audit_logs(
    current_user=Depends(role_required(["Admin"])),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Retrieve audit logs for admin users with pagination.
    
    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    """
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {"count": len(logs), "logs": logs}

@router.get("/users", response_model=List[UserOut])
def list_users(
    current_user=Depends(role_required(["Admin"])),
    skip: int = 0,
    limit: int = 50,
    username: str | None = None,
    email: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if username:
        query = query.filter(User.username.ilike(f"%{username}%"))
    if email:
        query = query.filter(User.email.ilike(f"%{email}%"))
    users = query.offset(skip).limit(limit).all()
    return users


@router.get("/roles", response_model=List[str])
def list_roles(
    current_user=Depends(role_required(["Admin"])),
    db: Session = Depends(get_db),
):
    roles = db.query(Role).all()
    return [role.name for role in roles]


@router.post("/roles")
def create_role(
    name: str,
    current_user=Depends(role_required(["Admin"])),
    db: Session = Depends(get_db),
):
    existing = db.query(Role).filter_by(name=name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role already exists")
    role = Role(name=name)
    db.add(role)
    db.commit()
    db.refresh(role)
    return {"detail": f"Role '{name}' created"}

@router.get("/sessions")
def list_sessions(
    current_user=Depends(role_required(["Admin"])),
    user_id: int | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(UserSession).filter(UserSession.is_active == True)
    if user_id:
        query = query.filter(UserSession.user_id == user_id)
    sessions = query.offset(skip).limit(limit).all()
    return [
        {
            "id": s.id,
            "user_id": s.user_id,
            "created_at": s.created_at,
            "expires_at": s.expires_at,
            "revoked": s.revoked,
        } for s in sessions
    ]


@router.post("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    current_user=Depends(role_required(["Admin"])),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_active = False
    db.commit()
    db.refresh(user)

    # Optionally log the admin action
    from app.utils.audit import log_event
    log_event(user_id=current_user.id, event_type=f"deactivated user {user.username}")

    return {"detail": f"User '{user.username}' deactivated"}

@router.post("/sessions/{session_id}/revoke")
def revoke_session(
    session_id: int,
    current_user=Depends(role_required(["Admin"])),
    db: Session = Depends(get_db),
):
    session = db.query(UserSession).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    session.revoked = True
    session.is_active = False
    db.commit()

    log_event(user_id=current_user.id, event_type=f"revoked session {session.id}")

    return {"detail": f"Session {session.id} revoked"}


