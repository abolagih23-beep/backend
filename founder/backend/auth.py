# auth.py
from flask import Blueprint, request, jsonify, session
from db import fetch_one
from utils import verify_password, hash_password  # Safe bcrypt version
from config import SESSION_TIMEOUT
from datetime import datetime, timedelta

auth_bp = Blueprint("auth_bp", __name__)

# --------------------------
# Login Route
# --------------------------
@auth_bp.route("/login", methods=["POST"])
def login_route():
    """
    Login endpoint.
    Expects JSON: { "name": str, "password": str }
    Sets session variables: user_id, role, last_active
    """
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    password = (data.get("password") or "").strip()

    if not name or not password:
        return jsonify({"status": "fail", "error": "Missing username or password"}), 400

    user = fetch_one("SELECT id, password, role FROM users WHERE name=%s", (name,))
    if not user or not verify_password(password, user.get("password", "")):
        return jsonify({"status": "fail", "error": "Invalid credentials"}), 401

    # ✅ Set session
    session["user_id"] = user["id"]
    session["role"] = user["role"]
    session["last_active"] = datetime.now().timestamp()

    return jsonify({"status": "success", "role": user["role"]})

# --------------------------
# Logout Route
# --------------------------
@auth_bp.route("/logout", methods=["POST"])
def logout_route():
    """Clears session"""
    session.clear()
    return jsonify({"status": "success"})

# --------------------------
# Session Check Helper
# --------------------------
def is_session_active(required_role: str = None) -> bool:
    """
    Checks if session is active and optionally if role matches.
    Refreshes last_active timestamp on success.
    """
    user_id = session.get("user_id")
    role = session.get("role")
    last_active = session.get("last_active")

    if not user_id or not last_active:
        return False

    # Check session timeout
    elapsed = datetime.now().timestamp() - last_active
    if elapsed > SESSION_TIMEOUT:
        session.clear()
        return False

    # Check role if provided
    if required_role and role != required_role:
        return False

    # Refresh last_active
    session["last_active"] = datetime.now().timestamp()
    return True

# --------------------------
# Current Session Info Route
# --------------------------
@auth_bp.route("/session", methods=["GET"])
def current_session():
    """
    Returns current session info for frontend.
    Ensures session is valid.
    """
    if not is_session_active():
        return jsonify({"error": "Unauthorized"}), 401

    return jsonify({
        "user_id": session.get("user_id"),
        "role": session.get("role")
    })

# --------------------------
# One-time password fixer (optional)
# --------------------------
@auth_bp.route("/fix_passwords", methods=["POST"])
def fix_passwords_route():
    """
    One-time route to reset invalid passwords in DB to a secure default.
    Only admin should call this. Returns number of users fixed.
    """
    if not is_session_active("admin"):
        return jsonify({"error": "Unauthorized"}), 401

    default_password = "ChangeMe123!"  # temporary password
    users = fetch_all("SELECT id, password FROM users")
    fixed_count = 0

    for u in users:
        if not verify_password(default_password, u.get("password", "")):
            new_hash = hash_password(default_password)
            execute_query("UPDATE users SET password=%s WHERE id=%s", (new_hash, u["id"]))
            fixed_count += 1

    return jsonify({"status": "success", "fixed_users": fixed_count, "temp_password": default_password})