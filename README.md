# Custom Identity Platform

A **Custom Identity Platform** built with **FastAPI**, **SQLAlchemy**, and **PostgreSQL**, providing secure authentication and authorization with **OAuth2**, **JWT access & refresh tokens**, and **Role-Based Access Control (RBAC)**.

This platform is designed for production-ready identity management — featuring token rotation, session tracking, **OpenID Connect–style user claims**, **public key discovery for JWT validation**, and **secure refresh token handling**.

---

## 🧩 Table of Contents

* [Features](#features)
* [Dependencies](#dependencies)
* [Setup](#setup)
* [Database Setup & Migrations](#database-setup--migrations)
* [Seeding RBAC, Users & OAuth Clients](#seeding-rbac-users--oauth-clients)
* [OAuth2 + JWT + Refresh Token Flow](#oauth2--jwt--refresh-token-flow)
* [Refresh Token Rotation & Revocation](#refresh-token-rotation--revocation)
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
* ✅ Refresh token revocation (manual & automatic)
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

---

## ⚙️ Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/henrymbuguakiarie/custom_identity_platform.git
   cd custom_identity_platform
   ```

1. **Configure environment**

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

1. **Generate RSA Key Pair**

   ```bash
   # Private key
   openssl genrsa -out private_key.pem 2048

   # Public key
   openssl rsa -in private_key.pem -pubout -out public_key.pem
   ```

1. **Install dependencies**

   ```bash
   poetry install

1. **Run Alembic migrations**

   ```bash
   poetry run alembic upgrade head
   ```

---

## 🪴 Seeding RBAC, Users & OAuth Clients

Run the following commands to initialize roles, permissions, default admin user, and OAuth clients:

1. **Seed RBAC roles, permissions, and admin user**:

    ```bash
    python -m app.utils.seed_rbac
    ```

1. **Seed a public OAuth client (SPA)**:

    ```bash
    python -m app.utils.seed_oauth_client
    ```

    > This script generates a `client_id` dynamically and saves it to `oauth_client.json`.

1. **Update redirect URIs**:

    ```bash
    python -m app.utils.update_redirect_uris
    ```

    > This script reads the `client_id` from `oauth_client.json` and updates redirect URIs.

1. **Optional combined workflow**:

    You can also run the **idempotent script** which handles both seeding and redirect URI updates:

    ```bash
    python -m app.utils.seed_or_update_oauth_client
    ```

---

## 🔑 OAuth2 + JWT + Refresh Token Flow

### 1️⃣ Login and Token Issuance

```bash
curl -X POST http://127.0.0.1:8000/auth/token \
  -F "grant_type=password" \
  -F "username=admin" \
  -F "password=adminpass"
```

✅ Example Response:

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

### 2️⃣ Accessing Protected Endpoints

```bash
 curl -X POST -H "Authorization: Bearer <ACCESS_TOKEN>" \
http://127.0.0.1:8000/auth/me
```

---

## 🔄 Refresh Token Rotation & Revocation

### Refresh Token Rotation

```bash
curl -X POST http://127.0.0.1:8000/auth/token/refresh \
  -F "refresh_token=<REFRESH_TOKEN>"
```

✅ Example Response:

```json
{
  "access_token": "<NEW_ACCESS_TOKEN>",
  "refresh_token": "<NEW_REFRESH_TOKEN>",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Notes:**

* Old refresh tokens are **revoked automatically** after use.
* Always store the **new refresh token** securely.

### Manual Token Revocation (Logout)

```bash
curl -X POST http://127.0.0.1:8000/auth/revoke \
  -F "refresh_token=<REFRESH_TOKEN>"
```

✅ Example Response:

```json
{
  "detail": "Refresh token revoked successfully"
}
```

After revocation, using the same refresh token returns:

```json
{
  "detail": "Invalid or revoked refresh token"
}
```

### Automatic Token Invalidation

Tokens are **automatically invalidated** when:

* A user changes their **password**
* A user’s **roles** change

---

## 🧾 User Info and JWKS Endpoints

### `/auth/userinfo` — Retrieve User Claims

```bash
GET /auth/userinfo
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

### `/.well-known/jwks.json` — Public Key Discovery

```bash
GET /.well-known/jwks.json
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
python -m app.utils.seed_rbac
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

---

## ▶️ Running the Application

```bash
poetry run uvicorn app.main:app --reload
```

Access:

* Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* Root: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 📚 API Endpoints

| Endpoint                 | Method   | Description                       |
| ------------------------ | -------- | --------------------------------- |
| `/auth/register`         | POST     | Register a new user               |
| `/auth/token`            | POST     | Get access + refresh + ID tokens  |
| `/auth/token/refresh`    | POST     | Refresh tokens                    |
| `/auth/revoke`           | POST     | Revoke refresh token              |
| `/auth/authorize`        | GET/POST | Authorization Code Flow (PKCE)    |
| `/auth/me`               | GET      | Get current authenticated user    |
| `/auth/userinfo`         | GET      | Get user claims (OpenID-style)    |
| `/.well-known/jwks.json` | GET      | Retrieve public signing keys      |
| `/admin/dashboard`       | GET      | Admin-only route (RBAC protected) |

