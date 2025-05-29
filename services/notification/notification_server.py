import socket
import time
import threading
import json
import yaml
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils.logger_config import LOGGER
import argparse
import sys

# Đường dẫn đến file cấu hình
CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'config.yaml'))

# Đọc cấu hình mặc định - được sử dụng nếu không chỉ định config hoặc không tìm thấy
DEFAULT_HOST = '192.168.1.142'
DEFAULT_PORT = 14678
DEFAULT_CONTROL_PORT = 14679
ALLOWED_IPS = []
SECRET_KEY = "3hinc14679"


class NotificationServer:
    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT, control_port=DEFAULT_CONTROL_PORT):
        self.host = host
        self.port = port
        self.control_port = control_port
        self.server_socket = None
        self.control_socket = None
        self.clients = []  # Danh sách các kết nối client
        self.clients_lock = threading.Lock()  # Lock để truy cập an toàn vào danh sách clients
        self.running = False
        self.setup_server()
        self.setup_control()

    def setup_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Thêm timeout để không chặn vô hạn
            self.server_socket.settimeout(1.0)
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
            # Thêm timeout để không chặn vô hạn
            self.control_socket.settimeout(1.0)
            host_ip = socket.gethostbyname(self.host)
            self.control_socket.bind((host_ip, self.control_port))
            self.control_socket.listen(5)
            LOGGER.info(f"Control socket đang lắng nghe tại {(host_ip, self.control_port)}")
        except Exception as e:
            LOGGER.error(f"Lỗi khi thiết lập control socket: {e}")
            self.cleanup()
            raise

    def accept_clients(self):        
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                client_ip = addr[0]
                
                # Kiểm tra xem IP có được phép không
                if ALLOWED_IPS and client_ip not in ALLOWED_IPS:
                    LOGGER.warning(f"Từ chối kết nối từ IP không được phép: {addr}")
                    client_socket.close()
                    continue
                    
                # Thiết lập socket không chặn
                client_socket.setblocking(0)
                
                with self.clients_lock:
                    self.clients.append({"socket": client_socket, "address": addr, "last_ping": time.time()})
                
                LOGGER.info(f"Kết nối mới từ client: {addr}")
                
                # Tạo thread mới để xử lý client
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, addr),
                    daemon=True
                )
                client_thread.start()
            except socket.timeout:
                # Bỏ qua timeout, tiếp tục vòng lặp
                continue
            except Exception as e:
                if self.running:
                    LOGGER.error(f"Lỗi khi chấp nhận client: {e}")
                    time.sleep(1)  # Tránh loop quá nhanh khi có lỗi

    def handle_client(self, client_socket, addr):
        """Xử lý kết nối từ một client cụ thể"""
        client_active = True
        
        while self.running and client_active:
            try:
                # Kiểm tra xem client này còn trong danh sách không
                with self.clients_lock:
                    client_exists = any(client["socket"] == client_socket for client in self.clients)
                
                if not client_exists:
                    LOGGER.info(f"Client {addr} đã bị xóa bởi tiến trình khác")
                    break
                
                # Cố gắng đọc dữ liệu (non-blocking)
                try:
                    data = client_socket.recv(1024).decode('utf-8')
                    if not data:  # Kết nối đã đóng
                        client_active = False
                        LOGGER.info(f"Client {addr} đã đóng kết nối")
                        self.remove_client(client_socket)
                        break
                        
                    # Xử lý thông tin từ client (ví dụ: message ping)
                    try:
                        message = json.loads(data)
                        if message.get("type") == "ping":
                            # Cập nhật thời gian ping
                            self.update_client_ping(client_socket)
                            # Gửi lại pong
                            client_socket.send(json.dumps({"type": "pong"}).encode('utf-8'))
                    except json.JSONDecodeError:
                        # Không phải JSON, có thể là message khác
                        pass
                except BlockingIOError:
                    # Socket không chặn, không có dữ liệu
                    pass
                except OSError as e:
                    if e.errno == 9:  # Bad file descriptor
                        client_active = False
                        LOGGER.info(f"Client {addr} socket đã bị đóng")
                        self.remove_client(client_socket)
                        break
                    raise  # Ném lại lỗi khác
                
                time.sleep(0.1)  # Giảm tải CPU
            except (ConnectionResetError, BrokenPipeError):
                LOGGER.info(f"Client {addr} đã ngắt kết nối")
                self.remove_client(client_socket)
                break
            except Exception as e:
                LOGGER.error(f"Lỗi khi xử lý client {addr}: {e}")
                self.remove_client(client_socket)
                break

    def update_client_ping(self, client_socket):
        """Cập nhật thời gian ping cuối cùng cho client"""
        with self.clients_lock:
            for client in self.clients:
                if client["socket"] == client_socket:
                    client["last_ping"] = time.time()
                    break

    def check_clients_alive(self):
        """Kiểm tra và xóa các client không hoạt động"""
        while self.running:
            time.sleep(30)  # Kiểm tra mỗi 30 giây
            current_time = time.time()
            with self.clients_lock:
                clients_to_remove = []
                for client in self.clients:
                    # Nếu client không ping trong 60 giây, coi như đã ngắt kết nối
                    if current_time - client["last_ping"] > 60:
                        clients_to_remove.append(client)
                
                for client in clients_to_remove:
                    try:
                        # Đánh dấu socket đã bị đóng trước khi thực sự đóng nó
                        socket_to_close = client["socket"]
                        # Xóa khỏi danh sách trước khi đóng để tránh race condition
                        self.clients.remove(client)
                        socket_to_close.close()
                    except Exception as e:
                        pass
                    LOGGER.info(f"Đã xóa client không hoạt động: {client['address']}")

    def remove_client(self, client_socket):
        """Xóa client khỏi danh sách"""
        with self.clients_lock:
            for client in self.clients[:]:
                if client["socket"] == client_socket:
                    try:
                        client["socket"].close()
                    except:
                        pass
                    self.clients.remove(client)
                    break

    def send_notification(self, message):
        """Gửi thông báo tới tất cả clients đã kết nối"""
        payload = json.dumps({"type": "notification", "message": message})
        successful_sends = 0
        
        with self.clients_lock:
            if not self.clients:
                LOGGER.info("Không có client nào kết nối")
                return False
            
            clients_to_remove = []
            for client in self.clients:
                try:
                    client["socket"].send(payload.encode('utf-8'))
                    successful_sends += 1
                except (ConnectionResetError, BrokenPipeError):
                    LOGGER.info(f"Client {client['address']} đã ngắt kết nối")
                    clients_to_remove.append(client)
                except Exception as e:
                    LOGGER.error(f"Lỗi khi gửi thông báo tới {client['address']}: {e}")
                    clients_to_remove.append(client)
            
            # Xóa các client không hoạt động
            for client in clients_to_remove:
                try:
                    client["socket"].close()
                except:
                    pass
                self.clients.remove(client)
        
        if successful_sends > 0:
            LOGGER.info(f"Đã gửi thông báo '{message}' tới {successful_sends}/{len(self.clients) + len(clients_to_remove)} clients")
            return True
        return False

    def handle_control(self):
        """Xử lý các kết nối từ control socket"""        
        while self.running:
            try:
                control_client, addr = self.control_socket.accept()
                try:
                    data = control_client.recv(1024).decode('utf-8')
                    if data:
                        # Kiểm tra xem có phải format JSON không
                        try:
                            message_data = json.loads(data)
                            # Kiểm tra secret key
                            if message_data.get('key') == SECRET_KEY:
                                # Nếu key hợp lệ, gửi thông báo
                                self.send_notification(message_data.get('message', ''))
                            else:
                                LOGGER.warning(f"Từ chối yêu cầu gửi thông báo với key không hợp lệ từ {addr}")
                        except json.JSONDecodeError:
                            LOGGER.warning(f"Từ chối yêu cầu không hợp lệ từ {addr}: không phải định dạng JSON")
                except UnicodeDecodeError:
                    LOGGER.warning(f"Từ chối yêu cầu không hợp lệ từ {addr}: không thể giải mã UTF-8")
                    
                control_client.close()
            except socket.timeout:
                # Bỏ qua timeout, tiếp tục vòng lặp
                continue
            except Exception as e:
                if self.running:
                    LOGGER.error(f"Lỗi khi xử lý control: {e}")

    def cleanup(self):
        """Dọn dẹp tài nguyên khi đóng server"""
        self.running = False
        
        # Đóng tất cả các kết nối client
        with self.clients_lock:
            for client in self.clients:
                try:
                    client["socket"].close()
                except:
                    pass
            self.clients.clear()
        
        # Đóng server sockets
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        if self.control_socket:
            try:
                self.control_socket.close()
            except:
                pass
        
        LOGGER.info("Đã đóng tất cả kết nối")

    def run(self):
        """Khởi chạy server với các luồng xử lý"""
        self.running = True
        
        # Thread chấp nhận clients
        accept_thread = threading.Thread(target=self.accept_clients, daemon=True)
        accept_thread.start()
        
        # Thread xử lý control
        control_thread = threading.Thread(target=self.handle_control, daemon=True)
        control_thread.start()
        
        # Thread kiểm tra clients còn sống
        check_alive_thread = threading.Thread(target=self.check_clients_alive, daemon=True)
        check_alive_thread.start()
        
        LOGGER.info("Server đã khởi động đầy đủ")
        
        # Quản lý các luồng và trạng thái ứng dụng
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            LOGGER.info("Nhận tín hiệu ngắt, đang dừng server...")
            self.cleanup()

