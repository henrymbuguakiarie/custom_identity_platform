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

✅ User registration with hashed passwords (bcrypt)
✅ OAuth2 Password Flow with JWT access tokens
✅ Refresh token rotation with database-backed session management
✅ Role-Based Access Control (RBAC) for endpoint protection
✅ **OpenID Connect–compatible `/userinfo` endpoint**
✅ **JWKS public key discovery endpoint (`/.well-known/jwks.json`)**
✅ Secure token revocation and expiration policies
✅ PostgreSQL + Alembic for migrations
✅ Clean modular FastAPI architecture
✅ Configuration management via Pydantic Settings

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

1. **Configure environment**

   Edit `app/config.py` or `.env` to include:

   ```python
   secret_key = "your_secret_key"
   algorithm = "RS256"
   access_token_expire_minutes = 30
   refresh_token_expire_days = 7
   database_url = "postgresql+psycopg2://postgres:password@localhost:5432/identity_db"
   private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
   public_key = "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
   ```

1. **Run Alembic migrations**

   ```bash
   poetry run alembic upgrade head
   ```

---

## 🔑 OAuth2 + JWT + Refresh Token Flow

This platform implements a **complete token lifecycle** for secure user authentication.

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
curl -H "Authorization: Bearer <access_token>" \
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

This endpoint returns standard OpenID Connect–style claims about the authenticated user.

**Endpoint:**

```
GET /auth/userinfo
```

**Example:**

```bash
curl -H "Authorization: Bearer <ACCESS_TOKEN>" \
http://127.0.0.1:8000/auth/userinfo
```

**Response:**

```json
{
  "sub": "user_id_123",
  "name": "John Doe",
  "email": "john@example.com",
  "roles": ["User"]
}
```

**Purpose:**

* Enables clients to retrieve user profile and claims using the access token.
* Mimics the `/userinfo` endpoint in OpenID Connect.

---

### 2. `/.well-known/jwks.json` — Public Key Discovery

This endpoint exposes your **JSON Web Key Set (JWKS)** used to verify JWT signatures.

**Endpoint:**

```
GET /.well-known/jwks.json
```

**Example:**

```bash
curl http://127.0.0.1:8000/.well-known/jwks.json | jq
```

**Response:**

```json
{
  "keys": [
    {
      "kty": "RSA",
      "use": "sig",
      "kid": "rsa1",
      "alg": "RS256",
      "n": "sM7f2u8YqM0...",
      "e": "AQAB"
    }
  ]
}
```

**Purpose:**

* Allows external clients or services to validate tokens signed by your platform.
* Conforms to OpenID Connect Discovery specifications.

---

## 🧱 RBAC Setup

Follow the same steps to seed roles, assign permissions, and protect routes.
Each JWT now carries user roles and claims for both RBAC and `/userinfo`.

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
