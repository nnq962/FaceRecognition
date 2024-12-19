import pandas as pd
from datetime import datetime

# Tạo DataFrame toàn cục để lưu dữ liệu khuôn mặt
face_data = pd.DataFrame(columns=["timestamp", "name", "recognition_prob", "emotion", "emotion_prob"])

def save_to_pandas(name, recognition_prob, emotion, emotion_prob):
    """
    Lưu dữ liệu khuôn mặt vào DataFrame Pandas.
    Args:
        name (str): Tên người nhận diện được.
        recognition_prob (int): Xác suất nhận diện.
        emotion (str): Cảm xúc phát hiện được.
        emotion_prob (float): Xác suất của cảm xúc.
    """
    global face_data
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

def save_pandas_to_csv(file_name="face_data.csv"):
    """
    Lưu DataFrame Pandas ra file CSV.
    """
    global face_data
    face_data.to_csv(file_name, index=False)
    print(f"✅ Data exported to {file_name}")