# Instance toàn cục
server_instance = None

def start_server(host=DEFAULT_HOST, port=DEFAULT_PORT, control_port=DEFAULT_CONTROL_PORT):
    """Khởi động server"""
    global server_instance
    if server_instance is None or not server_instance.running:
        server_instance = NotificationServer(host, port, control_port)
        server_thread = threading.Thread(target=server_instance.run, daemon=True)
        server_thread.start()
        time.sleep(1)
        LOGGER.info("Server đã khởi động")
    return server_instance

def stop_server():
    """Dừng server"""
    global server_instance
    if server_instance and server_instance.running:
        server_instance.cleanup()
        server_instance = None
        LOGGER.info("Server đã dừng")

def send_notification(message, host=DEFAULT_HOST, control_port=DEFAULT_CONTROL_PORT, secret_key="your_secret_key_here"):
    """Gửi thông báo tới control socket của server"""
    try:
        control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Thiết lập timeout để không chặn quá lâu
        control_socket.settimeout(5)
        control_socket.connect((host, control_port))
        
        # Đóng gói message với secret key
        message_data = json.dumps({
            'key': secret_key,
            'message': message
        })
        
        control_socket.send(message_data.encode('utf-8'))
        control_socket.close()
        return True
    except Exception as e:
        LOGGER.error(f"Lỗi khi gửi thông báo '{message}' tới server: {e}")
        return False

