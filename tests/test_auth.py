# tests/test_auth.py
import time
import pyotp
from app.models.rbac import Role
from app.models.audit import AuditLog


def test_register_user(client):
    response = client.post("/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "StrongP@ssword1"
    })
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["username"] == "testuser"
    assert "email" in data


def test_register_duplicate_user(client, create_test_user):
    # create_test_user inserts user1 already
    create_test_user()
    response = client.post("/auth/register", json={
        "username": "user1",
        "email": "user1@example.com",
        "password": "StrongP@ssword1"
    })
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_login_password_grant(client, create_test_user):
    create_test_user()
    response = client.post("/auth/token", data={
        "grant_type": "password",
        "username": "user1",
        "password": "StrongP@ss1"
    })
    assert response.status_code == 200, response.text
    tokens = response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert "id_token" in tokens


def test_login_invalid_password(client, create_test_user):
    create_test_user()
    response = client.post("/auth/token", data={
        "grant_type": "password",
        "username": "user1",
        "password": "wrongpassword"
    })
    assert response.status_code == 401


def test_refresh_token(client, create_test_user):
    create_test_user()
    login_resp = client.post("/auth/token", data={
        "grant_type": "password",
        "username": "user1",
        "password": "StrongP@ss1"
    })
    assert login_resp.status_code == 200, login_resp.text
    refresh_token = login_resp.json()["refresh_token"]

    response = client.post("/auth/token/refresh", data={
        "refresh_token": refresh_token
    })
    assert response.status_code == 200, response.text
    json_body = response.json()
    assert "access_token" in json_body
    assert "refresh_token" in json_body


def test_audit_log_created_on_login(client, create_test_user, db_session):
    # make sure there are no logs initially
    assert db_session.query(AuditLog).count() == 0

    create_test_user()
    # perform login
    resp = client.post("/auth/token", data={
        "grant_type": "password",
        "username": "user1",
        "password": "StrongP@ss1"
    })
    assert resp.status_code == 200, resp.text

    # give the backend a moment if your audit logger writes asynchronously
    time.sleep(0.01)

    logs = db_session.query(AuditLog).filter(AuditLog.event_type.like("%login%")).all()
    assert len(logs) >= 1


def test_admin_dashboard_access(client, db_session):
    # create an admin user directly using the CRUD helper
    from app.crud.user_crud import create_user

    admin_user = create_user(db_session, "admin", "admin@example.com", "StrongP@ss1")
    admin_role = Role(name="Admin", description="Administrator")
    db_session.add(admin_role)
    db_session.commit()

    # attach role
    admin_user.roles.append(admin_role)
    db_session.commit()

    # login as admin
    token_resp = client.post("/auth/token", data={
        "grant_type": "password",
        "username": "admin",
        "password": "StrongP@ss1"
    })
    assert token_resp.status_code == 200, token_resp.text
    access_token = token_resp.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/admin/dashboard", headers=headers)
    assert response.status_code == 200, response.text

def test_setup_and_verify_mfa(client, create_test_user):
    user = create_test_user()
    # Setup MFA
    resp = client.post("/auth/mfa/setup", headers={"Authorization": f"Bearer {user.token}"})
    data = resp.json()
    assert "otp_uri" in data

    # Verify MFA
    totp = pyotp.TOTP(data["secret"])
    code = totp.now()
    verify_resp = client.post("/auth/mfa/verify", json={"code": code}, headers={"Authorization": f"Bearer {user.token}"})
    assert verify_resp.status_code == 200
