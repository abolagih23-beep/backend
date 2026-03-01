# config.py

# ----------------------------
# SQLite Database Configuration
# ----------------------------
# This replaces PostgreSQL completely
# The database file will be created in the project root folder
DB_PATH = "mydatabase.db"
SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH}"

# ----------------------------
# Email Notifications (Gmail)
# ----------------------------
EMAIL_USER = "abolagih23@gmail.com"
EMAIL_PASS = "fgmo wyak dfkk vbyg"
ALERT_EMAILS = ["abolagih23@gmail.com"]

# ----------------------------
# Session timeout in seconds (3 minutes)
# ----------------------------
SESSION_TIMEOUT = 1800