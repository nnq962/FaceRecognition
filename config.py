from pymongo import MongoClient
from pathlib import Path
import os

class Config:
    """ Class chứa toàn bộ cấu hình của ứng dụng """
    
    # Cấu hình MongoDB
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    client = MongoClient(MONGO_URI)
    db = client["my_database"]

    # Các collection
    users_collection = db["users"]
    managers_collection = db["managers"]
    camera_collection = db["camera_information"]
    data_collection = db["camera_data"]
    

    # Đường dẫn lưu file
    save_path = Path.home() / "nnq_static"

# Tạo instance `config` để sử dụng trong toàn bộ project
config = Config()