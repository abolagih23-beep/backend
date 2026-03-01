from flask import Flask
from flask_cors import CORS

# -------------------------
# Import blueprints
# -------------------------
from admin_routes import admin_bp
from staff_routes import staff_bp
from auth import auth_bp      # login/logout/session
from founder.founder import founder_bp  # Founder Dashboard (no login needed)

# -------------------------
# Initialize Flask App
# -------------------------
app = Flask(__name__)
app.secret_key = "supersecretkey"  # session secret key

# Enable CORS with credentials so frontend can send cookies
CORS(app, supports_credentials=True)

# -------------------------
# Register Blueprints
# -------------------------
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(staff_bp, url_prefix="/staff")
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(founder_bp, url_prefix="/founder")  # NEW: founder dashboard

# -------------------------
# Health Check / Root Route
# -------------------------
@app.route("/")
def home():
    return "✅ Inventory & Sales System Backend Running - Full Blown PRO+"

# -------------------------
# Run Flask App
# -------------------------
if __name__ == "__main__":
    # Use host='0.0.0.0' for LAN access if needed
    app.run(debug=True)