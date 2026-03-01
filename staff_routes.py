# staff_bp.py
from flask import Blueprint, request, jsonify, session
from auth import is_session_active
from db import execute_query, fetch_all, fetch_one
from utils import now_local_str, generate_invoice  # ✅ Local time + invoice

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
    Input JSON: { "cart": [ {product_id, quantity} ] }
    Returns total sale AND JustRite-style invoice.
    Timestamp is stored in Nigeria local time (WAT).
    """
    if not is_session_active("staff"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}
    staff_id = session.get("user_id")
    cart_items = data.get("cart", [])

    if not cart_items or not isinstance(cart_items, list):
        return jsonify({"error": "Cart is empty or invalid"}), 400

    invoice_cart = []
    grand_total = 0

    # Validate all products first
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

        # Prepare for invoice
        invoice_cart.append({
            "product_id": product_id,
            "name": product["name"],
            "quantity": quantity,
            "sp": float(product["sp"])
        })
        grand_total += quantity * float(product["sp"])

    # Record each sale in DB
    for item in invoice_cart:
        execute_query(
            "INSERT INTO sales (product_id, quantity, staff_id, timestamp) VALUES (?, ?, ?, ?)",
            (item["product_id"], item["quantity"], staff_id, now_local_str())
        )
        execute_query(
            "UPDATE products SET quantity = quantity - ? WHERE id=?",
            (item["quantity"], item["product_id"])
        )

    # Generate invoice
    staff_name = fetch_one("SELECT name FROM users WHERE id=?", (staff_id,))["name"]
    invoice_text = generate_invoice(invoice_cart, sold_by=staff_name)

    return jsonify({
        "status": "success",
        "total": grand_total,
        "invoice": invoice_text,
        "message": f"Sale recorded! Total: ₦{grand_total}"
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
        WHERE s.staff_id = ?
        ORDER BY s.timestamp DESC  
    """, (staff_id,))

    # Cast numeric fields and fix timestamp format
    for s in sales:
        s["quantity"] = int(s["quantity"])
        s["sp"] = float(s["sp"])
        s["timestamp"] = s["timestamp"].isoformat() if hasattr(s["timestamp"], "isoformat") else str(s["timestamp"])

    return jsonify(sales or [])