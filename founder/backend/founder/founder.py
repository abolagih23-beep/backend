# founder.py
from flask import Blueprint, jsonify, request
from db import fetch_all, execute_query  # Your DB helpers

founder_bp = Blueprint("founder_bp", __name__, url_prefix="/founder")

# -------------------------
# DASHBOARD DATA
# -------------------------
@founder_bp.route("/dashboard-data", methods=["GET"])
def dashboard_data():
    """
    Returns all data for the founder dashboard:
    - Products with stock & low_stock flag
    - All sales with profit calculation
    - System status
    """
    # -------------------------
    # SYSTEM STATUS
    # -------------------------
    system_status_row = fetch_all("SELECT system_status FROM system_control WHERE id=1")
    system_status = system_status_row[0]["system_status"] if system_status_row else "active"

    # -------------------------
    # PRODUCTS
    # -------------------------
    products = fetch_all("SELECT id, name, sp, cp, quantity FROM products ORDER BY name")
    for p in products:
        p["sp"] = float(p["sp"])
        p["cp"] = float(p["cp"])
        p["quantity"] = int(p["quantity"])
        p["low_stock"] = p["quantity"] <= 5

    # -------------------------
    # SALES
    # -------------------------
    sales = fetch_all("""
        SELECT s.id, p.name AS product_name, s.quantity, p.sp, p.cp,
               (p.sp - p.cp)*s.quantity AS profit, s.timestamp
        FROM sales s
        JOIN products p ON s.product_id = p.id
        ORDER BY s.timestamp DESC
    """)
    for s in sales:
        s["quantity"] = int(s["quantity"])
        s["sp"] = float(s["sp"])
        s["cp"] = float(s["cp"])
        s["profit"] = float(s["profit"])
        s["timestamp"] = s["timestamp"].isoformat() if hasattr(s["timestamp"], "isoformat") else str(s["timestamp"])

    return jsonify({
        "system_status": system_status,
        "products": products,
        "sales": sales
    })


# -------------------------
# TOGGLE SYSTEM STATUS
# -------------------------
@founder_bp.route("/system-toggle", methods=["POST"])
def toggle_system():
    """
    Founder can toggle system status: active / inactive
    """
    data = request.json or {}
    action = data.get("action")  # "activate" or "deactivate"

    if action not in ("activate", "deactivate"):
        return jsonify({"error": "Invalid action"}), 400

    execute_query(
        "UPDATE system_control SET system_status=%s WHERE id=1",
        (action,)
    )

    return jsonify({"status": action, "message": f"System {action} successfully"})


# -------------------------
# OPTIONAL: LOW STOCK ALERTS ONLY
# -------------------------
@founder_bp.route("/low-stock", methods=["GET"])
def low_stock_alerts():
    """
    Returns only products with quantity <=5
    """
    low_stock_products = fetch_all(
        "SELECT id, name, sp, cp, quantity FROM products WHERE quantity <=5 ORDER BY quantity ASC"
    )
    for p in low_stock_products:
        p["sp"] = float(p["sp"])
        p["cp"] = float(p["cp"])
        p["quantity"] = int(p["quantity"])
        p["low_stock"] = True
    return jsonify(low_stock_products)