from flask import Flask, render_template, request, redirect, session, flash, url_for
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import smtplib
import re
import os
import sqlite3
import torch
from transformers import BertTokenizer, BertForSequenceClassification

app = Flask(__name__)
app.secret_key = "mysecretkey123"

# -------------------------------------------------------
# DATABASE (NO NAME CHANGES)
# -------------------------------------------------------
db = sqlite3.connect("users.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT UNIQUE,
    password TEXT
)
""")
db.commit()

# -------------------------------------------------------
# EMAIL CONFIG
# -------------------------------------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "rkr026089@gmail.com"
EMAIL_PASSWORD = "hjpj rokc ctoo cdzf"

# -------------------------------------------------------
# SEND OTP
# -------------------------------------------------------
def send_email_otp(receiver_email, otp):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = receiver_email
    msg["Subject"] = "Your KavyaGuard OTP Code"

    body = f"""
        <h2>KavyaGuard Login Verification</h2>
        <p>Your OTP is:</p>
        <h1>{otp}</h1>
        <p>Valid for 5 minutes.</p>
    """

    msg.attach(MIMEText(body, "html"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, receiver_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print("Email Error:", e)
        return False


# -------------------------------------------------------
# LOAD TRAINED MODEL  (ONLY ADDED CODE)
# -------------------------------------------------------
MODEL_DIR = "./saved_model"

tokenizer = BertTokenizer.from_pretrained(MODEL_DIR)
model = BertForSequenceClassification.from_pretrained(MODEL_DIR)
model.eval()

def predict_hate(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding="max_length", max_length=64)

    with torch.no_grad():
        outputs = model(**inputs)

    logits = outputs.logits
    prediction = torch.argmax(logits, dim=1).item()

    return "Hate" if prediction == 1 else "Non-Hate"


# -------------------------------------------------------
# HOME PAGE  (UNCHANGED)
# -------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/home")
def home():
    return render_template("index.html")


# -------------------------------------------------------
# SIGNUP (UNCHANGED)
# -------------------------------------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        exists = cursor.fetchone()

        if exists:
            flash("Email already registered!")
            return redirect(url_for("login"))

        cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                       (name, email, password))
        db.commit()

        flash("Account created! Login now.")
        return redirect(url_for("login"))

    return render_template("signup.html")


# -------------------------------------------------------
# LOGIN (UNCHANGED NAME)
# -------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form["email"]
    password = request.form["password"]

    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()

    if not user:
        flash("Email not registered! Please sign up.")
        return redirect(url_for("signup"))

    if user[3] != password:
        flash("Incorrect password!")
        return redirect(url_for("login"))

    otp = random.randint(100000, 999999)
    session["otp"] = str(otp)
    session["temp_email"] = email

    send_email_otp(email, otp)

    flash("OTP sent!")
    return redirect(url_for("otp_page"))


# -------------------------------------------------------
# OTP PAGE (UNCHANGED)
# -------------------------------------------------------
@app.route("/otp", methods=["GET", "POST"])
def otp_page():
    if request.method == "GET":
        return render_template("otp.html")

    entered = request.form["otp"]

    if entered == session.get("otp"):
        email = session["temp_email"]

        cursor.execute("SELECT name FROM users WHERE email = ?", (email,))
        user_name = cursor.fetchone()[0]

        session["email"] = email
        session["user_name"] = user_name

        session.pop("otp", None)
        session.pop("temp_email", None)

        return redirect(url_for("dashboard"))

    flash("Invalid OTP!")
    return redirect(url_for("otp_page"))


# -------------------------------------------------------
# DASHBOARD (UNCHANGED)
# -------------------------------------------------------
@app.route("/dashboard")
def dashboard():
    if "email" not in session:
        return redirect(url_for("login"))

    return render_template("dashboard.html", user_name=session["user_name"])


# -------------------------------------------------------
# DETECT PAGE (ONLY THIS PART ADDED)
# -------------------------------------------------------
@app.route("/detect", methods=["GET", "POST"])
def detect():
    if "email" not in session:
        flash("Login to use detector.")
        return redirect(url_for("login"))

    result = None

    if request.method == "POST":
        text = request.form["text"]
        result = predict_hate(text)

    return render_template("detect.html", result=result)


# -------------------------------------------------------
# LOGOUT (UNCHANGED)
# -------------------------------------------------------
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.")
    return redirect(url_for("index"))


# -------------------------------------------------------
# OTHER PAGES
# -------------------------------------------------------
@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

