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

# Đường dẫn và cấu hình
MAIN_SCRIPT_PATH = "./main.py"  # Thay đổi đường dẫn này
SUPERVISOR_CONF_DIR = "/etc/supervisor/conf.d"  # Thư mục chứa file conf của supervisor
TEMP_DIR = "./"  # Thư mục tạm để lưu file log và conf
WORK_DIR = "/home/pc/nnq_projects/Work/FaceRecognition"  # Thư mục làm việc cho main.py
USER = "pc"

# File lưu thông tin tiến trình
PROCESS_DB_FILE = os.path.join(TEMP_DIR, "process_db.json")

#
# PHẦN 1: ROUTES CHO WEB UI
#

@app.route('/')
def index():
    """Trang chủ web UI"""
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    """Phục vụ các file tĩnh (CSS, JS, ...)"""
    return send_from_directory('static', path)

@app.route('/get_available_sources')
def get_available_sources_route():
    """Fetch list of available video sources"""
    try:
        # Gọi function nội bộ, nó trả về list[{'id':..., 'camera_name':...}, ...]
        source_options = get_available_sources()

        # Chuyển thành format front-end cần: {'id':..., 'name':...}
        sources = [
            {'id': src['id'], 'name': src['camera_name']}
            for src in source_options
        ]

        LOGGER.debug(sources)
        return jsonify(sources), 200

    except Exception as e:
        LOGGER.error(f"Error fetching sources: {e}")
        return jsonify({
            "error": "Failed to retrieve sources due to internal error.",
            "details": str(e)
        }), 500


@app.route('/run_process', methods=['POST'])
def run_process():
    """Chạy một tiến trình mới từ web UI"""
    try:
        data = request.json
        
        # Lấy dữ liệu từ request
        process_name = data.get('process_name', 'Tiến trình mới')
        sources = data.get('sources', [])
        options = data.get('options', {})

        # Kiểm tra xem có nguồn dữ liệu được chọn không
        if not sources:
            return jsonify({
                'status': 'error',
                'message': 'Vui lòng chọn ít nhất một nguồn dữ liệu'
            }), 400
        
        # Sắp xếp sources tăng dần (nếu là số)
        sources.sort(key=lambda x: int(x) if x.isdigit() else x)
        
        # Chuyển đổi dữ liệu để gọi API
        tasks = [
            f"{name} {value}" if name == 'time_to_save' else name
            for name, value in options.items()
            if value
        ]

        # Gọi hàm tạo tiến trình của API
        result = create_process_internal(tasks, sources, process_name)

        LOGGER.debug(result)
        
        if result['status'] == 'success':
            process_id = result['process']['id']
            return jsonify({
                'status': 'success',
                'message': f'Đã bắt đầu tiến trình "{process_name}"',
                'process_id': process_id
            })
        else:
            return jsonify(result)
    except Exception as e:
        print(f"Lỗi khi chạy tiến trình: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi tạo tiến trình: {str(e)}'
        }), 500

@app.route('/stop_process', methods=['POST'])
def stop_process():
    """Dừng một tiến trình từ web UI"""
    try:
        data = request.json
        process_id = data.get('process_id')
        
        if not process_id:
            return jsonify({
                'status': 'error',
                'message': 'Thiếu ID tiến trình'
            }), 400
        
        # Gọi hàm dừng tiến trình của API
        result = stop_process_internal(process_id)
        return jsonify(result)
    except Exception as e:
        print(f"Lỗi khi dừng tiến trình: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi dừng tiến trình: {str(e)}'
        }), 500

@app.route('/get_all_processes')
def get_all_processes():
    """Lấy danh sách tất cả các tiến trình cho web UI"""
    try:
        # Lấy danh sách tiến trình từ hàm API
        processes_list = get_processes_internal()
        
        # Chuyển đổi định dạng cho web UI
        result = {}
        for process in processes_list:
            process_id = process['id']
            
            result[process_id] = {
                'name': process.get('name', process_id),  # Lấy tên từ thông tin tiến trình
                'command': process['command'],
                'running': process['status'] == 'RUNNING',
                'start_time': format_time(process['start_time'])
            }
        
        return jsonify(result)
    except Exception as e:
        print(f"Lỗi khi lấy danh sách tiến trình: {str(e)}")
        return jsonify({})

