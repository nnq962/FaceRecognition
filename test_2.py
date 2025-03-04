from flask import Flask, jsonify, request
from threading import Thread
import time
from config import config  # Giả sử bạn có file config.py
from insightface_detector import InsightFaceDetector  # Lớp xử lý nhận diện
from media_manager import MediaManager  # Lớp xử lý media
from websocket_server import start_ws_server  # WebSocket nếu cần

# Khởi tạo Flask app
app = Flask(__name__)

# Đối tượng Settings để lưu trạng thái các tính năng
class Settings:
    def __init__(self):
        self.source = "0"  # Mặc định là webcam
        self.save = False
        self.face_recognition = False
        self.face_emotion = False
        self.check_small_face = False
        self.streaming = False
        self.export_data = False
        self.time_to_save = 5
        self.show_time_process = False
        self.raise_hand = False
        self.view_img = False
        self.line_thickness = 3
        self.qr_code = False

# Khởi tạo settings
settings = Settings()

# Khởi tạo MediaManager với settings ban đầu
media_manager = MediaManager(
    source=settings.source,
    save=settings.save,
    face_recognition=settings.face_recognition,
    face_emotion=settings.face_emotion,
    check_small_face=settings.check_small_face,
    streaming=settings.streaming,
    export_data=settings.export_data,
    time_to_save=settings.time_to_save,
    show_time_process=settings.show_time_process,
    raise_hand=settings.raise_hand,
    view_img=settings.view_img,
    line_thickness=settings.line_thickness,
    qr_code=settings.qr_code
)

# Khởi tạo detector
detector = InsightFaceDetector(media_manager=media_manager)

# Hàm chạy backend chính
def run_backend():
    print("Backend is running...")
    detector.run_inference()  # Giả sử đây là hàm xử lý chính của bạn

# API để bật/tắt hoặc cập nhật trạng thái các tính năng
@app.route('/toggle/<feature>', methods=['POST'])
def toggle_feature(feature):
    data = request.json
    if not data or 'enable' not in data:
        return jsonify({"error": "Please provide 'enable' as a boolean"}), 400
    
    enable = data['enable']
    if not isinstance(enable, bool):
        return jsonify({"error": "'enable' must be a boolean"}), 400
    
    if hasattr(settings, feature):
        setattr(settings, feature, enable)
        setattr(media_manager, feature, enable)  # Cập nhật MediaManager
        return jsonify({"status": f"{feature} set to {enable}"})
    return jsonify({"error": f"Feature '{feature}' not found"}), 404

# API để cập nhật source
@app.route('/update/source', methods=['POST'])
def update_source():
    data = request.json
    if not data or 'value' not in data:
        return jsonify({"error": "Please provide 'value' as a string"}), 400
    
    value = data['value']
    settings.source = value
    media_manager.source = value  # Cập nhật source trong MediaManager
    return jsonify({"status": f"source updated to {value}"})

# API để cập nhật time_to_save
@app.route('/update/time_to_save', methods=['POST'])
def update_time_to_save():
    data = request.json
    if not data or 'value' not in data:
        return jsonify({"error": "Please provide 'value' as an integer"}), 400
    
    value = data['value']
    if not isinstance(value, int) or value <= 0:
        return jsonify({"error": "'value' must be a positive integer"}), 400
    
    settings.time_to_save = value
    media_manager.time_to_save = value
    return jsonify({"status": f"time_to_save updated to {value} seconds"})

# API để cập nhật line_thickness
@app.route('/update/line_thickness', methods=['POST'])
def update_line_thickness():
    data = request.json
    if not data or 'value' not in data:
        return jsonify({"error": "Please provide 'value' as an integer"}), 400
    
    value = data['value']
    if not isinstance(value, int) or value <= 0:
        return jsonify({"error": "'value' must be a positive integer"}), 400
    
    settings.line_thickness = value
    media_manager.line_thickness = value
    return jsonify({"status": f"line_thickness updated to {value}"})

# API để xem trạng thái
@app.route('/status', methods=['GET'])
def get_status():
    return jsonify(vars(settings))

# Khởi động WebSocket server nếu cần
def start_websocket_if_needed():
    while True:
        if settings.raise_hand or settings.qr_code:
            start_ws_server()
        time.sleep(5)  # Kiểm tra định kỳ

# Chạy backend và WebSocket trong thread riêng
Thread(target=run_backend, daemon=True).start()
Thread(target=start_websocket_if_needed, daemon=True).start()

# Chạy Flask server
if __name__ == "__main__":
    print("API server is running at http://localhost:5000")
    app.run(host="0.0.0.0", port=5000)