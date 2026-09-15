from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session
)

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from datetime import datetime, timedelta

import sqlite3
import re
import os
import qrcode
import time

from werkzeug.utils import secure_filename
from flask import send_file
from reportlab.pdfgen import canvas
from io import BytesIO
from datetime import datetime

# ==========================================================
# Flask Configuration
# ==========================================================

app = Flask(__name__)
app.secret_key = "payflow_secret_key_2026"

# ==========================================================
# Session Timeout Configuration
# ==========================================================

SESSION_TIMEOUT = 300   # 5 minutes (300 seconds)
# ==========================================================
# Session Timeout Checker
# ==========================================================

@app.before_request
def check_session_timeout():

    # Skip timeout check for login and static files
    if request.endpoint in ["login", "register", "static"]:
        return

    if "user_id" in session:

        current_time = time.time()

        last_activity = session.get("last_activity", current_time)

        if current_time - last_activity > SESSION_TIMEOUT:

            session.clear()

            return redirect(url_for("login"))

        session["last_activity"] = current_time
# ==========================================================
# Database Configuration
# ==========================================================

DATABASE = "wallet.db"

# ==========================================================
# Profile Picture Upload Configuration
# ==========================================================

UPLOAD_FOLDER = "static/profile_pictures"

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}

MAX_FILE_SIZE = 2 * 1024 * 1024

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ==========================================================
# Password Hasher
# ==========================================================

ph = PasswordHasher()

# ==========================================================
# Database Connection
# ==========================================================

