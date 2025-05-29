import requests
import os
import sys

# Thêm project root vào sys.path để import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils.logger_config import LOGGER
from config import config

def send_data_to_server(data_type, payload, room_id, server_address="http://localhost:3000", meta=None):
    """
    Gửi dữ liệu bất kỳ đến WebSocket server.

    Parameters:
    - data_type: Loại dữ liệu (ví dụ: "answers", "hand_raise", "attendance", ...)
    - payload: Dictionary chứa dữ liệu cần gửi
    - room_id: ID của phòng
    - server_address: Địa chỉ của WebSocket server
    - meta: Dictionary bổ sung thông tin meta (ví dụ: camera_id, version, source...)

    Returns:
    - dict: Kết quả từ server
    """
    url = f"{server_address}/submit/{room_id}"

    # Meta mặc định
    default_meta = {
        "source": "classroom_system",
        "version": "1.0"
    }

    # Gộp meta người dùng truyền vào nếu có
    if meta:
        default_meta.update(meta)

    data = {
        "timestamp": config.get_vietnam_time(),
        "type": data_type,
        "data": payload,
        "meta": default_meta
    }
    
    try:
        LOGGER.info(f"Gửi dữ liệu {data_type} đến phòng {room_id}")
        response = requests.post(url, json=data)
        result = response.json()
        
        if response.status_code == 200:
            LOGGER.info(f"Gửi dữ liệu {data_type} thành công đến phòng {room_id}")
        else:
            LOGGER.warning(f"Gửi dữ liệu {data_type} không thành công: {result}")
            
        return result
    except Exception as e:
        LOGGER.error(f"Lỗi khi gửi dữ liệu {data_type} đến phòng {room_id}: {e}")
        return {"status": "error", "message": str(e)}