import argparse
import json
from config import config
from insightface_detector import InsightFaceDetector
from media_manager import MediaManager
from websocket_server import start_ws_server
from utils.logger_config import LOGGER

# ---------------------- Load config theo task ----------------------
parser = argparse.ArgumentParser(description="Run face detection and analysis based on task config.")
parser.add_argument("--task", type=str, required=True, help="Task code defined in task_config.json")

args = parser.parse_args()
task_name = args.task

# Load toàn bộ config từ task_config.json
with open("task_config.json", "r") as f:
    all_tasks = json.load(f)

if task_name not in all_tasks:
    raise ValueError(f"'{task_name}' không có trong task_config.json")

task_config = all_tasks[task_name]

# ---------------------- Trích xuất thông tin ----------------------
room_id = task_config.get("room_id")
camera_codes = task_config.get("camera_codes", [])
enabled_features = task_config.get("enabled_features", {})
log_collection = task_config.get("log_collection")

if not camera_codes:
    raise ValueError(f"'{task_name}' không có camera_codes trong config")

# Xử lý danh sách camera đầu vào
sources = config.process_camera_input(camera_codes)

# Trích các flag tính năng từ enabled_features
time_to_save = enabled_features.get("time_to_save", 5)
line_thickness = enabled_features.get("line_thickness", 3)
save = enabled_features.get("save", False)
view_img = enabled_features.get("view_img", False)

# Bật websocket nếu có raise_hand hoặc qr_code
if enabled_features.get("raise_hand") or enabled_features.get("qr_code"):
    start_ws_server()

# ---------------------- Khởi tạo các thành phần ----------------------
media_manager = MediaManager(
    source=sources,
    save=save,
    view_img=view_img,
    line_thickness=line_thickness
)

detector = InsightFaceDetector(
    media_manager=media_manager,
    face_recognition=enabled_features.get("face_recognition", False),
    face_emotion=enabled_features.get("face_emotion", False),
    face_mask=enabled_features.get("face_mask", False),
    raise_hand=enabled_features.get("raise_hand", False),
    qr_code=enabled_features.get("qr_code", False),
    export_data=enabled_features.get("export_data", False),
    time_to_save=time_to_save,
    notification=enabled_features.get("notification", False),
    log_collection=log_collection,
    room_id=room_id
)

detector.run_inference()