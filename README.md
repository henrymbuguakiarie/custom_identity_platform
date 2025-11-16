# **Custom Identity Platform**

A **Custom Identity Platform** built with **FastAPI**, **SQLAlchemy**, and **PostgreSQL**, providing secure authentication and authorization with **OAuth2**, **JWT access & refresh tokens**, and **Role-Based Access Control (RBAC)**.

This platform is designed for production-ready identity management — featuring secure token rotation, refresh session tracking, **OpenID Connect–style user claims**, **JWKS public key discovery**, Authorization Code Flow with PKCE (for SPAs), and automatic refresh token revocation.

---

## 🧩 Table of Contents

* [Features](#-features)
* [Dependencies](#-dependencies)
* [Setup](#-setup)
* [Database Setup & Migrations](#-database-setup--migrations)
* [Seeding RBAC, Users & OAuth Clients](#-seeding-rbac-users--oauth-clients)
* [OAuth2 Authorization Code Flow (PKCE)](#-oauth2-authorization-code-flow-pkce)
* [OAuth2 Password + JWT + Refresh Token Flow](#-oauth2-password--jwt--refresh-token-flow)
* [Refresh Token Rotation & Revocation](#-refresh-token-rotation--revocation)
* [User Info and JWKS Endpoints](#-user-info-and-jwks-endpoints)
* [RBAC Setup](#-rbac-setup)
* [Running the Application](#️-running-the-application)
* [API Endpoints](#-api-endpoints)
* [Flow Diagrams](#-flow-diagrams)
* [Expected Responses](#-expected-responses)
* [Contributing](#-contributing)

---

## 🚀 Features

* ✅ **OAuth2 Password Flow** (first-party clients)
* ✅ **OAuth2 Authorization Code Flow with PKCE** (SPAs / Mobile Apps)
* ✅ JWT Access Tokens (RS256)
* ✅ Refresh tokens with **rotation** and DB-backed tracking
* ✅ Token revocation (manual + automatic)
* ✅ **OpenID Connect–compatible `/userinfo` endpoint**
* ✅ **JWKS endpoint (`/.well-known/jwks.json`)** for public key discovery
* ✅ Role-Based Access Control (RBAC)
* ✅ Seeders for roles, users, OAuth clients, and redirect URIs
* ✅ SQLAlchemy + Alembic migrations
* ✅ Clean, testable FastAPI architecture

---

## ⚙️ Dependencies

Core dependencies include:

* **FastAPI**
* **SQLAlchemy**
* **Alembic**
* **psycopg2-binary**
* **Authlib** (OAuth2 utilities)
* **python-jose** (JWT)
* **passlib[bcrypt]**
* **pydantic-settings**
* **python-multipart**

Dependency management handled via **Poetry**.

---

## ⚙️ Setup

### 1. Clone the repository

```bash
git clone https://github.com/henrymbuguakiarie/custom_identity_platform.git
cd custom_identity_platform
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
SECRET_KEY=your_secret_key
ALGORITHM=RS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
SQLALCHEMY_URL=postgresql+psycopg2://postgres:password@localhost:5432/identity_db
PRIVATE_KEY_PATH=/path/to/private_key.pem
PUBLIC_KEY_PATH=/path/to/public_key.pem
```

### 3. Generate RSA keys

```bash
openssl genrsa -out private_key.pem 2048
openssl rsa -in private_key.pem -pubout -out public_key.pem
```

### 4. Install dependencies

```bash
poetry install
```

---

## 🗄 Database Setup & Migrations

### Run Alembic migrations:

```bash
poetry run alembic upgrade head
```

---

## 🪴 Seeding RBAC, Users & OAuth Clients

The platform includes seed utilities to automatically bootstrap RBAC, an admin user, OAuth clients, and redirect URIs.

### 1. Seed RBAC roles, permissions, and admin user

```bash
python -m app.utils.seed_rbac
```

Creates:

* **Admin** and **User** roles
* Default permissions
* Default admin user:

  * `username`: `admin`
  * `password`: `adminpass`

---

### 2. Seed a public OAuth client (SPA-friendly, PKCE)

```bash
python -m app.utils.seed_oauth_client
```

This script:

* Creates a public OAuth client
* Generates a random `client_id`
* Saves it into **oauth_client.json**

  * If the file does **not exist**, it is **created**
  * If it exists, it is **overwritten**

**Example file:**

```json
{
  "client_id": "XyZ123..."
}
```

---

### 3. Update redirect URIs

```bash
python -m app.utils.update_redirect_uris
```

This script:

* Reads `client_id` from **oauth_client.json**
* Updates redirect URIs in DB

---

### 4. (Optional) Run combined idempotent workflow

```bash
python -m app.utils.seed_or_update_oauth_client
```

This:

* Seeds OAuth client if missing
* Updates redirect URIs
* Ensures consistent client configuration

---

## ▶️ Running the Application

```bash
poetry run uvicorn app.main:app --reload
```

Open:

* Docs → [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* Root → [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 🔐 OAuth2 Authorization Code Flow (PKCE)

This flow is used by **SPAs (Vue/React/Next), mobile apps, or public clients.**

### Step 1 — Generate PKCE values

```bash
VERIFIER=$(openssl rand -base64 32)
CHALLENGE=$(echo -n $VERIFIER | openssl dgst -sha256 -binary | openssl base64 | tr '+/' '-_' | tr -d '=')
```

### Step 2 — Begin login (GET Authorization Endpoint)

```bash
GET /auth/authorize
  ?response_type=code
  &client_id=<CLIENT_ID>
  &redirect_uri=http://localhost:3000/callback
  &code_challenge=$CHALLENGE
  &code_challenge_method=S256
```

### Step 3 — Exchange code for tokens

```bash
curl -X POST http://127.0.0.1:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "authorization_code",
    "client_id": "<CLIENT_ID>",
    "code_verifier": "'"$VERIFIER"'",
    "code": "<AUTH_CODE>",
    "redirect_uri": "http://localhost:3000/callback"
  }'
```

Response:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "id_token": "...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

## 🔑 OAuth2 Password + JWT + Refresh Token Flow

### 1. Login using username/password

```bash
curl -X POST http://127.0.0.1:8000/auth/token \
  -F "grant_type=password" \
  -F "username=admin" \
  -F "password=adminpass"
```

---

## 🔄 Refresh Token Rotation & Revocation

### 1. Exchange refresh token (rotation)

```bash
curl -X POST http://127.0.0.1:8000/auth/token/refresh \
  -F "refresh_token=<REFRESH_TOKEN>"
```

Response:

```json
{
  "access_token": "<NEW_ACCESS_TOKEN>",
  "refresh_token": "<NEW_REFRESH_TOKEN>",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Old refresh token is revoked automatically.**

---

### 2. Manual revocation (Logout)

```bash
curl -X POST http://127.0.0.1:8000/auth/revoke \
  -F "refresh_token=<REFRESH_TOKEN>"
```

Response:

```json
{ "detail": "Refresh token revoked successfully" }
```

After revocation:

```json
{ "detail": "Invalid or revoked refresh token" }
```

---

## 🧾 User Info and JWKS Endpoints

### `/auth/userinfo`

Returns OpenID Connect–style claims:

```json
{
  "sub": "user_id_123",
  "name": "John Doe",
  "email": "john@example.com",
  "roles": ["Admin"]
}
```

### `/.well-known/jwks.json`

JWKS public key discovery:

```json
{
  "keys": [
    {
      "kty": "RSA",
      "use": "sig",
      "kid": "rsa1",
      "alg": "RS256",
      "n": "...",
      "e": "AQAB"
    }
  ]
}
```

---

## 🧱 RBAC Setup

Protect an endpoint:

```python
@router.get("/admin/dashboard")
@role_required(["Admin"])
def admin_dashboard():
    return {"message": "Welcome Admin"}
```

---

## 📝 Logging & Audit

This platform logs **all authentication events** for traceability and compliance. Events include:

* **login** – successful login via password or authorization code
* **login_failed** – failed login attempt
* **refresh_token** – refresh token rotation
* **logout** – manual token revocation

All audit events are stored in the database and can optionally be sent to a centralized logging service.

---

### **1️⃣ Audit Logging in Action**

When a user logs in or refreshes a token, a new audit record is created. Example fields:

| Field        | Description                          |
| ------------ | ------------------------------------ |
| `id`         | Unique log entry ID                  |
| `user_id`    | ID of the user performing the action |
| `event_type` | Event type (`login`, `logout`, etc.) |
| `details`    | Additional details about the event   |
| `ip_address` | IP address from request              |
| `user_agent` | User-Agent string from request       |
| `created_at` | Timestamp of the event               |

---

### **2️⃣ Example: Login Event**

```bash
curl -X POST http://127.0.0.1:8000/auth/token \
  -F "grant_type=password" \
  -F "username=admin" \
  -F "password=adminpass"
```

✅ Response:

```json
{
  "access_token": "<ACCESS_TOKEN>",
  "refresh_token": "<REFRESH_TOKEN>",
  "id_token": "<ID_TOKEN>",
  "token_type": "bearer",
  "expires_in": 1800
}
```

> Audit log automatically created:

| id | user_id | event_type | details          | ip_address | user_agent  | created_at          |
| -- | ------- | ---------- | ---------------- | ---------- | ----------- | ------------------- |
| 1  | 1       | login      | Successful login | 127.0.0.1  | curl/7.85.0 | 2025-11-16 22:00:00 |

---

### **3️⃣ Example: Refresh Token Rotation Event**

```bash
curl -X POST http://127.0.0.1:8000/auth/token/refresh \
  -F "refresh_token=<REFRESH_TOKEN>"
```

✅ Response:

```json
{
  "access_token": "<NEW_ACCESS_TOKEN>",
  "refresh_token": "<NEW_REFRESH_TOKEN>",
  "id_token": "<ID_TOKEN>",
  "token_type": "bearer",
  "expires_in": 1800
}
```

> Audit log automatically created:

| id | user_id | event_type    | details                             | ip_address | user_agent  | created_at          |
| -- | ------- | ------------- | ----------------------------------- | ---------- | ----------- | ------------------- |
| 2  | 1       | refresh_token | Rotated refresh token old_session=5 | 127.0.0.1  | curl/7.85.0 | 2025-11-16 22:05:00 |

---

### **4️⃣ Example: Logout / Token Revocation**

```bash
curl -X POST http://127.0.0.1:8000/auth/revoke \
  -F "refresh_token=<REFRESH_TOKEN>"
```

✅ Response:

```json
{
  "detail": "Refresh token revoked successfully"
}
```

> Audit log automatically created:

| id | user_id | event_type | details               | ip_address | user_agent  | created_at          |
| -- | ------- | ---------- | --------------------- | ---------- | ----------- | ------------------- |
| 3  | 1       | logout     | Revoked refresh token | 127.0.0.1  | curl/7.85.0 | 2025-11-16 22:10:00 |

---

## 🔒 Security Hardening

The Custom Identity Platform implements multiple security best practices to protect authentication endpoints and sensitive user data.

### Password Policies

* Passwords must be at least 8 characters long.
* Include at least one uppercase letter, one lowercase letter, one number, and one special character.
* Password rules are reflected in the OpenAPI documentation for registration endpoints.

### Rate-Limiting

* Authentication endpoints (`/auth/token`, `/auth/register`) are rate-limited to prevent brute-force attacks.
* Default policy: **5 requests per minute per IP**.
* Example usage:

```bash
# Multiple rapid requests exceeding limit will receive HTTP 429
curl -X POST http://127.0.0.1:8000/auth/token -F "username=admin" -F "password=adminpass" -F "grant_type=password"
```

### HTTPS

* It is strongly recommended to serve all endpoints over HTTPS in production to encrypt tokens and credentials in transit.

### JWT Key Management

* JWT tokens are signed using RSA keys.
* Consider periodic rotation of JWT signing keys.
* The platform provides a public JWKS endpoint (`/.well-known/jwks.json`) to allow clients to validate tokens after key rotation.

---

### ✅ Summary of Security Features

* Strong password enforcement
* Rate-limiting on sensitive endpoints
* HTTPS for secure transport
* Refresh token rotation and revocation
* JWTs


## **Admin & User Management Endpoints**

This project now includes enhanced admin and user management endpoints with role-based access control, audit logging, and optional pagination/filtering.

### **Endpoints**

#### **1. Admin Dashboard**

```http
GET /admin/dashboard
```

* **Roles required:** `Admin`
* Returns a welcome message confirming access.

---

#### **2. Audit Logs**

```http
GET /admin/audit-logs?skip=0&limit=50
```

* **Roles required:** `Admin`
* Supports pagination with `skip` and `limit`.
* Returns recent audit logs, including admin actions like user deactivation and session revocation.

---

#### **3. List Users**

```http
GET /admin/users?skip=0&limit=50&username={username}&email={email}
```

* **Roles required:** `Admin`
* Supports pagination (`skip`, `limit`) and optional filtering by `username` or `email`.
* Returns a list of users with basic info.

---

#### **4. Deactivate User**

```http
POST /admin/users/{user_id}/deactivate
```

* **Roles required:** `Admin`
* Deactivates a user account.
* Action is logged in audit logs.

---

#### **5. List Active Sessions**

```http
GET /admin/sessions?skip=0&limit=50&user_id={user_id}
```

* **Roles required:** `Admin`
* Supports pagination (`skip`, `limit`) and optional filtering by `user_id`.
* Returns active sessions with session metadata.

---

#### **6. Revoke Session**

```http
POST /admin/sessions/{session_id}/revoke
```

* **Roles required:** `Admin`
* Revokes a session (sets `is_active` to `False` and `revoked` to `True`).
* Action is logged in audit logs.

---

### **Audit Logging**

All critical admin actions are logged via the `log_event` utility for compliance and traceability:

* User deactivation
* Session revocation
* Role or permission updates

Each log entry includes:

* User performing the action
* Action type
* Timestamp

---

### **Example: Admin List Users Response**

```json
[
  {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "is_active": true,
    "roles": ["User"]
  },
  {
    "id": 2,
    "username": "jane_admin",
    "email": "jane@example.com",
    "is_active": true,
    "roles": ["Admin"]
  }
]
```

---

### **Notes**

* All endpoints require an **access token** in the `Authorization` header.
* Role-based access is enforced via `role_required(["Admin"])`.
* Pagination and filtering help manage large datasets efficiently.
* Admin actions are tracked for **audit and compliance purposes**.

### **5️⃣ Implementation Notes**

1. **Database Table** – You should create an `audit_logs` table:

```python
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event_type = Column(String(50), nullable=False)
    details = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

1. **Utility function** – `log_event` captures events:

```python
def log_event(user_id: int | None, event_type: str, details: str = "", request: Request | None = None):
    ip_address = request.client.host if request else None
    user_agent = request.headers.get("user-agent") if request else None

    db = SessionLocal()
    try:
        audit = AuditLog(
            user_id=user_id,
            event_type=event_type,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(audit)
        db.commit()
    finally:
        db.close()
```

1. **Integration** – Add `log_event` calls to:

* `/auth/token` → `login` or `login_failed`
* `/auth/token/refresh` → `refresh_token`
* `/auth/revoke` → `logout`

---

## 📚 API Endpoints

| **Method** | **Endpoint**                 | **Access**    | **Description / Purpose**                                                                     |
| ---------- | ---------------------------- | ------------- | --------------------------------------------------------------------------------------------- |
| POST       | `/auth/register`             | Public        | Register a new user. Returns user info.                                                       |
| POST       | `/auth/token`                | Public        | Obtain access, refresh, and ID tokens. Supports password grant and authorization code (PKCE). |
| POST       | `/auth/token/refresh`        | Authenticated | Rotate refresh token and get new access + ID tokens.                                          |
| POST       | `/auth/token/revoke`         | Authenticated | Revoke a refresh token or session. User or admin can revoke.                                  |
| POST       | `/auth/logout`               | Authenticated | Log out the current session (revokes refresh token).                                          |
| GET        | `/me`                        | Authenticated | Return info about the currently authenticated user.                                           |
| GET        | `/userinfo`                  | Authenticated | Return user claims. Requires access token.                                                    |
| GET        | `/admin/dashboard`           | Admin         | Admin landing page / dashboard.                                                               |
| GET        | `/admin/audit-logs`          | Admin         | Retrieve audit logs with pagination (`skip`, `limit`).                                        |
| GET        | `/admin/users`               | Admin         | List and manage users. Supports pagination & filtering.                                       |
| POST       | `/admin/users/deactivate`    | Admin         | Deactivate a user account.                                                                    |
| GET        | `/admin/roles`               | Admin         | View and manage roles and permissions.                                                        |
| POST       | `/admin/roles`               | Admin         | Create or update roles/permissions.                                                           |
| GET        | `/admin/sessions`            | Admin         | View active sessions per user. Supports pagination & filtering.                               |
| POST       | `/admin/sessions/deactivate` | Admin         | Deactivate a specific session.                                                                |


---

## 📊 Flow Diagrams

```mermaid
flowchart TD
    subgraph Public Endpoints
        A1[POST /auth/register] -->|Creates user| A2[Return UserOut]
        B1[POST /auth/token] -->|Password Grant or Authorization Code Grant| B2[Return access_token, refresh_token, id_token]
    end

    subgraph Authenticated Endpoints
        C1[POST /auth/token/refresh] -->|Rotates refresh token| C2[Return new access_token, refresh_token, id_token]
        D1[POST /auth/logout] -->|Revoke current session| D2[Return message]
        E1[GET /me] -->|Return current user info| E2[UserOut]
        F1[GET /userinfo] -->|Return user claims| F2[UserOut]
        G1[POST /auth/token/revoke] -->|Revoke token/session| G2[Return detail]
    end

    subgraph Admin Endpoints
        H1[GET /admin/dashboard] -->|Admin access only| H2[Welcome message]
        I1[GET /admin/audit-logs] -->|Paginated logs| I2[Return logs]
        J1[GET /admin/users] -->|List/manage users| J2[Return users list]
        K1[POST /admin/users/deactivate] -->|Deactivate user| K2[Return status]
        L1[GET /admin/roles] -->|Manage roles/permissions| L2[Return roles]
        M1[POST /admin/roles] -->|Create/update roles| M2[Return status]
        N1[GET /admin/sessions] -->|View active sessions| N2[Return sessions]
        O1[POST /admin/sessions/deactivate] -->|Deactivate session| O2[Return status]
    end

    %% Connections
    A2 --> B1
    B2 --> C1
    B2 --> D1
    B2 --> E1
    B2 --> F1
    B2 --> G1
    H2 --> I1
    H2 --> J1
    H2 --> L1
    H2 --> N1
```

### Flow Explanation:

1. **User endpoints**

   * `/auth/register` → create new user.
   * `/auth/token` → obtain access and refresh tokens.
   * `/auth/token/refresh` → rotate refresh token.
   * `/auth/token/revoke` → revoke a session.
   * `/me` and `/userinfo` → get current user info.

2. **Admin endpoints**

   * `/admin/dashboard` → entry point for admin users.
   * `/admin/users` → list/manage users.
   * `/admin/roles` → manage roles and permissions.
   * `/admin/sessions` → view/revoke user sessions.

3. **Audit logging**

   * All key actions (logins, token refresh/revoke, admin actions) are recorded in `AuditLog`.

---

## 🙌 Contributing

PRs welcome — especially for:

* Distributed session stores (Redis)
* Mobile SDK helper modules
* Additional OAuth grant types
* More RBAC examples

---
