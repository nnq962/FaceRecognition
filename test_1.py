from flask import Flask, request, jsonify
import threading
from config import config
from insightface_detector import InsightFaceDetector
from media_manager import MediaManager
from websocket_server import start_ws_server

app = Flask(__name__)

# Biến toàn cục để lưu trữ trạng thái ứng dụng
global_state = {
    "detector": None,
    "media_manager": None,
    "is_running": False,
    "settings": {
        "source": None,
        "save": False,
        "face_recognition": False,
        "face_emotion": False,
        "check_small_face": False,
        "streaming": False,
        "export_data": False,
        "time_to_save": 5,
        "show_time_process": False,
        "raise_hand": False,
        "view_img": False,
        "line_thickness": 3,
        "qr_code": False
    }
}

def process_source(source_arg):
    """
    Process the source argument to determine the type of input.
    - '0': Webcam
    - Single camera ID: Generate RTSP URL
    - Multiple camera IDs: Write RTSP URLs or webcam ID to device.txt
    """
    # Reset camera_names để tránh tích lũy từ các lần gọi trước
    config.camera_names = []

    if source_arg.isdigit():  # Single numeric ID (e.g., '0' or '1')
        if source_arg == "0":  # Webcam
            config.camera_names.append("webcam")
            return "0"
        else:  # Single camera
            rtsp_urls = config.create_rtsp_urls_from_mongo([int(source_arg)])
            if rtsp_urls:
                return rtsp_urls[0]
            else:
                raise ValueError(f"Could not retrieve RTSP URL for camera ID: {source_arg}")

    if "," in source_arg:  # Multiple IDs (e.g., '0,1')
        device_ids = source_arg.split(",")
        devices = []
        for device_id in device_ids:
            device_id = device_id.strip()
            if device_id.isdigit():
                if device_id == "0":  # Webcam
                    config.camera_names.append("webcam")
                    devices.append("0")
                else:  # Camera IP
                    rtsp_urls = config.create_rtsp_urls_from_mongo([int(device_id)])
                    if rtsp_urls:
                        devices.extend(rtsp_urls)
                    else:
                        raise ValueError(f"Could not retrieve RTSP URL for camera ID: {device_id}")
        # Write to device.txt
        with open("device.txt", "w") as f:
            for device in devices:
                f.write(f"{device}\n")
        return "device.txt"

    return source_arg  # If it's not numeric or a list, assume it's a file path

def start_application(settings):
    """Khởi chạy ứng dụng với các cài đặt được chỉ định"""
    global global_state
    
    if global_state["is_running"]:
        return {"status": "error", "message": "Application is already running"}
    
    try:
        processed_source = process_source(settings["source"])
        
        media_manager = MediaManager(
            source=processed_source,
            save=settings["save"],
            face_recognition=settings["face_recognition"],
            face_emotion=settings["face_emotion"],
            check_small_face=settings["check_small_face"],
            streaming=settings["streaming"],
            export_data=settings["export_data"],
            time_to_save=settings["time_to_save"],
            show_time_process=settings["show_time_process"],
            raise_hand=settings["raise_hand"],
            view_img=settings["view_img"],
            line_thickness=settings["line_thickness"],
            qr_code=settings["qr_code"]
        )
        
        if settings["raise_hand"] or settings["qr_code"]:
            ws_thread = threading.Thread(target=start_ws_server)
            ws_thread.daemon = True
            ws_thread.start()
        
        detector = InsightFaceDetector(media_manager=media_manager)
        
        global_state["media_manager"] = media_manager
        global_state["detector"] = detector
        global_state["is_running"] = True
        
        # Chạy detector trong một thread riêng biệt
        detection_thread = threading.Thread(target=detector.run_inference)
        detection_thread.daemon = True
        detection_thread.start()
        
        return {"status": "success", "message": "Application started successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def stop_application():
    """Dừng ứng dụng hiện tại"""
    global global_state
    
    if not global_state["is_running"]:
        return {"status": "error", "message": "Application is not running"}
    
    try:
        # Gọi phương thức dừng nếu có
        if hasattr(global_state["media_manager"], "stop") and callable(global_state["media_manager"].stop):
            global_state["media_manager"].stop()
        
        if hasattr(global_state["detector"], "stop") and callable(global_state["detector"].stop):
            global_state["detector"].stop()
        
        global_state["is_running"] = False
        global_state["detector"] = None
        global_state["media_manager"] = None
        
        return {"status": "success", "message": "Application stopped successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def update_settings(new_settings):
    """Cập nhật cài đặt và khởi động lại ứng dụng nếu cần"""
    global global_state
    
    # Lưu cài đặt cũ để khôi phục nếu có lỗi
    old_settings = global_state["settings"].copy()
    
    # Cập nhật cài đặt
    for key, value in new_settings.items():
        if key in global_state["settings"]:
            global_state["settings"][key] = value
    
    # Nếu ứng dụng đang chạy, dừng và khởi động lại
    if global_state["is_running"]:
        stop_result = stop_application()
        if stop_result["status"] == "error":
            # Khôi phục cài đặt cũ nếu không thể dừng
            global_state["settings"] = old_settings
            return stop_result
        
        start_result = start_application(global_state["settings"])
        if start_result["status"] == "error":
            # Khôi phục cài đặt cũ nếu không thể khởi động
            global_state["settings"] = old_settings
            return start_result
    
    return {"status": "success", "message": "Settings updated successfully", "settings": global_state["settings"]}

# API endpoints

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """API endpoint để lấy cài đặt hiện tại"""
    return jsonify({
        "status": "success",
        "settings": global_state["settings"],
        "is_running": global_state["is_running"]
    })

@app.route('/api/settings', methods=['POST'])
def update_settings_endpoint():
    """API endpoint để cập nhật cài đặt"""
    new_settings = request.json
    result = update_settings(new_settings)
    return jsonify(result)

@app.route('/api/start', methods=['POST'])
def start_endpoint():
    """API endpoint để bắt đầu ứng dụng"""
    if not global_state["settings"]["source"]:
        return jsonify({"status": "error", "message": "Source must be set before starting"})
    
    result = start_application(global_state["settings"])
    return jsonify(result)

@app.route('/api/stop', methods=['POST'])
def stop_endpoint():
    """API endpoint để dừng ứng dụng"""
    result = stop_application()
    return jsonify(result)

@app.route('/api/toggle', methods=['POST'])
def toggle_feature():
    """API endpoint để bật/tắt một tính năng cụ thể"""
    data = request.json
    feature = data.get("feature")
    
    if not feature or feature not in global_state["settings"]:
        return jsonify({"status": "error", "message": "Invalid feature specified"})
    
    # Chuyển đổi giá trị của tính năng (nếu là boolean)
    if isinstance(global_state["settings"][feature], bool):
        new_settings = {feature: not global_state["settings"][feature]}
    else:
        value = data.get("value")
        if value is None:
            return jsonify({"status": "error", "message": "Value must be provided for non-boolean settings"})
        new_settings = {feature: value}
    
    result = update_settings(new_settings)
    return jsonify(result)

@app.route('/api/source', methods=['POST'])
def set_source():
    """API endpoint để cài đặt nguồn"""
    data = request.json
    source = data.get("source")
    
    if not source:
        return jsonify({"status": "error", "message": "Source must be provided"})
    
    result = update_settings({"source": source})
    return jsonify(result)

if __name__ == '__main__':
    # Chạy Flask trong chế độ debug và cho phép truy cập từ bên ngoài
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)