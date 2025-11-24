# Security Recommendations & Action Items
**Custom Identity Platform - Security Focus**

---

## 🚨 CRITICAL - Address Immediately (This Week)

### 1. Remove JWT Access Token Storage
**Current Issue:**
```python
# app/models/rbac.py:76
session_token = Column(String(1024), unique=True, nullable=True)

# app/core/security.py:99
session.session_token = access_token  # ❌ Don't store JWT
```

**Impact:** 
- Increases attack surface
- JWT tokens are self-contained and don't need database storage
- If database is compromised, all tokens are exposed

**Fix:**
```python
# Option 1: Remove the column entirely
# In migration: DROP COLUMN session_token

# Option 2: Use it for session identifier, not JWT
session.session_token = secrets.token_urlsafe(32)  # ✅ Random ID instead

# Update validation to not query by JWT
# app/core/dependencies.py:34
# Remove: session = db.query(UserSession).filter_by(session_token=token...)
# Instead: Decode JWT to get session ID, then validate session
```

**Estimated Time:** 4 hours

---

### 2. Implement Account Lockout
**Current Issue:**
- No protection against brute force beyond rate limiting (5/min)
- Attacker can try 7,200 passwords per day (5 per min * 1,440 min)

**Implementation:**
```python
# Add to User model
class User(Base):
    # ...existing fields...
    failed_login_attempts = Column(Integer, default=0)
    account_locked_until = Column(DateTime, nullable=True)
    last_failed_login = Column(DateTime, nullable=True)

# In authenticate_user
def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    
    # Check if account is locked
    if user and user.account_locked_until:
        if user.account_locked_until > datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account locked until {user.account_locked_until}"
            )
        else:
            # Unlock account
            user.account_locked_until = None
            user.failed_login_attempts = 0
            db.commit()
    
    if not user or not verify_password(password, user.password_hash):
        if user:
            user.failed_login_attempts += 1
            user.last_failed_login = datetime.utcnow()
            
            # Lock after 5 failed attempts
            if user.failed_login_attempts >= 5:
                user.account_locked_until = datetime.utcnow() + timedelta(minutes=30)
                log_event(
                    user_id=user.id, 
                    event_type="account_locked",
                    details="5 failed login attempts"
                )
            
            db.commit()
        return None
    
    # Successful login - reset counter
    user.failed_login_attempts = 0
    user.account_locked_until = None
    db.commit()
    
    return user
```

**Migration:**
```bash
alembic revision --autogenerate -m "add_account_lockout_fields"
alembic upgrade head
```

**Estimated Time:** 4 hours

---

### 3. Validate Password Length
**Current Issue:**
```python
# app/core/security.py:25
def hash_password(password: str) -> str:
    return pwd_context.hash(password[:72])  # ❌ Silent truncation
```

**Fix:**
```python
# app/schemas/user.py
from pydantic import validator, BaseModel
import re

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if len(v) > 72:
            raise ValueError('Password must not exceed 72 characters (bcrypt limit)')
        
        # Password complexity
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        
        return v
    
    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if len(v) > 50:
            raise ValueError('Username must not exceed 50 characters')
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username can only contain letters, numbers, and underscores')
        return v

# Remove truncation from hash_password
def hash_password(password: str) -> str:
    # Validation should happen before this point
    if len(password) > 72:
        raise ValueError("Password exceeds maximum length")
    return pwd_context.hash(password)
```

**Estimated Time:** 2 hours

---

### 4. Encrypt MFA Secrets
**Current Issue:**
```python
# app/models/user.py:18
mfa_secret = Column(String, nullable=True)  # ❌ Stored in plaintext
```

