from flask import Flask, render_template, request, jsonify
from config import config
from datetime import datetime

# Kết nối tới MongoDB
users_collection = config.users_collection
managers_collection = config.managers_collection
camera_collection = config.camera_collection
data_collection = config.data_collection
save_path = config.save_path
greeted_employees = {}


app = Flask(__name__)

"""
API
https://3hinc.nnq962.pro/get_attendance
https://3hinc.nnq962.pro/get_all_users?without_face_embeddings=1
"""

@app.route('/get_all_users', methods=['GET'])
def get_all_users():
    # Lấy tham số từ query
    department_id = request.args.get('department_id', None)
    without_face_embeddings = request.args.get('without_face_embeddings', '0') == '1'  # Chuyển thành bool

    # Tạo bộ lọc truy vấn MongoDB
    query = {}
    if department_id:
        query['department_id'] = department_id  # Lọc theo phòng ban

    # Truy vấn danh sách user
    users = list(users_collection.find(query))

    # Nếu without_face_embeddings=True, xóa trường face_embeddings khỏi kết quả
    if without_face_embeddings:
        for user in users:
            user.pop('face_embeddings', None)  # Xóa nếu tồn tại

    return jsonify(users)


@app.route('/get_attendance', methods=['GET'])
def get_attendance():
    try:
        # Lấy ngày hiện tại theo định dạng yyyy-mm-dd
        today = datetime.now().strftime("%Y-%m-%d")

        # Truy vấn tất cả bản ghi có trường date = hôm nay
        records = list(data_collection.find({"date": today}))

        # Tạo danh sách kết quả
        attendance_list = []
        for record in records:
            attendance_list.append({
                "name": record.get("name", f"Unknown ({record.get('user_id')})"),
                "check_in_time": record.get("check_in_time", "N/A"),
                "check_out_time": record.get("check_out_time", "N/A"),
            })

        return jsonify(attendance_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/")
def home():
    return render_template("view.html")


if __name__ == "__main__":
    app.run(port=5555)
