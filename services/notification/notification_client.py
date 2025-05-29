import socket
import os
import time
import json
import threading
import hashlib
import argparse
import queue
from gtts import gTTS
import subprocess
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils.logger_config import LOGGER
import yaml  # Thêm import yaml

# Đường dẫn đến file cấu hình
CONFIG_FILE = "config.yaml"  # Thay đổi từ main_config.json sang config.yaml

# Cấu hình mặc định
DEFAULT_HOST = '192.168.1.142'
DEFAULT_PORT = 9624

class NotificationClient:
    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT, reconnect_interval=5):
        self.host = host
        self.port = port
        self.client_socket = None
        self.running = False
        self.connected = False
        self.reconnect_interval = reconnect_interval
        self.connection_lock = threading.Lock()  # Lock để truy cập an toàn tới socket
        
        # Thêm hàng đợi thông báo để xử lý tuần tự
        self.notification_queue = queue.Queue()
        self.processing_notification = False
        self.notification_event = threading.Event()
        
        # Thư mục lưu trữ cache âm thanh
        self.audio_cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio_cache")
        # Tạo thư mục cache nếu chưa tồn tại
        if not os.path.exists(self.audio_cache_dir):
            os.makedirs(self.audio_cache_dir)
            LOGGER.info(f"Đã tạo thư mục cache âm thanh: {self.audio_cache_dir}")
        
        # Đường dẫn đến tệp metadata quản lý cache
        self.cache_metadata_path = os.path.join(self.audio_cache_dir, "cache_metadata.json")
        # Tải hoặc khởi tạo metadata
        self.cache_metadata = self.load_cache_metadata()
        # Lock để truy cập an toàn vào metadata
        self.metadata_lock = threading.Lock()
        
        # Kiểm tra xem SoX đã được cài đặt chưa
        self._check_sox_installation()

    def _check_sox_installation(self):
        """Kiểm tra xem SoX đã được cài đặt chưa"""
        try:
            subprocess.run(['sox', '--version'], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL, 
                         check=True)
            LOGGER.info("SoX đã được cài đặt và sẵn sàng sử dụng")
        except (subprocess.SubprocessError, FileNotFoundError):
            LOGGER.warning("SoX không được tìm thấy. Vui lòng cài đặt SoX để phát âm thanh.")
            LOGGER.warning("Trên Ubuntu/Debian: sudo apt install sox libsox-fmt-all")
            LOGGER.warning("Trên Fedora: sudo dnf install sox sox-plugins-all")
            LOGGER.warning("Trên Arch Linux: sudo pacman -S sox")

    def load_cache_metadata(self):
        """Tải metadata của cache từ tệp JSON"""
        try:
            if os.path.exists(self.cache_metadata_path):
                with open(self.cache_metadata_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {}
        except Exception as e:
            LOGGER.error(f"Lỗi khi tải metadata cache: {e}")
            return {}

    def save_cache_metadata(self):
        """Lưu metadata của cache vào tệp JSON"""
        try:
            with open(self.cache_metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.cache_metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            LOGGER.error(f"Lỗi khi lưu metadata cache: {e}")

    def update_cache_metadata(self, file_hash, text):
        """Cập nhật metadata cho một tệp cache"""
        with self.metadata_lock:
            current_time = time.time()
            readable_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(current_time))
            
            if file_hash in self.cache_metadata:
                # Cập nhật tệp đã tồn tại
                self.cache_metadata[file_hash]["last_used"] = current_time
                self.cache_metadata[file_hash]["last_used_readable"] = readable_time
                self.cache_metadata[file_hash]["use_count"] += 1
            else:
                # Thêm tệp mới
                self.cache_metadata[file_hash] = {
                    "text": text,
                    "created": current_time,
                    "created_readable": readable_time,
                    "last_used": current_time,
                    "last_used_readable": readable_time,
                    "use_count": 1
                }
            
            # Lưu metadata sau khi cập nhật
            self.save_cache_metadata()

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

    def get_audio_file_path(self, text):
        """Tạo tên file dựa trên nội dung của thông báo"""
        # Chuẩn hóa văn bản (chuyển thành chữ thường) trước khi tạo hash để đảm bảo
        # các phiên bản khác nhau về chữ hoa/thường sẽ sử dụng cùng một tệp audio
        normalized_text = text.lower()
        # Sử dụng MD5 hash để tạo tên file duy nhất cho mỗi câu thông báo
        text_hash = hashlib.md5(normalized_text.encode('utf-8')).hexdigest()
        return text_hash, os.path.join(self.audio_cache_dir, f"{text_hash}.mp3")

    def play_audio(self, text):
        """Phát âm thanh từ text với caching thông minh sử dụng SoX"""
        try:
            text_hash, audio_file_path = self.get_audio_file_path(text)
            
            # Kiểm tra xem file âm thanh đã tồn tại trong cache chưa
            if not os.path.exists(audio_file_path):
                LOGGER.info(f"Tạo file âm thanh mới cho: '{text}'")
                # Tạo file âm thanh mới nếu chưa có trong cache
                tts = gTTS(text=text, lang='vi')
                tts.save(audio_file_path)
            else:
                LOGGER.info(f"Sử dụng file âm thanh từ cache cho: '{text}'")
            
            # Cập nhật metadata
            self.update_cache_metadata(text_hash, text)
            
            # Thời gian bắt đầu để đo hiệu suất
            start_time = time.time()
            
            # Phát âm thanh sử dụng SoX (lệnh 'play')
            # -q: quiet mode (không hiển thị thông báo)
            # -V0: không hiển thị các chi tiết xử lý
            # -d: device mặc định
            play_command = ['play', '-q', '-V0', audio_file_path]
            
            LOGGER.info(f"Bắt đầu phát âm thanh lúc: {time.strftime('%H:%M:%S.%f')[:-3]}")
            subprocess.run(play_command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Tính thời gian phát
            play_duration = time.time() - start_time
            LOGGER.info(f"Kết thúc phát âm thanh lúc: {time.strftime('%H:%M:%S.%f')[:-3]}")
            LOGGER.info(f"Tổng thời gian phát: {play_duration:.3f} giây")
            
            return True
        except subprocess.SubprocessError as e:
            LOGGER.error(f"Lỗi khi phát âm thanh với SoX: {e}")
            # Thử phương pháp dự phòng với ffmpeg nếu SoX thất bại
            try:
                LOGGER.warning("Đang thử phương pháp dự phòng với ffmpeg...")
                subprocess.run(['ffmpeg', '-i', audio_file_path, '-f', 'alsa', 'default'],
                             check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except Exception as ffmpeg_error:
                LOGGER.error(f"Phương pháp dự phòng cũng thất bại: {ffmpeg_error}")
                return False
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
                        # Thêm thông báo vào hàng đợi thay vì phát ngay lập tức
                        self.add_to_notification_queue(notification_text)
                
                elif message.get("type") == "pong":
                    # Đây là phản hồi ping, có thể bỏ qua
                    pass
                    
            except json.JSONDecodeError:
                # Không phải JSON, xử lý như thông báo bình thường
                LOGGER.info(f"Nhận được thông báo (legacy): '{data}'")
                # Thêm thông báo vào hàng đợi thay vì phát ngay lập tức
                self.add_to_notification_queue(data)
                
        except Exception as e:
            LOGGER.error(f"Lỗi khi xử lý thông điệp: {e}")

    def add_to_notification_queue(self, notification_text):
        """Thêm thông báo vào hàng đợi và kích hoạt sự kiện xử lý"""
        self.notification_queue.put(notification_text)
        LOGGER.info(f"Đã thêm thông báo vào hàng đợi: '{notification_text}'")
        
        # Thông báo cho luồng xử lý hàng đợi
        self.notification_event.set()
    
    def notification_processor(self):
        """Luồng xử lý các thông báo từ hàng đợi tuần tự"""
        LOGGER.info("Khởi động luồng xử lý hàng đợi thông báo")
        
        while self.running:
            # Đợi cho đến khi có thông báo mới hoặc timeout
            self.notification_event.wait(timeout=1.0)
            
            # Kiểm tra xem có thông báo nào trong hàng đợi không
            if not self.notification_queue.empty():
                try:
                    # Lấy thông báo tiếp theo từ hàng đợi
                    notification_text = self.notification_queue.get(block=False)
                    
                    # Số lượng thông báo còn lại trong hàng đợi
                    remaining = self.notification_queue.qsize()
                    if remaining > 0:
                        LOGGER.info(f"Đang xử lý thông báo, còn {remaining} thông báo trong hàng đợi")
                    
                    # Đánh dấu đang xử lý
                    self.processing_notification = True
                    
                    # Phát âm thanh
                    self.play_audio(notification_text)
                    
                    # Đánh dấu hoàn thành
                    self.notification_queue.task_done()
                    self.processing_notification = False
                    
                except queue.Empty:
                    # Hàng đợi trống (có thể do đã được xử lý bởi luồng khác)
                    pass
                except Exception as e:
                    LOGGER.error(f"Lỗi khi xử lý thông báo từ hàng đợi: {e}")
                    # Đánh dấu hoàn thành để tránh bị treo
                    try:
                        self.notification_queue.task_done()
                    except:
                        pass
                    self.processing_notification = False
            
            # Reset sự kiện nếu hàng đợi đã trống
            if self.notification_queue.empty():
                self.notification_event.clear()

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

    def clean_cache(self, max_age_days=30, min_uses=1):
        """Dọn dẹp cache thông minh dựa trên thời gian và tần suất sử dụng"""
        with self.metadata_lock:
            current_time = time.time()
            max_age_seconds = max_age_days * 24 * 60 * 60
            files_to_remove = []
            
            # Xác định các tệp cần xóa
            for file_hash, metadata in self.cache_metadata.items():
                file_path = os.path.join(self.audio_cache_dir, f"{file_hash}.mp3")
                if not os.path.exists(file_path):
                    # Tệp đã bị xóa bên ngoài, đánh dấu để xóa khỏi metadata
                    files_to_remove.append(file_hash)
                    continue
                
                # Kiểm tra tuổi tệp và tần suất sử dụng
                age_seconds = current_time - metadata["last_used"]
                use_count = metadata["use_count"]
                
                # Chỉ xóa tệp nếu không được sử dụng trong thời gian dài
                if age_seconds > max_age_seconds:
                    try:
                        os.remove(file_path)
                        files_to_remove.append(file_hash)
                        LOGGER.info(f"Đã xóa file cache: {file_hash}.mp3 - "
                                     f"(Tuổi: {age_seconds/86400:.1f} ngày, Số lần sử dụng: {use_count})")
                    except Exception as e:
                        LOGGER.error(f"Lỗi khi xóa file cache {file_hash}.mp3: {e}")
            
            # Cập nhật metadata
            for file_hash in files_to_remove:
                del self.cache_metadata[file_hash]
            
            # Lưu metadata đã cập nhật
            self.save_cache_metadata()
            
            if files_to_remove:
                LOGGER.info(f"Đã xóa {len(files_to_remove)} file âm thanh khỏi cache")
                
            # Kiểm tra và xóa các tệp âm thanh không có trong metadata
            for filename in os.listdir(self.audio_cache_dir):
                if filename == "cache_metadata.json":
                    continue
                    
                if filename.endswith(".mp3"):
                    file_hash = filename[:-4]  # Bỏ phần .mp3
                    if file_hash not in self.cache_metadata:
                        try:
                            file_path = os.path.join(self.audio_cache_dir, filename)
                            os.remove(file_path)
                            LOGGER.info(f"Đã xóa file cache không có metadata: {filename}")
                        except Exception as e:
                            LOGGER.error(f"Lỗi khi xóa file không có metadata {filename}: {e}")

    def get_cache_stats(self):
        """Lấy thống kê về cache hiện tại"""
        with self.metadata_lock:
            total_files = len(self.cache_metadata)
            total_size = 0
            most_used = []
            recently_used = []
            
            # Tính kích thước và lấy thông tin các tệp
            for file_hash, metadata in self.cache_metadata.items():
                file_path = os.path.join(self.audio_cache_dir, f"{file_hash}.mp3")
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    total_size += file_size
                    
                    # Lưu thông tin để sắp xếp sau
                    most_used.append((metadata["text"], metadata["use_count"]))
                    recently_used.append((metadata["text"], metadata["last_used"]))
            
            # Sắp xếp theo số lần sử dụng (giảm dần)
            most_used.sort(key=lambda x: x[1], reverse=True)
            most_used = most_used[:5]  # Lấy 5 tệp được sử dụng nhiều nhất
            
            # Sắp xếp theo thời gian sử dụng gần đây nhất (giảm dần)
            recently_used.sort(key=lambda x: x[1], reverse=True)
            recently_used = [(text, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))) 
                             for text, ts in recently_used[:5]]  # Lấy 5 tệp sử dụng gần đây nhất
            
            return {
                "total_files": total_files,
                "total_size_mb": total_size / (1024 * 1024),
                "most_used": most_used,
                "recently_used": recently_used
            }

    def get_queue_stats(self):
        """Lấy thống kê về hàng đợi thông báo hiện tại"""
        queue_size = self.notification_queue.qsize()
        is_processing = self.processing_notification
        
        return {
            "queue_size": queue_size,
            "is_processing": is_processing
        }

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
        
        # Luồng xử lý hàng đợi thông báo
        queue_processor_thread = threading.Thread(target=self.notification_processor, daemon=True)
        queue_processor_thread.start()
        
        LOGGER.info("Client đã khởi động đầy đủ")
        
        return self

    def stop(self):
        """Dừng client và dọn dẹp tài nguyên"""
        self.running = False
        
        # Đảm bảo thức dậy các luồng đang đợi
        self.notification_event.set()
        
        with self.connection_lock:
            if self.client_socket:
                try:
                    self.client_socket.close()
                except:
                    pass
                self.client_socket = None
        
        self.connected = False
        LOGGER.info("Client đã dừng")

def run_client(host=DEFAULT_HOST, port=DEFAULT_PORT):
    """Hàm trợ giúp để chạy client"""
    client = NotificationClient(host, port)
    
    # Dọn dẹp cache cũ khi khởi động
    client.clean_cache()
    
    # Hiển thị thống kê cache
    stats = client.get_cache_stats()
    LOGGER.info(f"Thống kê cache: {stats['total_files']} tệp, "
               f"{stats['total_size_mb']:.2f}MB")
    
    client.start()
    
    try:
        # Kiểm tra và báo cáo trạng thái hàng đợi mỗi phút
        check_interval = 60  # Giây
        clean_interval = 7 * 24 * 60 * 60  # 1 tuần
        last_clean_time = time.time()
        
        while True:
            time.sleep(check_interval)
            
            # Kiểm tra trạng thái hàng đợi
            queue_stats = client.get_queue_stats()
            if queue_stats["queue_size"] > 0:
                LOGGER.info(f"Trạng thái hàng đợi: {queue_stats['queue_size']} thông báo đang chờ xử lý")
                if queue_stats["is_processing"]:
                    LOGGER.info("Đang xử lý thông báo hiện tại")
                else:
                    LOGGER.info("Không có thông báo nào đang được xử lý")
            
            # Dọn dẹp cache định kỳ
            current_time = time.time()
            if current_time - last_clean_time >= clean_interval:
                LOGGER.info("Thực hiện dọn dẹp cache định kỳ")
                client.clean_cache()
                last_clean_time = current_time
                
                # Hiển thị thống kê cache sau khi dọn dẹp
                stats = client.get_cache_stats()
                LOGGER.info(f"Thống kê cache sau khi dọn dẹp: {stats['total_files']} tệp, "
                           f"{stats['total_size_mb']:.2f}MB")
                
    except KeyboardInterrupt:
        LOGGER.info("Nhận tín hiệu ngắt, đang dừng client...")
    finally:
        client.stop()

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
    parser = argparse.ArgumentParser(description='Notification Client')
    parser.add_argument('--config', type=str, required=True, help='Configuration profile to use (e.g., 3HINC, EDULIVE)')
    
    args = parser.parse_args()
    config_name = args.config
    
    # Đọc file cấu hình
    config = load_config(config_name)
    if config is None:
        sys.exit(1)
    
    host = config.get("host", DEFAULT_HOST)
    port = config.get("noti_port", DEFAULT_PORT)
    
    LOGGER.info(f"Loaded configuration for '{config_name}'")
    LOGGER.info(f"Host: {host}, Port: {port}")
    
    # Khởi động client
    run_client(host=host, port=port)