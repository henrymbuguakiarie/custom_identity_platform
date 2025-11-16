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

## ▶️ Running the Application

```bash
poetry run uvicorn app.main:app --reload
```

Open:

* Docs → [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* Root → [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 📚 API Endpoints

| Endpoint                 | Method   | Description                  |
| ------------------------ | -------- | ---------------------------- |
| `/auth/register`         | POST     | Register a user              |
| `/auth/token`            | POST     | Access + refresh + ID tokens |
| `/auth/token/refresh`    | POST     | Rotate refresh token         |
| `/auth/revoke`           | POST     | Revoke refresh token         |
| `/auth/authorize`        | GET/POST | PKCE Authorization Code      |
| `/auth/me`               | GET      | Current authenticated user   |
| `/auth/userinfo`         | GET      | OIDC user claims             |
| `/.well-known/jwks.json` | GET      | Public signing keys          |
| `/admin/dashboard`       | GET      | RBAC-protected route         |

---

## 📊 Flow Diagrams

*(Optional — I can generate beautiful diagrams if you want them.)*

---

## 🙌 Contributing

PRs welcome — especially for:

* Distributed session stores (Redis)
* Mobile SDK helper modules
* Additional OAuth grant types
* More RBAC examples

---
