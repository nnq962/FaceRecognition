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

    # Đường dẫn tới thư mục lưu ảnh
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    model_urls = {
        "det_10g.onnx": "https://drive.google.com/uc?id=1j47suEUpM6oNAgNvI5YnaLSeSnh1m45X",
        "w600k_r50.onnx": "https://drive.google.com/uc?id=1JKwOYResiJf7YyixHCizanYmvPrl1bP2"
    }

    faiss_data_folder = "faiss_data"
    
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
    list_classes = database["list_classes"]
    list_cameras = database["list_cameras"]
    list_boards = database["list_boards"]

    def __init__(self):
        self.update_path = self.find_file_in_anaconda("degradations.py")
        # self.update_import(file_path=self.update_path)
        self.prepare_models(model_urls=self.model_urls, save_dir="models")

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

# Tạo instance `config` để sử dụng trong toàn bộ project
config = Config()