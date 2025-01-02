import asyncio
import websockets

# Địa chỉ IP và cổng của server
SERVER_IP = "192.168.1.142"
PORT = 6789

# Hàm xử lý giao tiếp với server
async def communicate():
    uri = f"ws://{SERVER_IP}:{PORT}"
    async with websockets.connect(uri) as websocket:
        print(f"Đã kết nối đến server tại {uri}")

        while True:
            # Nhận thông báo từ server
            response = await websocket.recv()
            print(f"Phản hồi từ server: {response}")

if __name__ == "__main__":
    asyncio.run(communicate())