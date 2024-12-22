import os
import pandas as pd
from datetime import datetime
import re

# Tạo DataFrame toàn cục để lưu dữ liệu khuôn mặt
face_data = pd.DataFrame(columns=["Timestamp", "Name", "Recognition_prob", "Emotion", "Emotion_prob"])

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
        "Timestamp": timestamp,
        "Name": name,
        "Recognition_prob": recognition_prob,
        "Emotion": emotion,
        "Emotion_prob": emotion_prob
    }

    # Kiểm tra nếu `new_row` không rỗng hoặc toàn bộ NaN
    if not pd.isna(pd.Series(new_row)).all():
        # Thêm dòng mới vào `face_data` mà không dùng `pd.concat`
        face_data.loc[len(face_data)] = new_row
        print(f"✅ Data added: {new_row}")
    else:
        print("⚠️ Warning: Attempted to add an empty or NaN row. Skipped.")

    # Kiểm tra nếu file CSV đã tồn tại
    if os.path.exists(file_name):
        # Đọc dữ liệu cũ và nối thêm dữ liệu mới
        existing_data = pd.read_csv(file_name)
        combined_data = pd.concat([existing_data, pd.DataFrame([new_row])], ignore_index=True)
        combined_data.to_csv(file_name, index=False)
    else:
        # Nếu file chưa tồn tại, ghi dữ liệu mới
        face_data.to_csv(file_name, index=False)

def filter_data(start_time, end_time, name, input_file="face_data.csv", output_file="filtered_data.csv"):
    """
    Lọc dữ liệu từ file CSV dựa trên thời gian và tên người, sau đó xuất ra file CSV mới.

    Args:
        start_time (str): Thời gian bắt đầu lọc (định dạng "YYYY-MM-DD HH:MM" hoặc "YYYY-MM-DD HH:MM:SS").
        end_time (str): Thời gian kết thúc lọc (định dạng "YYYY-MM-DD HH:MM" hoặc "YYYY-MM-DD HH:MM:SS").
        name (str): Tên người muốn lọc.
        input_file (str): Tên file CSV đầu vào.
        output_file (str): Tên file CSV để xuất dữ liệu lọc được.
    """
    # Kiểm tra nếu file CSV đầu vào không tồn tại
    try:
        data = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"❌ Input file '{input_file}' not found.")
        return

    # Kiểm tra nếu file trống hoặc không có dữ liệu
    if data.empty:
        print(f"❌ Input file '{input_file}' is empty.")
        return

    # Chuyển cột timestamp thành kiểu datetime
    data['timestamp'] = pd.to_datetime(data['timestamp'])

    # Lấy phạm vi thời gian trong file
    min_time = data['timestamp'].min()
    max_time = data['timestamp'].max()

    # Thêm giây vào thời gian nếu cần
    if len(start_time.split(":")) == 2:
        start_time += ":00"
    if len(end_time.split(":")) == 2:
        end_time += ":00"

    # Chuyển thời gian đầu vào thành kiểu datetime
    try:
        start_time = pd.to_datetime(start_time)
        end_time = pd.to_datetime(end_time)
    except ValueError:
        print("❌ Invalid time format. Please use 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD HH:MM:SS'.")
        return

    # Kiểm tra nếu thời gian nằm trong phạm vi dữ liệu
    if start_time < min_time or end_time > max_time or start_time > end_time:
        print(f"❌ Invalid time range. Allowed range: {min_time} to {max_time}.")
        return

    # Lọc dữ liệu
    filtered_data = data[
        (data['timestamp'] >= start_time) &
        (data['timestamp'] <= end_time) &
        (data['name'] == name)
    ]

    # Kiểm tra nếu không có dữ liệu phù hợp
    if filtered_data.empty:
        print(f"ℹ️ No data found for the given criteria: Name={name}, Time range={start_time} to {end_time}.")
        return

    # Xuất dữ liệu lọc được ra file CSV
    filtered_data.to_csv(output_file, index=False)
    print(f"✅ Filtered data exported to {output_file}.")

