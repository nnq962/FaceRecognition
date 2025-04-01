import socket
import os
import time
import json
import threading
from gtts import gTTS
import subprocess
from utils.logger_config import LOGGER

host = '192.168.1.142'

class NotificationClient:
    def __init__(self, host=host, port=9999, reconnect_interval=5):
        self.host = host
        self.port = port
        self.client_socket = None
        self.running = False
        self.connected = False
        self.reconnect_interval = reconnect_interval
        self.connection_lock = threading.Lock()  # Lock để truy cập an toàn tới socket

    def connect_to_server(self):
        """Kết nối tới server và trả về kết quả thành công/thất bại"""
        with self.connection_lock:
            # Đóng socket cũ nếu có
            if self.client_socket:
                try:
                    self.client_socket.close()
                except:
                    pass
                self.client_socket = None
            
            try:
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket.settimeout(10)  # Timeout kết nối
                self.client_socket.connect((self.host, self.port))
                # Thiết lập socket không chặn sau khi kết nối thành công
                self.client_socket.setblocking(0)
                self.connected = True
                LOGGER.info(f"Đã kết nối tới server {self.host}:{self.port}")
                return True
            except Exception as e:
                self.connected = False
                LOGGER.error(f"Không thể kết nối tới server: {e}")
                return False

    def reconnect_manager(self):
        """Quản lý việc kết nối lại tới server khi mất kết nối"""
        while self.running:
            if not self.connected:
                LOGGER.info(f"Đang thử kết nối lại sau {self.reconnect_interval} giây...")
                if self.connect_to_server():
                    LOGGER.info("Kết nối lại thành công!")
                else:
                    LOGGER.warning("Kết nối lại thất bại, sẽ thử lại sau...")
            
            time.sleep(self.reconnect_interval)

    def ping_server(self):
        """Gửi ping để giữ kết nối"""
        ping_interval = 15  # Gửi ping mỗi 15 giây
        
        while self.running:
            time.sleep(ping_interval)
            
            if self.connected:
                try:
                    with self.connection_lock:
                        if self.client_socket:
                            ping_message = json.dumps({"type": "ping"})
                            self.client_socket.send(ping_message.encode('utf-8'))
                except Exception as e:
                    LOGGER.warning(f"Lỗi khi ping server: {e}")
                    self.connected = False

    def play_audio(self, text):
        """Phát âm thanh từ text"""
        try:
            tts = gTTS(text=text, lang='vi')
            audio_file = "output.mp3"
            tts.save(audio_file)
            subprocess.run(['ffmpeg', '-i', audio_file, '-f', 'alsa', 'default'],
                         check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(audio_file):
                os.remove(audio_file)
            return True
        except Exception as e:
            LOGGER.error(f"Lỗi khi phát âm thanh: {e}")
            return False

    def process_message(self, data):
        """Xử lý thông điệp nhận được từ server"""
        try:
            # Kiểm tra xem có phải là JSON không
            try:
                message = json.loads(data)
                
                # Xử lý theo loại thông điệp
                if message.get("type") == "notification":
                    notification_text = message.get("message", "")
                    if notification_text:
                        LOGGER.info(f"Nhận được thông báo: '{notification_text}'")
                        self.play_audio(notification_text)
                
                elif message.get("type") == "pong":
                    # Đây là phản hồi ping, có thể bỏ qua
                    pass
                    
            except json.JSONDecodeError:
                # Không phải JSON, xử lý như thông báo bình thường
                LOGGER.info(f"Nhận được thông báo (legacy): {data}")
                self.play_audio(data)
                
        except Exception as e:
            LOGGER.error(f"Lỗi khi xử lý thông điệp: {e}")

    def listen_for_messages(self):
        """Lắng nghe và xử lý tin nhắn từ server"""
        buffer = ""
        
        while self.running:
            # Kiểm tra trạng thái kết nối trước
            if not self.connected:
                time.sleep(0.1)
                continue
                
            try:
                # Đọc dữ liệu từ socket (không chặn)
                try:
                    with self.connection_lock:
                        if self.client_socket:
                            chunk = self.client_socket.recv(1024).decode('utf-8')
                            if not chunk:  # Kết nối đã đóng
                                LOGGER.error("Mất kết nối với server")
                                self.connected = False
                                continue
                            
                            buffer += chunk
                except BlockingIOError:
                    # Socket không chặn, không có dữ liệu
                    time.sleep(0.1)
                    continue
                    
                # Xử lý buffer
                if buffer:
                    # Tìm các thông điệp hoàn chỉnh dựa trên JSON
                    while buffer:
                        # Nếu buffer có dấu hiệu là JSON
                        if buffer.startswith("{") and "}" in buffer:
                            end_pos = buffer.find("}") + 1
                            message = buffer[:end_pos]
                            buffer = buffer[end_pos:]
                            self.process_message(message)
                        else:
                            # Thử xử lý như thông điệp văn bản thông thường
                            if "\n" in buffer:
                                end_pos = buffer.find("\n")
                                message = buffer[:end_pos]
                                buffer = buffer[end_pos+1:]
                                self.process_message(message)
                            else:
                                # Không tìm thấy kí tự kết thúc, giữ buffer để đợi dữ liệu tiếp theo
                                self.process_message(buffer)
                                buffer = ""
                
            except (ConnectionResetError, BrokenPipeError):
                LOGGER.error("Kết nối bị đặt lại bởi server")
                self.connected = False
            except Exception as e:
                LOGGER.error(f"Lỗi khi nhận thông báo: {e}")
                self.connected = False

    def start(self):
        """Khởi động client và các luồng xử lý"""
        self.running = True
        
        # Kết nối lần đầu
        self.connect_to_server()
        
        # Khởi động luồng quản lý kết nối lại
        reconnect_thread = threading.Thread(target=self.reconnect_manager, daemon=True)
        reconnect_thread.start()
        
        # Khởi động luồng ping
        ping_thread = threading.Thread(target=self.ping_server, daemon=True)
        ping_thread.start()
        
        # Luồng lắng nghe thông báo
        listen_thread = threading.Thread(target=self.listen_for_messages, daemon=True)
        listen_thread.start()
        
        LOGGER.info("Client đã khởi động đầy đủ")
        
        return self

    def stop(self):
        """Dừng client và dọn dẹp tài nguyên"""
        self.running = False
        
        with self.connection_lock:
            if self.client_socket:
                try:
                    self.client_socket.close()
                except:
                    pass
                self.client_socket = None
        
        self.connected = False
        LOGGER.info("Client đã dừng")

def run_client(host=host, port=9999):
    """Hàm trợ giúp để chạy client"""
    client = NotificationClient(host, port)
    client.start()
    
    try:
        # Giữ tiến trình chính chạy
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        LOGGER.info("Nhận tín hiệu ngắt, đang dừng client...")
    finally:
        client.stop()

if __name__ == "__main__":
    run_client()