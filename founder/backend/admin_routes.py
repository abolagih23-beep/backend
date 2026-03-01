from flask import Blueprint, request, jsonify, session
from db import execute_query, fetch_all, fetch_one
from utils import get_fast_moving_items, get_low_stock, hash_password, verify_password
from email_alerts import low_stock_alert, fast_moving_alert

admin_bp = Blueprint("admin_bp", __name__)

# =========================
# SESSION GUARD
# =========================
def admin_required():
    """Check if user is logged in and is admin."""
    if "user_id" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401
    return None

# =========================
# DASHBOARD
# =========================
@admin_bp.route("/dashboard", methods=["GET"])
def dashboard():
    guard = admin_required()
    if guard: return guard

    total_stock = fetch_one("SELECT COALESCE(SUM(quantity),0) AS total FROM products")["total"]
    total_investment = fetch_one("SELECT COALESCE(SUM(cp * quantity),0) AS total FROM products")["total"]
    total_sales = fetch_one("""
        SELECT COALESCE(SUM(p.sp * s.quantity),0) AS total
        FROM sales s
        JOIN products p ON s.product_id = p.id
    """)["total"]

    daily_profit = fetch_one("""
        SELECT COALESCE(SUM((p.sp - p.cp) * s.quantity),0) AS profit
        FROM sales s
        JOIN products p ON s.product_id = p.id
        WHERE DATE(s.timestamp) = CURRENT_DATE
    """)["profit"]

    weekly_profit = fetch_one("""
        SELECT COALESCE(SUM((p.sp - p.cp) * s.quantity),0) AS profit
        FROM sales s
        JOIN products p ON s.product_id = p.id
        WHERE s.timestamp >= CURRENT_DATE - INTERVAL '7 days'
    """)["profit"]

    monthly_profit = fetch_one("""
        SELECT COALESCE(SUM((p.sp - p.cp) * s.quantity),0) AS profit
        FROM sales s
        JOIN products p ON s.product_id = p.id
        WHERE DATE_TRUNC('month', s.timestamp) = DATE_TRUNC('month', CURRENT_DATE)
    """)["profit"]

    fast_moving = get_fast_moving_items()
    low_stock = get_low_stock()

    try:
        low_stock_alert(low_stock)
        fast_moving_alert(fast_moving)
    except Exception:
        pass

    return jsonify({
        "total_stock": int(total_stock),
        "total_investment": float(total_investment),
        "total_sales": float(total_sales),
        "daily_profit": float(daily_profit),
        "weekly_profit": float(weekly_profit),
        "monthly_profit": float(monthly_profit),
        "cash_flow": float(total_sales),
        "stock_balance": float(total_investment),
        "fast_moving": fast_moving,
        "low_stock": low_stock
    })

# =========================
# PRODUCTS
# =========================
@admin_bp.route("/products", methods=["GET"])
def list_products():
    guard = admin_required()
    if guard: return guard

    products = fetch_all("SELECT id, name, cp, sp, quantity, category FROM products ORDER BY name")
    for p in products:
        p["cp"] = float(p["cp"])
        p["sp"] = float(p["sp"])
        p["quantity"] = int(p["quantity"])
    return jsonify(products)

@admin_bp.route("/products", methods=["POST"])
def add_product():
    guard = admin_required()
    if guard: return guard

    data = request.json
    execute_query("""
        INSERT INTO products (name, cp, sp, quantity, category)
        VALUES (%s,%s,%s,%s,%s)
    """, (data["name"], float(data["cp"]), float(data["sp"]), int(data["quantity"]), data.get("category")))
    return jsonify({"status": "success"})

@admin_bp.route("/products/<int:pid>", methods=["PUT"])
def edit_product(pid):
    guard = admin_required()
    if guard: return guard

    data = request.json
    execute_query("""
        UPDATE products
        SET name=%s, cp=%s, sp=%s, quantity=%s, category=%s
        WHERE id=%s
    """, (data["name"], float(data["cp"]), float(data["sp"]), int(data["quantity"]), data.get("category"), pid))
    return jsonify({"status": "updated"})

@admin_bp.route("/products/<int:pid>", methods=["DELETE"])
def delete_product(pid):
    guard = admin_required()
    if guard: return guard

    execute_query("DELETE FROM products WHERE id=%s", (pid,))
    return jsonify({"status": "deleted"})

# =========================
# STAFF MANAGEMENT
# =========================
@admin_bp.route("/staff", methods=["GET"])
def list_staff():
    guard = admin_required()
    if guard: return guard

    staff = fetch_all("SELECT id, name, role FROM users WHERE role='staff'")
    return jsonify(staff)