**Fix Using Fernet Encryption:**
```python
# app/core/encryption.py (new file)
from cryptography.fernet import Fernet
from app.config import settings

# Generate key: Fernet.generate_key()
# Store in environment: ENCRYPTION_KEY=...
fernet = Fernet(settings.encryption_key.encode())

def encrypt_secret(secret: str) -> str:
    """Encrypt a secret for database storage"""
    return fernet.encrypt(secret.encode()).decode()

def decrypt_secret(encrypted: str) -> str:
    """Decrypt a secret from database"""
    return fernet.decrypt(encrypted.encode()).decode()

# Usage in MFA setup
@router.post("/auth/mfa/setup")
def setup_mfa(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    secret = pyotp.random_base32()
    
    # Encrypt before storing
    user = db.query(User).filter_by(id=current_user.id).first()
    user.mfa_secret = encrypt_secret(secret)  # ✅ Encrypted
    db.commit()
    
    # Return QR code with unencrypted secret
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user.email,
        issuer_name="Custom Identity Platform"
    )
    return {"secret": secret, "qr_code": totp_uri}

# Usage in verification
def verify_mfa(user: User, code: str) -> bool:
    if not user.mfa_secret:
        return False
    
    decrypted_secret = decrypt_secret(user.mfa_secret)  # ✅ Decrypt
    totp = pyotp.TOTP(decrypted_secret)
    return totp.verify(code, valid_window=1)
```

**Add to .env:**
```env
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# ⚠️ CRITICAL: Generate separate keys for each environment (dev, staging, prod)
# ⚠️ NEVER commit encryption keys to version control
# ⚠️ Store production keys in a secure secrets manager
ENCRYPTION_KEY=your-fernet-key-here
```

**Security Notes:**
- Generate unique encryption keys for each environment
- Rotate keys periodically (every 90 days recommended)
- Store production keys in AWS Secrets Manager or HashiCorp Vault
- Never commit keys to version control
- Document key rotation procedures

**Estimated Time:** 3 hours

---

## ⚠️ HIGH PRIORITY - This Month

### 5. Implement Comprehensive Input Validation

**Missing Validation Areas:**
1. Redirect URIs (must be HTTPS)
2. Email formats (additional validation)
3. Session IDs (must be integers)
4. Pagination limits (max value)

**Implementation:**
```python
# app/core/validators.py (new file)
from urllib.parse import urlparse
import re

def validate_redirect_uri(uri: str) -> bool:
    """Validate OAuth redirect URI"""
    parsed = urlparse(uri)
    
    # Must use HTTPS in production
    if settings.environment == "production" and parsed.scheme != "https":
        raise ValueError("Redirect URI must use HTTPS in production")
    
    # Must have a valid domain
    if not parsed.netloc:
        raise ValueError("Redirect URI must have a valid domain")
    
    # No fragments allowed
    if parsed.fragment:
        raise ValueError("Redirect URI cannot contain fragments")
    
    return True

def validate_pagination(skip: int, limit: int) -> tuple[int, int]:
    """Validate and sanitize pagination parameters"""
    skip = max(0, skip)  # Minimum 0
    limit = max(1, min(limit, 100))  # Between 1 and 100
    return skip, limit

# Apply in routes
@router.get("/admin/audit-logs")
def get_audit_logs(
    current_user=Depends(role_required(["Admin"])),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    skip, limit = validate_pagination(skip, limit)  # ✅ Validate
    # ... rest of function
```

**Estimated Time:** 6 hours

---

### 6. Implement Secrets Management

**Current Issue:**
- Secrets in .env files
- No rotation mechanism
- Keys loaded on import

**Solution: Use AWS Secrets Manager or HashiCorp Vault**

```python
# app/config.py
import boto3
from botocore.exceptions import ClientError
import json

class Settings(BaseSettings):
    # Environment determines where to get secrets
    environment: str = "development"
    aws_region: str = "us-east-1"
    secrets_path: str = "custom-identity-platform"
    
    # Development defaults
    secret_key: str = None
    algorithm: str = "RS256"
    # ...
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Load secrets from AWS Secrets Manager in production
        if self.environment == "production":
            self._load_aws_secrets()
    
    def _load_aws_secrets(self):
        """Load secrets from AWS Secrets Manager"""
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=self.aws_region
        )
        
        try:
            response = client.get_secret_value(SecretId=self.secrets_path)
            secrets = json.loads(response['SecretString'])
            
            # Update settings with secrets
            self.secret_key = secrets['SECRET_KEY']
            self.database_url = secrets['DATABASE_URL']
            self.encryption_key = secrets['ENCRYPTION_KEY']
            # ...
        except ClientError as e:
            raise ValueError(f"Failed to load secrets: {e}")

# Lazy load settings
_settings = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

settings = get_settings()
```

