# models.py
from db import execute_query

def create_tables():
    # Users table
    execute_query("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        role TEXT NOT NULL,
        password TEXT NOT NULL,
        force_password_change INTEGER DEFAULT 0  -- 0 = False, 1 = True
    )
    """)

    # Products table
    execute_query("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        cp REAL NOT NULL,
        sp REAL NOT NULL,
        quantity INTEGER NOT NULL,
        category TEXT
    )
    """)

    # Sales table
    execute_query("""
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        quantity INTEGER NOT NULL,
        staff_id INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products(id),
        FOREIGN KEY (staff_id) REFERENCES users(id)
    )
    """)

if __name__ == "__main__":
    create_tables()
    print("✅ All tables created successfully!")