@admin_bp.route("/staff", methods=["POST"])
def add_staff():
    guard = admin_required()
    if guard: return guard

    data = request.json or {}
    name = data.get("name", "").strip()
    password = data.get("password", "").strip()

    if not name or not password:
        return jsonify({"error": "Name and password are required"}), 400

    hashed = hash_password(password)
    execute_query("INSERT INTO users (name, role, password) VALUES (%s,'staff',%s)", (name, hashed))
    return jsonify({"status": "success", "message": f"Staff {name} added successfully"})

@admin_bp.route("/staff/<int:staff_id>", methods=["DELETE"])
def remove_staff(staff_id):
    guard = admin_required()
    if guard: return guard

    execute_query("DELETE FROM users WHERE id=%s AND role='staff'", (staff_id,))
    return jsonify({"status": "success", "message": "Staff removed successfully"})

@admin_bp.route("/staff/<int:staff_id>/reset_password", methods=["POST"])
def reset_staff_password(staff_id):
    guard = admin_required()
    if guard: return guard

    data = request.json or {}
    new_pass = data.get("new_password", "").strip()
    if not new_pass:
        return jsonify({"error": "New password is required"}), 400

    hashed = hash_password(new_pass)
    execute_query("UPDATE users SET password=%s WHERE id=%s AND role='staff'", (hashed, staff_id))
    return jsonify({"status": "success", "message": "Staff password updated successfully"})

@admin_bp.route("/staff/<int:staff_id>/force_change_password", methods=["POST"])
def force_staff_password_change(staff_id):
    guard = admin_required()
    if guard: return guard

    execute_query("UPDATE users SET force_password_change=TRUE WHERE id=%s AND role='staff'", (staff_id,))
    return jsonify({"status": "success", "message": "Staff will be prompted to change password next login"})

# =========================
# SALES MANAGEMENT
# =========================
@admin_bp.route("/sales", methods=["GET"])
def list_sales():
    guard = admin_required()
    if guard: return guard

    sales = fetch_all("""
        SELECT s.id,
               p.name AS product_name,
               s.quantity,
               p.sp,
               p.cp,
               s.timestamp,
               COALESCE(u.name,'Admin') AS staff_name,
               ((p.sp - p.cp) * s.quantity) AS profit
        FROM sales s
        JOIN products p ON s.product_id = p.id
        LEFT JOIN users u ON s.staff_id = u.id
        ORDER BY s.timestamp DESC
    """)

    for s in sales:
        s["quantity"] = int(s["quantity"])
        s["sp"] = float(s["sp"])
        s["cp"] = float(s["cp"])
        s["profit"] = float(s["profit"])
        s["timestamp"] = s["timestamp"].isoformat() if hasattr(s["timestamp"], "isoformat") else str(s["timestamp"])
    return jsonify(sales)

@admin_bp.route("/sales", methods=["POST"])
def record_sale_admin():
    guard = admin_required()
    if guard: return guard

    data = request.json or {}
    admin_id = session.get("user_id")
    product_id = data.get("product_id")
    quantity = data.get("quantity")

    if not product_id or not quantity or int(quantity) <= 0:
        return jsonify({"error": "Invalid product or quantity"}), 400

    product = fetch_one("SELECT quantity, cp, sp FROM products WHERE id=%s", (product_id,))
    if not product:
        return jsonify({"error": "Product not found"}), 404

    available_qty = int(product["quantity"])
    cp = float(product["cp"])
    sp = float(product["sp"])

    if available_qty < int(quantity):
        return jsonify({"error": "Insufficient stock"}), 400

    execute_query(
        "INSERT INTO sales (product_id, quantity, staff_id, timestamp) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)",
        (product_id, int(quantity), admin_id)
    )
    execute_query("UPDATE products SET quantity = quantity - %s WHERE id = %s", (int(quantity), product_id))

    total_value = sp * int(quantity)
    return jsonify({"status": "success", "total": total_value, "message": f"Sale recorded successfully. Total: ₦{total_value}"})

# =========================
# PASSWORD MANAGEMENT
# =========================
@admin_bp.route("/change_password", methods=["POST"])
def change_admin_password():
    guard = admin_required()
    if guard: return guard

    data = request.json or {}
    current = data.get("current_password", "").strip()
    new_pass = data.get("new_password", "").strip()

    if not new_pass:
        return jsonify({"error": "New password is required"}), 400

    user = fetch_one("SELECT password FROM users WHERE id=%s", (session["user_id"],))
    current_hash = user.get("password", "") if user else ""

    if current_hash:
        if not current:
            return jsonify({"error": "Current password is required"}), 400
        if not verify_password(current, current_hash):
            return jsonify({"error": "Current password is incorrect"}), 400

    hashed_new = hash_password(new_pass)
    execute_query("UPDATE users SET password=%s WHERE id=%s", (hashed_new, session["user_id"]))
    return jsonify({"status": "success", "message": "Admin password updated successfully"})