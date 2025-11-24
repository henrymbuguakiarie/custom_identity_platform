# Quick Reference Checklist
**Custom Identity Platform - Developer Quick Guide**

---

## ✅ Immediate Actions (Do Today)

### 1. Review Documents
- [ ] Read `REVIEW_SUMMARY.md` (5 min read)
- [ ] Skim `CODE_REVIEW.md` (browse sections relevant to your work)
- [ ] Review `SECURITY_RECOMMENDATIONS.md` (focus on your areas)

### 2. Fix Critical Bug (Already Fixed)
✅ **DONE:** Missing import in `app/routes/admin.py` - Fixed in this PR

### 3. Code Quality Quick Fixes
```bash
# Install dev dependencies if not already installed
poetry install

# Format code automatically
poetry run black app tests

# Sort imports
poetry run isort app tests

# Check for issues
poetry run flake8 app tests --max-line-length=120
```

Expected: Most of 115 linting issues will be auto-fixed by black and isort

---

## 🚨 Week 1 Priority (This Week)

### Security Critical Items

#### 1. Remove JWT Storage (4 hours)
**File:** `app/core/security.py`, `app/core/dependencies.py`, `app/models/rbac.py`

**What to do:**
- [ ] Stop storing JWT access tokens in database
- [ ] Use session ID instead for validation
- [ ] Update session validation logic

**Quick check:**
```python
# Before: session.session_token = jwt_access_token  ❌
# After: session.session_token = secrets.token_urlsafe(32)  ✅
```

#### 2. Implement Account Lockout (4 hours)
**Files:** `app/models/user.py`, `app/crud/user_crud.py`

**What to do:**
- [ ] Add fields: `failed_login_attempts`, `account_locked_until`
- [ ] Create migration: `alembic revision --autogenerate -m "add_lockout_fields"`
- [ ] Update `authenticate_user` function
- [ ] Add tests for lockout behavior

**Quick test:**
```bash
# Try 5 wrong passwords - should lock account
# Try correct password - should be denied
```

#### 3. Add Password Validation (2 hours)
**File:** `app/schemas/user.py`

**What to do:**
- [ ] Add Pydantic validator for password length (8-72 chars)
- [ ] Add complexity checks (uppercase, lowercase, digit, special)
- [ ] Remove truncation from `hash_password`

**Quick test:**
```python
# Should reject: "short"
# Should reject: "verylongpassword" * 10  # > 72 chars
# Should reject: "alllowercase123"  # no uppercase
# Should accept: "StrongP@ss123"
```

#### 4. Encrypt MFA Secrets (3 hours)
**Files:** Create `app/core/encryption.py`, update MFA endpoints

**What to do:**
- [ ] Install: `poetry add cryptography`
- [ ] Generate encryption key: `Fernet.generate_key()`
- [ ] Add to .env: `ENCRYPTION_KEY=...`
- [ ] Create encrypt/decrypt functions
- [ ] Update MFA setup/verify to use encryption

---

## 📋 Development Standards

### Code Style
```python
# ✅ Good
def create_user(
    db: Session,
    username: str,
    email: str,
    password: str
) -> User:
    """
    Create a new user in the database.
    
    Args:
        db: Database session
        username: Unique username
        email: Valid email address
        password: Raw password (will be hashed)
    
    Returns:
        User: Created user object
    
    Raises:
        ValueError: If username already exists
    """
    # Implementation

# ❌ Bad
def create_user(db,username,email,password):
    # No docstring, no type hints, poor formatting
    pass
```

### Error Handling
```python
# ✅ Good
try:
    user = authenticate_user(db, username, password)
except ValueError as e:
    log_event(None, "login_failed", details=str(e))
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )

# ❌ Bad
try:
    user = authenticate_user(db, username, password)
except:
    pass  # Silent failure
```

### Database Operations
```python
# ✅ Good
def update_user(db: Session, user_id: int, updates: dict) -> User:
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found")
    
    for key, value in updates.items():
        setattr(user, key, value)
    
    db.commit()
    db.refresh(user)
    return user

# ❌ Bad
def update_user(db, user_id, updates):
    user = db.query(User).get(user_id)  # Can return None
    user.username = updates["username"]  # Crashes if None
    db.commit()
    return user  # Not refreshed
```

---

## 🧪 Testing Standards

### Required Tests for New Features
1. **Happy path** - Feature works as expected
2. **Error cases** - Feature handles errors gracefully
3. **Edge cases** - Boundary conditions
4. **Security** - No vulnerabilities introduced

### Example Test Structure
```python
class TestUserAuthentication:
    """Tests for user authentication"""
    
    def test_successful_login(self, client, create_test_user):
        """Test that valid credentials return tokens"""
        create_test_user(username="test", password="Test123!")
        
        response = client.post("/auth/token", data={
            "grant_type": "password",
            "username": "test",
            "password": "Test123!"
        })
        
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "refresh_token" in response.json()
    
    def test_invalid_password_fails(self, client, create_test_user):
        """Test that invalid password returns 401"""
        create_test_user(username="test", password="Test123!")
        
        response = client.post("/auth/token", data={
            "grant_type": "password",
            "username": "test",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
    
    def test_account_lockout_after_failures(self, client, create_test_user):
        """Test that 5 failed attempts lock account"""
        create_test_user(username="test", password="Test123!")
        
        # Attempt 5 failed logins
        for _ in range(5):
            client.post("/auth/token", data={
                "grant_type": "password",
                "username": "test",
                "password": "wrong"
            })
        
        # 6th attempt should be locked
        response = client.post("/auth/token", data={
            "grant_type": "password",
            "username": "test",
            "password": "Test123!"  # Even with correct password
        })
        
        assert response.status_code == 403
        assert "locked" in response.json()["detail"].lower()
```

