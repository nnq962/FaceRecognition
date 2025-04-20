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
WORK_DIR = "./"  # thư mục chính
USER = "pc"

# --- Thư mục supervisor (gồm: db, conf, log) ---
SUPERVISOR_DIR = os.path.join(WORK_DIR, "supervisor")
SUPERVISOR_CONF_DIR = os.path.join(SUPERVISOR_DIR, "conf")  # nơi lưu các file .conf
SUPERVISOR_LOG_DIR = os.path.join(SUPERVISOR_DIR, "log")    # nơi lưu log stdout/stderr
PROCESS_DB_FILE = os.path.join(SUPERVISOR_DIR, "supervisor_database.json")

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
        process_name = data.get('process_name', '')
        sources = data.get('sources', [])
        options = data.get('options', {})

        # Kiểm tra xem có tên tiến trình không
        if not process_name:
            return jsonify({
                'status': 'error',
                'message': 'Vui lòng nhập tên cho tiến trình'
            }), 400

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
        
        if not tasks:
            return jsonify({
                'status': 'error',
                'message': 'Không có task nào được chọn'
            }), 400

        # Gọi hàm tạo tiến trình của API
        result = create_process_internal(tasks, sources, process_name)
        
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
        LOGGER.error(f"Lỗi khi chạy tiến trình: {str(e)}")
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
        LOGGER.error(f"Lỗi khi dừng tiến trình: {str(e)}")
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
        LOGGER.error(f"Lỗi khi lấy danh sách tiến trình: {str(e)}")
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
        LOGGER.error(f"Lỗi khi lấy trạng thái tiến trình: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi lấy trạng thái tiến trình: {str(e)}'
        }), 500
    
@app.route('/get_process_details', methods=['GET'])
def get_process_details():
    """Lấy thông tin chi tiết của một tiến trình để chỉnh sửa"""
    try:
        process_id = request.args.get('process_id')
        
        if not process_id:
            return jsonify({
                'status': 'error',
                'message': 'Thiếu ID tiến trình'
            }), 400
        
        # Lấy thông tin tiến trình từ database
        processes = load_process_db()
        
        if process_id not in processes:
            return jsonify({
                'status': 'error',
                'message': 'Không tìm thấy tiến trình'
            }), 404
        
        process = processes[process_id]
        
        # Chuyển đổi tasks thành options
        options = {}
        for task in process.get('tasks', []):
            if task.startswith('time_to_save'):
                # Xử lý đặc biệt cho time_to_save
                parts = task.split()
                if len(parts) >= 2:
                    options['export_data'] = True
                    options['time_to_save'] = int(parts[1])
                else:
                    options['export_data'] = True
            else:
                options[task] = True
        
        # Trả về thông tin chi tiết của tiến trình
        LOGGER.debug(f"Thông tin chi tiết tiến trình: {process}")
        
        return jsonify({
            'status': 'success',
            'process': {
                'id': process_id,
                'name': process.get('name', ''),
                'sources': process.get('sources', []),
                'options': options,
                'command': process.get('command', '')
            }
        })
    except Exception as e:
        LOGGER.error(f"Lỗi khi lấy thông tin chi tiết tiến trình: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Lỗi khi lấy thông tin tiến trình: {str(e)}'
        }), 500

@app.route('/delete_process', methods=['POST'])
def delete_process_route():
    data = request.get_json(force=True)
    pid = data.get('process_id')
    if not pid:
        return jsonify(status='error', message='Thiếu process_id'), 400
    result = delete_process_internal(pid)
    return jsonify(result), (200 if result.get('status')=='success' else 500)

