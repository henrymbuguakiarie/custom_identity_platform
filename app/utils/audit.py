# app/utils/audit.py
from app.database import SessionLocal
from app.models.audit import AuditLog
from fastapi import Request

def log_event(user_id: int | None, event_type: str, request: Request = None, details: str | None = None):
    db = SessionLocal()
    try:
        ip_address = request.client.host if request else None
        user_agent = request.headers.get("user-agent") if request else None

        audit = AuditLog(
            user_id=user_id,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        db.add(audit)
        db.commit()
    finally:
        db.close()
