# admin_bp.py
from flask import Blueprint, request, jsonify, session
from db import execute_query, fetch_all, fetch_one
from utils import get_fast_moving_items, get_low_stock, hash_password, verify_password, generate_invoice, now_local_str
from email.message import EmailMessage
import smtplib
import socket
import threading
from config import EMAIL_USER, EMAIL_PASS, ALERT_EMAILS
from datetime import date, datetime
from zoneinfo import ZoneInfo  # Python 3.9+ built-in

# ----------------------
# LOCAL TIME CONFIG
# ----------------------
LOCAL_TZ = ZoneInfo("Africa/Lagos")

def now_local():
    """Return current local datetime in WAT as string."""
    return datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")

def today_local():
    """Return today's date in local timezone."""
    return datetime.now(LOCAL_TZ).date()

# ----------------------
# BLUEPRINT
# ----------------------
admin_bp = Blueprint("admin_bp", __name__)

# ----------------------
# SESSION GUARD
# ----------------------
def admin_required():
    if "user_id" not in session or session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 401
    return None

# =======================
# META / INVESTMENT HELPER
# =======================
execute_query("""
CREATE TABLE IF NOT EXISTS meta (
    id INTEGER PRIMARY KEY,
    total_investment REAL DEFAULT 0
)
""")
execute_query("INSERT OR IGNORE INTO meta (id, total_investment) VALUES (1,0)")

def recalc_total_investment():
    total = fetch_one("SELECT COALESCE(SUM(initial_quantity * initial_cp),0) AS total FROM products")["total"]
    execute_query("UPDATE meta SET total_investment=? WHERE id=1", (total,))

# =======================
# EMAIL ALERTS
# =======================
LOW_STOCK_THRESHOLD = 7

execute_query("""
CREATE TABLE IF NOT EXISTS email_alerts (
    email_type TEXT PRIMARY KEY,
    sent_date TEXT
)
""")

def send_email(subject, body):
    if not EMAIL_USER or not EMAIL_PASS or not ALERT_EMAILS:
        print("⚠️ Email config missing. Skipping email.")
        return
    try:
        msg = EmailMessage()
        msg["Subject"] = str(subject)
        msg["From"] = EMAIL_USER
        msg["To"] = ", ".join(ALERT_EMAILS)
        msg.set_content(str(body))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
        print(f"✅ Email sent: {subject}")
    except (smtplib.SMTPException, socket.gaierror, TimeoutError) as e:
        print("❌ Email failed safely:", e)
    except Exception as e:
        print("❌ Unexpected email error:", e)

def email_already_sent_today(email_type: str) -> bool:
    today = today_local().isoformat()
    row = fetch_one("SELECT 1 FROM email_alerts WHERE email_type=? AND sent_date=?", (email_type, today))
    return bool(row)

def mark_email_sent(email_type: str):
    today = today_local().isoformat()
    execute_query("INSERT OR REPLACE INTO email_alerts (email_type, sent_date) VALUES (?,?)", (email_type, today))

def async_send_email(email_type: str, subject: str, body: str):
    if email_already_sent_today(email_type):
        print(f"⚡ Email '{email_type}' already sent today. Skipping.")
        return
    def _send():
        try:
            send_email(subject, body)
            mark_email_sent(email_type)
        except Exception as e:
            print(f"❌ Failed async email '{email_type}':", e)
    threading.Thread(target=_send, daemon=True).start()

def send_dashboard_alerts_async():
    low_stock = get_low_stock(LOW_STOCK_THRESHOLD) or []
    fast_moving = get_fast_moving_items() or []

    if low_stock:
        body = "⚠️ LOW STOCK ALERT (Below 7 units)\n\n"
        for item in low_stock:
            name = item.get('name', 'Unknown')
            qty = int(item.get('quantity', 0))
            body += f"- {name} → Remaining: {qty}\n"
        async_send_email("low_stock", "⚠️ Low Stock Alert", body)

    if fast_moving:
        body = "🔥 FAST MOVING PRODUCTS ALERT\n\n"
        for item in fast_moving:
            name = item.get('name') or f"Product ID {item.get('id','Unknown')}"
            sold_qty = int(item.get('sold_qty', 0))
            body += f"- {name} → Sold: {sold_qty}\n"
        async_send_email("fast_moving", "🔥 Fast Moving Products Alert", body)

