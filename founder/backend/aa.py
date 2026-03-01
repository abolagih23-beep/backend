from werkzeug.security import generate_password_hash
from db import execute_query, fetch_one

# ------------------------
# ADMIN OVERRIDE
# ------------------------
ADMIN_NAME = "admin"
ADMIN_PASSWORD = "admin123"  # your override password
ROLE = "admin"

hashed_admin = generate_password_hash(ADMIN_PASSWORD)

# Check if admin exists
admin_user = fetch_one("SELECT id FROM users WHERE name=%s AND role='admin'", (ADMIN_NAME,))
if admin_user:
    execute_query(
        "UPDATE users SET password=%s WHERE id=%s",
        (hashed_admin, admin_user["id"])
    )
    print("✅ Admin password overridden")
else:
    execute_query(
        "INSERT INTO users (name, password, role) VALUES (%s,%s,%s)",
        (ADMIN_NAME, hashed_admin, ROLE)
    )
    print("✅ Admin user created")


# ------------------------
# STAFF OVERRIDE (OPTIONAL)
# ------------------------
STAFF_OVERRIDE_PASSWORD = "staff123"

hashed_staff = generate_password_hash(STAFF_OVERRIDE_PASSWORD)

# Update all staff passwords
execute_query(
    "UPDATE users SET password=%s WHERE role='staff'",
    (hashed_staff,)
)
print("✅ All staff passwords overridden")