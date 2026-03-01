# backend/dashboard_routes.py
from flask import Blueprint, jsonify
from db import fetch_all

dashboard_bp = Blueprint("dashboard_bp", __name__)

# ----------------------
# DASHBOARD DATA (TOTAL INVESTMENT)
# ----------------------
@dashboard_bp.route("/dashboard_data", methods=["GET"])
def dashboard_data():
    # Fetch all products
    products = fetch_all("SELECT cp, sp, quantity, initial_quantity FROM products")

    total_investment = 0
    total_stock_units = 0
    stock_market_value = 0

    for p in products:
        cp = float(p["cp"])
        sp = float(p["sp"])
        qty = int(p["quantity"])
        initial_qty = int(p["initial_quantity"])  # 🔹 use initial_quantity

        total_investment += cp * initial_qty      # Total investment fixed by initial_quantity
        total_stock_units += qty
        stock_market_value += sp * qty

    return jsonify({
        "total_investment": total_investment,
        "total_stock_units": total_stock_units,
        "stock_market_value": stock_market_value
    })