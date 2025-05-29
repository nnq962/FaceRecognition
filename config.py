from pymongo import MongoClient
from pathlib import Path
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import sys
import gdown
from utils.logger_config import LOGGER
from dotenv import load_dotenv
from urllib.parse import quote_plus
# Load .env file
load_dotenv()


class Config:
    """ Class chứa toàn bộ cấu hình của ứng dụng """
    
    user = quote_plus(os.getenv("MONGODB_USERNAME"))
    password = quote_plus(os.getenv("MONGODB_PASSWORD"))
    host = os.getenv("MONGODB_HOST")
    port = os.getenv("MONGODB_PORT")
    database = os.getenv("MONGODB_DATABASE")

    init_database = False
    vram_limit_for_FER = 2
    camera_ids = []

    # Đường dẫn tới thư mục lưu ảnh
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    model_urls = {
    "det_10g.onnx": "https://drive.google.com/uc?id=1j47suEUpM6oNAgNvI5YnaLSeSnh1m45X",
    "w600k_r50.onnx": "https://drive.google.com/uc?id=1JKwOYResiJf7YyixHCizanYmvPrl1bP2"
    }

    ann_file = "ann_data/face_index.ann"
    mapping_file = "ann_data/annoy_mapping.npy"
    faiss_file = "faiss_data/face_index.faiss"
    faiss_mapping_file = "faiss_data/faiss_mapping.pkl"
    vector_dim = 512
    
    # Tạo MONGO_URI linh hoạt
    if user and password:
        MONGO_URI = f"mongodb://{user}:{password}@{host}:{port}/{database}"
    else:
        MONGO_URI = f"mongodb://{host}:{port}/"

    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        client.server_info()  # force MongoDB to connect and check authentication
        LOGGER.info("MongoDB connection established successfully")
    except Exception as e:
        LOGGER.error(f"MongoDB connection failed: {e}")

    database = client["face_recognition"]

    # Các collection
    user_collection = database["users"]
    admin_collection = database["edulive_admins"]
    camera_collection = database["cameras"]
    reports_collection = database["reports"]
    feedbacks_collection = database["feedbacks"]

    def __init__(self):
        self.update_path = self.find_file_in_anaconda("degradations.py")
        # self.update_import(file_path=self.update_path)
        self.prepare_models(model_urls=self.model_urls, save_dir="models")

    def get_rtsp_by_id(self, camera_id):
        camera = self.camera_collection.find_one(
            {"camera_id": camera_id},
            {"RTSP": 1, "_id": 0}
        )
        return camera["RTSP"] if camera else None
    
    def get_camera_name_by_id(self, camera_id):
        # Tìm document theo _id
        camera = self.camera_collection.find_one({"camera_id": camera_id}, {"name": 1, "_id": 0})
        return camera["name"] if camera else None

    def get_vietnam_time(self):
        vietnam_now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
        return vietnam_now.strftime("%Y-%m-%d %H:%M:%S")
    
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
            LOGGER.warning(f"File not found: {file_path}")
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
                    
                LOGGER.info(f"Successfully updated the import in {file_path}")
            except Exception as e:
                LOGGER.error(f"An error occurred: {e}")

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
                LOGGER.info(f"Model '{model_name}' already exists at '{model_path}'")
            else:
                LOGGER.info(f"Downloading model '{model_name}' from '{model_url}' to '{model_path}'...")
                try:
                    # Tải mô hình từ Google Drive
                    gdown.download(model_url, str(model_path), quiet=False)
                    LOGGER.info(f"Model '{model_name}' downloaded successfully")
                except Exception as e:
                    LOGGER.error(f"Failed to download model '{model_name}': {e}")

    def process_camera_input(self, sources):
        """
        Xử lý đầu vào camera từ danh sách nguồn ["WEBCAM", "CAM1", "CAM2"]

        Args:
            sources (List[str]): danh sách nguồn camera (ví dụ: ["WEBCAM", "CAM1", "CAM2"])

        Returns:
            str: '0' nếu chỉ có webcam, hoặc 'device.txt' nếu nhiều nguồn
        """
        if not isinstance(sources, list):
            raise ValueError("Sources phải là danh sách (list)")

        camera_sources = []

        for id in sources:
            id = id.strip().upper()
            if id == "WEBCAM":
                self.camera_ids.append(id)
                camera_sources.append("0")
                LOGGER.info("Camera initialized: WEBCAM [ID: 0]")
            else:
                # Truy vấn RTSP từ MongoDB
                camera_doc = self.camera_collection.find_one({"camera_id": id})
                if not camera_doc:
                    raise ValueError(f"Không tìm thấy camera_id '{id}' trong MongoDB")
                rtsp_url = camera_doc["RTSP"]
                camera_sources.append(rtsp_url)
                self.camera_ids.append(id)
                LOGGER.info(f"Camera initialized: {id} [RTSP: {rtsp_url}]")

        # Nếu chỉ có 1 camera → trả về luôn (dùng cho webcam hoặc 1 RTSP)
        if len(camera_sources) == 1:
            return camera_sources[0]

        # Nếu có nhiều → ghi ra file
        with open("device.txt", "w") as f:
            for cam in camera_sources:
                f.write(f"{cam}\n")

        LOGGER.info(f"Created device.txt file with {len(camera_sources)} camera sources")
        return "device.txt"

# Tạo instance `config` để sử dụng trong toàn bộ project
config = Config()