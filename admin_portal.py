from flask import Flask, render_template, request, redirect, url_for, session, send_file
import sqlite3
import base64
import os
import csv
from io import StringIO
from dotenv import load_dotenv

# 載入 .env 環境變數
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

DB_FILE = "visitor.db"
PHOTO_FOLDER = "static/photos"

# 使用環境變數管理帳號密碼
USERS = {
    "sales": os.getenv("SALES_PW"),
    "admin": os.getenv("ADMIN_PW")
}

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if USERS.get(username) == password:
            session['logged_in'] = True
            session['role'] = username
            return redirect(url_for("dashboard"))
        else:
            return render_template("admin.html", error="帳號或密碼錯誤")
    return render_template("admin.html")

@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("admin"))

    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT visitor_id, name, host, checkin_time, mask_status, leave_time FROM visitors ORDER BY id DESC")
        records = c.fetchall()

    role = session.get("role")
    return render_template("admin.html", records=records, role=role, show_table=True)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin"))

@app.route("/export/sales")
def export_sales():
    if session.get("role") != "sales":
        return redirect(url_for("dashboard"))

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["受訪者", "訪客姓名", "來訪時間", "離場時間"])

    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT host, name, checkin_time, leave_time FROM visitors ORDER BY checkin_time DESC")
        for row in c.fetchall():
            writer.writerow(row)

    output.seek(0)
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name='visitor_flow_report.csv'
    )

@app.route("/export/admin")
def export_admin():
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["訪客姓名", "是否配戴口罩（辨識結果）", "是否違規"])

    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT name, mask_status FROM visitors")
        for row in c.fetchall():
            violated = "是" if "No Mask" in row[1] or "Improper" in row[1] else "否"
            writer.writerow([row[0], row[1], violated])

    output.seek(0)
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name='compliance_report.csv'
    )