@app.route('/get_process_status')
def get_process_status():
    """Lấy trạng thái của một tiến trình cụ thể cho web UI"""
    try:
        process_id = request.args.get('process_id')
        
        if not process_id:
            return jsonify({
                'status': 'error',
                'message': 'Thiếu ID tiến trình'
            }), 400
        
        # Kiểm tra xem tiến trình có tồn tại trong danh sách không
        processes = get_processes_internal()
        process = next((p for p in processes if p['id'] == process_id), None)
        
        if not process:
            return jsonify({
                'status': 'error',
                'message': 'Không tìm thấy tiến trình'
            }), 404
        
        # Lấy log của tiến trình
        log_result = get_process_log_internal(process_id)
        
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
        print(f"Lỗi khi lấy trạng thái tiến trình: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi lấy trạng thái tiến trình: {str(e)}'
        }), 500

#
# PHẦN 2: API ENDPOINTS
#

@app.route('/api/tasks', methods=['GET'])
def get_available_tasks():
    """API endpoint: Trả về danh sách các task có sẵn"""
    tasks = get_available_sources()
    return jsonify({
        "status": "success",
        "tasks": tasks
    })

@app.route('/api/processes', methods=['GET'])
def get_processes():
    """API endpoint: Lấy danh sách các tiến trình"""
    processes = get_processes_internal()
    return jsonify({
        "status": "success",
        "processes": processes
    })

@app.route('/api/processes', methods=['POST'])
def create_process():
    """API endpoint: Tạo tiến trình mới"""
    data = request.json
    tasks = data.get('tasks', [])
    source_value = data.get('source_value', '0')
    process_name = data.get('process_name', 'Tiến trình mới')
    
    result = create_process_internal(tasks, source_value, process_name)
    
    if result['status'] == 'success':
        return jsonify(result)
    else:
        return jsonify(result), 500

@app.route('/api/processes/<process_id>', methods=['DELETE'])
def delete_process(process_id):
    """API endpoint: Dừng tiến trình"""
    result = stop_process_internal(process_id)
    
    if result['status'] == 'success':
        return jsonify(result)
    else:
        return jsonify(result), 500

@app.route('/api/processes/<process_id>/log', methods=['GET'])
def get_process_log(process_id):
    """API endpoint: Lấy log của tiến trình"""
    result = get_process_log_internal(process_id)
    
    if result['status'] == 'success':
        return jsonify(result)
    else:
        return jsonify(result), 500

#
# PHẦN 3: LOGIC NGHIỆP VỤ (INTERNAL FUNCTIONS)
#

def get_available_sources():
    """Hàm nội bộ: Trả về danh sách các sources có sẵn"""

    # Kiểm tra webcam index 0
    cap = cv2.VideoCapture(0)
    has_webcam = cap.isOpened()
    cap.release()

    # Lấy camera từ database
    cameras = list(config.camera_collection.find({}))

    # Build danh sách options
    source_options = []

    if has_webcam:
        source_options.append({"id": "0", "camera_name": "Webcam"})

    for cam in cameras:
        id = str(cam["_id"])
        source_options.append({
            "id": id,
            "camera_name": cam.get("camera_name", f"Camera {id}")
        })

    return source_options

def generate_process_id(name):
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
    processes = load_process_db()
    
    # Nếu ID chưa tồn tại, sử dụng ngay
    if safe_name not in processes:
        return safe_name
    
    # Nếu ID đã tồn tại, thêm số vào cuối
    counter = 1
    while f"{safe_name}_{counter}" in processes:
        counter += 1
    
    return f"{safe_name}_{counter}"

def load_process_db():
    """Hàm nội bộ: Load process database from file"""
    if os.path.exists(PROCESS_DB_FILE):
        try:
            with open(PROCESS_DB_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_process_db(processes):
    """Hàm nội bộ: Save process database to file"""
    with open(PROCESS_DB_FILE, 'w') as f:
        json.dump(processes, f)

def format_time(timestamp):
    """Hàm nội bộ: Định dạng thời gian"""
    if isinstance(timestamp, (int, float)):
        return time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(timestamp))
    return str(timestamp)

