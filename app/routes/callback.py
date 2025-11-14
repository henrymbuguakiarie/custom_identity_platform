# app/routes/callback.py
from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/callback")
def callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    return {"code": code, "state": state}
