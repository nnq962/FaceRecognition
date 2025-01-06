import websocket

# Xử lý sự kiện khi nhận được tin nhắn từ server
def on_message(ws, message):
    print(f"Nhận thông báo từ server: {message}")

# Xử lý sự kiện khi kết nối đến server
def on_open(ws):
    print("Đã kết nối đến server!")

# Xử lý sự kiện khi kết nối bị đóng
def on_close(ws, close_status_code, close_msg):
    print("Kết nối bị đóng.")

# Xử lý sự kiện khi có lỗi
def on_error(ws, error):
    print(f"Lỗi: {error}")

if __name__ == "__main__":
    # Địa chỉ server
    server_address = "ws://192.168.1.142:6789"

    # Khởi tạo WebSocketApp và gán các callback
    ws = websocket.WebSocketApp(
        server_address,
        on_message=on_message,
        on_open=on_open,
        on_close=on_close,
        on_error=on_error,
    )

    # Chạy WebSocket client
    ws.run_forever()