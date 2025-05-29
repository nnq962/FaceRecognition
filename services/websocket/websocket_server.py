import os
import sys
import time
import json
import yaml
import argparse

from typing import Dict, List, Optional
from pydantic import BaseModel
import uvicorn

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Thêm project root vào sys.path để import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils.logger_config import LOGGER

# Đường dẫn static và templates tuyệt đối
static_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'static'))
templates_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'templates'))

# Config
CONFIG_FILE = "config.yaml"

# Khởi tạo FastAPI app
app = FastAPI(title="WebSocket Answer Distribution Server")
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Khởi tạo Jinja2 templates
templates = Jinja2Templates(directory=templates_path)

# Model cho dữ liệu thông tin
class ServerData(BaseModel):
    timestamp: Optional[str] = None
    type: str  # Loại dữ liệu (answers, hand_raise, attendance)
    data: dict  # Dữ liệu thực tế
    meta: Optional[dict] = None

# Quản lý kết nối WebSocket
class ConnectionManager:
    def __init__(self):
        # Lưu trữ kết nối theo phòng - phòng được tạo động
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Lưu trữ thông tin mới nhất của mỗi phòng
        self.latest_data: Dict[str, str] = {}
    
    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        # Tạo phòng mới nếu chưa tồn tại
        if room not in self.active_connections:
            self.active_connections[room] = []
            LOGGER.info(f"Tạo phòng mới: {room}")
        
        self.active_connections[room].append(websocket)
        LOGGER.info(f"Client mới kết nối đến phòng {room}. Tổng số client trong phòng: {len(self.active_connections[room])}")
        
        # Gửi dữ liệu mới nhất ngay khi kết nối
        if room in self.latest_data and self.latest_data[room]:
            await websocket.send_text(self.latest_data[room])
            LOGGER.debug(f"Đã gửi dữ liệu hiện tại cho client mới trong phòng {room}")
    
    def disconnect(self, websocket: WebSocket, room: str):
        if room in self.active_connections and websocket in self.active_connections[room]:
            self.active_connections[room].remove(websocket)
            LOGGER.info(f"Client ngắt kết nối khỏi phòng {room}. Số client còn lại: {len(self.active_connections[room])}")
            
            # Dọn dẹp phòng trống
            if len(self.active_connections[room]) == 0:
                LOGGER.info(f"Phòng {room} không còn client nào, giữ lại thông tin phòng")
    
    async def broadcast(self, message: str, room: str):
        # Tạo phòng mới nếu cần
        if room not in self.active_connections:
            self.active_connections[room] = []
            LOGGER.info(f"Tạo phòng mới từ broadcast: {room}")
        
        # Lưu trữ thông tin mới nhất
        self.latest_data[room] = message
        
        # Gửi đến tất cả các client trong phòng
        if len(self.active_connections[room]) > 0:
            LOGGER.info(f"Gửi dữ liệu mới đến {len(self.active_connections[room])} client trong phòng {room}")
            disconnected_clients = []
            
            for connection in self.active_connections[room]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    LOGGER.warning(f"Lỗi khi gửi tin nhắn đến client trong phòng {room}: {str(e)}")
                    disconnected_clients.append(connection)
            
            # Dọn dẹp các kết nối bị ngắt
            for client in disconnected_clients:
                self.active_connections[room].remove(client)
        else:
            LOGGER.info(f"Lưu dữ liệu cho phòng {room} nhưng hiện không có client nào kết nối")
    
    def get_stats(self):
        """Trả về thống kê về số lượng phòng và kết nối"""
        stats = {
            "total_rooms": len(self.active_connections),
            "total_connections": sum(len(clients) for clients in self.active_connections.values()),
            "rooms": {room: len(clients) for room, clients in self.active_connections.items()}
        }
        return stats


manager = ConnectionManager()

# Trang HTML sử dụng template
@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    LOGGER.info("Client truy cập trang chủ")
    return templates.TemplateResponse("websocket_server.html", {"request": request})

# WebSocket endpoint cho clients
@app.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    await manager.connect(websocket, room)
    LOGGER.info(f"Client đã kết nối đến phòng {room}")
    
    try:
        while True:
            # Chờ tin nhắn từ client (chỉ để giữ kết nối)
            data = await websocket.receive_text()
            LOGGER.debug(f"Nhận tin nhắn từ client trong phòng {room}: {data[:100]}...")
    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
        LOGGER.info(f"Client đã ngắt kết nối khỏi phòng {room}")
    except Exception as e:
        manager.disconnect(websocket, room)
        LOGGER.error(f"Lỗi với kết nối WebSocket trong phòng {room}: {str(e)}")

# HTTP endpoint để nhận thông tin từ các chương trình
@app.post("/submit/{room}")
async def submit_data(room: str, data: ServerData):
    start_time = time.time()
    LOGGER.info(f"Nhận dữ liệu {data.type} mới cho phòng {room}")
    
    if not data.timestamp:
        data.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        # Chuyển đổi dữ liệu thành chuỗi JSON
        message = json.dumps(data.model_dump())
        # Broadcast đến tất cả clients trong phòng
        await manager.broadcast(message, room)
        
        process_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        LOGGER.info(f"Đã xử lý và gửi thông tin cho phòng {room} trong {process_time:.2f}ms")
        
        return {
            "status": "success", 
            "room": room, 
            "timestamp": data.timestamp,
            "process_time_ms": round(process_time, 2)
        }
    except Exception as e:
        LOGGER.error(f"Lỗi khi xử lý thông tin cho phòng {room}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint lấy thông tin về số lượng kết nối
@app.get("/stats")
async def get_stats():
    LOGGER.info("Truy cập thống kê server")
    return manager.get_stats()

# Endpoint kiểm tra sức khỏe server
@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}

def load_config(config_name, config_file=CONFIG_FILE):
    """Tải cấu hình từ file YAML"""
    try:
        with open(config_file, 'r', encoding='utf-8') as file:
            all_configs = yaml.safe_load(file)
            
            if config_name in all_configs:
                return all_configs[config_name]
            else:
                available_configs = ", ".join(all_configs.keys())
                LOGGER.error(f"Không tìm thấy config '{config_name}'. Các config có sẵn: {available_configs}")
                return None
    except Exception as e:
        LOGGER.error(f"Lỗi khi đọc file config: {str(e)}")
        return None

# Chạy server
if __name__ == "__main__":
    LOGGER.info("Khởi động WebSocket Server...")
    parser = argparse.ArgumentParser(description="WebSocket Server")
    parser.add_argument('--config', type=str, required=True, help='Configuration profile to use')
    
    args = parser.parse_args()
    config_name = args.config

    # Đọc file cấu hình
    config = load_config(config_name)
    host = config.get("host")
    port = config.get("websocket_port")

    uvicorn.run(app, host=host, port=port, log_level="info")