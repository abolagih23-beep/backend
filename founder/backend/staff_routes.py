from flask import Blueprint, request, jsonify, session
from auth import is_session_active
from db import execute_query, fetch_all

staff_bp = Blueprint("staff_bp", __name__)

# -------------------------
# FETCH PRODUCTS (STAFF VIEW)
# -------------------------
@staff_bp.route("/products", methods=["GET"])
def list_products():
    """
    Returns all products with stock and selling price.
    Cost price and profit are hidden from staff.
    """
    if not is_session_active("staff"):
        return jsonify({"error": "Unauthorized"}), 401

    products = fetch_all("SELECT id, name, sp, quantity, category FROM products ORDER BY name")
    
    # Cast numeric fields for safety
    for p in products:
        p["sp"] = float(p["sp"])
        p["quantity"] = int(p["quantity"])
    
    return jsonify(products)


# -------------------------
# RECORD SALE (STAFF)
# -------------------------
@staff_bp.route("/sales", methods=["POST"])
def record_sale():
    """
    Staff records a sale.
    Input JSON: { "product_id": int, "quantity": int }
    Returns total sale only; profit is hidden.
    Timestamp is stored correctly in the DB.
    """
    if not is_session_active("staff"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}
    staff_id = session.get("user_id")
    product_id = data.get("product_id")
    quantity = data.get("quantity")

    if not product_id or not quantity or int(quantity) <= 0:
        return jsonify({"error": "Missing product_id or invalid quantity"}), 400

    # Fetch product
    stock = fetch_all("SELECT quantity, cp, sp FROM products WHERE id=%s", (product_id,))
    if not stock:
        return jsonify({"error": "Product not found"}), 404

    available_qty = int(stock[0]["quantity"])
    cp = float(stock[0]["cp"])
    sp = float(stock[0]["sp"])

    if available_qty < int(quantity):
        return jsonify({"error": "Insufficient stock"}), 400

    # Insert sale with CURRENT_TIMESTAMP
    execute_query(
        "INSERT INTO sales (product_id, quantity, staff_id, timestamp) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)",
        (product_id, int(quantity), staff_id)
    )

    # Update stock
    execute_query(
        "UPDATE products SET quantity = quantity - %s WHERE id=%s",
        (int(quantity), product_id)
    )

    total_value = sp * int(quantity)

    return jsonify({
        "status": "success",
        "total": total_value,
        "message": f"Sale recorded! Total: ₦{total_value}"
    })


# -------------------------
# SALES HISTORY (STAFF VIEW)
# -------------------------
@staff_bp.route("/sales/history", methods=["GET"])
def sales_history():
    """
    Returns all sales by the logged-in staff.
    Profit and cost price are hidden.
    Timestamp returned in ISO format for frontend consistency.
    """
    if not is_session_active("staff"):
        return jsonify({"error": "Unauthorized"}), 401

    staff_id = session.get("user_id")

    sales = fetch_all("""
        SELECT 
            s.id,
            p.name AS product_name,
            s.quantity,
            p.sp,
            s.timestamp
        FROM sales s
        JOIN products p ON s.product_id = p.id
        WHERE s.staff_id = %s
        ORDER BY s.timestamp DESC  
    """, (staff_id,))

    # Cast numeric fields and fix timestamp format
    for s in sales:
        s["quantity"] = int(s["quantity"])
        s["sp"] = float(s["sp"])
        s["timestamp"] = s["timestamp"].isoformat() if hasattr(s["timestamp"], "isoformat") else str(s["timestamp"])

    return jsonify(sales or [])