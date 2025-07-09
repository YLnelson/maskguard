import cv2
import base64
from cryptography.fernet import Fernet
import qrcode
import numpy as np
from io import BytesIO
from PIL import Image

# 產生金鑰
def generate_key_base64():
    return base64.urlsafe_b64encode(Fernet.generate_key()).decode()

# 加密照片
def encrypt_photo(frame):
    key = Fernet.generate_key()
    f = Fernet(key)

    # 轉為 JPG buffer
    success, buffer = cv2.imencode(".jpg", frame)
    encrypted = f.encrypt(buffer.tobytes())
    return base64.urlsafe_b64encode(key).decode(), encrypted

# 解密照片
def decrypt_photo(encrypted_data, key_b64):
    f = Fernet(base64.urlsafe_b64decode(key_b64.encode()))
    decrypted = f.decrypt(encrypted_data)
    img_array = np.frombuffer(decrypted, dtype=np.uint8)
    return cv2.imdecode(img_array, cv2.IMREAD_COLOR)

# 產生 QR Code
def generate_qr_code(data, output_path):
    img = qrcode.make(data)
    img.save(output_path)
