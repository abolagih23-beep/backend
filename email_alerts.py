import smtplib
import socket
import threading
from email.message import EmailMessage
from datetime import date
import sqlite3

from config import EMAIL_USER, EMAIL_PASS, ALERT_EMAILS, DB_PATH
from utils import get_low_stock, get_fast_moving_items

LOW_STOCK_THRESHOLD = 7
DB_TABLE = "email_cache"

# -----------------------------
# SQLite setup for caching
# -----------------------------
def init_cache():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {DB_TABLE} (
            id INTEGER PRIMARY KEY,
            last_sent DATE
        )
    """)
    # Ensure there’s always 1 row for today check
    cur.execute(f"INSERT OR IGNORE INTO {DB_TABLE} (id, last_sent) VALUES (1, NULL)")
    conn.commit()
    cur.close()
    conn.close()


def get_last_sent_date():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(f"SELECT last_sent FROM {DB_TABLE} WHERE id=1")
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row and row[0]:
        return date.fromisoformat(row[0])
    return None


def set_last_sent_date(today):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(f"UPDATE {DB_TABLE} SET last_sent=? WHERE id=1", (today.isoformat(),))
    conn.commit()
    cur.close()
    conn.close()


# -----------------------------
# Email sending
# -----------------------------
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


# -----------------------------
# Asynchronous wrapper
# -----------------------------
def async_send(func, *args, **kwargs):
    threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True).start()


# -----------------------------
# Alert functions
# -----------------------------
def low_stock_alert(items):
    if not isinstance(items, list):
        return

    low_items = [i for i in items if int(i.get("quantity", 0)) < LOW_STOCK_THRESHOLD]
    if not low_items:
        return

    body = "⚠️ LOW STOCK ALERT (Below 7 units)\n\n"
    for i in low_items:
        name = i.get("name", "Unknown Product")
        quantity = int(i.get("quantity", 0))
        body += f"- {name} → Remaining: {quantity}\n"

    async_send(send_email, "⚠️ Low Stock Alert", body)


def fast_moving_alert(items):
    if not items or not isinstance(items, list):
        return

    body = "🔥 FAST MOVING PRODUCTS ALERT\n\n"
    for i in items:
        name = i.get("name", "Product ID " + str(i.get("product_id")))
        sold_qty = int(i.get("sold_qty", 0))
        body += f"- {name} → Sold: {sold_qty}\n"

    async_send(send_email, "🔥 Fast Moving Products Alert", body)


# -----------------------------
# Dashboard alert main function
# -----------------------------
def send_dashboard_alerts():
    init_cache()
    today = date.today()
    last_sent = get_last_sent_date()

    # Only send once per day
    if last_sent == today:
        return

    try:
        low_stock = get_low_stock() or []
        fast_moving = get_fast_moving_items() or []

        if low_stock:
            low_stock_alert(low_stock)
        if fast_moving:
            fast_moving_alert(fast_moving)

        set_last_sent_date(today)

    except Exception as e:
        print("❌ Dashboard alert error:", e)