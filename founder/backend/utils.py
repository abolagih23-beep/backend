# utils.py
from db import fetch_all, fetch_one, execute_query
import bcrypt

# ==========================
# PASSWORD UTILITIES
# ==========================
def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password using bcrypt
    """
    if not isinstance(plain_password, str):
        raise ValueError("Password must be a string")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a hashed password.
    Returns False if hashed_password is invalid, malformed, or None.
    """
    try:
        if not hashed_password or not isinstance(hashed_password, str):
            return False
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except (ValueError, TypeError):  # ⚡ No bcrypt.error, safe
        return False


# ==========================
# CALCULATE DAILY PROFIT
# ==========================
def calculate_profit() -> float:
    """
    Returns total profit for today
    """
    daily = fetch_one("""
        SELECT COALESCE(SUM((products.sp - products.cp) * sales.quantity), 0) AS profit
        FROM sales
        JOIN products ON sales.product_id = products.id
        WHERE DATE(sales.timestamp) = CURRENT_DATE
    """)["profit"]
    return float(daily)


# ==========================
# UPDATE STOCK
# ==========================
def update_stock(product_id: int, qty_sold: int):
    """
    Decreases product quantity after a sale
    """
    execute_query(
        "UPDATE products SET quantity = quantity - %s WHERE id = %s",
        (qty_sold, product_id)
    )


# ==========================
# GET LOW STOCK PRODUCTS
# ==========================
def get_low_stock(threshold: int = 5):
    """
    Returns all products with quantity <= threshold
    """
    products = fetch_all(
        "SELECT id, name, quantity FROM products WHERE quantity <= %s ORDER BY quantity ASC",
        (threshold,)
    )
    for p in products:
        p["quantity"] = int(p["quantity"])
    return products


# ==========================
# GET FAST MOVING PRODUCTS
# ==========================
def get_fast_moving_items(days: int = 1, min_sold: int = 20, limit: int = 5):
    """
    Returns top-selling products in the last `days` days with at least `min_sold` quantity
    """
    products = fetch_all("""
        SELECT p.id, p.name, SUM(s.quantity) AS sold_qty
        FROM sales s
        JOIN products p ON s.product_id = p.id
        WHERE s.timestamp >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY p.id, p.name
        HAVING SUM(s.quantity) >= %s
        ORDER BY sold_qty DESC
        LIMIT %s
    """, (days, min_sold, limit))

    for p in products:
        p["sold_qty"] = int(p["sold_qty"])
    return products


# ==========================
# ONE-TIME PASSWORD FIX SCRIPT
# ==========================
def fix_all_passwords(default_password: str = "ChangeMe123!"):
    """
    One-time script to fix invalid or plain-text passwords in the database.
    Any user with invalid hash or empty password will have their password reset
    to a secure hashed default password.
    """
    print("Starting password fix...")

    users = fetch_all("SELECT id, password FROM users")
    fixed_count = 0

    for user in users:
        user_id = user["id"]
        pwd = user.get("password", "")

        # Check if the password is invalid
        valid = verify_password(default_password, pwd) if pwd else False

        if not valid:
            # Replace with new hashed password
            new_hashed = hash_password(default_password)
            execute_query("UPDATE users SET password=%s WHERE id=%s", (new_hashed, user_id))
            fixed_count += 1
            print(f"Fixed password for user ID {user_id}")

    print(f"Password fix completed. Total fixed: {fixed_count}")


# ==========================
# USAGE:
# Uncomment the next line and run this file once to fix all passwords
# fix_all_passwords("NewSecureDefault123!")