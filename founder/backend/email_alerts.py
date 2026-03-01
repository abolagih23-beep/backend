# email_alerts.py
import smtplib
import socket
from email.message import EmailMessage
from config import EMAIL_USER, EMAIL_PASS, ALERT_EMAILS
from utils import get_low_stock, get_fast_moving_items

LOW_STOCK_THRESHOLD = 7   # 🔥 alert when quantity < 7

# -------------------------
# Safe Email Sender
# -------------------------
def send_email(subject, body):
    """
    Sends email safely. Never crashes the app if email fails.
    """
    if not EMAIL_USER or not EMAIL_PASS or not ALERT_EMAILS:
        print("⚠️ Email config missing. Skipping email.")
        return

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = ", ".join(ALERT_EMAILS)
        msg.set_content(body)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)

        print(f"✅ Email sent: {subject}")

    except (smtplib.SMTPException, socket.gaierror, TimeoutError) as e:
        # 🔥 NEVER crash the app
        print("❌ Email failed safely:", e)


# -------------------------
# Low Stock Alert (< threshold)
# -------------------------
def low_stock_alert(items):
    """
    Sends low stock alert for items below LOW_STOCK_THRESHOLD
    """
    if not items:
        return

    # 🔍 filter only items below threshold
    low_items = [i for i in items if int(i.get("quantity", 0)) < LOW_STOCK_THRESHOLD]

    if not low_items:
        return

    body = "⚠️ LOW STOCK ALERT (Below 7 units)\n\n"
    for i in low_items:
        body += f"- {i['name']} → Remaining: {i['quantity']}\n"

    send_email("⚠️ Low Stock Alert", body)


# -------------------------
# Fast Moving Items Alert
# -------------------------
def fast_moving_alert(items):
    """
    Sends alert for fast-moving products
    """
    if not items:
        return

    body = "🔥 FAST MOVING PRODUCTS ALERT\n\n"
    for i in items:
        # Use product name from utils; fallback to product_id if missing
        body += (
            f"- {i.get('name', 'Product ID ' + str(i.get('product_id')))} "
            f"→ Sold: {i.get('sold_qty', 0)}\n"
        )

    send_email("🔥 Fast Moving Products Alert", body)