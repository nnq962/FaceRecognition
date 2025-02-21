from pymongo import MongoClient
from pathlib import Path
import os
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Tải biến môi trường từ `.env`
load_dotenv()

class Config:
    """ Class chứa toàn bộ cấu hình của ứng dụng """

    # Cấu hình MongoDB từ biến môi trường
    MONGODB_HOST = os.getenv("MONGODB_HOST", "127.0.0.1")  # Mặc định chạy local
    MONGODB_PORT = os.getenv("MONGODB_PORT", "27017")
    MONGODB_USERNAME = os.getenv("MONGODB_USERNAME", "root")
    MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD", "password")
    MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "my_database")

    init_database = True
    camera_names = []
    vram_limit_for_FER = 1

    # URI kết nối đến MongoDB
    MONGO_URI = f"mongodb://{MONGODB_USERNAME}:{MONGODB_PASSWORD}@{MONGODB_HOST}:{MONGODB_PORT}/{MONGODB_DATABASE}?authSource=admin"

    try:
        # Kết nối MongoDB
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[MONGODB_DATABASE]
        # Kiểm tra kết nối (chạy thử lệnh adminCommand)
        client.admin.command("ping")
        print("Kết nối MongoDB thành công!")
    except Exception as e:
        print(f"Lỗi kết nối MongoDB: {e}")
        db = None  # Đặt thành None nếu không kết nối được

    # Các collection
    users_collection = db["users"]
    managers_collection = db["managers"]
    camera_collection = db["camera_information"]
    data_collection = db["camera_data"]
    
    # Đường dẫn lưu file
    save_path = str(Path.home()) + "/nnq_static"

    # Chuyển đổi sang pathlib.Path để xử lý thư mục
    SAVE_PATH = Path(save_path)
    UPLOADS_PATH = SAVE_PATH / "uploads"
    DATABASE_PATH = SAVE_PATH / "data_base"

    # Tạo thư mục nếu chưa tồn tại
    for folder in [SAVE_PATH, UPLOADS_PATH, DATABASE_PATH]:
        Path(folder).mkdir(parents=True, exist_ok=True)

    def __init__(self):
        self.update_import()

    def get_vietnam_time(self):
        """Trả về thời gian hiện tại theo múi giờ Việt Nam (UTC+7) với định dạng YYYY-MM-DD HH:MM:SS."""
        vietnam_now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
        return vietnam_now.strftime("%Y-%m-%d %H:%M:%S")
    
    def get_ip_from_mac(self, mac_addresses):
        try:
            # Chạy lệnh `arp -a` để lấy danh sách các thiết bị trong mạng
            result = subprocess.check_output(['arp', '-a'], text=True)
            
            # Tạo dictionary để lưu kết quả
            mac_to_ip = {mac.lower(): None for mac in mac_addresses}
            
            # Duyệt qua các dòng trong kết quả để tìm địa chỉ MAC
            for line in result.splitlines():
                for mac in mac_to_ip.keys():
                    if mac in line.lower():
                        # Tách địa chỉ IP từ dòng chứa MAC
                        parts = line.split()
                        ip_address = [part for part in parts if "(" in part and ")" in part]
                        if ip_address:
                            mac_to_ip[mac] = ip_address[0].strip("()")  # Lấy địa chỉ IP
            return mac_to_ip
        except Exception as e:
            print(f"Error: {e}")
            return None

    def generate_rtsp_urls(self, mac_to_ip, credentials):
        rtsp_urls = []
        for mac, ip in mac_to_ip.items():
            if ip:
                # Lấy thông tin tài khoản từ credentials
                username, password = credentials.get(mac, ("", ""))
                rtsp_url = f"rtsp://{username}:{password}@{ip}:554/cam/realmonitor?channel=1&subtype=0"
                rtsp_urls.append(rtsp_url)
        return rtsp_urls

    def create_rtsp_urls_from_mongo(self, camera_ids):
        """
        Tạo danh sách RTSP URLs dựa trên danh sách _id của camera trong MongoDB.

        Args:
            camera_ids (list): Danh sách _id của các camera cần lấy RTSP URLs.

        Returns:
            list: Danh sách các URL RTSP tương ứng với các _id.
        """
        camera_collection = config.camera_collection

        # Truy vấn dữ liệu từ MongoDB với _id được cung cấp
        cameras = camera_collection.find(
            {"_id": {"$in": camera_ids}},
            {"MAC_address": 1, "user": 1, "password": 1, "camera_name": 1, "_id": 0}
        )
        credentials = {}
        mac_addresses = []

        # Lấy thông tin MAC address, user, và password
        for camera in cameras:
            mac = camera.get("MAC_address", "").lower()
            camera_name = camera.get("camera_name", "")
            user = camera.get("user", "")
            password = camera.get("password", "")
            if mac:
                credentials[mac] = (user, password)
                mac_addresses.append(mac)
            self.camera_names.append(camera_name)

        # Lấy IP từ MAC address
        mac_to_ip = self.get_ip_from_mac(mac_addresses)

        # Tạo đường dẫn RTSP
        rtsp_urls = self.generate_rtsp_urls(mac_to_ip, credentials)

        return rtsp_urls

    def update_import(self, file_path="/home/pc/.local/lib/python3.10/site-packages/basicsr/data/degradations.py"):
        # Đường dẫn tới tệp cần chỉnh sửa

        # Nội dung cũ và nội dung thay thế
        old_import = "from torchvision.transforms.functional_tensor import rgb_to_grayscale"
        new_import = "from torchvision.transforms.functional import rgb_to_grayscale"
        
        print("-" * 80)

        # Kiểm tra tệp có tồn tại không
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
        else:
            try:
                # Đọc nội dung tệp
                with open(file_path, "r") as file:
                    lines = file.readlines()

                # Thay thế nội dung
                updated_lines = [line.replace(old_import, new_import) for line in lines]

                # Ghi lại tệp với nội dung đã cập nhật
                with open(file_path, "w") as file:
                    file.writelines(updated_lines)
                    
                print(f"Successfully updated the import in {file_path}")
            except Exception as e:
                print(f"An error occurred: {e}")


# Tạo instance `config` để sử dụng trong toàn bộ project
config = Config()