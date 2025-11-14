# Custom Identity Platform

A **Custom Identity Platform** built with **FastAPI**, **SQLAlchemy**, and **PostgreSQL**, providing secure authentication and authorization with **OAuth2**, **JWT access & refresh tokens**, and **Role-Based Access Control (RBAC)**.

This platform is designed for production-ready identity management — featuring token rotation, session tracking, **OpenID Connect–style user claims**, and **public key discovery for JWT validation**.

---

## 🧩 Table of Contents

* [Features](#features)
* [Dependencies](#dependencies)
* [Setup](#setup)
* [Database Setup & Migrations](#database-setup--migrations)
* [OAuth2 + JWT + Refresh Token Flow](#oauth2--jwt--refresh-token-flow)
* [User Info and JWKS Endpoints](#user-info-and-jwks-endpoints)
* [RBAC Setup](#rbac-setup)
* [Running the Application](#running-the-application)
* [API Endpoints](#api-endpoints)
* [JWT Authentication & Refresh Flow Diagram](#jwt-authentication--refresh-flow-diagram)
* [Expected Responses](#expected-responses)
* [Contributing](#contributing)

---

## 🚀 Features

* ✅ User registration with hashed passwords (bcrypt)
* ✅ OAuth2 Password Flow with JWT access tokens
* ✅ Refresh token rotation with database-backed session management
* ✅ Role-Based Access Control (RBAC) for endpoint protection
* ✅ **OpenID Connect–compatible `/userinfo` endpoint**
* ✅ **JWKS public key discovery endpoint (`/.well-known/jwks.json`)**
* ✅ Secure token revocation and expiration policies
* ✅ PostgreSQL + Alembic for migrations
* ✅ Clean modular FastAPI architecture
* ✅ Configuration management via `.env` and Pydantic Settings

---

## ⚙️ Dependencies

Key dependencies managed by **Poetry**:

* **FastAPI** – modern web framework
* **SQLAlchemy** – ORM
* **Alembic** – database migrations
* **psycopg2-binary** – PostgreSQL adapter
* **python-jose** – JWT handling
* **passlib[bcrypt]** – password hashing
* **Authlib** – OAuth2 utilities
* **pydantic-settings** – environment configuration
* **python-multipart** – form data handling

Install with:

```bash
poetry install
poetry shell
```

---

## ⚙️ Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/henrymbuguakiarie/custom_identity_platform.git
   cd custom_identity_platform
   ```

2. **Configure environment**

   Copy the example `.env` file and update it with your configuration:

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

3. **Generate RSA Key Pair**

   ```bash
   # Private key
   openssl genrsa -out private_key.pem 2048

   # Public key
   openssl rsa -in private_key.pem -pubout -out public_key.pem
   ```

4. **Run Alembic migrations**

   ```bash
   poetry run alembic upgrade head
   ```

5. **Seed RBAC roles, permissions, and admin user**

   ```bash
   python app/seeds/seed_rbac.py
   ```

   This ensures your roles, permissions, and default admin user are initialized.

---

## 🔑 OAuth2 + JWT + Refresh Token Flow

### 1. Login and Token Issuance

```bash
curl -X POST "http://127.0.0.1:8000/auth/token" \
-d "username=john&password=secret"
```

✅ Returns:

```json
{
  "access_token": "<JWT_ACCESS_TOKEN>",
  "refresh_token": "<JWT_REFRESH_TOKEN>",
  "token_type": "bearer"
}
```

---

### 2. Accessing Protected Endpoints

```bash
curl -H "Authorization: Bearer <ACCESS_TOKEN>" \
http://127.0.0.1:8000/auth/me
```

---

### 3. Refresh Token Rotation

```bash
curl -X POST http://127.0.0.1:8000/auth/token/refresh \
  -d "refresh_token=<YOUR_REFRESH_TOKEN>"
```

✅ Returns new tokens:

```json
{
  "access_token": "<NEW_ACCESS_TOKEN>",
  "refresh_token": "<NEW_REFRESH_TOKEN>",
  "token_type": "bearer"
}
```

---

### 4. Token Revocation

Refresh tokens are stored in the database and can be revoked by setting `revoked=True` in the `sessions` table.

---

## 🧾 User Info and JWKS Endpoints

### 1. `/auth/userinfo` — Retrieve User Claims

```bash
GET /auth/userinfo
```

Example:

```bash
curl -H "Authorization: Bearer <ACCESS_TOKEN>" \
http://127.0.0.1:8000/auth/userinfo
```

Response:

```json
{
  "sub": "user_id_123",
  "name": "John Doe",
  "email": "john@example.com",
  "roles": ["User"]
}
```

---

### 2. `/.well-known/jwks.json` — Public Key Discovery

```bash
GET /.well-known/jwks.json
```

Example:

```bash
curl http://127.0.0.1:8000/.well-known/jwks.json | jq
```

Response:

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

Seed roles, permissions, and the admin user:

```bash
python app/seeds/seed_rbac.py
```

Protect endpoints by role:

```python
from app.utils.auth import role_required
from fastapi import APIRouter

router = APIRouter()

@router.get("/admin/dashboard")
@role_required(["Admin"])
def admin_dashboard():
    return {"message": "Welcome, Admin! Access granted."}
```

Each JWT now carries user roles and claims for RBAC and `/userinfo`.

---

## 🪪 ID Token Support (OpenID Connect)

This platform now supports **ID Tokens** — short-lived JWTs that prove the user's identity to clients in **OpenID Connect (OIDC)**–compatible flows.

### 🔍 What is an ID Token?

An **ID Token** is a JSON Web Token (JWT) that contains information about the authenticated user.  
It’s typically issued alongside the **Access Token** and used by clients (like web or mobile apps) to verify the user’s identity.

### 📦 Standard Claims

Each ID token contains the following claims:

| Claim | Description |
|-------|--------------|
| `sub` | Subject — unique user identifier (usually the user ID) |
| `name` | User’s full name |
| `email` | User’s email address |
| `roles` | Custom claim — list of roles assigned to the user |
| `iss` | Issuer — your platform’s base URL |
| `aud` | Audience — the client ID |
| `iat` | Issued-at timestamp |
| `exp` | Expiration time |
| `auth_time` | (Optional) Time the user authenticated |

### ⏱️ Lifetime

ID tokens are **short-lived** (typically 15–30 minutes) to reduce risk if intercepted.

---

### 🧩 Example Response

After logging in through `/auth/token`, you’ll now receive **three tokens**:

```json
{
  "access_token": "<JWT_ACCESS_TOKEN>",
  "refresh_token": "<JWT_REFRESH_TOKEN>",
  "id_token": "<JWT_ID_TOKEN>",
  "token_type": "bearer"
}
````

### 🧠 Example Decoded ID Token

```json
{
  "sub": "1",
  "name": "Jane Doe",
  "email": "jane@example.com",
  "roles": ["User", "Admin"],
  "iss": "http://localhost:8000",
  "aud": "your-client-id",
  "iat": 1731449872,
  "exp": 1731450872
}
```

---

### 🧾 Decoding and Verifying the ID Token

#### 1️⃣ Decode (without verification)

You can safely inspect an ID token using `python-jose`:

```python
from jose import jwt

token = "<your_id_token_here>"
decoded = jwt.get_unverified_claims(token)
print(decoded)
```

#### 2️⃣ Decode (with verification)

If you want to verify the signature and audience:

```python
from jose import jwt
from app.config import settings

decoded = jwt.decode(
    token,
    settings.public_key,          # or settings.secret_key if using HS256
    algorithms=[settings.algorithm],
    audience=settings.default_aud,
)
print(decoded)
```

#### 3️⃣ View in Browser

You can also decode it visually using [https://jwt.io](https://jwt.io)
Paste your token and the corresponding public or secret key.

---

### ✅ ID Token Use Cases

* Verifying user identity on the client (e.g., web or mobile app)
* Displaying user information without another API call
* Integrating with OIDC-compatible clients

---

> ⚠️ **Security Note:**
> Never store ID tokens in insecure storage (like localStorage).
> Treat them like access tokens — store securely and refresh often.

---

## 🔑 Authorization Code Flow with PKCE

This platform supports **Authorization Code Flow with PKCE**, enabling SPAs and mobile apps to securely authenticate without exposing client secrets.

### Step 1: Request Authorization Code

Client sends a request to `/auth/authorize` with:

* `response_type=code`
* `client_id=<CLIENT_ID>`
* `redirect_uri=http://127.0.0.1:8000/callback`
* `scope=openid profile email`
* `state=xyz` (for CSRF protection)
* `code_challenge=<CODE_CHALLENGE>` (PKCE)
* `code_challenge_method=S256`

> If the user is not authenticated, the server shows a login form.
> After successful login, a temporary authorization code is generated and linked to the user, PKCE code challenge, redirect URI, and client ID.

Server responds with:

```
HTTP/1.1 302 Found
Location: http://127.0.0.1:8000/callback?code=<AUTH_CODE>&state=xyz
```

---

### Step 2: Exchange Authorization Code for Tokens

Client sends a POST request to `/auth/token` with:

```bash
curl -X POST "http://127.0.0.1:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=<AUTH_CODE>" \
  -d "redirect_uri=http://127.0.0.1:8000/callback" \
  -d "client_id=<CLIENT_ID>" \
  -d "code_verifier=<CODE_VERIFIER>"
```

Server validates:

1. `code_verifier` against the stored `code_challenge` (PKCE validation)
2. That the `code` matches the `client_id` and `redirect_uri`
3. That the code is unused and not expired

Returns:

```json
{
  "access_token": "<ACCESS_TOKEN>",
  "refresh_token": "<REFRESH_TOKEN>",
  "id_token": "<ID_TOKEN>",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

### Step 3: PKCE Validation

The server verifies the code using:

```python
verify_code_challenge(code_verifier, code_challenge, method="S256")
```

---

## 🧪 Testing Authorization Code Flow + PKCE with Curl

1. **Generate PKCE challenge and verifier**

```python
import secrets, hashlib, base64

code_verifier = secrets.token_urlsafe(64)
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode()).digest()
).decode().rstrip("=")

print("Code Verifier:", code_verifier)
print("Code Challenge:", code_challenge)
```

1. **Request authorization code**

```bash
curl -v "http://127.0.0.1:8000/auth/authorize?response_type=code&client_id=<CLIENT_ID>&redirect_uri=http://127.0.0.1:8000/callback&scope=openid%20profile%20email&state=xyz&code_challenge=<CODE_CHALLENGE>&code_challenge_method=S256&username=admin&password=adminpass"
```

1. **Exchange code for tokens**

```bash
curl -X POST "http://127.0.0.1:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=<AUTH_CODE>" \
  -d "redirect_uri=http://127.0.0.1:8000/callback" \
  -d "client_id=<CLIENT_ID>" \
  -d "code_verifier=<CODE_VERIFIER>"
```

---

### ✅ Notes

* PKCE ensures clients do **not need to store secrets** for public apps
* Authorization codes are **short-lived** and **single-use**
* ID tokens are returned alongside access tokens for OIDC compatibility


## ▶️ Running the Application

```bash
poetry run uvicorn app.main:app --reload
```

Access:

* Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* Root: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 📚 API Endpoints

| Endpoint                 | Method | Description                         |
| ------------------------ | ------ | ----------------------------------- |
| `/auth/register`         | POST   | Register a new user                 |
| `/auth/token`            | POST   | Get access + refresh tokens         |
| `/auth/token/refresh`    | POST   | Refresh tokens                      |
| `/auth/me`               | GET    | Get current authenticated user      |
| `/auth/userinfo`         | GET    | Get user claims (OpenID-style)      |
| `/.well-known/jwks.json` | GET    | Retrieve public signing keys (JWKS) |
| `/admin/dashboard`       | GET    | Admin-only route (RBAC protected)   |

---

## 🧠 Summary

| Feature                   | Description                              |
| ------------------------- | ---------------------------------------- |
| OAuth2 Password Grant     | ✅ Implemented                            |
| JWT Access Token          | ✅ Includes roles & claims                |
| Refresh Token             | ✅ Secure rotation + DB tracking          |
| Session Management        | ✅ Via `sessions` table                   |
| Role-Based Access Control | ✅ Enforced via decorators                |
| UserInfo Endpoint         | ✅ OIDC-style claims via `/auth/userinfo` |
| JWKS Endpoint             | ✅ Public key discovery for JWTs          |
| Token Revocation          | ✅ Supported                              |

---
