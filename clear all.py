import sqlite3

DB_NAME = "mydatabase.db"

# ---------------------------
# Connect to DB
# ---------------------------
conn = sqlite3.connect(DB_NAME)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# ---------------------------
# Fix existing products
# ---------------------------
# Replace these with actual CP values per product if known
product_cp_map = {
    "Nivea": 5000,     # CP per unit
    "Maggi": 1000,     # CP per unit
    # Add more products here
}

for row in cursor.execute("SELECT id, name, quantity FROM products"):
    pid = row["id"]
    name = row["name"]
    qty = row["quantity"]
    cp = product_cp_map.get(name, 0)  # default CP if not listed
    if cp == 0:
        print(f"⚠️ CP missing for product '{name}', skipping...")
        continue

    # Update initial_quantity and initial_cp
    cursor.execute("""
        UPDATE products
        SET initial_quantity = ?, initial_cp = ?
        WHERE id = ?
    """, (qty, cp, pid))

    # Check if stock_additions already exist
    existing = cursor.execute("SELECT COUNT(*) AS cnt FROM stock_additions WHERE product_id=?", (pid,)).fetchone()["cnt"]
    if existing == 0:
        # Insert initial stock addition
        cursor.execute("""
            INSERT INTO stock_additions (product_id, quantity, cp)
            VALUES (?,?,?)
        """, (pid, qty, cp))

# ---------------------------
# Recalculate total investment
# ---------------------------
cursor.execute("SELECT SUM(initial_quantity * initial_cp) AS total_investment FROM products")
total_investment = cursor.fetchone()["total_investment"] or 0
cursor.execute("UPDATE total_investment SET value=? WHERE id=1", (total_investment,))

conn.commit()
conn.close()

print(f"✅ Migration completed. Total Investment updated: {total_investment:,.2f}")