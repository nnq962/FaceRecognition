import pandas as pd
from datetime import datetime

# Tạo DataFrame toàn cục để lưu dữ liệu khuôn mặt
face_data = pd.DataFrame(columns=["timestamp", "name", "recognition_prob", "emotion", "emotion_prob"])

import os
import pandas as pd
from datetime import datetime

# Tạo DataFrame toàn cục để lưu dữ liệu khuôn mặt
face_data = pd.DataFrame(columns=["timestamp", "name", "recognition_prob", "emotion", "emotion_prob"])

def save_to_pandas(name, recognition_prob, emotion, emotion_prob, file_name="face_data.csv"):
    """
    Lưu dữ liệu khuôn mặt vào DataFrame Pandas và ghi bổ sung vào file CSV nếu đã tồn tại.
    Args:
        name (str): Tên người nhận diện được.
        recognition_prob (int): Xác suất nhận diện.
        emotion (str): Cảm xúc phát hiện được.
        emotion_prob (float): Xác suất của cảm xúc.
        file_name (str): Tên file CSV để ghi.
    """
    global face_data

    # Thêm dữ liệu mới vào DataFrame
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_row = {
        "timestamp": timestamp,
        "name": name,
        "recognition_prob": recognition_prob,
        "emotion": emotion,
        "emotion_prob": round(emotion_prob * 100, 2)  # Chuyển từ xác suất 0-1 thành %
    }
    face_data = pd.concat([face_data, pd.DataFrame([new_row])], ignore_index=True)
    print(f"✅ Data saved: {new_row}")

    # Kiểm tra nếu file CSV đã tồn tại
    if os.path.exists(file_name):
        # Đọc dữ liệu cũ và nối thêm dữ liệu mới
        existing_data = pd.read_csv(file_name)
        combined_data = pd.concat([existing_data, pd.DataFrame([new_row])], ignore_index=True)
        combined_data.to_csv(file_name, index=False)
    else:
        # Nếu file chưa tồn tại, ghi dữ liệu mới
        face_data.to_csv(file_name, index=False)

    print(f"✅ Data exported to {file_name}")

def save_pandas_to_csv(file_name="face_data.csv"):
    """
    Lưu DataFrame Pandas ra file CSV.
    """
    global face_data
    face_data.to_csv(file_name, index=False)
    print(f"✅ Data exported to {file_name}")