# =======================
# DASHBOARD
# =======================
@admin_bp.route("/dashboard", methods=["GET"])
def dashboard():
    guard = admin_required()
    if guard:
        return guard

    selected_date = request.args.get("date")
    selected_month = request.args.get("month")
    today = today_local()
    today_str = today.isoformat()

    # Totals
    total_stock = fetch_one("SELECT COALESCE(SUM(quantity),0) AS total FROM products")["total"]
    total_investment = fetch_one("SELECT total_investment FROM meta WHERE id=1")["total_investment"]
    stock_market_value = fetch_one("SELECT COALESCE(SUM(sp * quantity),0) AS total FROM products")["total"]
    total_sales = fetch_one("SELECT COALESCE(SUM(p.sp * s.quantity),0) AS total FROM sales s JOIN products p ON s.product_id = p.id")["total"]
    total_profit = fetch_one("SELECT COALESCE(SUM((p.sp - p.cp) * s.quantity),0) AS profit FROM sales s JOIN products p ON s.product_id = p.id")["profit"]
    expenses_total = fetch_one("SELECT COALESCE(SUM(amount),0) AS total FROM expenses")["total"]
    cash_in_hand = total_sales - expenses_total

    daily_summary = fetch_one("""
        SELECT COALESCE(SUM(p.sp * s.quantity),0) AS revenue,
               COALESCE(SUM((p.sp - p.cp) * s.quantity),0) AS profit
        FROM sales s
        JOIN products p ON s.product_id = p.id
        WHERE DATE(s.timestamp) = ?
    """, (today_str,))

    weekly_summary = fetch_one("""
        SELECT COALESCE(SUM(p.sp * s.quantity),0) AS revenue,
               COALESCE(SUM((p.sp - p.cp) * s.quantity),0) AS profit
        FROM sales s
        JOIN products p ON s.product_id = p.id
        WHERE DATE(s.timestamp) >= DATE(?, '-6 days')
    """, (today_str,))

    weekly_breakdown = fetch_all("""
        SELECT DATE(s.timestamp) as date,
               SUM(p.sp * s.quantity) as revenue,
               SUM((p.sp - p.cp) * s.quantity) as profit
        FROM sales s
        JOIN products p ON s.product_id = p.id
        WHERE DATE(s.timestamp) >= DATE(?, '-6 days')
        GROUP BY DATE(s.timestamp)
        ORDER BY DATE(s.timestamp) ASC
    """, (today_str,))

    first_day_month = date(today.year, today.month, 1).isoformat()
    monthly_summary = fetch_one("""
        SELECT COALESCE(SUM(p.sp * s.quantity),0) AS revenue,
               COALESCE(SUM((p.sp - p.cp) * s.quantity),0) AS profit
        FROM sales s
        JOIN products p ON s.product_id = p.id
        WHERE DATE(s.timestamp) BETWEEN ? AND ?
    """, (first_day_month, today_str))

    monthly_breakdown = fetch_all("""
        SELECT DATE(s.timestamp) as date,
               SUM(p.sp * s.quantity) as revenue,
               SUM((p.sp - p.cp) * s.quantity) as profit
        FROM sales s
        JOIN products p ON s.product_id = p.id
        WHERE DATE(s.timestamp) BETWEEN ? AND ?
        GROUP BY DATE(s.timestamp)
        ORDER BY DATE(s.timestamp) ASC
    """, (first_day_month, today_str))

    filtered_day = None
    if selected_date:
        fd = fetch_one("""
            SELECT COALESCE(SUM(p.sp * s.quantity),0) AS revenue,
                   COALESCE(SUM((p.sp - p.cp) * s.quantity),0) AS profit
            FROM sales s
            JOIN products p ON s.product_id = p.id
            WHERE DATE(s.timestamp) = ?
        """, (selected_date,))
        if fd:
            filtered_day = {"revenue": float(fd["revenue"]), "profit": float(fd["profit"])}

    filtered_month = None
    if selected_month:
        fm = fetch_one("""
            SELECT COALESCE(SUM(p.sp * s.quantity),0) AS revenue,
                   COALESCE(SUM((p.sp - p.cp) * s.quantity),0) AS profit
            FROM sales s
            JOIN products p ON s.product_id = p.id
            WHERE strftime('%Y-%m', s.timestamp) = ?
        """, (selected_month,))
        if fm:
            filtered_month = {"revenue": float(fm["revenue"]), "profit": float(fm["profit"])}

    # Async alerts
    try:
        send_dashboard_alerts_async()
    except Exception as e:
        print("❌ Dashboard async email error:", e)

    return jsonify({
        "total_stock_units": int(total_stock),
        "total_investment": float(total_investment),
        "stock_balance_cost": float(total_investment),
        "stock_market_value": float(stock_market_value),
        "total_sales": float(total_sales),
        "total_profit": float(total_profit),
        "cash_in_hand": float(cash_in_hand),
        "daily_sales": float(daily_summary["revenue"]),
        "daily_profit": float(daily_summary["profit"]),
        "weekly_sales": float(weekly_summary["revenue"]),
        "weekly_profit": float(weekly_summary["profit"]),
        "weekly_breakdown": weekly_breakdown,
        "monthly_sales": float(monthly_summary["revenue"]),
        "monthly_profit": float(monthly_summary["profit"]),
        "monthly_breakdown": monthly_breakdown,
        "filtered_day": filtered_day,
        "filtered_month": filtered_month,
        "fast_moving_products": get_fast_moving_items(),
        "low_stock_products": get_low_stock(LOW_STOCK_THRESHOLD),
    })

