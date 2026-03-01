import sqlite3

# -------------------------
# Connect to SQLite DB
# -------------------------
conn = sqlite3.connect("business.db")  # creates file if not exists
c = conn.cursor()

# -------------------------
# USERS TABLE
# -------------------------
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin','staff')),
    password TEXT NOT NULL,
    force_password_change INTEGER DEFAULT 0
)
""")

# -------------------------
# PRODUCTS TABLE
# -------------------------
c.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cp REAL NOT NULL,           -- Cost Price
    sp REAL NOT NULL,           -- Selling Price
    quantity INTEGER NOT NULL,  -- Current stock
    category TEXT
)
""")

# -------------------------
# SALES TABLE
# -------------------------
c.execute("""
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    staff_id INTEGER,            -- NULL if admin
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(product_id) REFERENCES products(id),
    FOREIGN KEY(staff_id) REFERENCES users(id)
)
""")

# -------------------------
# EXPENSES TABLE
# -------------------------
c.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT,
    amount REAL NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

# -------------------------
# EMAIL ALERTS CACHE TABLE
# -------------------------
c.execute("""
CREATE TABLE IF NOT EXISTS email_alerts (
    email_type TEXT PRIMARY KEY,
    sent_date TEXT
)
""")

# -------------------------
# FAST MOVING CACHE
# -------------------------
c.execute("""
CREATE TABLE IF NOT EXISTS fast_moving_cache (
    product_id INTEGER PRIMARY KEY,
    sold_qty INTEGER,
    last_checked DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(product_id) REFERENCES products(id)
)
""")

# -------------------------
# LOW STOCK CACHE
# -------------------------
c.execute("""
CREATE TABLE IF NOT EXISTS low_stock_cache (
    product_id INTEGER PRIMARY KEY,
    quantity_left INTEGER,
    last_checked DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(product_id) REFERENCES products(id)
)
""")

# -------------------------
# Commit and Close
# -------------------------
conn.commit()
conn.close()

print("✅ All tables created successfully!")