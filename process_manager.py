"""
sudo chown -R pc:pc /home/pc/nnq_projects/Work/FaceRecognition/supervisor/log
sudo chmod -R u+rw /home/pc/nnq_projects/Work/FaceRecognition/supervisor/log
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
import subprocess
import os
import time
import json
import re
from config import config
import cv2
from unidecode import unidecode
from utils.logger_config import LOGGER

app = Flask(__name__)


# --- Đường dẫn chính ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
WORK_DIR = BASE_DIR
USER = "3hinc"

# --- Thư mục supervisor (gồm: db, conf, log) ---
SUPERVISOR_DIR = os.path.join(WORK_DIR, "supervisor")
SUPERVISOR_CONF_DIR = os.path.join(SUPERVISOR_DIR, "conf")  # nơi lưu các file .conf
SUPERVISOR_LOG_DIR = os.path.join(SUPERVISOR_DIR, "log")    # nơi lưu log stdout/stderr
TASK_CONFIG_FILE = os.path.join(WORK_DIR, "main_config.json")

# Biến mặc định global
HOST = "192.168.1.142"
PROCESS_MANAGER_PORT = 9620
APP_PORT = 9621
WEBSOCKET_PORT = 9622
NOTI_PORT = 9623
NOTI_CONTROL_PORT = 9624
NOTI_SECRET_KEY = "3hinc"
NOTI_ALLOWED_IPS = []
DEFAULT_FEATURES = {}

# Đường dẫn tới python
PYTHON_PATH = ""


#
# PHẦN 1: ROUTES CHO WEB UI
#

@app.route('/')
def index():
    """Trang chủ web UI"""
    return render_template('process_manager.html')

@app.route('/static/<path:path>')
def serve_static(path):
    """Phục vụ các file tĩnh (CSS, JS, ...)"""
    return send_from_directory('static', path)

@app.route('/get_available_cameras')
def get_available_cameras_route():
    """Fetch list of available cameras"""
    try:
        # Gọi hàm nội bộ, trả về list[{'camera_id': ..., 'name': ...}]
        camera_list = get_available_cameras()

        # Trả thẳng ra JSON
        return jsonify(camera_list), 200

    except Exception as e:
        LOGGER.error(f"Error fetching camera_ids: {e}")
        return jsonify({
            "error": "Failed to retrieve camera_ids due to internal error.",
            "details": str(e)
        }), 500
    
@app.route('/get_available_rooms')
def get_available_rooms_route():
    """Lấy danh sách các phòng có camera"""
    try:
        # Gọi hàm nội bộ, trả về danh sách các phòng
        rooms = get_available_rooms()
        
        # Trả về JSON
        return jsonify(rooms), 200

    except Exception as e:
        LOGGER.error(f"Error fetching rooms: {e}")
        return jsonify({
            "error": "Failed to retrieve rooms due to internal error.",
            "details": str(e)
        }), 500

@app.route('/run_task', methods=['POST'])
def run_task():
    """Chạy một tiến trình mới từ web UI"""
    try:
        data = request.json
        
        # Lấy dữ liệu từ request
        task_name = data.get('task_name', '')
        camera_ids = data.get('camera_ids', [])
        features = data.get('features', {})
        room_id = data.get('room_id')

        # Kiểm tra xem có tên tiến trình không
        if not task_name:
            return jsonify({
                'status': 'error',
                'message': 'Vui lòng nhập tên cho tiến trình'
            }), 400

        # Kiểm tra xem có nguồn dữ liệu được chọn không
        if not camera_ids:
            return jsonify({
                'status': 'error',
                'message': 'Vui lòng chọn ít nhất một nguồn dữ liệu'
            }), 400
        
        # Chuyển đổi dữ liệu để gọi API
        features = [
            f"{name} {value}" if name == 'time_to_save' else name
            for name, value in features.items()
            if value
        ]
        
        if not features:
            return jsonify({
                'status': 'error',
                'message': 'Không có feature nào được chọn'
            }), 400
            
        # Gọi hàm tạo tiến trình của API
        result = create_process_internal(features, camera_ids, task_name, room_id)
        
        if result['status'] == 'success':
            task_id = result['process']['id']
            return jsonify({
                'status': 'success',
                'message': f'Đã bắt đầu tiến trình "{task_name}"',
                'task_id': task_id
            })
        else:
            return jsonify(result)
    except Exception as e:
        LOGGER.error(f"Lỗi khi chạy tiến trình: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi tạo tiến trình: {str(e)}'
        }), 500

@app.route('/stop_task', methods=['POST'])
def stop_task():
    """Dừng một tiến trình từ web UI"""
    try:
        data = request.json
        task_id = data.get('task_id')
        
        if not task_id:
            return jsonify({
                'status': 'error',
                'message': 'Thiếu ID tiến trình'
            }), 400
        
        # Gọi hàm dừng tiến trình của API
        result = stop_task_internal(task_id)
        return jsonify(result)
    except Exception as e:
        LOGGER.error(f"Lỗi khi dừng tiến trình: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi dừng tiến trình: {str(e)}'
        }), 500

@app.route('/get_all_task_ids')
def get_all_task_ids():
    """Lấy danh sách tất cả các tiến trình cho web UI"""
    try:
        # Lấy danh sách tiến trình từ hàm API
        task_ids_list = get_task_ids_internal()

        # Chuyển đổi định dạng cho web UI
        result = {}
        for process in task_ids_list:
            task_id = process['id']
            
            result[task_id] = {
                'name': process.get('name', task_id),  # Lấy tên từ thông tin tiến trình
                'features': process.get('features', {}),
                'running': process['status'] == 'RUNNING',
                'start_time': format_time(process['start_time'])
            }
        
        return jsonify(result)
    except Exception as e:
        LOGGER.error(f"Lỗi khi lấy danh sách tiến trình: {str(e)}")
        return jsonify({})

@app.route('/get_task_status')
def get_task_status():
    """Lấy trạng thái của một tiến trình cụ thể cho web UI"""
    try:
        task_id = request.args.get('task_id')

        if not task_id:
            return jsonify({
                'status': 'error',
                'message': 'Thiếu ID tiến trình'
            }), 400
        
        # Kiểm tra xem tiến trình có tồn tại trong danh sách không
        task_ids = get_task_ids_internal()
        process = next((p for p in task_ids if p['id'] == task_id), None)
        
        if not process:
            return jsonify({
                'status': 'error',
                'message': 'Không tìm thấy tiến trình'
            }), 404
        
        # Lấy log của tiến trình
        log_result = get_process_log_internal(task_id)
        
        if log_result['status'] == 'error':
            return jsonify(log_result), 500
        
        # Kiểm tra xem tiến trình có đang chạy không
        is_running = process['status'] == 'RUNNING'
        
        # Chia log thành các dòng
        log_content = log_result.get('log', '')
        output_lines = log_content.split('\n') if log_content else []
        
        return jsonify({
            'status': 'success',
            'running': is_running,
            'output': output_lines
        })
    except Exception as e:
        LOGGER.error(f"Lỗi khi lấy trạng thái tiến trình: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi lấy trạng thái tiến trình: {str(e)}'
        }), 500
    
@app.route('/get_task_details', methods=['GET'])
def get_task_details():
    """Lấy thông tin chi tiết của một tiến trình để chỉnh sửa"""
    try:
        task_id = request.args.get('task_id')
        
        if not task_id:
            return jsonify({
                'status': 'error',
                'message': 'Thiếu ID tiến trình'
            }), 400

        config = load_json_file(TASK_CONFIG_FILE)
        
        if task_id not in config:
            return jsonify({
                'status': 'error',
                'message': 'Không tìm thấy tiến trình'
            }), 404
        
        task = config[task_id]

        return jsonify({
            'status': 'success',
            'config': {
                'name': task.get('name'),
                'task_id': task_id,
                'camera_ids': task.get('camera_ids', []),
                'features': task.get('features', {}),
                'room_id': task.get('room_id'),
            }
        })

    except Exception as e:
        LOGGER.error(f"Lỗi khi lấy thông tin chi tiết tiến trình: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi lấy thông tin tiến trình: {str(e)}'
        }), 500

@app.route('/delete_task', methods=['POST'])
def delete_task_route():
    data = request.get_json(force=True)
    pid = data.get('task_id')
    if not pid:
        return jsonify(status='error', message='Thiếu task_id'), 400
    result = delete_task_internal(pid)
    return jsonify(result), (200 if result.get('status')=='success' else 500)

@app.route('/restart_task', methods=['POST'])
def restart_task():
    data = request.json or {}
    pid = data.get('task_id')

    if not pid:
        return jsonify(status='error', message='Thiếu task_id'), 400
    try:
        # Lấy thông tin từ database
        db = load_json_file(TASK_CONFIG_FILE)
        if pid not in db:
            return jsonify(status='error', message=f'Không tìm thấy tiến trình {pid}'), 404
        
        # Lấy đường dẫn tệp log
        log_file = db[pid].get('log_file')
        error_log = db[pid].get('error_log')

        # Lấy tên tiến trình
        name = db[pid].get('name', pid)
                
        # Gọi supervisorctl restart
        subprocess.run(['supervisorctl', 'restart', pid], check=True)
        
        # Cập nhật start_time mới
        if pid in db:
            db[pid]['start_time'] = time.time()
            save_json_file(db, TASK_CONFIG_FILE)
            
        return jsonify(status='success', message=f'Đã restart: {name}')
    
    except subprocess.CalledProcessError as e:
        return jsonify(status='error', message=f'Restart thất bại: {e}'), 500
    except Exception as e:
        return jsonify(status='error', message=f'Lỗi khi xử lý: {str(e)}'), 500

@app.route('/update_task', methods=['POST'])
def update_task():
    """Cập nhật một tiến trình hiện có"""
    try:
        data = request.json
        
        # Lấy dữ liệu từ request
        task_id = data.get('task_id')
        task_name = data.get('task_name', '')
        camera_ids = data.get('camera_ids', [])
        features = data.get('features', {})
        room_id = data.get('room_id')

        if not task_id:
            return jsonify({
                'status': 'error',
                'message': 'Thiếu ID tiến trình'
            }), 400
        
        # Load cấu hình hiện tại
        config = load_json_file(TASK_CONFIG_FILE)
        
        # Kiểm tra xem tiến trình có tồn tại không
        if task_id not in config:
            return jsonify({
                'status': 'error',
                'message': 'Không tìm thấy tiến trình'
            }), 404
        
        # Kiểm tra xem có tên tiến trình không
        if not task_name:
            return jsonify({
                'status': 'error',
                'message': 'Vui lòng nhập tên cho tiến trình'
            }), 400
        
        # Kiểm tra xem có nguồn dữ liệu được chọn không
        if not camera_ids:
            return jsonify({
                'status': 'error',
                'message': 'Vui lòng chọn ít nhất một nguồn dữ liệu'
            }), 400
        
        if not features:
            return jsonify({
                'status': 'error',
                'message': 'Không có features nào được chọn'
            }), 400
        
        # Lưu trạng thái hiện tại của tiến trình
        is_running = config[task_id].get('status') == 'RUNNING'
        
        # Lấy đường dẫn đến file log hiện tại
        old_log_file = config[task_id].get('log_file')
        old_error_log = config[task_id].get('error_log')
        
        # Nếu đang chạy, dừng tiến trình trước
        if is_running:
            stop_result = stop_task_internal(task_id)
            if stop_result['status'] == 'error':
                return jsonify(stop_result), 500
            
        # Parse các tính năng
        parsed_features = {}
        for feat in features:
            if feat.startswith("time_to_save"):
                try:
                    val = int(feat.split(" ")[-1])
                    parsed_features["time_to_save"] = val
                except:
                    continue
            else:
                parsed_features[feat] = True

        # Xây dựng lệnh Python mới
        python_cmd = f"{PYTHON_PATH} main.py --config {task_id}"
        
        # Cập nhật cấu hình tiến trình
        config[task_id].update({
            "room_id": room_id,
            "camera_ids": camera_ids,
            "features": parsed_features,
            "name": task_name,
            "command": python_cmd,
            "status": "STOPPED",
            "log_file": old_log_file,
            "error_log": old_error_log,
            "log_collection": "attendance_logs"
        })

        # Lưu lại file cấu hình
        save_json_file(config, TASK_CONFIG_FILE)

        # Cập nhật file cấu hình supervisor
        cmd_str = f"/bin/bash -c 'cd {WORK_DIR} && {python_cmd}'"
        conf_content = f"""[program:{task_id}]
