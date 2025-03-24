import socket
import time
import threading
from utils.logger_config import LOGGER

host = '192.168.1.142'

class NotificationServer:
    def __init__(self, host=host, port=9999, control_port=9998):
        self.host = host
        self.port = port
        self.control_port = control_port  # Port để nhận lệnh từ process khác
        self.server_socket = None
        self.client_socket = None
        self.control_socket = None
        self.running = False
        self.setup_server()
        self.setup_control()

    def setup_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            host_ip = socket.gethostbyname(self.host)
            self.server_socket.bind((host_ip, self.port))
            self.server_socket.listen(5)
            LOGGER.info(f"Server đang lắng nghe tại {(host_ip, self.port)}")
        except Exception as e:
            LOGGER.error(f"Lỗi khi thiết lập server: {e}")
            self.cleanup()
            raise

    def setup_control(self):
        try:
            self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.control_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            host_ip = socket.gethostbyname(self.host)
            self.control_socket.bind((host_ip, self.control_port))
            self.control_socket.listen(5)
            LOGGER.info(f"Control socket đang lắng nghe tại {(host_ip, self.control_port)}")
        except Exception as e:
            LOGGER.error(f"Lỗi khi thiết lập control socket: {e}")
            self.cleanup()
            raise

    def accept_client(self):
        try:
            self.client_socket, addr = self.server_socket.accept()
            LOGGER.info(f"Kết nối từ client: {addr}")
        except Exception as e:
            LOGGER.error(f"Lỗi khi chấp nhận client: {e}")

    def send_notification(self, message):
        try:
            if self.client_socket:
                self.client_socket.send(message.encode('utf-8'))
                LOGGER.info(f"Đã gửi tới client: {message}")
                return True
            else:
                LOGGER.info("Chưa có kết nối client")
                return False
        except Exception as e:
            LOGGER.error(f"Lỗi khi gửi thông báo: {e}")
            return False

    def handle_control(self):
        while self.running:
            try:
                control_client, addr = self.control_socket.accept()
                message = control_client.recv(1024).decode('utf-8')
                if message:
                    self.send_notification(message)
                control_client.close()
            except Exception as e:
                LOGGER.error(f"Lỗi khi xử lý control: {e}")

    def cleanup(self):
        self.running = False
        if self.client_socket:
            self.client_socket.close()
        if self.server_socket:
            self.server_socket.close()
        if self.control_socket:
            self.control_socket.close()
        LOGGER.info("Đã đóng tất cả kết nối")

    def run(self):
        self.running = True
        self.accept_client()
        control_thread = threading.Thread(target=self.handle_control, daemon=True)
        control_thread.start()
        while self.running:
            time.sleep(1)

# Instance toàn cục
server_instance = None

def start_server(host=host, port=9999, control_port=9998):
    global server_instance
    if server_instance is None or not server_instance.running:
        server_instance = NotificationServer(host, port, control_port)
        server_thread = threading.Thread(target=server_instance.run, daemon=True)
        server_thread.start()
        time.sleep(1)
        LOGGER.info("Server đã khởi động")
    return server_instance

def send_notification(message, host=host, control_port=9998):
    # Gửi thông báo tới control socket của server
    try:
        control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        control_socket.connect((host, control_port))
        control_socket.send(message.encode('utf-8'))
        control_socket.close()
        return True
    except Exception as e:
        LOGGER.error(f"Lỗi khi gửi thông báo tới server: {e}")
        return False

if __name__ == "__main__":
    start_server()
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        if server_instance:
            server_instance.cleanup()
