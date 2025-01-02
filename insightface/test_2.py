import asyncio
import websockets

# Địa chỉ IP và cổng của server
HOST = "192.168.1.94"
PORT = 6789

# Danh sách các kết nối WebSocket
clients = set()

# Xử lý kết nối từ client
async def handle_client(websocket):
    # Thêm client vào danh sách
    clients.add(websocket)
    print(f"Đã kết nối từ {websocket.remote_address}")

    try:
        while True:
            # Nhận dữ liệu từ client
            message = await websocket.recv()
            print(f"Nhận từ client: {message}")
    except websockets.ConnectionClosed:
        print(f"Kết nối từ {websocket.remote_address} đã đóng.")
    finally:
        # Loại bỏ client khi ngắt kết nối
        clients.remove(websocket)

# Hàm gửi tin nhắn đến tất cả client
async def broadcast_message(text):
    print(f"Gửi tin nhắn đến tất cả client: {text}")
    if clients:  # Kiểm tra có client nào đang kết nối không
        await asyncio.gather(*(client.send(text) for client in clients))
    else:
        print("Không có client nào đang kết nối.")

# Hàm xử lý hình ảnh
async def process_images():
    while True:
        # Giả lập xử lý hình ảnh
        await asyncio.sleep(1)  # Thời gian xử lý mỗi khung hình
        # Giả lập logic phát hiện học sinh dơ tay
        raise_hand = True  # Thay bằng logic xử lý hình ảnh thực tế
        if raise_hand:
            await broadcast_message("Có học sinh dơ tay!")

# Hàm chính chạy server và xử lý hình ảnh
async def main():
    print(f"Server đang chạy tại ws://{HOST}:{PORT}")
    # Chạy server WebSocket
    async with websockets.serve(handle_client, HOST, PORT):
        # Chạy xử lý hình ảnh song song với server
        await process_images()

if __name__ == "__main__":
    asyncio.run(main())