def get_processes_internal():
    """Hàm nội bộ: Lấy danh sách các tiến trình"""
    processes = load_process_db()
    
    try:
        # Lấy trạng thái từ supervisorctl với sudo
        result = subprocess.run(["sudo", "supervisorctl", "status"], 
                              capture_output=True, text=True, check=True)
        
        # Parse output
        supervisor_status = {}
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0].startswith("task_"):
                process_id = parts[0].replace("task_", "")
                status = parts[1]
                supervisor_status[process_id] = status
        
        # Cập nhật trạng thái trong DB
        for process_id, process in list(processes.items()):
            if process_id in supervisor_status:
                process["status"] = supervisor_status[process_id]
            elif process["status"] == "RUNNING":
                # Nếu không còn trong supervisor nhưng trạng thái vẫn là RUNNING
                # Kiểm tra xem tiến trình có tồn tại thực sự không
                try:
                    supervisor_detail = subprocess.run(
                        ["sudo", "supervisorctl", "status", f"task_{process_id}"], 
                        capture_output=True, text=True
                    )
                    if "no such process" in supervisor_detail.stderr.lower() or "no such process" in supervisor_detail.stdout.lower():
                        process["status"] = "STOPPED"
                    else:
                        process["status"] = supervisor_detail.stdout.strip().split()[1] if len(supervisor_detail.stdout.strip().split()) > 1 else "UNKNOWN"
                except:
                    process["status"] = "UNKNOWN"
        
        save_process_db(processes)
    except Exception as e:
        print(f"Lỗi khi cập nhật trạng thái: {str(e)}")
    
    # Chuyển đổi từ dict sang list
    return [{"id": pid, **p} for pid, p in processes.items()]

def create_process_internal(tasks, sources, process_name=None):
    """Hàm nội bộ: Tạo tiến trình mới"""
    if not tasks:
        return {"status": "error", "message": "Không có task nào được chọn"}
    
    if not sources:
        return {"status": "error", "message": "Không có nguồn dữ liệu nào được chọn"}
    
    # Lấy tên tiến trình hoặc sử dụng mặc định
    if not process_name:
        process_name = 'Tiến trình mới'
    
    # Tạo ID dễ đọc từ tên tiến trình
    process_id = generate_process_id(process_name)

    # Nối các nguồn dữ liệu bằng dấu phẩy
    source_param = ",".join(sources)
    
    # Xây dựng lệnh Python
    python_cmd = f"python3 main.py --source {source_param}"
    
    # Thêm các tham số khác
    for task in tasks:
        python_cmd += f" --{task}"
    
    LOGGER.debug(python_cmd)

    # Lệnh hoàn chỉnh với kích hoạt Conda
    cmd_str = f"/bin/bash -c 'source /home/pc/anaconda3/bin/activate nnq && cd {WORK_DIR} && {python_cmd}'"
    
    # Tạo file cấu hình supervisor với tên tiến trình
    conf_content = f"""[program:task_{process_id}]
                        command={cmd_str}
                        directory={WORK_DIR}
                        user={USER}
                        autostart=true
                        autorestart=false
                        startsecs=10
                        stopwaitsecs=10
                        redirect_stderr=true
                        stdout_logfile=/tmp/task_{process_id}.log
                        stderr_logfile=/tmp/task_{process_id}_error.log
                        environment=HOME="/home/pc",USER={USER}
                    """
    
    # Đường dẫn tới file cấu hình trong thư mục supervisor
    supervisor_conf_path = f"/etc/supervisor/conf.d/task_{process_id}.conf"
    
    try:
        # Lưu file cấu hình tạm thời
        temp_conf_path = f"/tmp/task_{process_id}.conf"
        with open(temp_conf_path, 'w') as f:
            f.write(conf_content)
        
        # Copy file với sudo vào thư mục supervisor
        subprocess.run(["sudo", "cp", temp_conf_path, supervisor_conf_path], check=True)
        
        # Ghi log để debug
        LOGGER.debug(f"Đã tạo file cấu hình: {supervisor_conf_path}")
        LOGGER.debug(f"Nội dung: {conf_content}")
        
        # Cập nhật supervisor
        subprocess.run(["sudo", "supervisorctl", "reread"], check=True)
        subprocess.run(["sudo", "supervisorctl", "update"], check=True)
        
        # Chờ một chút để supervisor cập nhật
        time.sleep(2)
        
        # Kiểm tra trạng thái
        result = subprocess.run(["sudo", "supervisorctl", "status", f"task_{process_id}"], capture_output=True, text=True)
        LOGGER.debug(f"Trạng thái sau khi cập nhật: {result.stdout}")
        
        # Khởi động tiến trình
        subprocess.run(["sudo", "supervisorctl", "start", f"task_{process_id}"], check=True)
        
        # Lưu thông tin tiến trình với tên ở bên trong thông tin
        processes = load_process_db()
        processes[process_id] = {
            "name": process_name,  # Lưu tên tiến trình trực tiếp trong process_db
            "command": python_cmd,
            "tasks": tasks,
            "sources": sources,
            "status": "RUNNING",
            "start_time": time.time(),
            "log_file": f"/tmp/task_{process_id}.log",
            "error_log": f"/tmp/task_{process_id}_error.log"
        }
        save_process_db(processes)
        
        return {
            "status": "success",
            "message": f"Đã tạo tiến trình với ID: {process_id}",
            "process": {"id": process_id, **processes[process_id]}
        }
    
    except Exception as e:
        # Xử lý lỗi
        print(f"Lỗi: {str(e)}")
        
        # Xóa file config nếu có lỗi
        try:
            if os.path.exists(temp_conf_path):
                os.remove(temp_conf_path)
            subprocess.run(["sudo", "rm", "-f", supervisor_conf_path], check=False)
        except Exception as cleanup_error:
            print(f"Lỗi khi dọn dẹp: {str(cleanup_error)}")
        
        return {
            "status": "error",
            "message": f"Lỗi khi tạo tiến trình: {str(e)}"
        }

