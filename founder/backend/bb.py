# fix_passwords.py
from db import fetch_all, execute_query
from utils import hash_password, verify_password

DEFAULT_PASSWORD = "Admin123!"  # Change this to whatever default you want

def fix_all_passwords():
    users = fetch_all("SELECT id, password FROM users")
    fixed_count = 0

    for user in users:
        user_id = user["id"]
        pwd = user.get("password") or ""
        
        # If password is invalid (empty or cannot be verified)
        if not pwd or not verify_password(DEFAULT_PASSWORD, pwd):
            new_hash = hash_password(DEFAULT_PASSWORD)
            execute_query("UPDATE users SET password=%s WHERE id=%s", (new_hash, user_id))
            fixed_count += 1
            print(f"Fixed password for user ID {user_id}")

    print(f"✅ Password fix completed. Total fixed: {fixed_count}")
    print(f"All users now have valid bcrypt passwords. Default password: {DEFAULT_PASSWORD}")

if __name__ == "__main__":
    fix_all_passwords()