def get_db_connection():

    conn = sqlite3.connect(
        DATABASE,
        timeout=30,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    return conn
# ==========================================================
# Notification Helper
# ==========================================================

def add_notification(cursor, user_id, title, message):

    cursor.execute("""
        INSERT INTO notifications(user_id, title, message)
        VALUES (?, ?, ?)
    """, (
        user_id,
        title,
        message
    )) 
# ==========================================================
# Image Validation
# ==========================================================

def allowed_file(filename):

    return (

        "." in filename

        and

        filename.rsplit(".", 1)[1].lower()

        in ALLOWED_EXTENSIONS

    )

# ==========================================================
# Validation Functions
# ==========================================================

def is_valid_name(name):

    name = name.strip()

    if len(name) < 3:
        return False

    return bool(re.fullmatch(r"[A-Za-z ]+", name))


def is_valid_email(email):

    email = email.strip().lower()

    pattern = r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$"

    return bool(re.fullmatch(pattern, email))


def is_valid_phone(phone):

    return bool(re.fullmatch(r"[6-9]\d{9}", phone))

# ==========================================================
# Password Validation
# ==========================================================

def has_sequential_characters(text):

    sequences = [

        "abcdefghijklmnopqrstuvwxyz",
        "zyxwvutsrqponmlkjihgfedcba",
        "0123456789",
        "9876543210"

    ]

    text = text.lower()

    for sequence in sequences:

        for i in range(len(sequence) - 3):

            if sequence[i:i+4] in text:
                return True

    return False


def is_valid_password(password, fullname, email, phone):

    if len(password) < 8 or len(password) > 10:
        return False, "Password must be 8–10 characters."

    if " " in password:
        return False, "Password cannot contain spaces."

    if password.lower() == "password":
        return False, "'password' cannot be used."

    if password == fullname:
        return False, "Password cannot be your name."

    if password == email:
        return False, "Password cannot be your email."

    if password == phone:
        return False, "Password cannot be your phone."

    if not re.search(r"[A-Z]", password):
        return False, "One uppercase letter required."

    if not re.search(r"[a-z]", password):
        return False, "One lowercase letter required."

    if not re.search(r"\d", password):
        return False, "One number required."

    if not re.search(r"[^A-Za-z0-9]", password):
        return False, "One special character required."

    if has_sequential_characters(password):
        return False, "Sequential passwords are not allowed."

    return True, "Password is valid."

# ==========================================================
# Landing Page
# ==========================================================

@app.route("/")
def home():
    return render_template("index.html")

# ==========================================================
# Login
# ==========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        )

        user = cursor.fetchone()

        # --------------------------------------------------
        # Email not found
        # --------------------------------------------------

        if user is None:

            conn.close()

            return "❌ Email not registered."

        # --------------------------------------------------
        # Check account lock
        # --------------------------------------------------

        if user["lock_until"]:

            lock_time = datetime.fromisoformat(user["lock_until"])

            if datetime.now() < lock_time:

                remaining = lock_time - datetime.now()

                minutes = remaining.seconds // 60

                conn.close()

                return (
                    f"❌ Account locked. "
                    f"Try again in {minutes} minute(s)."
                )

        try:

            # --------------------------------------------------
            # Verify password
            # --------------------------------------------------

            ph.verify(user["password"], password)

            # Reset failed attempts
            cursor.execute(
                """
                UPDATE users
                SET failed_attempts=0,
                    lock_until=NULL
                WHERE id=?
                """,
                (user["id"],)
            )

            conn.commit()

            # Create session
            session["user_id"] = user["id"]
            session["fullname"] = user["fullname"]
            session["email"] = user["email"]

            conn.close()

            return redirect(url_for("dashboard"))

        except VerifyMismatchError:

            failed_attempts = user["failed_attempts"] + 1

            # --------------------------------------------------
            # Lock account after 5 failures
            # --------------------------------------------------

            if failed_attempts >= 5:

                lock_until = datetime.now() + timedelta(minutes=15)

                cursor.execute(
                    """
                    UPDATE users
                    SET failed_attempts=?,
                        lock_until=?
                    WHERE id=?
                    """,
                    (
                        failed_attempts,
                        lock_until.isoformat(),
                        user["id"]
                    )
                )

                conn.commit()
                conn.close()

                return (
                    "❌ Too many failed attempts. "
                    "Account locked for 15 minutes."
                )

            else:

                cursor.execute(
                    """
                    UPDATE users
                    SET failed_attempts=?
                    WHERE id=?
                    """,
                    (
                        failed_attempts,
                        user["id"]
                    )
                )

                conn.commit()
                conn.close()

                remaining = 5 - failed_attempts

                return (
                    f"❌ Incorrect Password. "
                    f"{remaining} attempt(s) remaining."
                )

    return render_template("login.html")
# ==========================================================
# Dashboard
# ==========================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # -------------------------
    # User Details
    # -------------------------

    cursor.execute("""
        SELECT
            fullname,
            balance,
            profile_image
        FROM users
        WHERE id = ?
    """, (session["user_id"],))

    user = cursor.fetchone()

    # -------------------------
    # Total Added
    # -------------------------

    cursor.execute("""
        SELECT COALESCE(SUM(amount),0)
        FROM transactions
        WHERE user_id=?
        AND transaction_type='ADD MONEY'
    """, (session["user_id"],))

    total_added = cursor.fetchone()[0]

    # -------------------------
    # Total Sent
    # -------------------------

    cursor.execute("""
        SELECT COALESCE(SUM(amount),0)
        FROM transactions
        WHERE user_id=?
        AND transaction_type='SEND MONEY'
    """, (session["user_id"],))

    total_sent = cursor.fetchone()[0]

    # -------------------------
    # Biggest Expense
    # -------------------------

    cursor.execute("""
        SELECT COALESCE(MAX(amount),0)
        FROM transactions
        WHERE user_id=?
        AND transaction_type='SEND MONEY'
    """, (session["user_id"],))

    biggest_expense = cursor.fetchone()[0]

    # -------------------------
    # Average Transaction
    # -------------------------

    cursor.execute("""
        SELECT COALESCE(AVG(amount),0)
        FROM transactions
        WHERE user_id=?
    """, (session["user_id"],))

    average_transaction = round(cursor.fetchone()[0], 2)

    # -------------------------
    # Total Transactions
    # -------------------------

    cursor.execute("""
        SELECT COUNT(*)
        FROM transactions
        WHERE user_id=?
    """, (session["user_id"],))

    total_transactions = cursor.fetchone()[0]

    # -------------------------
    # AI Message
    # -------------------------

    if total_added == 0:

        ai_message = "💡 Start by adding money to your wallet."

    elif user["balance"] <= 100:

        ai_message = "🔴 Your wallet balance is very low."

    elif total_sent >= total_added * 0.80:

        ai_message = "🟠 You have spent more than 80% of your money."

    elif total_sent >= total_added * 0.50:

        ai_message = "🟡 Your spending is moderate."

    else:

        ai_message = "🟢 Excellent! Your spending looks healthy."

    # --------------------------------------------------
    # Monthly Analytics (Last 6 Months)
    # --------------------------------------------------

    cursor.execute("""
        SELECT
            strftime('%Y-%m', created_at) AS month,
            SUM(CASE
                    WHEN transaction_type='ADD MONEY'
                    THEN amount
                    ELSE 0
                END) AS added,
            SUM(CASE
                    WHEN transaction_type='SEND MONEY'
                    THEN amount
                    ELSE 0
                END) AS sent
        FROM transactions
        WHERE user_id=?
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6
    """, (session["user_id"],))

    analytics_rows = cursor.fetchall()

    # Reverse for chronological order
    analytics_rows = analytics_rows[::-1]

    chart_labels = [row["month"] for row in analytics_rows]
    chart_added = [float(row["added"] or 0) for row in analytics_rows]
    chart_sent  = [float(row["sent"] or 0) for row in analytics_rows]
    
    # --------------------------------------------------
# Unread Notifications Count
# --------------------------------------------------

    cursor.execute("""
    SELECT COUNT(*)
    FROM notifications
    WHERE user_id=?
      AND is_read=0
    """, (session["user_id"],))

    unread_notifications = cursor.fetchone()[0]
    conn.close()

    return render_template(

        "dashboard.html",

        fullname=user["fullname"],
        balance=user["balance"],
        profile_image=user["profile_image"],

        total_added=total_added,
        total_sent=total_sent,
        biggest_expense=biggest_expense,
        average_transaction=average_transaction,
        total_transactions=total_transactions,

        ai_message=ai_message,

        chart_labels=chart_labels,
        chart_added=chart_added,
        chart_sent=chart_sent,
        
        unread_notifications=unread_notifications,
    )

# ==========================================================
# Profile
# ==========================================================

@app.route("/profile", methods=["GET","POST"])
def profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":

        fullname = request.form.get("fullname").strip()
        phone = request.form.get("phone").strip()
        country = request.form.get("country").strip()

        image = request.files.get("profile_image")

        profile_image = None

        if image and image.filename != "":

            if allowed_file(image.filename):

                filename = secure_filename(image.filename)

                filename = f"{session['user_id']}_{filename}"

                image.save(
                    os.path.join(
                        app.config["UPLOAD_FOLDER"],
                        filename
                    )
                )

                profile_image = filename

        if profile_image:

            cursor.execute("""

                UPDATE users

                SET

                    fullname=?,
                    phone=?,
                    country=?,
                    profile_image=?

                WHERE id=?

            """,(

                fullname,
                phone,
                country,
                profile_image,
                session["user_id"]

            ))

        else:

            cursor.execute("""

                UPDATE users

                SET

                    fullname=?,
                    phone=?,
                    country=?

                WHERE id=?

            """,(

                fullname,
                phone,
                country,
                session["user_id"]

            ))

        conn.commit()

    cursor.execute("""

        SELECT
            fullname,
            email,
            phone,
            country,
            balance,
            profile_image

        FROM users

        WHERE id=?

    """,(session["user_id"],))

    user = cursor.fetchone()

    conn.close()

    return render_template(

        "profile.html",

        user=user

    )
# ==========================================================
# Settings
# ==========================================================

@app.route("/settings")
def settings():

    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template("settings.html")
# ==========================================================
# My QR Code
# ==========================================================

@app.route("/my_qr")
def my_qr():

    if "user_id" not in session:
        return redirect(url_for("login"))

    email = session["email"]

    qr_path = f"static/qr_codes/{session['user_id']}.png"

    # Create folder automatically
    os.makedirs("static/qr_codes", exist_ok=True)

    # Generate QR only if not exists
    if not os.path.exists(qr_path):

        payment_url = url_for(
            "pay_via_qr",
            email=email,
            _external=True
        )

        img = qrcode.make(payment_url)

        img.save(qr_path)

    return render_template(
        "my_qr.html",
        qr_image=f"qr_codes/{session['user_id']}.png",
        email=email
    )
# ==========================================================
# Pay via QR
# ==========================================================

@app.route("/pay")
def pay_via_qr():

    email = request.args.get("email", "").strip().lower()

    if not email:
        return "❌ Invalid QR Code."

    return redirect(
        url_for(
            "send_money",
            receiver_email=email
        )
    )
# ==========================================================
# Verify UPI PIN and Show Balance
# ==========================================================

from flask import jsonify

@app.route("/check_balance", methods=["POST"])
def check_balance():

    if "user_id" not in session:
        return jsonify({"success": False, "message": "Login required"}), 401

    upi_pin = request.form.get("upi_pin", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT balance, upi_pin FROM users WHERE id=?",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    conn.close()

    if user is None:
        return jsonify({"success": False, "message": "User not found"}), 404

    if user["upi_pin"] != upi_pin:
        return jsonify({"success": False, "message": "Incorrect UPI PIN"}), 400

    return jsonify({
        "success": True,
        "balance": f"₹{user['balance']:.2f}"
    })
# ==========================================================
# Set UPI PIN
# ==========================================================

@app.route("/set_upi_pin", methods=["GET", "POST"])
def set_upi_pin():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        upi_pin = request.form.get("upi_pin", "").strip()
        confirm_pin = request.form.get("confirm_upi_pin", "").strip()

        if not upi_pin.isdigit() or len(upi_pin) != 4:
            return "❌ UPI PIN must be exactly 4 digits."

        if upi_pin != confirm_pin:
            return "❌ UPI PINs do not match."

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users
            SET upi_pin = ?
            WHERE id = ?
            """,
            (
                upi_pin,
                session["user_id"]
            )
        )

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    return render_template("set_upi_pin.html")

# ==========================================================
# Analytics Page
# ==========================================================

@app.route("/analytics")
def analytics():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Total Added
    cursor.execute("""
        SELECT COALESCE(SUM(amount),0)
        FROM transactions
        WHERE user_id=?
        AND transaction_type='ADD MONEY'
    """, (session["user_id"],))

    total_added = cursor.fetchone()[0]

    # Total Sent
    cursor.execute("""
        SELECT COALESCE(SUM(amount),0)
        FROM transactions
        WHERE user_id=?
        AND transaction_type='SEND MONEY'
    """, (session["user_id"],))

    total_sent = cursor.fetchone()[0]

    # Current Balance
    cursor.execute("""
        SELECT balance
        FROM users
        WHERE id=?
    """, (session["user_id"],))

    balance = cursor.fetchone()[0]

    # Last 6 months
    cursor.execute("""
        SELECT
            strftime('%Y-%m', created_at) AS month,
            SUM(CASE WHEN transaction_type='ADD MONEY'
                     THEN amount ELSE 0 END) AS added,
            SUM(CASE WHEN transaction_type='SEND MONEY'
                     THEN amount ELSE 0 END) AS sent
        FROM transactions
        WHERE user_id=?
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6
    """, (session["user_id"],))

    rows = cursor.fetchall()[::-1]

    chart_labels = [r["month"] for r in rows]
    chart_added  = [float(r["added"] or 0) for r in rows]
    chart_sent   = [float(r["sent"] or 0) for r in rows]

    conn.close()

    return render_template(
        "analytics.html",
        total_added=total_added,
        total_sent=total_sent,
        balance=balance,
        chart_labels=chart_labels,
        chart_added=chart_added,
        chart_sent=chart_sent
    )
# ==========================================================
# Bank Accounts
# ==========================================================

@app.route("/bank_accounts", methods=["GET", "POST"])
def bank_accounts():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":

        bank_name = request.form.get("bank_name")
        account_number = request.form.get("account_number").strip()
        ifsc = request.form.get("ifsc").strip().upper()
        balance = float(request.form.get("balance", 0))

        # Prevent duplicate account numbers

        cursor.execute(
            "SELECT id FROM bank_accounts WHERE account_number=?",
            (account_number,)
        )

        if cursor.fetchone():

            conn.close()

            return "❌ Account number already linked."

        cursor.execute(
            """
            INSERT INTO bank_accounts(
                user_id,
                bank_name,
                account_number,
                ifsc,
                balance
            )
            VALUES(?,?,?,?,?)
            """,
            (
                session["user_id"],
                bank_name,
                account_number,
                ifsc,
                balance
            )
        )

        conn.commit()

    # Fetch linked accounts

    cursor.execute(
        """
        SELECT *
        FROM bank_accounts
        WHERE user_id=?
        ORDER BY id DESC
        """,
        (session["user_id"],)
    )

    accounts = cursor.fetchall()

    conn.close()

    return render_template(
        "bank_accounts.html",
        accounts=accounts
    )
# ==========================================================
# Bank to Wallet Transfer
# ==========================================================

@app.route("/transfer_bank", methods=["GET", "POST"])
def transfer_bank():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":

        bank_id = request.form.get("bank_id")
        amount = float(request.form.get("amount", 0))
        upi_pin = request.form.get("upi_pin", "").strip()

        # Fetch bank account
        cursor.execute(
            """
            SELECT *
            FROM bank_accounts
            WHERE id=?
            AND user_id=?
            """,
            (
                bank_id,
                session["user_id"]
            )
        )

        account = cursor.fetchone()

        # Verify UPI PIN
        cursor.execute(
            """
            SELECT upi_pin
            FROM users
            WHERE id=?
            """,
            (session["user_id"],)
        )

        user = cursor.fetchone()

        if user["upi_pin"] is None:

            conn.close()

            return "❌ Please set your UPI PIN first."

        if upi_pin != user["upi_pin"]:

            conn.close()

            return "❌ Incorrect UPI PIN."

        # Check bank account
        if account is None:

            conn.close()

            return "❌ Bank account not found."

        # Validate amount
        if amount <= 0:

            conn.close()

            return "❌ Invalid amount."

        # Check bank balance
        if account["balance"] < amount:

            conn.close()

            return "❌ Insufficient bank balance."

        # Deduct from bank account
        cursor.execute(
            """
            UPDATE bank_accounts
            SET balance = balance - ?
            WHERE id=?
            """,
            (
                amount,
                bank_id
            )
        )

        # Add to wallet
        cursor.execute(
            """
            UPDATE users
            SET balance = balance + ?
            WHERE id=?
            """,
            (
                amount,
                session["user_id"]
            )
        )

        # Save transaction
        cursor.execute(
            """
            INSERT INTO transactions(
                user_id,
                transaction_type,
                amount,
                description
            )
            VALUES(?,?,?,?)
            """,
            (
                session["user_id"],
                "BANK TO WALLET",
                amount,
                f"Transferred from {account['bank_name']}"
            )
        )

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    # GET request
    cursor.execute(
        """
        SELECT *
        FROM bank_accounts
        WHERE user_id=?
        ORDER BY bank_name
        """,
        (session["user_id"],)
    )

    accounts = cursor.fetchall()

    conn.close()

    return render_template(
        "transfer_bank.html",
        accounts=accounts
    )
# ==========================================================
# Send Money
# ==========================================================

@app.route("/send_money", methods=["GET", "POST"])
def send_money():

    if "user_id" not in session:
        return redirect(url_for("login"))

    receiver_email_prefill = request.args.get("receiver_email", "")

    # ------------------------------------------------------
    # POST Request
    # ------------------------------------------------------
    if request.method == "POST":

        receiver_email = request.form.get(
            "receiver_email", ""
        ).strip().lower()

        amount = float(request.form.get("amount", 0))

        upi_pin = request.form.get("upi_pin", "").strip()

        conn = get_db_connection()
        cursor = conn.cursor()

        # Sender
        cursor.execute(
            "SELECT * FROM users WHERE id=?",
            (session["user_id"],)
        )
        sender = cursor.fetchone()

        # Verify UPI PIN
        cursor.execute(
            "SELECT upi_pin FROM users WHERE id=?",
            (session["user_id"],)
        )
        user = cursor.fetchone()

        if user["upi_pin"] is None:
            conn.close()
            return "❌ Please set your UPI PIN first."

        if upi_pin != user["upi_pin"]:
            conn.close()
            return "❌ Incorrect UPI PIN."

        # Prevent self transfer
        if sender["email"] == receiver_email:
            conn.close()
            return "❌ You cannot send money to yourself."

        # Receiver
        cursor.execute(
            "SELECT * FROM users WHERE email=?",
            (receiver_email,)
        )
        receiver = cursor.fetchone()

        if receiver is None:
            conn.close()
            return "❌ Receiver not found."

        # Validate amount
        if amount <= 0:
            conn.close()
            return "❌ Invalid Amount."

        # Check balance
        if sender["balance"] < amount:
            conn.close()
            return "❌ Insufficient Balance."

        # Deduct sender
        cursor.execute("""
            UPDATE users
            SET balance = balance - ?
            WHERE id=?
        """, (amount, sender["id"]))

        # Credit receiver
        cursor.execute("""
            UPDATE users
            SET balance = balance + ?
            WHERE id=?
        """, (amount, receiver["id"]))

        # Sender transaction
        cursor.execute("""
            INSERT INTO transactions(
                user_id,
                transaction_type,
                amount,
                description
            )
            VALUES(?,?,?,?)
        """, (
            sender["id"],
            "SEND MONEY",
            amount,
            f"Sent to {receiver_email}"
        ))

        # Receiver transaction
        cursor.execute("""
            INSERT INTO transactions(
                user_id,
                transaction_type,
                amount,
                description
            )
            VALUES(?,?,?,?)
        """, (
            receiver["id"],
            "RECEIVED MONEY",
            amount,
            f"Received from {sender['email']}"
        ))

        # Notifications
        add_notification(
            cursor,
            receiver["id"],
            "Money Received",
            f"₹{amount:.2f} received from {sender['fullname']}"
        )

        add_notification(
            cursor,
            sender["id"],
            "Money Sent",
            f"₹{amount:.2f} sent to {receiver['fullname']}"
        )

        conn.commit()
        conn.close()

        # Toast notification
        session["toast_message"] = (
            f"₹{amount:.2f} sent successfully to {receiver['fullname']}."
        )

        return redirect(url_for("dashboard"))

    # ------------------------------------------------------
    # GET Request
    # ------------------------------------------------------
    return render_template(
        "send_money.html",
        receiver_email_prefill=receiver_email_prefill
    )
# ==========================================================
# Receive Money Request
# ==========================================================

@app.route("/receive_money", methods=["GET", "POST"])
def receive_money():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        sender_email = request.form.get(
            "sender_email",
            ""
        ).strip().lower()

        amount_text = request.form.get(
            "amount",
            "0"
        ).strip()

        # --------------------------------------------------
        # Validate Amount
        # --------------------------------------------------

        try:

            amount = float(amount_text)

            if amount <= 0:
                return "❌ Amount must be greater than 0."

        except ValueError:

            return "❌ Invalid amount."

        conn = get_db_connection()
        cursor = conn.cursor()

        # --------------------------------------------------
        # Find User by Email
        # --------------------------------------------------

        cursor.execute(
            """
            SELECT id, fullname, email
            FROM users
            WHERE email=?
            """,
            (sender_email,)
        )

        sender = cursor.fetchone()

        if sender is None:

            conn.close()

            return "❌ User not found."

        # --------------------------------------------------
        # Prevent Self Request
        # --------------------------------------------------

        if sender["id"] == session["user_id"]:

            conn.close()

            return "❌ You cannot request money from yourself."

        # --------------------------------------------------
        # Insert Payment Request
        # --------------------------------------------------

        cursor.execute(
            """
            INSERT INTO payment_requests(
                sender_id,
                receiver_id,
                amount,
                status
            )
            VALUES(?,?,?,?)
            """,
            (
                sender["id"],
                session["user_id"],
                amount,
                "PENDING"
            )
        )

        # --------------------------------------------------
        # Notification for Requested User
        # --------------------------------------------------

        add_notification(
         cursor,
         sender["id"],
         "Payment Request",
         f"{session['fullname']} requested ₹{amount:.2f}"
        )

        conn.commit()
        conn.close()

        # --------------------------------------------------
        # Toast Notification
        # --------------------------------------------------

        session["toast_message"] = (
            f"Money request of ₹{amount:.2f} sent successfully."
        )

        return redirect(url_for("dashboard"))

    # ------------------------------------------------------
    # GET Request
    # ------------------------------------------------------

    return render_template("receive_money.html")

# ==========================================================
# Notifications Page
# ==========================================================

@app.route("/notifications")
def notifications():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM notifications
        WHERE user_id=?
        ORDER BY created_at DESC
    """, (session["user_id"],))

    notifications = cursor.fetchall()

    # Mark all as read
    cursor.execute("""
        UPDATE notifications
        SET is_read=1
        WHERE user_id=?
    """, (session["user_id"],))

    conn.commit()
    conn.close()

    return render_template(
        "notifications.html",
        notifications=notifications
    )
# ==========================================================
# Transactions
# ==========================================================

@app.route("/transactions")
def transactions():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            transaction_type,
            amount,
            description,
            datetime(created_at, '+5 hours', '+30 minutes') AS created_at
        FROM transactions
        WHERE user_id=?
        ORDER BY created_at DESC
        """,
        (session["user_id"],)
    )

    records = cursor.fetchall()

    conn.close()

    return render_template(
        "transactions.html",
        records=records
    )
# ==========================================================
# Download Receipt
# ==========================================================

@app.route("/receipt/<int:transaction_id>")
def download_receipt(transaction_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            transaction_type,
            amount,
            description,
            datetime(created_at, '+5 hours', '+30 minutes') AS created_at
        FROM transactions
        WHERE id=?
        AND user_id=?
        """,
        (
            transaction_id,
            session["user_id"]
        )
    )

    transaction = cursor.fetchone()

    conn.close()

    if transaction is None:
        return "❌ Receipt not found."

    # Create PDF in memory
    buffer = BytesIO()

    p = canvas.Canvas(buffer)

    # Title
    p.setFont("Helvetica-Bold", 18)
    p.drawString(180, 800, "PayFlow Receipt")

    # Line
    p.line(50, 785, 550, 785)

    # Receipt details
    p.setFont("Helvetica", 12)

    p.drawString(50, 740, f"Receipt No: PF-{transaction['id']:06d}")

    p.drawString(50, 710, f"Transaction Type: {transaction['transaction_type']}")

    p.drawString(50, 680, f"Amount: ₹{transaction['amount']:.2f}")

    p.drawString(50, 650, f"Description: {transaction['description']}")

    p.drawString(50, 620, f"Date & Time: {transaction['created_at']}")

    p.drawString(50, 590, "Status: SUCCESS")

    p.drawString(50, 560, "Payment Method: PayFlow Wallet")

    # Footer
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(50, 500, "Thank you for using PayFlow.")

    p.drawString(50, 485, "This is a computer-generated receipt.")

    p.showPage()
    p.save()

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"PayFlow_Receipt_{transaction_id}.pdf",
        mimetype="application/pdf"
    )

