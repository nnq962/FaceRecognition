from pymongo import MongoClient
from pathlib import Path
import os
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
import sys
import gdown
import numpy as np
from annoy import AnnoyIndex

class Config:
    """ Class chứa toàn bộ cấu hình của ứng dụng """
    
    user = ""
    password = ""
    host = "localhost"
    port = "27017"
    database = ""
    init_database = False
    vram_limit_for_FER = 1
    camera_names = []
    save_path = str(Path.home()) + "/nnq_static"
    model_urls = {
    "det_10g.onnx": "https://drive.google.com/uc?id=1j47suEUpM6oNAgNvI5YnaLSeSnh1m45X",
    "w600k_r50.onnx": "https://drive.google.com/uc?id=1JKwOYResiJf7YyixHCizanYmvPrl1bP2",
    "GFPGANv1.3.pth": "https://drive.google.com/uc?id=1zmW9g7vaRWuFSUKIS9ShCmP-6WU6Xxan",
    "detection_Resnet50_Final.pth": "https://drive.google.com/uc?id=1jP3-UU8LhBvG8ArZQNl6kpDUfH_Xan9m",
    "parsing_parsenet.pth": "https://drive.google.com/uc?id=1ZFqra3Vs4i5fB6B8LkyBo_WQXaPRn77y",
    "yolov11-face.pt": "https://drive.google.com/uc?id=1Y6syEi7jMbRkiEC-4Wd5cqwOKWtiD2at"
    }
    ann_file = "face_index.ann"
    mapping_file = "annoy_mapping.npy"
    vector_dim = 512
    
    # Tạo MONGO_URI linh hoạt
    if user and password:
        MONGO_URI = f"mongodb://{user}:{password}@{host}:{port}/{database}"
    else:
        MONGO_URI = f"mongodb://{host}:{port}/"

    client = MongoClient(MONGO_URI)
    db = client["my_database"]

    # Các collection
    users_collection = db["users"]
    managers_collection = db["managers"]
    camera_collection = db["camera_information"]
    data_collection = db["camera_data"]

    SAVE_PATH = Path(save_path)
    UPLOADS_PATH = SAVE_PATH / "uploads"
    DATABASE_PATH = SAVE_PATH / "data_base"

    # Tạo thư mục nếu chưa tồn tại
    for folder in [SAVE_PATH, UPLOADS_PATH, DATABASE_PATH]:
        Path(folder).mkdir(parents=True, exist_ok=True)

    def __init__(self):
        self.annoy_index = None
        self.id_mapping = None
        print("-" * 80)
        self.update_path = self.find_file_in_anaconda("degradations.py")
        self.update_import(file_path=self.update_path)
        self.prepare_models(model_urls=self.model_urls, save_dir="~/Models")
        print("-" * 80)

    def get_vietnam_time(self):
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
    
    def search_file(self, filename, search_path):
        """Tìm tệp trong thư mục cụ thể."""
        for root, dirs, files in os.walk(search_path):
            if filename in files:
                return os.path.join(root, filename)
        return None

    def find_file_in_anaconda(self, filename):
        """
        Tìm kiếm tệp trong thư mục site-packages của môi trường Anaconda hiện tại.

        Args:
            filename (str): Tên tệp cần tìm.

        Returns:
            str | None: Đường dẫn đầy đủ đến tệp nếu tìm thấy, ngược lại trả về None.
        """
        # Lấy đường dẫn site-packages trong môi trường Anaconda hiện tại
        if hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix:
            # Nếu đang chạy trong môi trường ảo của Anaconda
            site_packages_path = os.path.join(sys.prefix, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
        else:
            # Nếu không, tìm site-packages mặc định
            import site
            site_packages_path = site.getsitepackages()[0]

        # Tìm tệp trong thư mục site-packages của môi trường hiện tại
        result = self.search_file(filename, site_packages_path)

        return result
    
    def update_import(self, file_path="/home/pc/.local/lib/python3.10/site-packages/basicsr/data/degradations.py"):
        # Đường dẫn tới tệp cần chỉnh sửa

        # Nội dung cũ và nội dung thay thế
        old_import = "from torchvision.transforms.functional_tensor import rgb_to_grayscale"
        new_import = "from torchvision.transforms.functional import rgb_to_grayscale"
        
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

    def prepare_models(self, model_urls, save_dir="~/Models"):
        """
        Kiểm tra và tải xuống các mô hình từ Google Drive nếu chưa tồn tại.

        Args:
            model_urls (dict): Từ điển chứa tên mô hình và URL Google Drive tương ứng.
                            Ví dụ: {"model1": "https://drive.google.com/uc?id=FILE_ID", ...}
        """
        # Chuẩn bị đường dẫn thư mục lưu trữ
        save_dir = os.path.expanduser(save_dir)
        os.makedirs(save_dir, exist_ok=True)

        for model_name, model_url in model_urls.items():
            # Đường dẫn lưu mô hình
            model_path = Path(save_dir) / model_name
            
            if model_path.exists():
                print(f"Model '{model_name}' already exists at '{model_path}'.")
            else:
                print(f"Downloading model '{model_name}' from '{model_url}' to '{model_path}'...")
                try:
                    # Tải mô hình từ Google Drive
                    gdown.download(model_url, str(model_path), quiet=False)
                    print(f"Model '{model_name}' downloaded successfully!")
                except Exception as e:
                    print(f"Failed to download model '{model_name}': {e}")

# Tạo instance `config` để sử dụng trong toàn bộ project
config = Config()
