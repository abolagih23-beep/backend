# founder/founder.py
from flask import Blueprint, jsonify, request
from db import fetch_all, fetch_one, execute_query
from utils import get_low_stock, get_fast_moving_items
from datetime import datetime, date

founder_bp = Blueprint("founder_bp", __name__)

# Internal system toggle (simulate enabling/disabling sales globally)
SYSTEM_ENABLED = True

# -------------------------
# SYSTEM STATUS
# -------------------------
@founder_bp.route("/system/status", methods=["GET"])
def system_status():
    """Returns whether the system is currently enabled or disabled"""
    return jsonify({"system_enabled": SYSTEM_ENABLED})

@founder_bp.route("/system/toggle", methods=["POST"])
def toggle_system():
    """
    Enable or disable the entire system.
    Example POST JSON: {"enable": true} or {"enable": false}
    """
    global SYSTEM_ENABLED
    data = request.json or {}
    enable = data.get("enable")
    if enable is None:
        return jsonify({"error": "Missing 'enable' field"}), 400

    SYSTEM_ENABLED = bool(enable)
    status = "enabled" if SYSTEM_ENABLED else "disabled"
    return jsonify({"status": f"System {status}"})

# -------------------------
# FULL DASHBOARD (FOUNDER VIEW)
# -------------------------
@founder_bp.route("/dashboard", methods=["GET"])
def founder_dashboard():
    """Founder sees everything: stock, sales, profit, staff, fast-moving, low-stock"""
    # Products
    products = fetch_all("SELECT * FROM products ORDER BY name")
    for p in products:
        p["cp"] = float(p["cp"])
        p["sp"] = float(p["sp"])
        p["quantity"] = int(p["quantity"])

    # Staff
    staff = fetch_all("SELECT id, name, role FROM users ORDER BY role, name")

    # Sales
    sales = fetch_all("""
        SELECT s.id, s.product_id, p.name AS product_name, s.quantity, p.cp, p.sp,
               ((p.sp - p.cp) * s.quantity) AS profit, s.staff_id, u.name AS staff_name, s.timestamp
        FROM sales s
        JOIN products p ON s.product_id = p.id
        LEFT JOIN users u ON s.staff_id = u.id
        ORDER BY s.timestamp DESC
    """)
    for s in sales:
        s["cp"] = float(s["cp"])
        s["sp"] = float(s["sp"])
        s["quantity"] = int(s["quantity"])
        s["profit"] = float(s["profit"])
        s["timestamp"] = s["timestamp"].isoformat() if hasattr(s["timestamp"], "isoformat") else str(s["timestamp"])

    # Low stock & fast moving
    low_stock = get_low_stock()
    fast_moving = get_fast_moving_items()

    # Total metrics
    total_stock = sum(p["quantity"] for p in products)
    total_investment = sum(p["cp"] * p["quantity"] for p in products)
    projected_revenue = sum(p["sp"] * p["quantity"] for p in products)
    total_profit = sum(s["profit"] for s in sales)

    return jsonify({
        "system_enabled": SYSTEM_ENABLED,
        "products": products,
        "staff": staff,
        "sales": sales,
        "low_stock": low_stock,
        "fast_moving": fast_moving,
        "metrics": {
            "total_stock": total_stock,
            "total_investment": total_investment,
            "projected_revenue": projected_revenue,
            "total_profit": total_profit
        }
    })


# -------------------------
# SALES HISTORY FILTERED
# -------------------------
@founder_bp.route("/sales/history", methods=["GET"])
def founder_sales_history():
    """
    Founder sees all sales optionally filtered by date range:
    Example GET params: ?start=2026-01-01&end=2026-01-31
    """
    start = request.args.get("start")
    end = request.args.get("end")
    query = """
        SELECT s.id, s.product_id, p.name AS product_name, s.quantity, p.cp, p.sp,
               ((p.sp - p.cp) * s.quantity) AS profit, s.staff_id, u.name AS staff_name, s.timestamp
        FROM sales s
        JOIN products p ON s.product_id = p.id
        LEFT JOIN users u ON s.staff_id = u.id
        WHERE 1=1
    """
    params = []

    if start:
        query += " AND s.timestamp >= %s"
        params.append(start)
    if end:
        query += " AND s.timestamp <= %s"
        params.append(end)

    query += " ORDER BY s.timestamp DESC"

    sales = fetch_all(query, tuple(params))
    for s in sales:
        s["cp"] = float(s["cp"])
        s["sp"] = float(s["sp"])
        s["quantity"] = int(s["quantity"])
        s["profit"] = float(s["profit"])
        s["timestamp"] = s["timestamp"].isoformat() if hasattr(s["timestamp"], "isoformat") else str(s["timestamp"])

    return jsonify(sales)


# -------------------------
# STAFF ACTIVITY LOG
# -------------------------
@founder_bp.route("/staff/activity", methods=["GET"])
def staff_activity():
    """
    Founder sees all staff sales activity
    """
    activities = fetch_all("""
        SELECT s.id AS sale_id, u.id AS staff_id, u.name AS staff_name,
               s.product_id, p.name AS product_name, s.quantity,
               ((p.sp - p.cp) * s.quantity) AS profit, s.timestamp
        FROM sales s
        JOIN products p ON s.product_id = p.id
        JOIN users u ON s.staff_id = u.id
        ORDER BY s.timestamp DESC
    """)
    for a in activities:
        a["quantity"] = int(a["quantity"])
        a["profit"] = float(a["profit"])
        a["timestamp"] = a["timestamp"].isoformat() if hasattr(a["timestamp"], "isoformat") else str(a["timestamp"])
    return jsonify(activities)


# -------------------------
# SYSTEM SHUTDOWN
# -------------------------
@founder_bp.route("/system/shutdown", methods=["POST"])
def shutdown_system():
    """
    Shuts down the Flask backend safely.
    """
    def shutdown():
        from flask import request
        func = request.environ.get("werkzeug.server.shutdown")
        if func:
            func()

    shutdown()
    return jsonify({"status": "success", "message": "System shutdown initiated"})


# -------------------------
# CLEAR ALL DATA (FOUNDER ONLY)
# -------------------------
@founder_bp.route("/clear/all", methods=["DELETE"])
def clear_all_data():
    """
    Deletes all sales, products, users, and purchases.
    Use with extreme caution.
    """
    for table in ["sales", "products", "users", "purchases"]:
        execute_query(f"DELETE FROM {table}")
    return jsonify({"status": "success", "message": "All tables cleared"})


# -------------------------
# NOTIFICATIONS & ALERTS (OPTIONAL)
# -------------------------
@founder_bp.route("/alerts/low-stock", methods=["GET"])
def founder_low_stock_alert():
    """
    Founder can view low stock products instantly
    """
    low_stock = get_low_stock()
    return jsonify(low_stock)


@founder_bp.route("/alerts/fast-moving", methods=["GET"])
def founder_fast_moving_alert():
    """
    Founder can view fast moving products instantly
    """
    fast_moving = get_fast_moving_items()
    return jsonify(fast_moving)