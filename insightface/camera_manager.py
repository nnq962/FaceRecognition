from flask import Flask, jsonify, request
import json
import os

app = Flask(__name__)

# Đường dẫn tới tệp JSON lưu trữ thông tin camera managers
JSON_FILE = "camera_managers.json"

# Danh sách các camera có sẵn
available_cameras = {
    1: "rtsp://192.168.1.142:8554/stream1",
    2: "rtsp://192.168.1.142:8554/stream2",
}

# Tải dữ liệu từ JSON
def load_data():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r") as file:
            return json.load(file)
    return {"camera_managers": {}, "camera_user_id_counter": 1}

# Lưu dữ liệu vào JSON
def save_data(data):
    with open(JSON_FILE, "w") as file:
        json.dump(data, file, indent=4)

# Dữ liệu ban đầu
data = load_data()

@app.route("/camera_managers", methods=["POST"])
def add_camera_manager():
    """Thêm người quản lý camera mới."""
    camera_manager_info = request.get_json()
    username = camera_manager_info.get("username")
    password = camera_manager_info.get("password")
    camera_id = camera_manager_info.get("camera_id")

    if not username or not password or not camera_id:
        return jsonify({"error": "Missing username, password, or camera_id"}), 400

    if username in data["camera_managers"]:
        return jsonify({"error": "Username already exists"}), 409

    if camera_id not in available_cameras:
        return jsonify({"error": "Invalid camera_id"}), 400

    # Tạo người quản lý camera mới
    camera_user_id = data["camera_user_id_counter"]
    data["camera_user_id_counter"] += 1

    data["camera_managers"][username] = {
        "id": camera_user_id,
        "password": password,
        "camera_id": camera_id,
        "camera_url": available_cameras[camera_id],
    }

    save_data(data)
    return jsonify({"message": "Camera manager added successfully", "camera_manager": data["camera_managers"][username]}), 201

@app.route("/camera_managers", methods=["GET"])
def view_camera_managers():
    """Xem danh sách người quản lý camera."""
    return jsonify(data["camera_managers"])

@app.route("/camera_managers/<username>", methods=["PUT"])
def update_camera_manager(username):
    """Cập nhật thông tin người quản lý camera."""
    if username not in data["camera_managers"]:
        return jsonify({"error": "Camera manager not found"}), 404

    camera_manager_info = request.get_json()
    password = camera_manager_info.get("password")
    camera_id = camera_manager_info.get("camera_id")

    if camera_id and camera_id not in available_cameras:
        return jsonify({"error": "Invalid camera_id"}), 400

    if password:
        data["camera_managers"][username]["password"] = password
    if camera_id:
        data["camera_managers"][username]["camera_id"] = camera_id
        data["camera_managers"][username]["camera_url"] = available_cameras[camera_id]

    save_data(data)
    return jsonify({"message": "Camera manager updated successfully", "camera_manager": data["camera_managers"][username]}), 200

@app.route("/camera_managers/<username>", methods=["DELETE"])
def delete_camera_manager(username):
    """Xóa người quản lý camera."""
    if username not in data["camera_managers"]:
        return jsonify({"error": "Camera manager not found"}), 404

    password = request.get_json().get("password")
    if password != data["camera_managers"][username]["password"]:
        return jsonify({"error": "Incorrect password"}), 403

    del data["camera_managers"][username]
    save_data(data)
    return jsonify({"message": f"Camera manager '{username}' deleted successfully"}), 200

@app.route("/available_cameras", methods=["GET"])
def get_available_cameras():
    """Lấy danh sách các camera có sẵn."""
    return jsonify(available_cameras)

if __name__ == "__main__":
    app.run(debug=True)