# =======================
# PRODUCTS MANAGEMENT
# =======================
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
    quantity = int(data["quantity"])
    cp = float(data["cp"])
    execute_query("""
        INSERT INTO products (name, cp, sp, quantity, category, initial_quantity, initial_cp)
        VALUES (?,?,?,?,?,?,?)
    """, (data["name"], cp, float(data["sp"]), quantity, data.get("category"), quantity, cp))
    recalc_total_investment()
    return jsonify({"status":"success"})

@admin_bp.route("/products/<int:pid>", methods=["PUT"])
def edit_product(pid):
    guard = admin_required()
    if guard: return guard
    data = request.json
    quantity = int(data["quantity"])
    cp = float(data["cp"])
    execute_query("""
        UPDATE products
        SET name=?, cp=?, sp=?, quantity=?, category=?,
            initial_quantity=?, initial_cp=?
        WHERE id=?
    """, (data["name"], cp, float(data["sp"]), quantity, data.get("category"), quantity, cp, pid))
    recalc_total_investment()
    return jsonify({"status":"updated"})

@admin_bp.route("/products/<int:pid>", methods=["DELETE"])
def delete_product(pid):
    guard = admin_required()
    if guard: return guard
    execute_query("DELETE FROM products WHERE id=?", (pid,))
    recalc_total_investment()
    return jsonify({"status":"deleted"})

# =======================
# STAFF MANAGEMENT
# =======================
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
    name = data.get("name","").strip()
    password = data.get("password","").strip()
    if not name or not password:
        return jsonify({"error":"Name and password required"}), 400
    hashed = hash_password(password)
    execute_query("INSERT INTO users (name, role, password) VALUES (?,?,?)", (name, 'staff', hashed))
    return jsonify({"status":"success","message":f"Staff {name} added"})

@admin_bp.route("/staff/<int:staff_id>", methods=["DELETE"])
def remove_staff(staff_id):
    guard = admin_required()
    if guard: return guard
    execute_query("DELETE FROM users WHERE id=? AND role='staff'", (staff_id,))
    return jsonify({"status":"success","message":"Staff removed"})

@admin_bp.route("/staff/<int:staff_id>/reset_password", methods=["POST"])
def reset_staff_password(staff_id):
    guard = admin_required()
    if guard: return guard
    data = request.json or {}
    new_pass = data.get("new_password","").strip()
    if not new_pass: return jsonify({"error":"New password required"}),400
    hashed = hash_password(new_pass)
    execute_query("UPDATE users SET password=? WHERE id=? AND role='staff'", (hashed, staff_id))
    return jsonify({"status":"success","message":"Staff password updated"})

@admin_bp.route("/staff/<int:staff_id>/force_change_password", methods=["POST"])
def force_staff_password_change(staff_id):
    guard = admin_required()
    if guard: return guard
    execute_query("UPDATE users SET force_password_change=1 WHERE id=? AND role='staff'", (staff_id,))
    return jsonify({"status":"success","message":"Staff will be prompted to change password next login"})

