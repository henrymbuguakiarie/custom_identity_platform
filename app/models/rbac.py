from datetime import datetime
import re
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, DateTime,
    Table, Index, CheckConstraint, Text
)
from sqlalchemy.orm import relationship, validates
from app.database import Base

# --- Association Tables ---
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete="CASCADE"), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete="CASCADE"), primary_key=True)
)

role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id', ondelete="CASCADE"), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete="CASCADE"), primary_key=True)
)

# --- Models ---
class Role(Base):
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    permissions = relationship('Permission', secondary=role_permissions, back_populates='roles')
    users = relationship('User', secondary=user_roles, back_populates='roles')

    __table_args__ = (
        Index('idx_role_name', 'name'),
        CheckConstraint("name != ''", name="check_role_name_not_empty"),
    )

    @validates('name')
    def validate_name(self, key, value):
        if not re.match(r'^[A-Za-z0-9_]+$', value):
            raise ValueError("Role name can only contain alphanumeric characters and underscores.")
        return value

class Permission(Base):
    __tablename__ = 'permissions'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    roles = relationship('Role', secondary=role_permissions, back_populates='permissions')

    __table_args__ = (
        Index('idx_permission_name', 'name'),
        CheckConstraint("name != ''", name="check_permission_name_not_empty"),
    )

    @validates('name')
    def validate_name(self, key, value):
        if not re.match(r'^[A-Za-z0-9_.]+$', value):
            raise ValueError("Permission name can only contain alphanumeric characters, underscores, and dots.")
        return value

class Session(Base):
    __tablename__ = 'sessions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False)
    refresh_token = Column(String(255), unique=True, nullable=True)
    is_active = Column(Boolean, default=True)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

    user = relationship('User', back_populates='sessions')

    __table_args__ = (
        Index('idx_session_token', 'session_token'),
    )
