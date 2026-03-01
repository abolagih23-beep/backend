from db import fetch_all, fetch_one, execute_query
import bcrypt
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # ✅ Python 3.9+ built-in

# ✅ Nigeria timezone (WAT = UTC+1)
LOCAL_TZ = ZoneInfo("Africa/Lagos")

def now_local() -> datetime:
    """Returns current datetime in Nigeria local time (WAT)."""
    return datetime.now(LOCAL_TZ)

def now_local_str() -> str:
    """Returns current local time as a formatted string for DB insertion."""
    return now_local().strftime("%Y-%m-%d %H:%M:%S")

def today_local_str() -> str:
    """Returns today's date string in Nigeria local time."""
    return now_local().strftime("%Y-%m-%d")


# ==========================
# PASSWORD UTILITIES
# ==========================
def hash_password(plain_password: str) -> str:
    if not isinstance(plain_password, str):
        raise ValueError("Password must be a string")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        if not hashed_password or not isinstance(hashed_password, str):
            return False
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except (ValueError, TypeError):
        return False


# ==========================
# CALCULATE DAILY PROFIT
# ==========================
def calculate_profit() -> float:
    today = today_local_str()
    daily = fetch_one("""
        SELECT COALESCE(SUM((products.sp - products.cp) * sales.quantity), 0) AS profit
        FROM sales
        JOIN products ON sales.product_id = products.id
        WHERE DATE(sales.timestamp) = ?
    """, (today,))["profit"]
    return float(daily)


# ==========================
# UPDATE STOCK
# ==========================
def update_stock(product_id: int, qty_sold: int):
    execute_query(
        "UPDATE products SET quantity = quantity - ? WHERE id = ?",
        (qty_sold, product_id)
    )


# ==========================
# GET LOW STOCK PRODUCTS
# ==========================
def get_low_stock(threshold: int = 5):
    products = fetch_all(
        "SELECT id, name, quantity FROM products WHERE quantity <= ? ORDER BY quantity ASC",
        (threshold,)
    )
    for p in products:
        p["quantity"] = int(p["quantity"])
    return products


# ==========================
# GET FAST MOVING PRODUCTS
# ==========================
def get_fast_moving_items(days: int = 1, min_sold: int = 20, limit: int = 5):
    since_date = (now_local() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    products = fetch_all("""
        SELECT p.id, p.name, SUM(s.quantity) AS sold_qty
        FROM sales s
        JOIN products p ON s.product_id = p.id
        WHERE s.timestamp >= ?
        GROUP BY p.id, p.name
        HAVING sold_qty >= ?
        ORDER BY sold_qty DESC
        LIMIT ?
    """, (since_date, min_sold, limit))
    for p in products:
        p["sold_qty"] = int(p["sold_qty"])
    return products


# ==========================
# ONE-TIME PASSWORD FIX SCRIPT
# ==========================
def fix_all_passwords(default_password: str = "ChangeMe123!"):
    print("Starting password fix...")
    users = fetch_all("SELECT id, password FROM users")
    fixed_count = 0
    for user in users:
        user_id = user["id"]
        pwd = user.get("password", "")
        valid = verify_password(default_password, pwd) if pwd else False
        if not valid:
            new_hashed = hash_password(default_password)
            execute_query("UPDATE users SET password=? WHERE id=?", (new_hashed, user_id))
            fixed_count += 1
            print(f"Fixed password for user ID {user_id}")
    print(f"Password fix completed. Total fixed: {fixed_count}")


# ==========================
# JUSTRITE-STYLE SALES INVOICE GENERATOR
# ==========================
def generate_invoice(cart_items: list, sold_by: str, sale_id: int = None):
    """
    Generates a full JustRite-style invoice as a string.
    cart_items: list of dicts [{product_id, name, quantity, sp}]
    sold_by: staff/admin name
    sale_id: optional sale ID
    """
    invoice_lines = []
    invoice_lines.append("===== JustRite Sales Invoice =====")
    invoice_lines.append(f"Date: {now_local_str()}")
    if sale_id:
        invoice_lines.append(f"Sale ID: {sale_id}")
    invoice_lines.append(f"Sold By: {sold_by}")
    invoice_lines.append("-" * 40)
    invoice_lines.append(f"{'Item':20} {'Qty':>3} {'Unit':>6} {'Total':>8}")
    invoice_lines.append("-" * 40)

    grand_total = 0
    for item in cart_items:
        name = item.get("name","Unknown")[:20]
        qty = int(item.get("quantity",0))
        sp = float(item.get("sp",0))
        total = qty * sp
        grand_total += total
        invoice_lines.append(f"{name:20} {qty:>3} {sp:>6.2f} {total:>8.2f}")

    invoice_lines.append("-" * 40)
    invoice_lines.append(f"{'GRAND TOTAL':>31} {grand_total:>8.2f}")
    invoice_lines.append("=" * 40)
    invoice_lines.append("Thank you for your purchase!")
    return "\n".join(invoice_lines)


# ==========================
# USAGE EXAMPLE (ADD TO CART)
# ==========================
# cart = [
#     {"product_id": 1, "name": "Widget A", "quantity": 2, "sp": 500},
#     {"product_id": 3, "name": "Gadget X", "quantity": 1, "sp": 1200},
# ]
# print(generate_invoice(cart, sold_by="Abolaji", sale_id=101))