@app.route('/restart_process', methods=['POST'])
def restart_process():
    data = request.json or {}
    pid = data.get('process_id')
    if not pid:
        return jsonify(status='error', message='Thiếu process_id'), 400
    try:
        # Lấy thông tin từ database
        db = load_process_db()
        if pid not in db:
            return jsonify(status='error', message=f'Không tìm thấy tiến trình {pid}'), 404
        
        # Lấy đường dẫn tệp log
        log_file = db[pid].get('log_file')
        error_log = db[pid].get('error_log')

        # Lấy tên tiến trình
        name = db[pid].get('name', pid)
        
        # Xóa nội dung của tệp log
        if log_file and os.path.exists(log_file):
            subprocess.run(['bash', '-c', f'echo "" > {log_file}'], check=True)
                
        if error_log and os.path.exists(error_log):
            subprocess.run(['bash', '-c', f'echo "" > {error_log}'], check=True)
        
        # Gọi supervisorctl restart
        subprocess.run(['supervisorctl', 'restart', pid], check=True)
        
        # Cập nhật start_time mới
        if pid in db:
            db[pid]['start_time'] = time.time()
            save_process_db(db)
            
        return jsonify(status='success', message=f'Đã restart: {name}')
    
    except subprocess.CalledProcessError as e:
        return jsonify(status='error', message=f'Restart thất bại: {e}'), 500
    except Exception as e:
        return jsonify(status='error', message=f'Lỗi khi xử lý: {str(e)}'), 500

