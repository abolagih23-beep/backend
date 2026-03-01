# fix_investment.py
import sqlite3

DB_PATH = "mydatabase.db"  # <-- change to your SQLite database path

def recalc_total_investment():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Calculate total investment from existing products
    cursor.execute("SELECT COALESCE(SUM(initial_quantity * initial_cp),0) AS total FROM products")
    row = cursor.fetchone()
    total_investment = row["total"]

    # Update meta table (insert if missing)
    cursor.execute("INSERT OR IGNORE INTO meta (id, total_investment) VALUES (1,0)")
    cursor.execute("UPDATE meta SET total_investment=? WHERE id=1", (total_investment,))

    conn.commit()
    conn.close()
    print(f"✅ Total investment recalculated: {total_investment}")

if __name__ == "__main__":
    recalc_total_investment()