def stop_process_internal(process_id):
    """Hàm nội bộ: Dừng tiến trình"""
    processes = load_process_db()
    
    if process_id not in processes:
        return {"status": "error", "message": "Không tìm thấy tiến trình"}
    
    try:
        # Dừng tiến trình trong supervisor (thêm sudo)
        subprocess.run(["sudo", "supervisorctl", "stop", f"task_{process_id}"], check=True)
        
        # Xóa khỏi cấu hình supervisor (thêm sudo)
        supervisor_conf_path = os.path.join(SUPERVISOR_CONF_DIR, f"task_{process_id}.conf")
        subprocess.run(["sudo", "rm", "-f", supervisor_conf_path], check=True)
        
        # Cập nhật supervisor (thêm sudo)
        subprocess.run(["sudo", "supervisorctl", "reread"], check=True)
        subprocess.run(["sudo", "supervisorctl", "update"], check=True)
        
        # Cập nhật trạng thái
        processes[process_id]["status"] = "STOPPED"
        save_process_db(processes)
        
        return {
            "status": "success",
            "message": f"Đã dừng tiến trình {process_id}"
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Lỗi khi dừng tiến trình: {str(e)}"
        }

def get_process_log_internal(process_id):
    """Hàm nội bộ: Lấy log của tiến trình"""
    processes = load_process_db()
    
    if process_id not in processes:
        return {"status": "error", "message": "Không tìm thấy tiến trình"}
    
    log_file = processes[process_id]["log_file"]
    
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
            "process_id": process_id,
            "log": log_content
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Lỗi khi đọc log: {str(e)}"
        }

if __name__ == '__main__':
    # Đảm bảo thư mục DB tồn tại
    os.makedirs(os.path.dirname(PROCESS_DB_FILE), exist_ok=True)
    
    # Khởi tạo process DB nếu chưa tồn tại
    if not os.path.exists(PROCESS_DB_FILE):
        save_process_db({})
    
    # Khởi động server
    app.run(host='0.0.0.0', port=5543, debug=True)