**Key Rotation Script:**
```python
# scripts/rotate_jwt_keys.py
from app.core.security import rotate_keys
from app.config import settings
import boto3

def rotate_jwt_keys():
    """Rotate JWT signing keys"""
    # Generate new keys
    new_private_path = f"./keys/private_key_{timestamp}.pem"
    new_public_path = f"./keys/public_key_{timestamp}.pem"
    
    rotate_keys(new_private_path, new_public_path)
    
    # Upload to secrets manager
    # Update settings
    # Keep old key for 24 hours to validate existing tokens
    
    print("JWT keys rotated successfully")

if __name__ == "__main__":
    rotate_jwt_keys()
```

**Estimated Time:** 16 hours

---

### 7. Add Distributed Rate Limiting

**Current Issue:**
- Rate limiting per instance only
- Can be bypassed in multi-instance setup

**Solution: Use Redis backend**

```python
# requirements: slowapi with redis backend
# poetry add redis

# app/main.py
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
import redis

# Redis connection for distributed rate limiting
redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=0,
    decode_responses=True
)

# Use Redis as storage backend
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=f"redis://{settings.redis_host}:{settings.redis_port}/0"
)

app = FastAPI(title="Custom Identity Platform API")
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# Enhanced rate limiting with multiple tiers
@router.post("/token")
@limiter.limit("5/minute")  # IP-based
@limiter.limit("20/hour", key_func=lambda request: f"user:{request.form.get('username')}")  # User-based
def token_endpoint(...):
    # ...
```

**Add to .env:**
```env
REDIS_HOST=localhost
REDIS_PORT=6379
```

**Estimated Time:** 8 hours

---

## 📋 MEDIUM PRIORITY - Next Quarter

### 8. Implement Service Layer

**Current Issue:**
- Business logic in route handlers
- Difficult to test
- Code duplication

**Solution:**
```python
# app/services/auth_service.py
from typing import Optional, Tuple
from sqlalchemy.orm import Session

class AuthenticationService:
    """Service for authentication operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def authenticate_user(
        self, 
        username: str, 
        password: str,
        mfa_code: Optional[str] = None
    ) -> Tuple[User, str, str, str]:
        """
        Authenticate user with username, password, and optional MFA
        
        Returns: (user, access_token, refresh_token, id_token)
        Raises: HTTPException on failure
        """
        user = self._validate_credentials(username, password)
        self._validate_account_status(user)
        
        if user.mfa_secret:
            self._validate_mfa(user, mfa_code)
        
        session, refresh_token, access_token = self._create_session(user)
        id_token = self._create_id_token(user)
        
        self._log_login(user)
        
        return user, access_token, refresh_token, id_token
    
    def _validate_credentials(self, username: str, password: str) -> User:
        """Validate username and password"""
        # Implementation
        pass
    
    def _validate_account_status(self, user: User):
        """Check if account is locked or inactive"""
        # Implementation
        pass
    
    def _validate_mfa(self, user: User, code: Optional[str]):
        """Validate MFA code if required"""
        # Implementation
        pass
    
    # ... other methods

# Usage in routes
@router.post("/token")
def token_endpoint(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    auth_service = AuthenticationService(db)
    user, access_token, refresh_token, id_token = auth_service.authenticate_user(
        form_data.username,
        form_data.password
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "id_token": id_token,
        "token_type": "bearer"
    }
```

**Estimated Time:** 24 hours

---

### 9. Improve Test Coverage to 80%

**Current Coverage:** ~20%  
**Target:** 80%+

