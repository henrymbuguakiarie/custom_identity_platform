from fastapi import APIRouter, Depends
from app.utils.auth import role_required
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from app.models.audit import AuditLog
from app.utils.auth import role_required

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

