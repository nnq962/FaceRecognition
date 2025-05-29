from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from typing import Dict, List, Optional
import uvicorn
import json
import yaml
import time
from pydantic import BaseModel
from utils.logger_config import LOGGER
from fastapi.staticfiles import StaticFiles
import argparse
import sys

CONFIG_FILE = "config.yaml"
app = FastAPI(title="WebSocket Answer Distribution Server")
app.mount("/static", StaticFiles(directory="static"), name="static")

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

# Trang HTML đơn giản cho khách truy cập
@app.get("/", response_class=HTMLResponse)
async def get():
    LOGGER.info("Client truy cập trang chủ")
    html = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Hệ thống theo dõi thông tin</title>
            <link rel="icon" href="/static/images/server.png" type="image/png">
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
                .container { max-width: 800px; margin: 0 auto; }
                h1 { color: #333; }
                #answers { margin-top: 20px; padding: 10px; border: 1px solid #ddd; min-height: 200px; }
                #status { padding: 10px; background-color: #f4f4f4; margin-bottom: 10px; }
                .roomSelector { margin-bottom: 20px; }
                button { padding: 8px 16px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
                button:hover { background-color: #45a049; }
                input { padding: 8px; width: 200px; }
            </style>
            <script>
                let ws = null;
                
                function connectToRoom() {
                    const roomId = document.getElementById('roomInput').value.trim();
                    if (!roomId) {
                        alert('Vui lòng nhập ID phòng');
                        return;
                    }
                    
                    // Đóng kết nối cũ nếu có
                    if (ws) {
                        ws.close();
                    }
                    
                    document.getElementById('status').innerHTML = 'Đang kết nối...';
                    ws = new WebSocket(`ws://${window.location.host}/ws/${roomId}`);

                    ws.onmessage = function(event) {
                        try {
                            const data = JSON.parse(event.data);
                            
                            // Hiển thị toàn bộ dữ liệu, không chỉ phần data
                            document.getElementById('answers').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                            
                            // Vẫn giữ lại logic xử lý theo loại nếu cần
                            switch (data.type) {
                                case "answers":
                                    // Xử lý thông tin nếu cần
                                    break;
                                case "hand_raise":
                                    // Xử lý giơ tay nếu cần
                                    break;
                                case "attendance":
                                    // Xử lý điểm danh nếu cần
                                    break;
                                default:
                                    console.log("Nhận dữ liệu:", data);
                            }
                        } catch (e) {
                            console.error("Lỗi khi xử lý dữ liệu:", e);
                            document.getElementById('answers').innerHTML = event.data;
                        }
                    };
                    
                    ws.onclose = function(event) {
                        document.getElementById('status').innerHTML = 'Mất kết nối!';
                    };
                    
                    ws.onopen = function(event) {
                        document.getElementById('status').innerHTML = 'Đã kết nối đến phòng ' + roomId;
                    };                    
                }

                function displayAnswers(answers) {
                    // Hiển thị thông tin trong #answers
                    document.getElementById('answers').innerHTML = '<pre>' + JSON.stringify(answers, null, 2) + '</pre>';
                }

                function updateHandRaiseStatus(handRaiseData) {
                    // Cập nhật trạng thái giơ tay
                    document.getElementById('answers').innerHTML = '<h3>Trạng thái giơ tay</h3><pre>' + JSON.stringify(handRaiseData, null, 2) + '</pre>';
                }

                function updateAttendance(attendanceData) {
                    // Cập nhật thông tin điểm danh
                    document.getElementById('answers').innerHTML = '<h3>Điểm danh</h3><pre>' + JSON.stringify(attendanceData, null, 2) + '</pre>';
                }

            </script>
        </head>
        <body>
            <div class="container">
                <h1>Hệ thống theo dõi thông tin</h1>
                <div class="roomSelector">
                    <input type="text" id="roomInput" placeholder="Nhập ID phòng...">
                    <button onclick="connectToRoom()">Kết nối</button>
                </div>
                <div id="status">Chưa kết nối</div>
                <div id="answers">Thông tin sẽ hiển thị ở đây...</div>
            </div>
        </body>
    </html>
    """
    return html

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