### Running Tests
```bash
# Run all tests
poetry run pytest tests/ -v

# Run specific test file
poetry run pytest tests/test_auth.py -v

# Run with coverage
poetry run pytest tests/ --cov=app --cov-report=html

# Run specific test
poetry run pytest tests/test_auth.py::TestUserAuthentication::test_successful_login -v
```

---

## 🔍 Code Review Checklist

### Before Submitting PR
- [ ] Code formatted with black
- [ ] Imports sorted with isort
- [ ] No flake8 errors
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Docstrings added to new functions
- [ ] Type hints on all functions
- [ ] No hardcoded secrets or credentials
- [ ] Error handling implemented
- [ ] Logging added for important operations

### Security Checklist
- [ ] Input validation on all user inputs
- [ ] No SQL injection vulnerabilities (use ORM)
- [ ] No secrets in code or logs
- [ ] Sensitive data encrypted if stored
- [ ] Authentication required where needed
- [ ] Authorization checks in place
- [ ] Rate limiting considered
- [ ] Error messages don't leak sensitive info

---

## 📚 Common Tasks

### Add New Endpoint
```python
# 1. Define route in app/routes/
@router.post("/users/{user_id}/action")
def perform_action(
    user_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Perform action on user.
    
    Requires: User must be admin or self
    """
    # Validate authorization
    if current_user.id != user_id and "Admin" not in [r.name for r in current_user.roles]:
        raise HTTPException(403, "Not authorized")
    
    # Perform action
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    # Log action
    log_event(current_user.id, "action_performed", details=f"user_id={user_id}")
    
    return {"status": "success"}

# 2. Add tests in tests/
def test_perform_action_as_self(client, authenticated_user):
    response = client.post(f"/users/{authenticated_user.id}/action")
    assert response.status_code == 200

# 3. Update documentation if needed
```

### Add Database Migration
```bash
# 1. Modify model in app/models/
class User(Base):
    # Add new field
    new_field = Column(String(100), nullable=True)

# 2. Generate migration
poetry run alembic revision --autogenerate -m "add_new_field_to_user"

# 3. Review migration file in alembic/versions/
# Edit if needed

# 4. Apply migration
poetry run alembic upgrade head

# 5. Test rollback
poetry run alembic downgrade -1
poetry run alembic upgrade head
```

### Add New Validation
```python
# In app/schemas/
class UserUpdate(BaseModel):
    email: Optional[EmailStr]
    phone: Optional[str]
    
    @validator('phone')
    def validate_phone(cls, v):
        if v is None:
            return v
        
        # Simple validation - adjust as needed
        import re
        if not re.match(r'^\+?1?\d{9,15}$', v):
            raise ValueError('Invalid phone number format')
        
        return v
```

---

## 🐛 Debugging Tips

### Check Logs
```bash
# Application logs
poetry run uvicorn app.main:app --log-level debug

# Check database
poetry run alembic current  # Current migration
poetry run alembic history  # Migration history
```

### Common Issues

**Issue: Tests fail with validation errors**
```python
# Solution: Mock settings in conftest.py
import os
os.environ.update({
    'SECRET_KEY': 'test-secret',
    'ALGORITHM': 'HS256',
    'ACCESS_TOKEN_EXPIRE_MINUTES': '30',
    'REFRESH_TOKEN_EXPIRE_DAYS': '7',
    # ... other required settings
})
```

**Issue: Import errors**
```bash
# Solution: Install app as package
poetry install
```

**Issue: Database locked (SQLite)**
```bash
# Solution: Close all connections or delete test.db
rm test.db
```

---

## 📞 Getting Help

### Resources
- **Detailed Review:** See `CODE_REVIEW.md`
- **Security Guide:** See `SECURITY_RECOMMENDATIONS.md`
- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **SQLAlchemy Docs:** https://docs.sqlalchemy.org/

### Quick Questions?
- Check existing code for patterns
- Look at test files for examples
- Review related routes/models

### Found a Bug?
1. Check if already in review documents
2. Write a failing test
3. Fix the bug
4. Ensure test passes
5. Submit PR with test

---

## 📊 Progress Tracking

### This Week
- [ ] Review all documents
- [ ] Run code formatters
- [ ] Fix critical security issues (4 items)
- [ ] Increase test coverage to 30%

### This Month
- [ ] Complete all Week 1 items
- [ ] Implement remaining security fixes
- [ ] Increase test coverage to 50%
- [ ] Add comprehensive documentation

### This Quarter
- [ ] Test coverage to 80%
- [ ] All security issues resolved
- [ ] CI/CD pipeline complete
- [ ] Production ready

---

**Last Updated:** November 24, 2025  
**Version:** 1.0  
**Status:** ✅ Ready for Development Team
