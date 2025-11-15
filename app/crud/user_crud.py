from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import hash_password, verify_password
from app.models.rbac import UserSession

def create_user(db: Session, username: str, email: str, password: str):
    hashed_pw = hash_password(password)
    user = User(username=username, email=email, hashed_password=hashed_pw)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(User).offset(skip).limit(limit).all()

def update_user(db: Session, user: User):
    db.merge(user)
    db.commit()
    return user

def delete_user(db: Session, user: User):
    db.delete(user)
    db.commit()
    return user 

def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user 


def change_password(db: Session, user: User, new_password: str):
    user.password_hash = hash_password(new_password)
    # revoke all user sessions
    db.query(UserSession).filter_by(user_id=user.id, revoked=False).update({
        "revoked": True,
        "is_active": False
    })
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_user_roles(db: Session, user: User, new_role_list):
    # (update roles logic)
    db.query(UserSession).filter_by(user_id=user.id, revoked=False).update({
        "revoked": True,
        "is_active": False
    })
    db.commit()
