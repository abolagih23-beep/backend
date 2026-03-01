from flask import Flask, send_from_directory
from flask_cors import CORS

# -------------------------
# Import blueprints
# -------------------------
from admin_routes import admin_bp
from staff_routes import staff_bp
from auth import auth_bp      # login/logout/session
from founder.founder import founder_bp  # Founder Dashboard (no login needed)
from dashboard_routes import dashboard_bp  # NEW: Dashboard for Total Investment

# -------------------------
# Initialize Flask App
# -------------------------
app = Flask(__name__, static_folder="static")
app.secret_key = "supersecretkey"  # session secret key

# Enable CORS with credentials so frontend can send cookies
CORS(app, supports_credentials=True)

# -------------------------
# Register Blueprints
# -------------------------
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(staff_bp, url_prefix="/staff")
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(founder_bp, url_prefix="/founder")  # Founder dashboard
app.register_blueprint(dashboard_bp, url_prefix="/api")      # NEW: Dashboard routes

# -------------------------
# Serve static files (CSS, JS, images, manifest, sw.js)
# -------------------------
@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

@app.route("/admin/<path:filename>")
def serve_admin_static(filename):
    return send_from_directory(f"{app.static_folder}/admin", filename)

@app.route("/staff/<path:filename>")
def serve_staff_static(filename):
    return send_from_directory(f"{app.static_folder}/staff", filename)

@app.route("/icons/<path:filename>")
def serve_icons(filename):
    return send_from_directory(f"{app.static_folder}/icons", filename)

@app.route("/image/<path:filename>")
def serve_images(filename):
    return send_from_directory(f"{app.static_folder}/image", filename)

# -------------------------
# Health Check / Root Route
# -------------------------
@app.route("/")
def home():
    # Serve your login page from static
    return send_from_directory(app.static_folder, "index.html")

# -------------------------
# Run Flask App
# -------------------------
if __name__ == "__main__":
    # Use host='0.0.0.0' for LAN access if needed
    app.run(host="0.0.0.0", port=5000, debug=True)