command={cmd_str}
directory={WORK_DIR}
user={USER}
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=10
startretries=3
redirect_stderr=true
stdout_logfile={old_log_file}
stderr_logfile={old_error_log}
environment=HOME="{os.path.expanduser('~')}",USER="{USER}"
"""
        
        try:
            # Cập nhật file cấu hình supervisor
            supervisor_conf_path = os.path.join(SUPERVISOR_CONF_DIR, f"{task_id}.conf")
            with open(supervisor_conf_path, 'w') as f:
                f.write(conf_content)
            
            # Cập nhật supervisor
            subprocess.run(["supervisorctl", "reread"], check=True)
            subprocess.run(["supervisorctl", "update"], check=True)
            
            # Nếu tiến trình đang chạy trước đó, khởi động lại
            if is_running:
                subprocess.run(["supervisorctl", "start", f"{task_id}"], check=True)
                config[task_id]["status"] = "RUNNING"
                config[task_id]["start_time"] = time.time()
                save_json_file(config, TASK_CONFIG_FILE)  # Lưu lại trạng thái RUNNING
            
            return jsonify({
                'status': 'success',
                'message': f'Đã cập nhật tiến trình "{task_name}"',
                'task_id': task_id
            })
        
        except Exception as e:
            LOGGER.error(f"Lỗi khi cập nhật supervisor: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'Lỗi khi cập nhật supervisor: {str(e)}'
            }), 500
            
    except Exception as e:
        LOGGER.error(f"Lỗi khi cập nhật tiến trình: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi cập nhật tiến trình: {str(e)}'
        }), 500

#
# PHẦN 2: LOGIC NGHIỆP VỤ (INTERNAL FUNCTIONS)
#

def get_available_cameras():
    """Hàm nội bộ: Trả về danh sách dict gồm camera_id và name các camera_ids có sẵn"""

    # Kiểm tra webcam index 0
    cap = cv2.VideoCapture(0)
    has_webcam = cap.isOpened()
    cap.release()

    # Lấy toàn bộ camera từ database (bao gồm cả WEBCAM nếu có)
    cameras = list(config.camera_collection.find({}))

    # Nếu không có webcam thật, loại bỏ camera_id == 'WEBCAM'
    if not has_webcam:
        cameras = [cam for cam in cameras if cam.get("camera_id") != "WEBCAM"]

    # Trả về danh sách {'camera_id':..., 'name':...}
    return [
        {
            'camera_id': cam.get("camera_id"),
            'name': cam.get("name", cam.get("camera_id"))
        }
        for cam in cameras if cam.get("camera_id")
    ]

def get_available_rooms():
    """Hàm nội bộ: Trả về danh sách các phòng có camera"""
    return config.user_collection.distinct("room_id") 


def generate_task_id(name):
    """Tạo ID từ tên tiến trình"""
    # Chuyển sang chữ thường và loại bỏ dấu
    name_no_accents = unidecode(name.lower())
    
    # Thay thế ký tự không phải chữ/số thành gạch dưới
    safe_name = ''.join(c if c.isalnum() else '_' for c in name_no_accents)
    
    # Loại bỏ gạch dưới thừa
    safe_name = re.sub('_+', '_', safe_name)
    safe_name = safe_name.strip('_')
    
    # Đảm bảo ID không trống
    if not safe_name:
        safe_name = "process"
    
    # Kiểm tra xem ID này đã tồn tại chưa
    task_ids = load_json_file(TASK_CONFIG_FILE)
    
    # Nếu ID chưa tồn tại, sử dụng ngay
    if safe_name not in task_ids:
        return safe_name
    
    # Nếu ID đã tồn tại, thêm số vào cuối
    counter = 1
    while f"{safe_name}_{counter}" in task_ids:
        counter += 1
    
    return f"{safe_name}_{counter}"

def load_json_file(db_file_path, skip_keys=None):
    """
    Hàm nội bộ: Load process database from file và bỏ qua các key chỉ định
    
    Args:
        db_file_path (str): Đường dẫn đến file JSON
        skip_keys (list, optional): Danh sách các keys cần bỏ qua. Mặc định là ["DEFAULT"]

    Returns:
        dict: Dữ liệu JSON đã được đọc với các key đã được bỏ qua
    """
    if skip_keys is None:
        skip_keys = ["DEFAULT"]
        
    if os.path.exists(db_file_path):
        try:
            with open(db_file_path, 'r') as f:
                data = json.load(f)
                # Loại bỏ các key được chỉ định
                for key in skip_keys:
                    if key in data:
                        del data[key]
                return data
        except Exception as e:
            LOGGER.error(f"Lỗi khi đọc file JSON {db_file_path}: {e}")
            return {}
    return {}

def save_json_file(task_ids, db_file_path):
    """
    Hàm nội bộ: Save process database to file
    
    Args:
        task_ids (dict): Thông tin các tiến trình cần lưu
        db_file_path (str): Đường dẫn đến file JSON
    """
    LOGGER.debug(f"Đang lưu file JSON vào {db_file_path}")
    
    # Đọc dữ liệu hiện có để giữ lại DEFAULT
    current_data = {}
    if os.path.exists(db_file_path):
        try:
            with open(db_file_path, 'r') as f:
                current_data = json.load(f)
        except Exception as e:
            LOGGER.error(f"Lỗi khi đọc file JSON hiện có {db_file_path}: {e}")
    
    # Cập nhật dữ liệu mới, giữ nguyên DEFAULT
    for task_id, task_data in task_ids.items():
        if task_id in current_data:
            # Cập nhật thông tin cho task hiện có
            current_data[task_id].update(task_data)
        else:
            # Thêm task mới
            current_data[task_id] = task_data
    
    # Lưu toàn bộ dữ liệu
    try:
        with open(db_file_path, 'w') as f:
            json.dump(current_data, f, indent=4)
        LOGGER.info(f"Đã lưu thành công dữ liệu vào {db_file_path}")
    except Exception as e:
        LOGGER.error(f"Lỗi khi lưu file JSON {db_file_path}: {e}")

def delete_json_config(db_file_path, config_key):
    """
    Xóa một cấu hình cụ thể khỏi file JSON

    Args:
        db_file_path (str): Đường dẫn đến file JSON
        config_key (str): Tên key cấu hình cần xóa
    """
    try:
        # Đọc dữ liệu hiện có
        with open(db_file_path, 'r') as f:
            current_data = json.load(f)
        
        # Kiểm tra và xóa key nếu tồn tại
        if config_key in current_data:
            del current_data[config_key]
            
            # Lưu lại file JSON
            with open(db_file_path, 'w') as f:
                json.dump(current_data, f, indent=4)
            
            LOGGER.info(f"Đã xóa cấu hình '{config_key}' thành công từ {db_file_path}")
        else:
            LOGGER.warning(f"Không tìm thấy cấu hình '{config_key}' trong file JSON")
    
    except FileNotFoundError:
        LOGGER.error(f"File JSON không tồn tại: {db_file_path}")
    except json.JSONDecodeError:
        LOGGER.error(f"Lỗi đọc file JSON: {db_file_path}")
    except Exception as e:
        LOGGER.error(f"Lỗi khi xóa cấu hình {config_key}: {e}")

def format_time(timestamp):
    """Hàm nội bộ: Định dạng thời gian"""
    if isinstance(timestamp, (int, float)):
        return time.strftime("%d-%m-%Y %H:%M:%S", time.localtime(timestamp))
    return str(timestamp)

def get_task_ids_internal():
    """Hàm nội bộ: Lấy danh sách các tiến trình"""
    task_ids = load_json_file(TASK_CONFIG_FILE)
    
    try:
        result = subprocess.run(["supervisorctl", "status"], capture_output=True, text=True)
        
        # Parse output ngay cả khi có exit code khác 0
        supervisor_status = {}
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                task_id = parts[0]
                status = parts[1]
                supervisor_status[task_id] = status
        
        # Cập nhật trạng thái trong DB
        for task_id, process in list(task_ids.items()):
            if task_id in supervisor_status:
                process["status"] = supervisor_status[task_id]
            elif process["status"] == "RUNNING":
                try:
                    # Không dùng check=True
                    supervisor_detail = subprocess.run(["supervisorctl", "status", f"{task_id}"], capture_output=True, text=True
                    )
                    if "no such process" in supervisor_detail.stderr.lower() or "no such process" in supervisor_detail.stdout.lower():
                        process["status"] = "STOPPED"
                    else:
                        status_parts = supervisor_detail.stdout.strip().split()
                        process["status"] = status_parts[1] if len(status_parts) > 1 else "UNKNOWN"
                except Exception as detail_error:
                    process["status"] = "UNKNOWN"
        
        save_json_file(task_ids, TASK_CONFIG_FILE)
    except Exception as e:
        LOGGER.error(f"Lỗi khi cập nhật trạng thái: {str(e)}")
    
    return [{"id": pid, **p} for pid, p in task_ids.items()]

def create_process_internal(features, camera_ids, task=None, room_id=None):
    """Hàm nội bộ: Tạo tiến trình mới"""
    # Tạo ID dễ đọc từ tên tiến trình
    task_id = generate_task_id(task)

    # Parse các tính năng
    parsed_features = {}
    for feat in features:
        if feat.startswith("time_to_save"):
            try:
                val = int(feat.split(" ")[-1])
                parsed_features["time_to_save"] = val
            except:
                continue
        else:
            parsed_features[feat] = True

    # Định nghĩa các giá trị mặc định
    default_values = {
        "host": HOST,
        "process_manager_port": PROCESS_MANAGER_PORT,
        "app_port": APP_PORT,
        "websocket_port": WEBSOCKET_PORT,
        "noti_port": NOTI_PORT,
        "noti_control_port": NOTI_CONTROL_PORT,
        "noti_secret_key": NOTI_SECRET_KEY,
        "noti_allowed_ips": NOTI_ALLOWED_IPS,
        "features": DEFAULT_FEATURES
    }

    # Load cấu hình hiện tại
    config = load_json_file(TASK_CONFIG_FILE)

    # Cập nhật task mới với các giá trị mặc định
    config[task_id] = {
        **default_values,  # Áp dụng các giá trị mặc định
        "room_id": room_id,
        "camera_ids": camera_ids,
        "features": parsed_features
    }

    # Lưu lại file
    save_json_file(config, TASK_CONFIG_FILE)

    # Xây dựng lệnh Python
    python_cmd = f"{PYTHON_PATH} main.py --config {task_id}"

    # Lệnh hoàn chỉnh
    cmd_str = f"/bin/bash -c 'cd {WORK_DIR} && {python_cmd}'"

    # File log đúng đường dẫn supervisor/log/
    stdout_log = os.path.join(SUPERVISOR_LOG_DIR, f"{task_id}.log")
    stderr_log = os.path.join(SUPERVISOR_LOG_DIR, f"{task_id}_error.log")
    
    # Tạo file cấu hình supervisor với tên tiến trình
    conf_content = f"""[program:{task_id}]
