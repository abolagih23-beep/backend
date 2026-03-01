# ==========================================
# PRO+ ADMIN PASSWORD RESET TOOL (bcrypt)
# Author: Programmer Access Only
# ==========================================

import sqlite3
import getpass
import os
import sys
from datetime import datetime
from utils import hash_password  # must be your backend utils hash_password (bcrypt)

# ==============================
# CONFIGURATION
# ==============================
DATABASE = "mydatabase.db"   # Your POS database file
PROGRAMMER_MASTER_PASSWORD = "Key123!"  # change to your secret master password

# ==============================
# SECURITY FUNCTIONS
# ==============================
def verify_master_password():
    print("\n🔐 PROGRAMMER AUTHENTICATION REQUIRED")
    entered = getpass.getpass("Enter Programmer Master Password: ")
    return entered == PROGRAMMER_MASTER_PASSWORD

# ==============================
# DATABASE FUNCTIONS
# ==============================
def connect_db():
    if not os.path.exists(DATABASE):
        print("❌ Database file not found!")
        sys.exit(1)
    return sqlite3.connect(DATABASE)

def reset_admin_password():
    conn = connect_db()
    cursor = conn.cursor()

    # Fetch admin by role
    cursor.execute("SELECT id, name FROM users WHERE role='admin'")
    admin = cursor.fetchone()

    if not admin:
        print("❌ No admin account found.")
        conn.close()
        return

    admin_id, admin_name = admin
    print(f"\n👤 Admin Found: {admin_name}")

    while True:
        new_password = getpass.getpass("Enter NEW admin password: ")
        confirm_password = getpass.getpass("Confirm NEW admin password: ")

        if new_password != confirm_password:
            print("❌ Passwords do not match. Try again.\n")
            continue

        if len(new_password) < 6:
            print("❌ Password must be at least 6 characters.\n")
            continue

        break

    # Hash using backend's bcrypt function
    hashed = hash_password(new_password)

    cursor.execute("UPDATE users SET password=? WHERE id=?", (hashed, admin_id))
    conn.commit()
    conn.close()

    print("\n✅ Admin password successfully reset!")
    print("📅 Time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("🔒 You can now log in as admin immediately.")


# ==============================
# MAIN PROGRAM
# ==============================
def main():
    print("======================================")
    print("     PRO+ ADMIN PASSWORD RESET TOOL")
    print("======================================")

    if not verify_master_password():
        print("\n❌ Unauthorized access detected!")
        sys.exit(1)

    print("\n✅ Programmer authenticated.\n")
    reset_admin_password()

if __name__ == "__main__":
    main()