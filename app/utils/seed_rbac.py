from app.database import SessionLocal
from app.models.rbac import Role, Permission
from app.models.user import User
from app.core.security import hash_password

def get_or_create(db, model, defaults=None, **kwargs):
    instance = db.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    params = {**kwargs, **(defaults or {})}
    instance = model(**params)
    db.add(instance)
    return instance, True

def main():
    db = SessionLocal()

    try:
        # -----------------------------
        # 1) Create or get Permissions
        # -----------------------------
        permissions_data = {
            "view_user": "Can view users",
            "delete_user": "Can delete users",
        }

        permissions = {}
        for name, desc in permissions_data.items():
            perm, created = get_or_create(
                db,
                Permission,
                name=name,
                defaults={"description": desc},
            )
            permissions[name] = perm

        # -----------------------------
        # 2) Create or get Roles
        # -----------------------------
        roles_data = {
            "Admin": {
                "description": "Administrator role",
                "permissions": ["view_user", "delete_user"],
            },
            "User": {
                "description": "Standard user role",
                "permissions": ["view_user"],
            },
        }

        roles = {}
        for role_name, data in roles_data.items():
            role, created = get_or_create(
                db,
                Role,
                name=role_name,
                defaults={"description": data["description"]},
            )
            roles[role_name] = role

            # Attach permissions (update every run)
            role.permissions = [permissions[p] for p in data["permissions"]]

        # -----------------------------
        # 3) Create or update Admin User
        # -----------------------------
        admin_user = db.query(User).filter_by(username="admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                email="admin@example.com",
                hashed_password=hash_password("adminpass"),
                roles=[roles["Admin"]],
            )
            db.add(admin_user)
            print("Created admin user.")
        else:
            # Ensure admin role is linked
            if roles["Admin"] not in admin_user.roles:
                admin_user.roles.append(roles["Admin"])
            print("Admin user already exists — updated roles.")

        db.commit()
        print("RBAC Seeding complete.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