command={cmd_str}
directory={WORK_DIR}
user={USER}
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=10
startretries=3
redirect_stderr=true
stdout_logfile={stdout_log}
stderr_logfile={stderr_log}
environment=HOME="{os.path.expanduser('~')}",USER="{USER}"
"""    
 
    try:
        # Lưu file cấu hình
        supervisor_conf_path = os.path.join(SUPERVISOR_CONF_DIR, f"{task_id}.conf")
        with open(supervisor_conf_path, 'w') as f:
            f.write(conf_content)
        
        # Ghi log để debug
        # LOGGER.debug(f"Đã tạo file cấu hình: {supervisor_conf_path}")
        # LOGGER.debug(f"Nội dung: {conf_content}")
        
        # Cập nhật supervisor
        subprocess.run(["supervisorctl", "reread"], check=True)
        subprocess.run(["supervisorctl", "update"], check=True)
        
        LOGGER.info(f"Supervisor đã reload và update thành công.")

        # Chờ một chút để supervisor cập nhật
        time.sleep(5)
        
        # Kiểm tra trạng thái
        result = subprocess.run(["supervisorctl", "status", f"{task_id}"], capture_output=True, text=True)
        # LOGGER.debug(f"Trạng thái sau khi cập nhật: {result.stdout}")
        
        # Khởi động tiến trình
        subprocess.run(["supervisorctl", "start", f"{task_id}"], check=True)
        
        # Lưu thông tin tiến trình với tên ở bên trong thông tin
        config = load_json_file(TASK_CONFIG_FILE)
        config[task_id].update({
            "name": get_unique_task_name(task),
            "command": python_cmd,
            "status": "RUNNING",
            "start_time": time.time(),
            "log_file": stdout_log,
            "error_log": stderr_log
        })
        save_json_file(config, TASK_CONFIG_FILE)
        
        return {
            "status": "success",
            "message": f"Đã tạo tiến trình với ID: {task_id}",
            "process": {"id": task_id, **config[task_id]}
        }
    
    except Exception as e:
        # Xử lý lỗi
        LOGGER.error(f"Lỗi: {str(e)}")
        
        # Xóa file config nếu có lỗi
        try:
            if os.path.exists(supervisor_conf_path):
                os.remove(supervisor_conf_path)
        except Exception as cleanup_error:
            LOGGER.error(f"Lỗi khi dọn dẹp: {str(cleanup_error)}")
        
        return {
            "status": "error",
            "message": f"Lỗi khi tạo tiến trình: {str(e)}"
        }

def stop_task_internal(task_id):
    """Hàm nội bộ: Dừng tiến trình"""
    task_ids = load_json_file(TASK_CONFIG_FILE)
    
    if task_id not in task_ids:
        return {"status": "error", "message": "Không tìm thấy tiến trình"}
    
    try:
        # Dừng tiến trình trong supervisor
        subprocess.run(["supervisorctl", "stop", f"{task_id}"], check=True)
        
        # Cập nhật supervisor
        subprocess.run(["supervisorctl", "reread"], check=True)
        subprocess.run(["supervisorctl", "update"], check=True)
        
        # Cập nhật trạng thái
        task_ids[task_id]["status"] = "STOPPED"
        save_json_file(task_ids, TASK_CONFIG_FILE)
        
        return {
            "status": "success",
            "message": f"Đã dừng tiến trình: {task_ids[task_id]['name']}"
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Lỗi khi dừng tiến trình: {str(e)}"
        }

def get_process_log_internal(task_id):
    """Hàm nội bộ: Lấy log của tiến trình"""
    task_ids = load_json_file(TASK_CONFIG_FILE)
    
    if task_id not in task_ids:
        return {"status": "error", "message": "Không tìm thấy tiến trình"}
    
    log_file = task_ids[task_id]["log_file"]
    
    try:
        # Lấy n dòng log cuối cùng (mặc định 100 dòng)
        lines = 100
        
        if os.path.exists(log_file):
            # Đọc n dòng cuối cùng của file log
            result = subprocess.run(["tail", "-n", str(lines), log_file], 
                                   capture_output=True, text=True, check=True)
            log_content = result.stdout
        else:
            log_content = "File log không tồn tại hoặc tiến trình chưa tạo log."
        
        return {
            "status": "success",
            "task_id": task_id,
            "log": log_content
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Lỗi khi đọc log: {str(e)}"
        }

def delete_task_internal(task_id):
    task_ids = load_json_file(TASK_CONFIG_FILE)

    if task_id not in task_ids:
        return {'status': 'error', 'message': 'Không tìm thấy tiến trình'}

    try:
        name = task_ids[task_id].get('name', task_id)

        # 1. Dừng tiến trình nếu đang chạy
        stop_task_internal(task_id)

        # 2. Xóa file cấu hình supervisor
        conf_path = os.path.join(SUPERVISOR_CONF_DIR, f"{task_id}.conf")
        if os.path.exists(conf_path):
            os.remove(conf_path)

        # 3. Xóa nội dung tệp log
        # log_file = task_ids[task_id].get('log_file')
        # error_log = task_ids[task_id].get('error_log')
        
        # if log_file and os.path.exists(log_file):
        #     subprocess.run(['bash', '-c', f'echo "" > {log_file}'], check=True)
                
        # if error_log and os.path.exists(error_log):
        #     subprocess.run(['bash', '-c', f'echo "" > {error_log}'], check=True)

        # 3. Reload supervisor
        subprocess.run(["supervisorctl", "reread"], check=True)
        subprocess.run(["supervisorctl", "update"], check=True)

        # 4. Gỡ khỏi DB
        delete_json_config(TASK_CONFIG_FILE, task_id)

        return {
            'status': 'success',
            'message': f'Đã xóa tiến trình: {name}'
        }

    except Exception as e:
        return {
            'status': 'error',
            'message': f'Lỗi khi xóa tiến trình: {e}'
        }

def get_unique_task_name(name):
    """
    Trả về tên không trùng trong database, thêm hậu tố số nếu cần.
    """
    # Load database
    if os.path.exists(TASK_CONFIG_FILE):
        try:
            with open(TASK_CONFIG_FILE, 'r') as f:
                db = json.load(f)
        except:
            db = {}
    else:
        db = {}

    existing_names = {p.get('name') for p in db.values() if 'name' in p}

    if name not in existing_names:
        return name

    # Tạo tên mới với hậu tố số
    counter = 1
    while True:
        new_name = f"{name} {counter}"
        if new_name not in existing_names:
            return new_name
        counter += 1


if __name__ == '__main__':
    # Kiểm tra và tạo các thư mục cần thiết
    for dir_path in [SUPERVISOR_DIR, SUPERVISOR_CONF_DIR, SUPERVISOR_LOG_DIR]:
        os.makedirs(dir_path, exist_ok=True)
 
    # Khởi động server
    app.run(host='0.0.0.0', port=9620, debug=False)