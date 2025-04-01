from pymongo import MongoClient
from pathlib import Path
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import sys
import gdown
from utils.logger_config import LOGGER
from dotenv import load_dotenv
# Load .env file
load_dotenv()


class Config:
    """ Class chứa toàn bộ cấu hình của ứng dụng """
    
    user = os.getenv("MONGODB_USERNAME")
    password = os.getenv("MONGODB_PASSWORD")
    host = os.getenv("MONGODB_HOST")
    port = os.getenv("MONGODB_PORT")
    database = os.getenv("MONGODB_DATABASE")

    init_database = False
    vram_limit_for_FER = 2
    camera_names = []
    save_path = str(Path.home()) + "/3hinc_database"

    model_urls = {
    "det_10g.onnx": "https://drive.google.com/uc?id=1j47suEUpM6oNAgNvI5YnaLSeSnh1m45X",
    "w600k_r50.onnx": "https://drive.google.com/uc?id=1JKwOYResiJf7YyixHCizanYmvPrl1bP2"
    }

    ann_file = "data_base/face_index.ann"
    mapping_file = "data_base/annoy_mapping.npy"
    faiss_file = "data_base/face_index.faiss"
    faiss_mapping_file = "data_base/faiss_mapping.pkl"
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

    db = client["my_database"]

    # Các collection
    users_collection = db["3hinc_users"]
    managers_collection = db["managers"]
    camera_collection = db["camera_information"]
    data_collection = db["3hinc_data"]

    SAVE_PATH = Path(save_path)
    UPLOADS_PATH = SAVE_PATH / "uploads"

    # Tạo thư mục nếu chưa tồn tại
    for folder in [SAVE_PATH, UPLOADS_PATH]:
        Path(folder).mkdir(parents=True, exist_ok=True)

    def __init__(self):
        self.update_path = self.find_file_in_anaconda("degradations.py")
        # self.update_import(file_path=self.update_path)
        self.prepare_models(model_urls=self.model_urls, save_dir="~/Models")

    def get_rtsp_by_id(self, camera_id):
        # Tìm document theo _id
        camera = self.camera_collection.find_one({"_id": camera_id}, {"RTSP": 1, "_id": 0})

        # Trả về đường dẫn RTSP hoặc None nếu không tìm thấy
        return camera["RTSP"] if camera else None
    
    def get_camera_name_by_id(self, camera_id):
        # Tìm document theo _id
        camera = self.camera_collection.find_one({"_id": camera_id}, {"camera_name": 1, "_id": 0})
        return camera["camera_name"] if camera else None

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

    def process_camera_input(self, source):
        """
        Xử lý đầu vào camera từ tham số --source.
        
        Args:
            source (str): Chuỗi chứa các ID camera, phân tách bởi dấu phẩy (ví dụ: "0,1,2") 
                        hoặc đường dẫn đến tệp device.txt
                        hoặc đường dẫn đến tệp media (video, hình ảnh)           
        Returns:
            str: Đường dẫn tới nguồn video hoặc tên tệp chứa đường dẫn các nguồn
        """
        # Kiểm tra nếu source là đường dẫn tới một tệp (không phải device.txt)
        if os.path.isfile(source) and not source.endswith('.txt'):
            LOGGER.info(f"Reading source from file: {source}")
            self.camera_names.append(os.path.basename(source))
            return source
        
        # Kiểm tra nếu source là tệp device.txt
        if source.endswith('.txt'):
            LOGGER.info(f"Reading camera source from file: {source}")
            
            # Kiểm tra xem tệp tồn tại
            if not os.path.exists(source):
                raise FileNotFoundError(f"File not found: {source}")
            
            # Đọc tệp và xử lý các nguồn camera
            with open(source, 'r') as f:
                lines = f.readlines()
            
            # Xử lý từng dòng trong tệp
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue  # Bỏ qua dòng trống hoặc bình luận
                    
                if line == "0":
                    self.camera_names.append("webcam")
                    LOGGER.info(f"Camera initialized: webcam [ID: 0]")
                elif line.startswith('rtsp://') or line.startswith('http://'):
                    # Nếu là đường dẫn RTSP/HTTP trực tiếp
                    self.camera_names.append(f"camera_{len(self.camera_names)}")
                    LOGGER.info(f"Camera initialized: camera_{len(self.camera_names)-1} [URL: {line}]")
                else:
                    try:
                        # Giả định là ID camera
                        camera_id = int(line)
                        rtsp_url = self.get_rtsp_by_id(camera_id)
                        camera_name = self.get_camera_name_by_id(camera_id)
                        self.camera_names.append(camera_name)
                        LOGGER.info(f"Camera initialized: {camera_name} [ID: {camera_id}, URL: {rtsp_url}]")
                    except ValueError:
                        LOGGER.warning(f"Warning: Unable to process camera source: {line}")
            
            return source
        
        # Tách chuỗi đầu vào thành danh sách các ID camera
        camera_ids = source.split(',')
        
        # Nếu chỉ có một camera
        if len(camera_ids) == 1:
            camera_id = camera_ids[0].strip()
            
            # Nếu camera là webcam (ID = 0)
            if camera_id == "0":
                self.camera_names.append("webcam")
                LOGGER.info("Camera initialized: webcam [ID: 0]")
                return "0"
            
            # Nếu camera là RTSP (ID > 0)
            else:
                try:
                    camera_id = int(camera_id)
                    rtsp_url = self.get_rtsp_by_id(camera_id)
                    camera_name = self.get_camera_name_by_id(camera_id)
                    self.camera_names.append(camera_name)
                    LOGGER.info(f"Camera initialized: {camera_name} [ID: {camera_id}, URL: {rtsp_url}]")
                    return rtsp_url
                except ValueError:
                    raise ValueError(f"Invalid camera ID: {camera_id}")
        
        # Nếu có nhiều camera
        else:
            # Tạo tệp device.txt chứa các đường dẫn camera
            with open("device.txt", "w") as f:
                for camera_id in camera_ids:
                    camera_id = camera_id.strip()
                    
                    if camera_id == "0":
                        f.write("0\n")
                        self.camera_names.append("webcam")
                        LOGGER.info("Camera initialized: webcam [ID: 0]")
                    else:
                        try:
                            camera_id = int(camera_id)
                            rtsp_url = self.get_rtsp_by_id(camera_id)
                            camera_name = self.get_camera_name_by_id(camera_id)
                            f.write(f"{rtsp_url}\n")
                            self.camera_names.append(camera_name)
                            LOGGER.info(f"Camera initialized: {camera_name} [ID: {camera_id}, URL: {rtsp_url}]")
                        except ValueError:
                            raise ValueError(f"Invalid camera ID: {camera_id}")
            
            LOGGER.info(f"Created device.txt file with {len(camera_ids)} camera sources")
            return "device.txt"

# Tạo instance `config` để sử dụng trong toàn bộ project
config = Config()