# ==========================================================
# Add Money Page
# ==========================================================

@app.route("/add_money_page")
def add_money_page():

    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template("add_money.html")

@app.route("/add_money", methods=["POST"])
def add_money():

    if "user_id" not in session:
        return redirect(url_for("login"))

    amount = float(request.form.get("amount", 0))

    if amount <= 0:
        return "Invalid Amount"

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET balance = balance + ?
        WHERE id=?
    """, (amount, session["user_id"]))

    cursor.execute("""
        INSERT INTO transactions(
            user_id,
            transaction_type,
            amount,
            description
        )
        VALUES(?,?,?,?)
    """, (
        session["user_id"],
        "ADD MONEY",
        amount,
        "Money added to wallet"
    ))

    conn.commit()
    conn.close()

    session["toast_message"] = "Money added successfully."

    return redirect(url_for("dashboard"))
# ==========================================================
# Logout
# ==========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))
# ==========================================================
# Register
# ==========================================================

@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        fullname = request.form.get("fullname").strip()
        email = request.form.get("email").strip().lower()
        country = request.form.get("country").strip()
        phone = request.form.get("phone").strip()
        password = request.form.get("password")
        confirm_password = request.form.get("confirmPassword")

        if not is_valid_name(fullname):
            return "❌ Invalid Name"

        if not is_valid_email(email):
            return "❌ Invalid Email"

        if not is_valid_phone(phone):
            return "❌ Invalid Phone"

        valid,message = is_valid_password(

            password,
            fullname,
            email,
            phone

        )

        if not valid:

            return message

        if password != confirm_password:

            return "❌ Passwords do not match."

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(

            "SELECT id FROM users WHERE email=?",

            (email,)

        )

        if cursor.fetchone():

            conn.close()

            return "❌ Email already exists."

        cursor.execute(

            "SELECT id FROM users WHERE phone=?",

            (phone,)

        )

        if cursor.fetchone():

            conn.close()

            return "❌ Phone already exists."

        hashed_password = ph.hash(password)

        cursor.execute("""

            INSERT INTO users(

                fullname,
                email,
                country,
                phone,
                password,
                balance

            )

            VALUES(?,?,?,?,?,?)

        """,(

            fullname,
            email,
            country,
            phone,
            hashed_password,
            0.0

        ))

        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")

# ==========================================================
# View Payment Requests
# ==========================================================

@app.route("/payment_requests")
def payment_requests():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            pr.id,
            u.fullname,
            u.email,
            pr.amount,
            pr.status,
            pr.created_at
        FROM payment_requests pr
        JOIN users u
            ON pr.sender_id = u.id
        WHERE pr.receiver_id = ?
          AND pr.status = 'PENDING'
        ORDER BY pr.created_at DESC
    """, (session["user_id"],))

    requests = cursor.fetchall()

    conn.close()

    return render_template(
        "payment_requests.html",
        requests=requests
    )
