from websocket_server import WebsocketServer
from threading import Thread

# Địa chỉ IP và cổng của server
HOST = "192.168.1.142"
PORT = 6789

# Danh sách các kết nối WebSocket
clients = []

# Gửi tin nhắn đến tất cả client
def broadcast_message(server, message):
    print(f"Gửi tin nhắn đến tất cả client: {message}")
    for client in clients:
        server.send_message(client, message)

# Xử lý sự kiện khi có client kết nối
def client_connected(client, server):
    print(f"Client đã kết nối: {client['address']}")
    clients.append(client)

# Xử lý sự kiện khi client ngắt kết nối
def client_disconnected(client, server):
    print(f"Client đã ngắt kết nối: {client['address']}")
    clients.remove(client)

# Hàm khởi chạy server WebSocket
def run_server():
    server = WebsocketServer(host=HOST, port=PORT)
    server.set_fn_new_client(client_connected)
    server.set_fn_client_left(client_disconnected)
    print(f"Server đang chạy tại ws://{HOST}:{PORT}")
    server.run_forever()

# Tạo luồng chạy server WebSocket
server = WebsocketServer(host=HOST, port=PORT)
Thread(target=server.run_forever, daemon=True).start()