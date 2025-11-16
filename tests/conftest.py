import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db


SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------
# FIXED: db_session must be a fixture and must yield a REAL session obj
# ---------------------------------------------------------------------
@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------
# FIXED: override must yield the *session instance*, not the function
# ---------------------------------------------------------------------
@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session   # ✔️ real SQLAlchemy Session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


# ---------------------------------------------------------------------
# Utility fixture to create a user for login tests
# ---------------------------------------------------------------------
@pytest.fixture()
def create_test_user(db_session):
    from app.crud.user_crud import create_user

    def _create(
        username="user1",
        email="user1@example.com",
        password="StrongP@ss1"
    ):
        return create_user(db_session, username, email, password)

    return _create
