import asyncio
import websockets
import threading
import json
from utils.logger_config import LOGGER

# Tập hợp các client đang kết nối
connected_clients = set()

# Vòng lặp (event loop) để server WebSocket chạy ngầm
loop = None

# Handler cơ bản: thêm client mới vào danh sách, lắng nghe và gỡ client khi đóng
async def handler(websocket):
    LOGGER.info("Client mới kết nối.")
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            LOGGER.info(f"Client gửi: {message}")
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.remove(websocket)
        LOGGER.info("Client đã ngắt kết nối.")

async def notify_all_clients(message: str):
    """
    Gửi message tới tất cả client hiện đang kết nối.
    Dùng await nên phải chạy trong event loop.
    """
    if connected_clients:
        # Tạo danh sách các tác vụ gửi message đến mỗi client
        tasks = [ws.send(message) for ws in connected_clients]
        await asyncio.gather(*tasks)

def start_ws_server(host="0.0.0.0", port=8765):
    """
    Khởi động WebSocket server trên host:port trong một thread riêng.
    Hàm này sẽ không chặn luồng chính (không block).
    """
    global loop
    loop = asyncio.new_event_loop()

    async def _start_server():
        async with websockets.serve(handler, host, port):
            LOGGER.info(f"WebSocket server đang chạy tại ws://{host}:{port}")
            # Chờ vô hạn để giữ server sống
            await asyncio.Future()

    def run_loop():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_start_server())

    # Tạo 1 thread để chạy event loop
    t = threading.Thread(target=run_loop, daemon=True)
    t.start()

def send_notification(message: dict):
    """
    Sends a notification message to all connected WebSocket clients.

    Args:
        message (dict): A dictionary containing notification details.
    """
    if loop is None:
        LOGGER.warning("WebSocket server chưa khởi động! Gọi start_ws_server() trước.")
        return
    
    # Chuyển đổi message thành JSON string trước khi gửi
    message_json = json.dumps(message)
    
    # Gọi hàm notify_all_clients trong event loop đang chạy ở thread khác
    future = asyncio.run_coroutine_threadsafe(notify_all_clients(message_json), loop)
    
    # future.result() sẽ chờ gửi xong (nếu muốn), hoặc có thể bỏ dòng này.
    future.result()
