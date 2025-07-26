from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
import cv2
import uuid
from datetime import datetime, date
from utils import encrypt_photo, generate_qr_code, generate_key_base64
from keras.models import load_model
import numpy as np
from pyzbar.pyzbar import decode

app = Flask(__name__)
app.secret_key = "your-secret-key"

DB_FILE = "visitor.db"
PHOTO_FOLDER = "static/photos"
QR_FOLDER = "static/qrcodes"
MODEL_PATH = "MASK_CLASSIFIER.h5"

os.makedirs(PHOTO_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)

model = load_model(MODEL_PATH)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
classes = ["Mask", "No Mask", "Improper"]

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
                leave_time TEXT,
                mask_status TEXT,
                photo_path TEXT,
                encryption_key TEXT,
                qr_code_path TEXT
            )
        ''')
        conn.commit()

@app.route("/", methods=["GET", "POST"])
def index():
    # 啟動攝影機
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if not ret:
        return "無法啟動相機"
    decoded_objs = decode(frame)
    for obj in decoded_objs:
        visitor_id = obj.data.decode("utf-8")
        today = date.today().isoformat()
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("SELECT id, name FROM visitors WHERE visitor_id=? AND date(checkin_time)=? AND leave_time IS NULL", (visitor_id, today))
            row = c.fetchone()
            if row:
                now = datetime.now().isoformat(sep=' ', timespec='seconds')
                c.execute("UPDATE visitors SET leave_time=? WHERE id=?", (now, row[0]))
                conn.commit()
                flash(f"✅ {row[1]} 已成功登記離場，祝您身體健康，求職順利！")

    if request.method == "POST":
        name = request.form["name"]
        host = request.form["host"]
        visitor_id = f"VIS-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:4]}"
        checkin_time = datetime.now().isoformat(sep=' ', timespec='seconds')

        # 再次拍照
        ret, frame = cap.read()
        if not ret:
            return "無法擷取影像"
        cap.release()

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        mask_status = "Unknown"
        for (x, y, w, h) in faces:
            face_img = frame[y:y+h, x:x+w]
            face_img = cv2.resize(face_img, (128, 128)) / 255.0
            face_img = np.expand_dims(face_img, axis=0)
            pred = model.predict(face_img)[0]
            mask_status = classes[np.argmax(pred)]
            break

        # 加密儲存照片
        img_path = os.path.join(PHOTO_FOLDER, visitor_id + ".jpg.enc")
        key_base64, encrypted = encrypt_photo(frame)
        with open(img_path, 'wb') as f:
            f.write(encrypted)

        # 產生 QR Code
        qr_path = os.path.join(QR_FOLDER, f"{visitor_id}.png")
        generate_qr_code(visitor_id, qr_path)

        # 寫入資料庫
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO visitors (visitor_id, name, host, checkin_time, leave_time, mask_status, photo_path, encryption_key, qr_code_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (visitor_id, name, host, checkin_time, None, mask_status, img_path, key_base64, qr_path))
            conn.commit()

        return redirect(url_for("index"))

    # 顯示近期記錄
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT visitor_id, name, host, checkin_time, mask_status, leave_time, qr_code_path FROM visitors ORDER BY id DESC LIMIT 10")
        records = c.fetchall()

    return render_template("index.html", records=records)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
