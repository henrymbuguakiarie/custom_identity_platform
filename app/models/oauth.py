from datetime import datetime, timedelta
import secrets
from sqlalchemy import (Column, String, DateTime, Integer, ForeignKey, Boolean, Text, Index)
from sqlalchemy.orm import relationship
from app.database import Base

class OAuthClient(Base):
    __tablename__ = "oauth_clients"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String(64), unique=True, nullable=False, index=True)
    client_name = Column(String(200))
    client_secret = Column(String(255), nullable=True)  # only for confidential clients
    redirect_uris = Column(Text, nullable=False)  # store newline-separated or JSON array
    is_confidential = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_oauth_client_client_id", "client_id"),)

    def redirect_uri_list(self):
        # If stored as newline separated
        return [u.strip() for u in self.redirect_uris.splitlines() if u.strip()]
    
class AuthorizationCode(Base):
    __tablename__ = "authorization_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(128), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(Integer, ForeignKey("oauth_clients.id", ondelete="CASCADE"), nullable=False)
    redirect_uri = Column(String(512), nullable=False)
    code_challenge = Column(String(256), nullable=True)
    code_challenge_method = Column(String(10), nullable=True)
    scope = Column(String(512), nullable=True)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User")
    client = relationship("OAuthClient")

    __table_args__ = (
        Index("ix_auth_code_client_id", "client_id"),
        Index("ix_auth_code_expires_at", "expires_at"),
    )