# =======================
# SALES MANAGEMENT
# =======================
@admin_bp.route("/sales", methods=["GET"])
def list_sales():
    guard = admin_required()
    if guard: return guard
    sales = fetch_all("""
        SELECT s.id, p.name AS product_name, s.quantity, p.sp, p.cp, s.timestamp,
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
        if isinstance(s["timestamp"], str):
            try:
                dt = datetime.fromisoformat(s["timestamp"])
                s["timestamp"] = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                s["timestamp"] = str(s["timestamp"])
        elif hasattr(s["timestamp"], "strftime"):
            s["timestamp"] = s["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    return jsonify(sales)

@admin_bp.route("/sales", methods=["POST"])
def record_sale_admin():
    guard = admin_required()
    if guard: return guard

    data = request.json or {}
    admin_id = session.get("user_id")
    cart_items = data.get("cart", [])

    if not cart_items or not isinstance(cart_items, list):
        return jsonify({"error": "Cart is empty or invalid"}), 400

    invoice_cart = []
    grand_total = 0

    for item in cart_items:
        product_id = item.get("product_id")
        quantity = int(item.get("quantity", 0))
        if not product_id or quantity <= 0:
            return jsonify({"error": f"Invalid product or quantity for product_id {product_id}"}), 400

        product = fetch_one("SELECT id, name, sp, quantity FROM products WHERE id=?", (product_id,))
        if not product:
            return jsonify({"error": f"Product ID {product_id} not found"}), 404

        available_qty = int(product["quantity"])
        if available_qty < quantity:
            return jsonify({"error": f"Insufficient stock for {product['name']}"}), 400

        invoice_cart.append({
            "product_id": product_id,
            "name": product["name"],
            "quantity": quantity,
            "sp": float(product["sp"])
        })
        grand_total += quantity * float(product["sp"])

    # Record sale and update stock
    for item in invoice_cart:
        execute_query(
            "INSERT INTO sales (product_id, quantity, staff_id, timestamp) VALUES (?,?,?,?)",
            (item["product_id"], item["quantity"], admin_id, now_local_str())
        )
        execute_query(
            "UPDATE products SET quantity = quantity - ? WHERE id=?",
            (item["quantity"], item["product_id"])
        )

    # Generate invoice
    admin_name = fetch_one("SELECT name FROM users WHERE id=?", (admin_id,))["name"]
    invoice_text = generate_invoice(invoice_cart, sold_by=admin_name)

    return jsonify({
        "status": "success",
        "total": grand_total,
        "invoice": invoice_text,
        "message": f"Sale recorded successfully. Total: ₦{grand_total}"
    })

@admin_bp.route("/sales/<int:sale_id>", methods=["DELETE"])
def delete_sale(sale_id):
    guard = admin_required()
    if guard: return guard
    sale = fetch_one("SELECT product_id, quantity FROM sales WHERE id=?", (sale_id,))
    if not sale:
        return jsonify({"error": "Sale not found"}), 404
    product_id = sale["product_id"]
    quantity_sold = int(sale["quantity"])
    execute_query("DELETE FROM sales WHERE id=?", (sale_id,))
    execute_query("UPDATE products SET quantity = quantity + ? WHERE id=?", (quantity_sold, product_id))
    return jsonify({"status": "deleted", "message": f"Sale ID {sale_id} deleted and stock restored"})

# =======================
# PASSWORD MANAGEMENT
# =======================
@admin_bp.route("/change_password", methods=["POST"])
def change_admin_password():
    guard = admin_required()
    if guard: return guard

    data = request.json or {}
    current = data.get("current_password","").strip()
    new_pass = data.get("new_password","").strip()
    if not new_pass: return jsonify({"error":"New password required"}),400

    user = fetch_one("SELECT password FROM users WHERE id=?",(session["user_id"],))
    current_hash = user.get("password","") if user else ""
    if current_hash:
        if not current: return jsonify({"error":"Current password required"}),400
        if not verify_password(current,current_hash):
            return jsonify({"error":"Current password incorrect"}),400

    hashed_new = hash_password(new_pass)
    execute_query("UPDATE users SET password=? WHERE id=?",(hashed_new,session["user_id"]))
    return jsonify({"status":"success","message":"Admin password updated successfully"})

# =======================
# CLEAR ALL ACTIVITIES
# =======================
@admin_bp.route("/clear_all_activities", methods=["POST"])
def clear_all_activities():
    guard = admin_required()
    if guard: return guard

    data = request.json or {}
    password = data.get("password","").strip()
    if not password:
        return jsonify({"error": "Admin password required."}), 400

    admin_user = fetch_one("SELECT password FROM users WHERE id=?", (session["user_id"],))
    if not admin_user or not verify_password(password, admin_user.get("password","")):
        return jsonify({"error": "Incorrect admin password."}), 401

    def _clear_all():
        try:
            execute_query("DELETE FROM sales")
            execute_query("DELETE FROM products")
            execute_query("DELETE FROM users WHERE role='staff'")
            execute_query("DELETE FROM email_alerts")
            execute_query("UPDATE meta SET total_investment = 0 WHERE id = 1" )
            print("✅ All activities cleared successfully (Admins preserved)")
        except Exception as e:
            print("❌ Error clearing activities:", e)

    threading.Thread(target=_clear_all, daemon=True).start()
    return jsonify({"status":"success","message":"Clearing all activities has started in the background. Admins are preserved."})
