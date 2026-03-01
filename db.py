import sqlite3
from config import DB_PATH

# -------------------------
# Dict-like row factory
# -------------------------
def dict_factory(cursor, row):
    """
    Converts SQLite rows to dictionaries for easy access by column name.
    """
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

# -------------------------
# Get connection
# -------------------------
def get_connection():
    """
    Returns a connection to the SQLite database.
    """
    # timeout prevents "database is locked" errors under light concurrency
    conn = sqlite3.connect(DB_PATH, timeout=10)

    # Enable WAL mode for better concurrent read/write performance
    conn.execute("PRAGMA journal_mode=WAL;")

    # Slight performance improvement & durability balance
    conn.execute("PRAGMA synchronous=NORMAL;")

    conn.row_factory = dict_factory  # Makes fetches return dicts
    return conn

# -------------------------
# Execute INSERT/UPDATE/DELETE
# -------------------------
def execute_query(query, values=None):
    """
    Executes a query that modifies the database (INSERT, UPDATE, DELETE).
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        if values:
            cur.execute(query, values)
        else:
            cur.execute(query)
        conn.commit()
    finally:
        cur.close()
        conn.close()

# -------------------------
# Fetch one row
# -------------------------
def fetch_one(query, values=None):
    """
    Executes a SELECT query and returns a single row as a dictionary.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        if values:
            cur.execute(query, values)
        else:
            cur.execute(query)
        result = cur.fetchone()
        return result
    finally:
        cur.close()
        conn.close()

# -------------------------
# Fetch all rows
# -------------------------
def fetch_all(query, values=None):
    """
    Executes a SELECT query and returns all rows as a list of dictionaries.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        if values:
            cur.execute(query, values)
        else:
            cur.execute(query)
        result = cur.fetchall()
        return result
    finally:
        cur.close()
        conn.close()