from flask import Flask, request, jsonify
import pandas as pd
import json
import os

app = Flask(__name__)

USERS_FILE = "users.json"  # File lưu thông tin người dùng

def load_users():
    """Load dữ liệu người dùng từ tệp JSON."""
    try:
        with open(USERS_FILE, "r") as file:
            return json.load(file)["users"]
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return {}

@app.route("/analyze_emotions", methods=["POST"])
def analyze_emotions():
    """
    REST API để phân tích cảm xúc cho tất cả người dùng, với camera ID làm đầu vào.
    """
    data = request.get_json()

    # Trích xuất thông tin từ request
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    camera_id = data.get("camera_id")

    if not start_time or not end_time or camera_id is None:
        return jsonify({"error": "Missing start_time, end_time, or camera_id"}), 400

    # Xác định tệp CSV dựa trên camera_id
    input_file = f"data_export/face_data_camera_{camera_id - 1}.csv"

    # Tải dữ liệu người dùng
    users = load_users()
    if not users:
        return jsonify({"error": "No users found in users.json"}), 404

    try:
        # Đọc file CSV
        data = pd.read_csv(input_file)
    except FileNotFoundError:
        return jsonify({"error": f"Input file '{input_file}' not found"}), 404

    if data.empty:
        return jsonify({"error": f"Input file '{input_file}' is empty"}), 400

    # Chuyển đổi cột Timestamp thành kiểu datetime
    data["Timestamp"] = pd.to_datetime(data["Timestamp"])
    min_time = data["Timestamp"].min()
    max_time = data["Timestamp"].max()

    if len(start_time.split(":")) == 2:
        start_time += ":00"
    if len(end_time.split(":")) == 2:
        end_time += ":00"

    try:
        start_time = pd.to_datetime(start_time)
        end_time = pd.to_datetime(end_time)
    except ValueError:
        return jsonify({"error": "Invalid time format. Use 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD HH:MM:SS'"}), 400

    if start_time < min_time or end_time > max_time or start_time > end_time:
        return jsonify({"error": f"Invalid time range. Allowed range: {min_time} to {max_time}"}), 400

    # Kết quả phân tích
    analysis_results = []

    for name, user_info in users.items():
        # Lọc dữ liệu cho từng người dùng
        filtered_data = data[
            (data["Timestamp"] >= start_time) &
            (data["Timestamp"] <= end_time) &
            (data["Name"] == name) &
            (data["Emotion_prob"] > 60)
        ]

        if filtered_data.empty:
            continue

        # Tính tổng xác suất cho mỗi cảm xúc
        emotion_summary = filtered_data.groupby("Emotion")["Emotion_prob"].sum()
        total_emotion_prob = emotion_summary.sum()
        emotion_percentages = (emotion_summary / total_emotion_prob * 100).sort_values(ascending=False)

        # Suy luận cảm xúc chính
        dominant_emotion = emotion_percentages.idxmax()
        dominant_percentage = emotion_percentages.max()

        analysis_results.append({
            "userid": user_info["userid"],
            "name": name,
            "emotion_percentages": emotion_percentages.apply(lambda x: f"{x:.2f}%").to_dict(),
            "dominant_emotion": {"emotion": dominant_emotion, "percentage": f"{dominant_percentage:.2f}%"}
        })

    if not analysis_results:
        return jsonify({"message": "No significant emotions found for any user in the specified time range."}), 200

    return jsonify({
        "message": "Emotion analysis for all users completed.",
        "time_range": {"start": str(start_time), "end": str(end_time)},
        "camera_id": camera_id,
        "analysis": analysis_results
    }), 200

@app.route("/csv_info", methods=["GET"])
def csv_info():
    """
    REST API để xuất thông tin chi tiết về dữ liệu trong tệp CSV.
    
    Trả về:
        - Số lượng user_id xuất hiện trong tệp.
        - Danh sách toàn bộ user_id.
        - Thời gian đầu tiên trong tệp.
        - Thời gian cuối cùng trong tệp.
    """
    # Đọc file CSV từ tham số query (mặc định là camera 1)
    camera_id = request.args.get("camera_id", default=1, type=int)
    input_file = f"data_export/face_data_camera_{camera_id - 1}.csv"

    # Kiểm tra nếu file CSV không tồn tại
    if not os.path.exists(input_file):
        return jsonify({"error": f"Input file '{input_file}' not found."}), 404

    try:
        # Đọc dữ liệu từ file CSV
        data = pd.read_csv(input_file)
    except Exception as e:
        return jsonify({"error": f"Failed to read CSV file: {str(e)}"}), 500

    if data.empty:
        return jsonify({"error": "Input file is empty."}), 400

    # Chuyển cột Timestamp thành kiểu datetime
    data["Timestamp"] = pd.to_datetime(data["Timestamp"])

    # Lấy danh sách user_id
    user_ids = data["Name"].unique().tolist()

    # Lấy thời gian đầu tiên và cuối cùng trong tệp
    min_time = data["Timestamp"].min()
    max_time = data["Timestamp"].max()

    return jsonify({
        "camera_id": camera_id,
        "user_count": len(user_ids),
        "user_ids": user_ids,
        "first_timestamp": str(min_time),
        "last_timestamp": str(max_time),
    }), 200

if __name__ == "__main__":
    app.run(debug=True)