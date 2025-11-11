from fastapi import APIRouter, Depends
from app.utils.auth import role_required

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/dashboard")
def admin_dashboard(current_user=Depends(role_required(["Admin"]))):
    return {"message": f"Welcome, {current_user.username}! Access granted."}