@app.route('/update_process', methods=['POST'])
def update_process():
    """Cập nhật một tiến trình hiện có"""
    try:
        data = request.json
        
        # Lấy dữ liệu từ request
        process_id = data.get('process_id')
        process_name = data.get('process_name', '')
        sources = data.get('sources', [])
        options = data.get('options', {})

        LOGGER.debug(f"Nhận yêu cầu cập nhật tiến trình: {process_id}")

        if not process_id:
            return jsonify({
                'status': 'error',
                'message': 'Thiếu ID tiến trình'
            }), 400
        
        # Kiểm tra xem tiến trình có tồn tại không
        processes = load_process_db()
        if process_id not in processes:
            return jsonify({
                'status': 'error',
                'message': 'Không tìm thấy tiến trình'
            }), 404
        
        # Kiểm tra xem có tên tiến trình không
        if not process_name:
            return jsonify({
                'status': 'error',
                'message': 'Vui lòng nhập tên cho tiến trình'
            }), 400
        
        # Kiểm tra xem có nguồn dữ liệu được chọn không
        if not sources:
            return jsonify({
                'status': 'error',
                'message': 'Vui lòng chọn ít nhất một nguồn dữ liệu'
            }), 400
        
        # Sắp xếp sources tăng dần (nếu là số)
        sources.sort(key=lambda x: int(x) if x.isdigit() else x)
        
        # Chuyển đổi options thành tasks
        tasks = []
        for name, value in options.items():
            if not value:
                continue
                
            if name == 'export_data':
                # Thêm export_data
                tasks.append('export_data')
                # Thêm time_to_save nếu có
                if 'time_to_save' in options and options['time_to_save']:
                    tasks.append(f"time_to_save {options['time_to_save']}")
            elif name != 'time_to_save':  # Bỏ qua time_to_save, đã xử lý ở trên
                tasks.append(name)
        
        if not tasks:
            return jsonify({
                'status': 'error',
                'message': 'Không có task nào được chọn'
            }), 400
        
        # Lưu trạng thái hiện tại của tiến trình
        is_running = processes[process_id].get('status') == 'RUNNING'
        
        # Lấy đường dẫn đến file cấu hình và log hiện tại
        old_log_file = processes[process_id].get('log_file')
        old_error_log = processes[process_id].get('error_log')
        
        # Nếu đang chạy, dừng tiến trình trước
        if is_running:
            stop_result = stop_process_internal(process_id)
            if stop_result['status'] == 'error':
                return jsonify(stop_result), 500
        
        # Xây dựng lệnh Python mới
        source_param = ",".join(sources)
        python_cmd = f"python3 main.py --source {source_param}"
        
        # Thêm các tham số khác
        for task in tasks:
            python_cmd += f" --{task}"
        
        # Lệnh hoàn chỉnh với kích hoạt Conda
        cmd_str = f"/bin/bash -c 'source /home/pc/anaconda3/bin/activate nnq && cd {WORK_DIR} && {python_cmd}'"
        
        # Cập nhật file cấu hình supervisor
        conf_content = f"""[program:{process_id}]
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
            # Cập nhật file cấu hình
            supervisor_conf_path = os.path.join(SUPERVISOR_CONF_DIR, f"{process_id}.conf")
            with open(supervisor_conf_path, 'w') as f:
                f.write(conf_content)
            
            # Cập nhật supervisor
            subprocess.run(["supervisorctl", "reread"], check=True)
            subprocess.run(["supervisorctl", "update"], check=True)
            
            # Cập nhật thông tin tiến trình trong database
            processes[process_id].update({
                "name": process_name,
                "command": python_cmd,
                "tasks": tasks,
                "sources": sources,
                "status": "STOPPED"
            })
            
            save_process_db(processes)
            
            # Nếu tiến trình đang chạy trước đó, khởi động lại
            if is_running:
                subprocess.run(["supervisorctl", "start", f"{process_id}"], check=True)
                processes[process_id]["status"] = "RUNNING"
                processes[process_id]["start_time"] = time.time()
                save_process_db(processes)
            
            return jsonify({
                'status': 'success',
                'message': f'Đã cập nhật tiến trình "{process_name}"',
                'process_id': process_id
            })
        
        except Exception as e:
            LOGGER.error(f"Lỗi khi cập nhật tiến trình: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'Lỗi khi cập nhật tiến trình: {str(e)}'
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
        return time.strftime("%d-%m-%Y %H:%M:%S", time.localtime(timestamp))
    return str(timestamp)

def get_processes_internal():
    """Hàm nội bộ: Lấy danh sách các tiến trình"""
    processes = load_process_db()
    
    try:
        result = subprocess.run(["supervisorctl", "status"], capture_output=True, text=True)
        
        # Parse output ngay cả khi có exit code khác 0
        supervisor_status = {}
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                process_id = parts[0]
                status = parts[1]
                supervisor_status[process_id] = status
        
        # Cập nhật trạng thái trong DB
        for process_id, process in list(processes.items()):
            if process_id in supervisor_status:
                process["status"] = supervisor_status[process_id]
            elif process["status"] == "RUNNING":
                try:
                    # Không dùng check=True
                    supervisor_detail = subprocess.run(["supervisorctl", "status", f"{process_id}"], capture_output=True, text=True
                    )
                    if "no such process" in supervisor_detail.stderr.lower() or "no such process" in supervisor_detail.stdout.lower():
                        process["status"] = "STOPPED"
                    else:
                        status_parts = supervisor_detail.stdout.strip().split()
                        process["status"] = status_parts[1] if len(status_parts) > 1 else "UNKNOWN"
                except Exception as detail_error:
                    process["status"] = "UNKNOWN"
        
        save_process_db(processes)
    except Exception as e:
        LOGGER.error(f"Lỗi khi cập nhật trạng thái: {str(e)}")
    
    return [{"id": pid, **p} for pid, p in processes.items()]

def create_process_internal(tasks, sources, process_name=None):
    """Hàm nội bộ: Tạo tiến trình mới"""
    # Tạo ID dễ đọc từ tên tiến trình
    process_id = generate_process_id(process_name)

    # Nối các nguồn dữ liệu bằng dấu phẩy
    source_param = ",".join(sources)
    
    # Xây dựng lệnh Python
    python_cmd = f"python3 main.py --source {source_param}"
    
    # Thêm các tham số khác
    for task in tasks:
        python_cmd += f" --{task}"
    
    # Lệnh hoàn chỉnh với kích hoạt Conda
    cmd_str = f"/bin/bash -c 'source /home/pc/anaconda3/bin/activate nnq && cd {WORK_DIR} && {python_cmd}'"

    # File log đúng đường dẫn supervisor/log/
    stdout_log = os.path.join(SUPERVISOR_LOG_DIR, f"{process_id}.log")
    stderr_log = os.path.join(SUPERVISOR_LOG_DIR, f"{process_id}_error.log")
    
    # Tạo file cấu hình supervisor với tên tiến trình
    conf_content = f"""[program:{process_id}]
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
        supervisor_conf_path = os.path.join(SUPERVISOR_CONF_DIR, f"{process_id}.conf")
        with open(supervisor_conf_path, 'w') as f:
            f.write(conf_content)
        
        # Ghi log để debug
        LOGGER.debug(f"Đã tạo file cấu hình: {supervisor_conf_path}")
        LOGGER.debug(f"Nội dung: {conf_content}")
        
        # Cập nhật supervisor
        subprocess.run(["supervisorctl", "reread"], check=True)
        subprocess.run(["supervisorctl", "update"], check=True)
        
        LOGGER.info(f"Supervisor đã reload và update thành công.")

        # Chờ một chút để supervisor cập nhật
        time.sleep(5)
        
        # Kiểm tra trạng thái
        result = subprocess.run(["supervisorctl", "status", f"{process_id}"], capture_output=True, text=True)
        LOGGER.debug(f"Trạng thái sau khi cập nhật: {result.stdout}")
        
        # Khởi động tiến trình
        subprocess.run(["supervisorctl", "start", f"{process_id}"], check=True)
        
        # Lưu thông tin tiến trình với tên ở bên trong thông tin
        processes = load_process_db()
        processes[process_id] = {
            "name": get_unique_process_name(process_name),  # Lưu tên tiến trình trực tiếp trong process_db
            "command": python_cmd,
            "tasks": tasks,
            "sources": sources,
            "status": "RUNNING",
            "start_time": time.time(),
            "log_file": stdout_log,
            "error_log": stderr_log
        }
        save_process_db(processes)
        
        return {
            "status": "success",
            "message": f"Đã tạo tiến trình với ID: {process_id}",
            "process": {"id": process_id, **processes[process_id]}
        }
    
    except Exception as e:
        # Xử lý lỗi
        LOGGER.error(f"Lỗi: {str(e)}")
        
        # Xóa file config nếu có lỗi
        try:
            if os.path.exists(supervisor_conf_path):
                os.remove(supervisor_conf_path)
            LOGGER.debug(f"Đã xóa file cấu hình: {supervisor_conf_path}")
        except Exception as cleanup_error:
            LOGGER.error(f"Lỗi khi dọn dẹp: {str(cleanup_error)}")
        
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
        # Dừng tiến trình trong supervisor
        subprocess.run(["supervisorctl", "stop", f"{process_id}"], check=True)
        
        # Cập nhật supervisor
        subprocess.run(["supervisorctl", "reread"], check=True)
        subprocess.run(["supervisorctl", "update"], check=True)
        
        # Cập nhật trạng thái
        processes[process_id]["status"] = "STOPPED"
        save_process_db(processes)
        
        return {
            "status": "success",
            "message": f"Đã dừng tiến trình: {processes[process_id]['name']}"
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

def delete_process_internal(process_id):
    processes = load_process_db()
    if process_id not in processes:
        return {'status': 'error', 'message': 'Không tìm thấy tiến trình'}

    try:
        name = processes[process_id].get('name', process_id)

        # 1. Dừng tiến trình nếu đang chạy
        stop_process_internal(process_id)

        # 2. Xóa file cấu hình supervisor
        conf_path = os.path.join(SUPERVISOR_CONF_DIR, f"{process_id}.conf")
        if os.path.exists(conf_path):
            os.remove(conf_path)

        # 3. Reload supervisor
        subprocess.run(["supervisorctl", "reread"], check=True)
        subprocess.run(["supervisorctl", "update"], check=True)

        # 4. Gỡ khỏi DB
        del processes[process_id]
        save_process_db(processes)

        return {
            'status': 'success',
            'message': f'Đã xóa tiến trình: {name}'
        }

    except Exception as e:
        return {
            'status': 'error',
            'message': f'Lỗi khi xóa tiến trình: {e}'
        }

def get_unique_process_name(name):
    """
    Trả về tên không trùng trong database, thêm hậu tố số nếu cần.
    """
    # Load database
    if os.path.exists(PROCESS_DB_FILE):
        try:
            with open(PROCESS_DB_FILE, 'r') as f:
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
    
    # Khởi tạo process DB nếu chưa tồn tại
    if not os.path.exists(PROCESS_DB_FILE):
        save_process_db({})
    
    # Khởi động server
    app.run(host='0.0.0.0', port=5543, debug=True)