from flask import jsonify

# ==========================================================
# AI Chatbot
# ==========================================================

@app.route("/chatbot", methods=["POST"])
def chatbot():

    if "user_id" not in session:
        return jsonify({"reply": "Please login first."})

    message = request.form.get("message", "").strip().lower()

    conn = get_db_connection()
    cursor = conn.cursor()

    # --------------------------------------------------
    # Balance
    # --------------------------------------------------
    if "balance" in message or "check for me" in message:

        cursor.execute(
            "SELECT balance FROM users WHERE id=?",
            (session["user_id"],)
        )

        balance = cursor.fetchone()["balance"]

        reply = f"💰 Your current wallet balance is ₹{balance:.2f}."

    # --------------------------------------------------
    # Spent this month
    # --------------------------------------------------
    elif "spent this month" in message or "spend this month" in message:

        cursor.execute("""
            SELECT COALESCE(SUM(amount),0)
            FROM transactions
            WHERE user_id=?
              AND transaction_type='SEND MONEY'
              AND strftime('%Y-%m', created_at)=strftime('%Y-%m','now')
        """, (session["user_id"],))

        spent = cursor.fetchone()[0]

        reply = f"📤 You have spent ₹{spent:.2f} this month."

    # --------------------------------------------------
    # Largest expense
    # --------------------------------------------------
    elif "largest expense" in message or "biggest expense" in message:

        cursor.execute("""
            SELECT COALESCE(MAX(amount),0)
            FROM transactions
            WHERE user_id=?
              AND transaction_type='SEND MONEY'
        """, (session["user_id"],))

        largest = cursor.fetchone()[0]

        reply = f"💸 Your largest expense is ₹{largest:.2f}."

    # --------------------------------------------------
    # Monthly analysis
    # --------------------------------------------------
    elif "monthly analysis" in message or "sending and receiving" in message:

        cursor.execute("""
            SELECT COALESCE(SUM(amount),0)
            FROM transactions
            WHERE user_id=?
              AND transaction_type='ADD MONEY'
              AND strftime('%Y-%m', created_at)=strftime('%Y-%m','now')
        """, (session["user_id"],))

        added = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COALESCE(SUM(amount),0)
            FROM transactions
            WHERE user_id=?
              AND transaction_type='SEND MONEY'
              AND strftime('%Y-%m', created_at)=strftime('%Y-%m','now')
        """, (session["user_id"],))

        sent = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COALESCE(SUM(amount),0)
            FROM transactions
            WHERE user_id=?
              AND transaction_type='RECEIVED MONEY'
              AND strftime('%Y-%m', created_at)=strftime('%Y-%m','now')
        """, (session["user_id"],))

        received = cursor.fetchone()[0]

        reply = (
            f"📊 This month:\n\n"
            f"➕ Added: ₹{added:.2f}\n"
            f"📤 Sent: ₹{sent:.2f}\n"
            f"📥 Received: ₹{received:.2f}"
        )
    
        # --------------------------------------------------
    # Payment requests pending
    # --------------------------------------------------
    elif "payment request" in message or "payment requests" in message \
         or "pending request" in message or "requests to pay" in message:

        cursor.execute("""
            SELECT COUNT(*)
            FROM payment_requests
            WHERE receiver_id=?
              AND status='PENDING'
        """, (session["user_id"],))

        pending = cursor.fetchone()[0]

        if pending == 0:
            reply = "✅ You do not have any pending payment requests."
        elif pending == 1:
            reply = "📩 You have 1 pending payment request waiting for payment."
        else:
            reply = f"📩 You have {pending} pending payment requests waiting for payment."

    # --------------------------------------------------
    # Financial advice
    # --------------------------------------------------
    elif "financial advice" in message or "advice" in message:

        cursor.execute("""
            SELECT balance
            FROM users
            WHERE id=?
        """, (session["user_id"],))

        balance = cursor.fetchone()["balance"]

        if balance < 500:
            reply = "⚠️ Your balance is low. Try reducing unnecessary spending."
        elif balance < 2000:
            reply = "🙂 Your balance is moderate. Keep saving regularly."
        else:
            reply = "✅ Your financial condition looks healthy."

    # --------------------------------------------------
    # Greeting
    # --------------------------------------------------
    elif "hi" in message or "hello" in message:

        reply = (
            f"Hello {session['fullname']}! 👋 "
            "How can I help you with your PayFlow wallet today?"
        )

    # --------------------------------------------------
    # Default
    # --------------------------------------------------
    else:

        reply = (
            "🤖 I can help with:\n"
            "• Wallet balance\n"
            "• Monthly spending\n"
            "• Largest expense\n"
            "• Monthly analysis\n"
            "• Financial advice"
        )

    conn.close()

    return jsonify({"reply": reply})
# ==========================================================
# Run Flask
# ==========================================================
 
if __name__ == "__main__":

    app.run(debug=True)