# migrate_add_column.py
import sqlite3
from config import DB_PATH

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

try:
    cur.execute("""
    ALTER TABLE users
    ADD COLUMN force_password_change INTEGER DEFAULT 0
    """)
    conn.commit()
    print("✅ Column force_password_change added successfully!")
except sqlite3.OperationalError as e:
    print("⚠️ Column already exists or error:", e)

cur.close()
conn.close()