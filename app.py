from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
import cv2
import uuid
from datetime import datetime
from utils import encrypt_photo, generate_qr_code, generate_key_base64, decrypt_photo

app = Flask(__name__)

DB_FILE = "visitor.db"
PHOTO_FOLDER = "static/photos"
QR_FOLDER = "static/qrcodes"

os.makedirs(PHOTO_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)

# 初始化資料庫
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS visitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visitor_id TEXT,
                name TEXT,
                host TEXT,
                checkin_time TEXT,
                photo_path TEXT,
                encryption_key TEXT,
                qr_code_path TEXT
            )
        ''')
        conn.commit()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form["name"]
        host = request.form["host"]
        visitor_id = f"VIS-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:4]}"
        checkin_time = datetime.now().isoformat(sep=' ', timespec='seconds')

        # 拍照並加密
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            return "無法啟動相機或擷取影像"

        img_name = f"{visitor_id}.jpg"
        img_path = os.path.join(PHOTO_FOLDER, img_name + ".enc")
        key_base64, encrypted = encrypt_photo(frame)
        with open(img_path, 'wb') as f:
            f.write(encrypted)

        # 產生 QR Code
        qr_path = os.path.join(QR_FOLDER, f"{visitor_id}.png")
        generate_qr_code(visitor_id, qr_path)

        # 儲存進資料庫
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO visitors (visitor_id, name, host, checkin_time, photo_path, encryption_key, qr_code_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (visitor_id, name, host, checkin_time, img_path, key_base64, qr_path))
            conn.commit()

        return redirect(url_for("index"))

    # 查詢最近 10 筆紀錄
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT visitor_id, name, host, checkin_time, qr_code_path FROM visitors ORDER BY id DESC LIMIT 10")
        records = c.fetchall()

    return render_template("index.html", records=records)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