def get_server_status():
    """Kiểm tra trạng thái server"""
    global server_instance
    if server_instance and server_instance.running:
        with server_instance.clients_lock:
            client_count = len(server_instance.clients)
        return {"running": True, "client_count": client_count}
    return {"running": False, "client_count": 0}

def load_config(config_name=None, config_file=CONFIG_FILE):
    """
    Tải cấu hình từ file YAML
    
    Args:
        config_name (str, optional): Tên cấu hình cần tải, nếu để None sẽ tải toàn bộ
        config_file (str, optional): Đường dẫn file cấu hình. Mặc định là CONFIG_FILE
        
    Returns:
        dict: Cấu hình được tải
    """
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            all_configs = yaml.safe_load(f)
            
            if config_name is None:
                return all_configs
            elif config_name in all_configs:
                return all_configs[config_name]
            else:
                available_configs = ", ".join(all_configs.keys())
                LOGGER.error(f"Không tìm thấy cấu hình '{config_name}'. Các cấu hình có sẵn: {available_configs}")
                return None
    except Exception as e:
        LOGGER.error(f"Lỗi khi đọc file cấu hình: {e}")
        return None

if __name__ == "__main__":
    # Thiết lập parser tham số dòng lệnh - chỉ nhận một tham số config
    parser = argparse.ArgumentParser(description='Notification Server')
    parser.add_argument('--config', type=str, required=True, help='Configuration profile to use (e.g., 3HINC, EDULIVE)')
    
    args = parser.parse_args()
    config_name = args.config
    
    # Đọc file cấu hình
    config = load_config(config_name)
    if config is None:
        sys.exit(1)
    
    host = config.get("host", DEFAULT_HOST)
    port = config.get("noti_port", DEFAULT_PORT)
    control_port = config.get("noti_control_port", DEFAULT_CONTROL_PORT)
    allowed_ips = config.get("noti_allowed_ips", ALLOWED_IPS)
    secret_key = config.get("noti_secret_key", SECRET_KEY)
    
    LOGGER.info(f"Loaded configuration for '{config_name}'")
    LOGGER.info(f"Host: {host}, Port: {port}, Control Port: {control_port}")
    LOGGER.info(f"Allowed IPs: {', '.join(allowed_ips) if allowed_ips else 'All'}")
    
    # Cập nhật biến toàn cục
    ALLOWED_IPS = allowed_ips
    SECRET_KEY = secret_key
    
    # Khởi động server
    start_server(host=host, port=port, control_port=control_port)
    
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        if server_instance:
            server_instance.cleanup()
        LOGGER.info("\nServer stopped")