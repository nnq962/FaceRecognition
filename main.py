import argparse
import json
import os
from config import config
from insightface_detector import InsightFaceDetector
from media_manager import MediaManager
from utils.logger_config import LOGGER
from app import build_faiss_index

def load_config(config_name):
    """Load and validate configuration from main_config.json"""
    try:
        # Kiểm tra tồn tại của file config
        config_path = "main_config.json"
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"File cấu hình '{config_path}' không tìm thấy")
            
        # Load toàn bộ config từ file
        with open(config_path, "r", encoding="utf-8") as f:
            try:
                all_configs = json.load(f)
            except json.JSONDecodeError:
                raise ValueError(f"File '{config_path}' không phải là JSON hợp lệ")
        
        # Kiểm tra config_name có tồn tại trong config hay không
        if config_name not in all_configs:
            # Liệt kê các cấu hình có sẵn để thông báo
            available_configs = ", ".join(all_configs.keys())
            raise ValueError(f"'{config_name}' không có trong main_config.json. Các cấu hình có sẵn: {available_configs}")
        
        # Lấy config theo tên
        main_config = all_configs[config_name]
        LOGGER.info(f"Đã tải cấu hình '{config_name}' thành công")
        return main_config
        
    except Exception as e:
        LOGGER.error(f"Lỗi khi tải cấu hình: {str(e)}")
        raise

def main():
    # Phân tích tham số dòng lệnh
    parser = argparse.ArgumentParser(description="Run face detection and analysis based on main config.")
    parser.add_argument("--config", type=str, default="DEFAULT", help="Config code defined in main_config.json")
    args = parser.parse_args()
    
    # Load config
    main_config = load_config(args.config)
    
    # Trích xuất thông tin
    room_id = main_config.get("room_id")
    camera_ids = main_config.get("camera_ids", [])
    features = main_config.get("features", {})
    
    # Lấy các giá trị từ features với giá trị mặc định
    time_to_save = features.get("time_to_save", 5)
    line_thickness = features.get("line_thickness", 3)
    save = features.get("save", False)
    view_img = features.get("view_img", False)
    host = main_config.get("host", "localhost")
    websocket_port = main_config.get("websocket_port", 3000)
    data2ws_url = f"http://{host}:{websocket_port}"
    noti_control_port = main_config.get("noti_control_port")
    noti_secret_key = main_config.get("noti_secret_key")
    
    # Log cấu hình đã tải
    LOGGER.info(f"Room ID: {room_id}")
    LOGGER.info(f"Camera IDs: {camera_ids}")
    LOGGER.info(f"Host: {host}")
    LOGGER.info(f"WebSocket Port: {websocket_port}")
    LOGGER.info(f"Notification Control Port: {noti_control_port}")
    LOGGER.info(f"Data2WS URL: {data2ws_url}")
    
    # Xử lý danh sách camera đầu vào
    sources = config.process_camera_input(camera_ids)
    
    # Khởi tạo các thành phần
    media_manager = MediaManager(
        source=sources,
        save=save,
        view_img=view_img,
        line_thickness=line_thickness
    )
    
    detector = InsightFaceDetector(
        media_manager=media_manager,
        face_recognition=features.get("face_recognition", False),
        face_emotion=features.get("face_emotion", False),
        face_mask=features.get("face_mask", False),
        raise_hand=features.get("raise_hand", False),
        qr_code=features.get("qr_code", False),
        export_data=features.get("export_data", False),
        time_to_save=time_to_save,
        notification=features.get("notification", False),
        room_id=room_id,
        host=host,
        data2ws_url=data2ws_url,
        noti_control_port=noti_control_port,
        noti_secret_key=noti_secret_key,
    )
    
    detector.run_inference()

if __name__ == "__main__":
    build_faiss_index()
    main()