def analyze_emotions(start_time, end_time, name, input_file="face_data.csv"):
    """
    Phân tích cảm xúc của một người trong khoảng thời gian được chỉ định (tính theo %).
    
    Args:
        start_time (str): Thời gian bắt đầu lọc (định dạng "YYYY-MM-DD HH:MM" hoặc "YYYY-MM-DD HH:MM:SS").
        end_time (str): Thời gian kết thúc lọc (định dạng "YYYY-MM-DD HH:MM" hoặc "YYYY-MM-DD HH:MM:SS").
        name (str): Tên người muốn phân tích.
        input_file (str): Tên file CSV đầu vào.
    """
    # Kiểm tra nếu file CSV đầu vào không tồn tại
    try:
        data = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"❌ Input file '{input_file}' not found.")
        return

    # Kiểm tra nếu file trống hoặc không có dữ liệu
    if data.empty:
        print(f"❌ Input file '{input_file}' is empty.")
        return

    # Chuyển cột timestamp thành kiểu datetime
    data['timestamp'] = pd.to_datetime(data['timestamp'])

    # Lấy phạm vi thời gian trong file
    min_time = data['timestamp'].min()
    max_time = data['timestamp'].max()

    # Thêm giây vào thời gian nếu cần
    if len(start_time.split(":")) == 2:
        start_time += ":00"
    if len(end_time.split(":")) == 2:
        end_time += ":00"

    # Chuyển thời gian đầu vào thành kiểu datetime
    try:
        start_time = pd.to_datetime(start_time)
        end_time = pd.to_datetime(end_time)
    except ValueError:
        print("❌ Invalid time format. Please use 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD HH:MM:SS'.")
        return

    # Kiểm tra nếu thời gian nằm trong phạm vi dữ liệu
    if start_time < min_time or end_time > max_time or start_time > end_time:
        print(f"❌ Invalid time range. Allowed range: {min_time} to {max_time}.")
        return

    # Lọc dữ liệu
    filtered_data = data[
        (data['timestamp'] >= start_time) &
        (data['timestamp'] <= end_time) &
        (data['name'] == name) &
        (data['emotion_prob'] > 60)  # Chỉ lấy cảm xúc có xác suất > 60
    ]

    # Kiểm tra nếu không có dữ liệu phù hợp
    if filtered_data.empty:
        print(f"ℹ️ No significant emotions found for {name} in the range {start_time} to {end_time}.")
        return

    # Tính tổng xác suất cho mỗi cảm xúc
    emotion_summary = filtered_data.groupby('emotion')['emotion_prob'].sum()

    # Tính tổng tất cả cảm xúc
    total_emotion_prob = emotion_summary.sum()

    # Chuyển sang % dựa trên tổng các cảm xúc
    emotion_percentages = (emotion_summary / total_emotion_prob * 100).sort_values(ascending=False)

    # Hiển thị kết quả
    print(f"\nEmotion analysis for {name} from {start_time} to {end_time}:")
    print(emotion_percentages.apply(lambda x: f"{x:.2f}%").to_string(index=True))  # Loại bỏ 'Name' và 'dtype'

    # Suy luận cảm xúc chính
    dominant_emotion = emotion_percentages.idxmax()
    dominant_percentage = emotion_percentages.max()
    print(f"🧐 Dominant emotion: {dominant_emotion} ({dominant_percentage:.2f}%).")

def parse_face_data(text):
    """
    Xử lý chuỗi văn bản và trích xuất thông tin <Tên> <Xác suất> <Cảm xúc> <Xác suất>.
    Args:
        text (str): Chuỗi văn bản đầu vào, ví dụ "quyet 66% | Neutral 92%".
    Returns:
        tuple: (name, recognition_prob, emotion, emotion_prob) nếu hợp lệ, hoặc None nếu không hợp lệ.
    """
    # Kiểm tra nếu text không phải là chuỗi
    if not isinstance(text, str):
        return None

    # Sử dụng regex để trích xuất tên, xác suất nhận diện, cảm xúc và xác suất cảm xúc
    match = re.match(r"(\w+)\s(\d+)%\s\|\s(\w+)\s(\d+)%", text)
    if match:
        name = match.group(1)  # Tên
        recognition_prob = int(match.group(2))  # Xác suất nhận diện (dạng số nguyên)
        emotion = match.group(3)  # Cảm xúc
        emotion_prob = int(match.group(4))  # Xác suất cảm xúc (dạng số nguyên)
        return name, recognition_prob, emotion, emotion_prob
    else:
        return None