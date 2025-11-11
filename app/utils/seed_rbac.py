from app.database import SessionLocal
from app.models.rbac import Role, Permission
from app.models.user import User
from app.core.security import hash_password

# Create roles
admin_role = Role(name="Admin", description="Administrator role")
user_role = Role(name="User", description="Standard user role")

# Create permissions
view_user = Permission(name="view_user", description="Can view users")
delete_user = Permission(name="delete_user", description="Can delete users")

# Assign permissions to roles
admin_role.permissions = [view_user, delete_user]
user_role.permissions = [view_user]

# Create default admin user
admin_user = User(username="admin", email="admin@example.com", password_hash=hash_password("adminpass"))
admin_user.roles = [admin_role]

# Commit to DB
db_session = SessionLocal()
db_session.add_all([admin_role, user_role, view_user, delete_user, admin_user])
db_session.commit()
db_session.close()