**Testing Strategy:**
```python
# tests/test_auth_service.py
import pytest
from app.services.auth_service import AuthenticationService

class TestAuthentication:
    def test_successful_login(self, db_session, create_test_user):
        user = create_test_user()
        service = AuthenticationService(db_session)
        
        result = service.authenticate_user("user1", "StrongP@ss1")
        
        assert result[0].id == user.id
        assert result[1]  # access_token
        assert result[2]  # refresh_token
    
    def test_failed_login_increments_counter(self, db_session, create_test_user):
        user = create_test_user()
        service = AuthenticationService(db_session)
        
        with pytest.raises(HTTPException):
            service.authenticate_user("user1", "wrongpassword")
        
        db_session.refresh(user)
        assert user.failed_login_attempts == 1
    
    def test_account_lockout_after_5_attempts(self, db_session, create_test_user):
        user = create_test_user()
        service = AuthenticationService(db_session)
        
        # Try 5 failed logins
        for i in range(5):
            with pytest.raises(HTTPException):
                service.authenticate_user("user1", "wrongpassword")
        
        db_session.refresh(user)
        assert user.account_locked_until is not None
        
        # 6th attempt should be blocked
        with pytest.raises(HTTPException) as exc_info:
            service.authenticate_user("user1", "StrongP@ss1")
        
        assert "locked" in str(exc_info.value.detail).lower()

# tests/test_mfa.py
class TestMFA:
    def test_mfa_setup_generates_secret(self, client, authenticated_user):
        response = client.post("/auth/mfa/setup")
        assert response.status_code == 200
        assert "secret" in response.json()
        assert "qr_code" in response.json()
    
    def test_mfa_required_when_enabled(self, client, user_with_mfa):
        response = client.post("/auth/token", data={
            "grant_type": "password",
            "username": "user1",
            "password": "StrongP@ss1"
        })
        assert response.status_code == 401
        assert "MFA code required" in response.json()["detail"]

# tests/test_admin.py
class TestAdminEndpoints:
    def test_admin_dashboard_requires_admin_role(self, client, regular_user):
        response = client.get("/admin/dashboard")
        assert response.status_code == 403
    
    def test_deactivate_user_logs_action(self, client, admin_user, db_session):
        response = client.post("/admin/users/1/deactivate")
        assert response.status_code == 200
        
        # Check audit log
        log = db_session.query(AuditLog).filter_by(
            event_type="deactivated user user1"
        ).first()
        assert log is not None
```

**Estimated Time:** 40 hours

---

### 10. Add Monitoring and Alerting

**Implementation:**
```python
# app/middleware/metrics.py
from prometheus_client import Counter, Histogram, generate_latest
from fastapi import Request
import time

# Metrics
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

auth_failures = Counter(
    'auth_failures_total',
    'Total authentication failures',
    ['reason']
)

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

**Alerts Configuration (Prometheus):**
```yaml
# alerts.yml
groups:
  - name: authentication
    rules:
      - alert: HighAuthFailureRate
        expr: rate(auth_failures_total[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High authentication failure rate"
          
      - alert: AccountLockoutsIncreasing
        expr: rate(account_locked_total[1h]) > 5
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Multiple accounts being locked"
```

**Estimated Time:** 16 hours

---

## 📊 Progress Tracking

### Week 1 Checklist
- [ ] Remove JWT storage from database
- [ ] Implement account lockout
- [ ] Add password validation
- [ ] Encrypt MFA secrets
- [ ] Fix all linting errors
- [ ] Set up test environment

### Month 1 Checklist
- [ ] Complete all Week 1 items
- [ ] Implement input validation
- [ ] Set up secrets management
- [ ] Add distributed rate limiting
- [ ] Increase test coverage to 50%
- [ ] Add monitoring basics

### Quarter 1 Checklist
- [ ] Complete all Month 1 items
- [ ] Implement service layer
- [ ] Test coverage to 80%
- [ ] Complete monitoring and alerting
- [ ] Security audit
- [ ] Documentation complete

---

## 🎯 Success Metrics

### Security Metrics
- [ ] Zero critical vulnerabilities
- [ ] All secrets encrypted or in secrets manager
- [ ] 100% of endpoints validated
- [ ] Rate limiting on all sensitive endpoints
- [ ] Account lockout working (test with pentesting)

### Quality Metrics
- [ ] Test coverage > 80%
- [ ] Zero linting errors
- [ ] All functions documented
- [ ] CI/CD passing
- [ ] Load tests passing

### Operations Metrics
- [ ] Monitoring in place
- [ ] Alerting configured
- [ ] Incident runbooks complete
- [ ] Backup/restore tested
- [ ] Key rotation documented and tested

---

**Document Version:** 1.0  
**Last Updated:** November 24, 2025  
**Next Review:** December 1, 2025
