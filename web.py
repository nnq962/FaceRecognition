from flask import Flask, render_template, request, jsonify
import subprocess
import threading
import time
import os
import json
import uuid
from datetime import datetime

app = Flask(__name__)

# Biến lưu trạng thái các quy trình
processes = {}

# Cấu trúc process: 
# {
#   "process_id": {
#       "process": subprocess.Popen object,
#       "output": [log lines],
#       "running": True/False,
#       "command": [command list],
#       "name": "Process Name",
#       "start_time": timestamp
#   }
# }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run_process', methods=['POST'])
def run_process():
    data = request.json
    sources = data.get('sources', [])
    options = data.get('options', {})
    process_name = data.get('process_name', f"Process {len(processes) + 1}")
    
    # Kiểm tra sources
    if not sources:
        return jsonify({'status': 'error', 'message': 'Chưa chọn nguồn dữ liệu nào'})
    
    # Tạo command
    source_str = ','.join(map(str, sources))
    command = ['python3', 'main.py', '--source', source_str]
    
    # Thêm các tùy chọn
    for option, value in options.items():
        if value is True:
            command.append(f'--{option}')
        elif value not in [False, None, '']:
            command.append(f'--{option}')
            command.append(str(value))
    
    # Tạo process_id
    process_id = str(uuid.uuid4())
    
    # Tạo process object
    processes[process_id] = {
        "process": None,
        "output": [],
        "running": True,
        "command": command,
        "name": process_name,
        "start_time": datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    }
    
    # Chạy quy trình trong thread riêng biệt
    threading.Thread(target=run_command, args=(process_id, command)).start()
    
    return jsonify({
        'status': 'success', 
        'message': f'Quy trình "{process_name}" đã bắt đầu', 
        'process_id': process_id
    })

@app.route('/stop_process', methods=['POST'])
def stop_process():
    process_id = request.json.get('process_id')
    
    if not process_id or process_id not in processes:
        return jsonify({'status': 'error', 'message': 'Process ID không hợp lệ'})
    
    process_data = processes[process_id]
    
    if process_data["running"] and process_data["process"]:
        try:
            process_data["process"].terminate()
            process_data["running"] = False
            return jsonify({
                'status': 'success', 
                'message': f'Quy trình "{process_data["name"]}" đã dừng'
            })
        except:
            return jsonify({
                'status': 'error', 
                'message': f'Không thể dừng quy trình "{process_data["name"]}"'
            })
    else:
        return jsonify({
            'status': 'error', 
            'message': f'Quy trình "{process_data["name"]}" không đang chạy'
        })

@app.route('/get_process_status', methods=['GET'])
def get_process_status():
    process_id = request.args.get('process_id')
    
    if not process_id or process_id not in processes:
        return jsonify({'status': 'error', 'message': 'Process ID không hợp lệ'})
    
    process_data = processes[process_id]
    
    return jsonify({
        'running': process_data["running"],
        'output': process_data["output"],
        'name': process_data["name"],
        'start_time': process_data["start_time"]
    })

@app.route('/get_all_processes', methods=['GET'])
def get_all_processes():
    result = {}
    
    for pid, process_data in processes.items():
        result[pid] = {
            'running': process_data["running"],
            'name': process_data["name"],
            'start_time': process_data["start_time"],
            'command': ' '.join(process_data["command"])
        }
    
    return jsonify(result)

@app.route('/get_available_sources', methods=['GET'])
def get_available_sources():
    # TODO: Thay thế bằng API để lấy nguồn camera thực tế
    # Hiện tại trả về list mẫu
    sources = [
        {"id": "0", "name": "Webcam"},
        {"id": "1", "name": "Camera 1 (USB)"},
        {"id": "2", "name": "Camera 2 (RTSP)"},
        {"id": "3", "name": "Camera 3 (IP)"},
        {"id": "4", "name": "Camera 4 (File)"}
    ]
    
    return jsonify(sources)

def run_command(process_id, command):
    process_data = processes.get(process_id)
    
    if not process_data:
        return
    
    try:
        # Chạy lệnh và lưu quy trình
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Lưu process vào dict
        process_data["process"] = process
        
        # Đọc output từ quy trình
        for line in process.stdout:
            timestamp = datetime.now().strftime("%H:%M:%S")
            process_data["output"].append(f"[{timestamp}] {line.strip()}")
            # Giới hạn số lượng dòng output để tránh memory leak
            if len(process_data["output"]) > 1000:
                process_data["output"] = process_data["output"][-1000:]
        
        # Đợi quy trình kết thúc
        process.wait()
        
    except Exception as e:
        timestamp = datetime.now().strftime("%H:%M:%S")
        process_data["output"].append(f"[{timestamp}] Lỗi: {str(e)}")
    
    finally:
        process_data["running"] = False
        process_data["process"] = None

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=6789)