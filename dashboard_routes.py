from flask import Blueprint, jsonify
import sqlite3

dashboard_bp = Blueprint("dashboard_bp", __name__)

DB_PATH = "mydatabase.db"   # change if your db path is different

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# -----------------------------
# Total Investment (Commercial Safe)
# -----------------------------
@dashboard_bp.route("/api/total-investment", methods=["GET"])
def total_investment():
    conn = get_connection()
    cursor = conn.cursor()

    # ✅ Use initial_quantity * cp for total investment
    # It reflects current products only (new, edited, or deleted products)
    cursor.execute("""
        SELECT SUM(initial_cp * initial_quantity) AS total
        FROM products
    """)

    result = cursor.fetchone()
    conn.close()

    total = result["total"] if result["total"] else 0

    return jsonify({
        "total_investment": total
    })