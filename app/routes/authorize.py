# app/routes/authorize.py
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user  # existing
from app.crud import oauth_crud, user_crud
from app.core.utils import generate_code_challenge_s256
from typing import Optional

router = APIRouter()

@router.get("/auth/authorize")
def authorize_get(
    request: Request,
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: Optional[str] = None,
    state: Optional[str] = None,
    code_challenge: Optional[str] = None,
    code_challenge_method: Optional[str] = "S256",
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),  # user or raises 401
):
    """
    If user is authenticated (via cookie/session), issue code immediately.
    Otherwise show simple login form (HTML).
    """
    # Validate client + redirect_uri
    client = oauth_crud.get_client_by_client_id(db, client_id)
    if not client or redirect_uri not in client.redirect_uri_list():
        raise HTTPException(status_code=400, detail="Invalid client_id or redirect_uri")

    # Only support response_type=code
    if response_type != "code":
        raise HTTPException(status_code=400, detail="Unsupported response_type")

    # If user already authenticated, create code and redirect
    if current_user:
        auth_code = oauth_crud.create_authorization_code(
            db=db,
            user_id=current_user.id,
            client=client.id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            scope=scope,
        )
        redirect_to = f"{redirect_uri}?code={auth_code.code}"
        if state:
            redirect_to += f"&state={state}"
        return RedirectResponse(redirect_to)

    # If not authenticated, show login form - this is a simple HTML form POSTing back to /auth/authorize
    html = f"""
    <html>
      <body>
        <h2>Login to authorize {client.client_name or client_id}</h2>
        <form method="post" action="/auth/authorize">
          <input type="hidden" name="response_type" value="{response_type}"/>
          <input type="hidden" name="client_id" value="{client_id}"/>
          <input type="hidden" name="redirect_uri" value="{redirect_uri}"/>
          <input type="hidden" name="scope" value="{scope or ''}"/>
          <input type="hidden" name="state" value="{state or ''}"/>
          <input type="hidden" name="code_challenge" value="{code_challenge or ''}"/>
          <input type="hidden" name="code_challenge_method" value="{code_challenge_method or ''}"/>
          <label>Username: <input name="username" /></label><br/>
          <label>Password: <input type="password" name="password" /></label><br/>
          <button type="submit">Log in and authorize</button>
        </form>
      </body>
    </html>
    """
    return HTMLResponse(html)


@router.post("/auth/authorize")
def authorize_post(
    response_type: str = Form(...),
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    scope: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    code_challenge: Optional[str] = Form(None),
    code_challenge_method: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Handles login form submission and issues code on success.
    """
    client = oauth_crud.get_client_by_client_id(db, client_id)
    if not client or redirect_uri not in client.redirect_uri_list():
        raise HTTPException(status_code=400, detail="Invalid client or redirect_uri")

    if response_type != "code":
        raise HTTPException(status_code=400, detail="Unsupported response_type")

    user = user_crud.authenticate_user(db, username, password)
    if not user:
        # Could re-present the form with error; for simplicity redirect with error param
        raise HTTPException(status_code=401, detail="Invalid credentials")

    auth_code = oauth_crud.create_authorization_code(
        db=db,
        user_id=user.id,
        client_id=client.id,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        scope=scope,
    )

    redirect_to = f"{redirect_uri}?code={auth_code.code}"
    if state:
        redirect_to += f"&state={state}"
    return RedirectResponse(redirect_to)
