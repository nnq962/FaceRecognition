from api_config import api
from database_config import config
from utils.logger_config import LOGGER
from datetime import datetime
from pymongo import ReplaceOne
import os
import requests
from zoneinfo import ZoneInfo
import math
import numpy as np
import faiss
import pickle
from insightface_utils import get_embedding
from utils.onvif_camera_tools import get_camera_rtsp_url
import shutil

class Sync:
    """
    Đồng bộ dữ liệu từ API vào database
    - Đồng bộ staffs
    - Đồng bộ học sinh các lớp
    - Đồng bộ thiết bị
    """
    def __init__(self, face_recognizer=None, speaker_recognizer=None):
        self.api = api
        self.config = config
        self.face_recognizer = face_recognizer
        self.speaker_recognizer = speaker_recognizer
        self.server_id = "MC12321"
        self.list_cameras = []
        self.camera_ids = []
        self.camera_sources = None

        # Xử lý đồng bộ
        self.sync_staffs()
        self.sync_classes()

    def sync_classes(self):
        response = self.api.get_classes(self.server_id)

        # Nếu không có dữ liệu thì log rồi dừng chương trình
        if not response.get("data"):
            LOGGER.warning("Không lấy được danh sách lớp từ API.")
            raise RuntimeError("Không có dữ liệu lớp từ API.")

        print("-" * 100)
        self._get_list_cameras(response["data"])
        print("-" * 100)
        
        class_list = response["data"].get("list_classes", [])

        if not class_list:
            LOGGER.warning("Không có lớp học nào trong dữ liệu API.")
            raise RuntimeError("Danh sách lớp trống.")

        LOGGER.info(f"Phát hiện {len(class_list)} lớp học từ API.")

        for class_data in class_list:
            class_id = class_data["id"]
            print("-" * 100)
            LOGGER.info(f"Đang đồng bộ lớp {class_id}...")
            self.sync_class(class_id)
            self.build_faiss_index(class_id)
            LOGGER.info(f"Đã đồng bộ lớp {class_id}.")
        
        print("-" * 100)

    def _download_file(self, url, save_dir="downloads", filename=None, allowed_types=None):
        """
        Tải file từ URL về thư mục local.

        Args:
            url (str): Đường dẫn file.
            save_dir (str): Thư mục lưu file.
            filename (str): Tên file lưu (nếu không có sẽ lấy từ URL).
            allowed_types (list): Danh sách content-type được phép (VD: ["application/pdf", "image/jpeg"]).

        Returns:
            str hoặc None: Đường dẫn file đã tải, hoặc None nếu có lỗi.
        """
        try:
            os.makedirs(save_dir, exist_ok=True)

            # Nếu không có tên file, tự lấy từ URL
            if not filename:
                filename = url.split("/")[-1]
            save_path = os.path.join(save_dir, filename)

            # Gửi request
            response = requests.get(url, stream=True, timeout=15)
            response.raise_for_status()

            # Kiểm tra định dạng file nếu được yêu cầu
            content_type = response.headers.get("Content-Type", "")
            if allowed_types and all(ct not in content_type for ct in allowed_types):
                LOGGER.warning(f"Unsupported Content-Type: {content_type} | URL: {url}")
                return None

            # Ghi file xuống ổ cứng
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            LOGGER.info(f"Downloaded file: {save_path}")
            return save_path

        except Exception as e:
            LOGGER.warning(f"Failed to download {url}")
            return None

    def sync_class(self, class_id):
        response = self.api.get_pupils_by_class_id(class_id)
        if not response["data"]:
            LOGGER.warning(f"Không có học sinh nào trong class_id: {class_id}")
            return

        api_data = response["data"]
        new_ids = [p["id"] for p in api_data]

        collection = self.config.database[str(class_id)]
        
        # Lấy danh sách học sinh cần xóa trước khi thực hiện bulk operations
        to_delete_query = {"id": {"$nin": new_ids}}
        to_delete_docs = list(collection.find(to_delete_query, {"id": 1}))
        deleted_ids = [doc["id"] for doc in to_delete_docs]
        
        # Lấy existing data để so sánh
        existing_docs = collection.find({})
        existing_map = {doc["id"]: doc for doc in existing_docs}

        operations = []
        added_count = 0
        updated_count = 0

        # Xử lý từng học sinh trong API
        for pupil in api_data:
            pupil_id = pupil["id"]
            pupil["class_id"] = class_id
            pupil["synced_at"] = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%Y-%m-%d %H:%M:%S")

            existing = existing_map.get(pupil_id)
            is_new = existing is None
            is_updated = False

            # Kiểm tra version với error handling
            if not is_new:
                existing_version = existing.get("version")
                if existing_version is not None:
                    try:
                        if not math.isclose(pupil["version"], existing_version, abs_tol=1e-6):
                            is_updated = True
                    except (TypeError, ValueError) as e:
                        LOGGER.warning(f"Error comparing versions for pupil {pupil_id}: {e}")
                        is_updated = True  # Treat as updated if comparison fails
                else:
                    is_updated = True  # No version info, treat as updated

            # Xử lý học sinh mới hoặc cần update
            if is_new or is_updated:
                try:
                    self._clean_pupil_folder(class_id, pupil_id)
                    
                    # Tải ảnh và tạo embedding cho mỗi ảnh của học sinh
                    identities = pupil.get("pupil_identities", [])
                    total = len(identities)

                    for idx, identity in enumerate(identities, start=1):
                        url = identity.get("url")
                        filename = identity.get("name")

                        if url and filename:
                            LOGGER.info(f"Downloading image {idx}/{total}: {filename}")

                            save_dir = f"users_data/pupils/{class_id}/{pupil_id}"
                            try:
                                saved_path = self._download_file(
                                    url,
                                    save_dir=save_dir,
                                    filename=filename
                                )
                                if saved_path:
                                    identity["local_path"] = saved_path
                                    success, msg = self._generate_image_embedding(identity)
                                    if success:
                                        LOGGER.info(f"{saved_path}: {msg}")
                                    else:
                                        LOGGER.error(f"{saved_path}: {msg}")
                                else:
                                    LOGGER.error(f"Failed to download {filename}")
                            except Exception as e:
                                LOGGER.error(f"Error processing image {filename}: {e}")

                    operations.append(ReplaceOne({"id": pupil_id}, pupil, upsert=True))

                    if is_new:
                        added_count += 1
                    elif is_updated:
                        updated_count += 1
                        
                except Exception as e:
                    LOGGER.error(f"Error processing pupil {pupil_id}: {e}")
                    continue

        # Thực hiện bulk operations nếu có
        if operations:
            try:
                collection.bulk_write(operations)
            except Exception as e:
                LOGGER.error(f"Error performing bulk write for class {class_id}: {e}")

        # Xóa học sinh không còn trong API
        deleted_count = 0
        if deleted_ids:
            try:
                delete_result = collection.delete_many({"id": {"$nin": new_ids}})
                deleted_count = delete_result.deleted_count
                
                # Clean thư mục của học sinh đã xóa
                for deleted_id in deleted_ids:
                    try:
                        self._clean_pupil_folder(class_id, deleted_id)
                        LOGGER.info(f"Cleaned folder for deleted pupil: {deleted_id}")
                    except Exception as e:
                        LOGGER.error(f"Failed to clean folder for pupil {deleted_id}: {e}")
                        
            except Exception as e:
                LOGGER.error(f"Error deleting pupils from class {class_id}: {e}")

        LOGGER.info(
            f"Synced class {class_id} → Added: {added_count}, Updated: {updated_count}, Deleted: {deleted_count}"
        )

    def _clean_pupil_folder(self, class_id, pupil_id):
        folder = os.path.join("users_data/pupils", str(class_id), str(pupil_id))
        if os.path.exists(folder):
            shutil.rmtree(folder)
            LOGGER.info(f"Đã clean thư mục ảnh học sinh: {folder}")

    def _clean_staff_folder(self, staff_id):
        folder = os.path.join("users_data/staffs", str(staff_id))
        if os.path.exists(folder):
            shutil.rmtree(folder)
            LOGGER.info(f"Đã clean thư mục staff: {folder}")

    def _generate_image_embedding(self, identity):
        """
        Xử lý embedding cho một đối tượng identity.

        Args:
            identity (dict): Thông tin học sinh, cần có key "image_url" hoặc "local_path".
            detector: Đối tượng detector có các hàm get_face_detects và get_face_embeddings.

        Returns:
            - bool: True nếu xử lý thành công, False nếu có lỗi.
            - str: Thông báo chi tiết (nếu lỗi).
        """
        image_path = identity.get("local_path")
        if not image_path:
            return False, "Missing local image path."

        embedding, message = get_embedding(image_path, self.face_recognizer)
        if embedding is not None:
            identity["embedding"] = embedding.tolist()
            return True, message
        else:
            return False, message

    def build_faiss_index(self, class_id):
        """
        Tạo FAISS index (.faiss) và ánh xạ index → user (id, name, type) từ:
        - pupil_identities của từng học sinh trong class_id
        - identities (asset_type=image) của toàn bộ staffs
        """
        embeddings = []
        id_mapping = {}
        index_counter = 0

        data_folder = os.path.join(self.config.faiss_data_folder, str(class_id))
        os.makedirs(data_folder, exist_ok=True)

        # 1. Xử lý học sinh trong class_id
        pupils = self.config.database[str(class_id)].find(
            {"class_id": class_id},
            {"id": 1, "name": 1, "pupil_identities": 1}
        )

        pupil_count = 0
        pupil_embeddings = 0
        
        for pupil in pupils:
            pupil_id = pupil.get("id")
            name = pupil.get("name", "Unknown")
            identities = pupil.get("pupil_identities", [])

            valid = False
            for identity in identities:
                embedding = identity.get("embedding")
                if embedding and isinstance(embedding, list):
                    if len(embedding) != 512:
                        LOGGER.warning(f"Bỏ qua embedding độ dài khác 512 của pupil {pupil_id}")
                        continue

                    embeddings.append(embedding)
                    id_mapping[index_counter] = {
                        "id": pupil_id,
                        "name": name,
                        "type": "pupil"
                    }
                    index_counter += 1
                    pupil_embeddings += 1
                    valid = True

            if valid:
                pupil_count += 1

        # 2. Xử lý toàn bộ staffs (chỉ image)
        staffs = self.config.database["staffs"].find(
            {},
            {"id": 1, "name": 1, "identities": 1}
        )

        staff_count = 0
        staff_embeddings = 0
        
        for staff in staffs:
            staff_id = staff.get("id")
            name = staff.get("name", "Unknown")
            identities = staff.get("identities", [])

            valid = False
            for identity in identities:
                # Chỉ xử lý asset_type = "image"
                asset_type = identity.get("asset_type")
                if asset_type != "image":
                    continue
                    
                embedding = identity.get("embedding")
                if embedding and isinstance(embedding, list):
                    if len(embedding) != 512:
                        LOGGER.warning(f"Bỏ qua embedding độ dài khác 512 của staff {staff_id}")
                        continue

                    embeddings.append(embedding)
                    id_mapping[index_counter] = {
                        "id": staff_id,
                        "name": name,
                        "type": "staff"
                    }
                    index_counter += 1
                    staff_embeddings += 1
                    valid = True

            if valid:
                staff_count += 1

        # 3. Kiểm tra và tạo FAISS index
        if not embeddings:
            LOGGER.warning(f"[Class {class_id}] Không tìm thấy embedding hợp lệ từ pupils và staffs.")
            return False

        try:
            embeddings_array = np.array(embeddings, dtype=np.float32)
            vector_dim = embeddings_array.shape[1]

            index = faiss.IndexFlatIP(vector_dim)
            index.add(embeddings_array)

            faiss_path = os.path.join(data_folder, "face_index.faiss")
            mapping_path = os.path.join(data_folder, "face_index_mapping.pkl")

            faiss.write_index(index, faiss_path)
            with open(mapping_path, "wb") as f:
                pickle.dump(id_mapping, f)

            LOGGER.info(f"[Class {class_id}] FAISS index saved to: {faiss_path}")
            LOGGER.info(f"[Class {class_id}] Mapping saved to: {mapping_path}")
            LOGGER.info(f"[Class {class_id}] Pupils: {pupil_embeddings} embeddings từ {pupil_count} học sinh")
            LOGGER.info(f"[Class {class_id}] Staffs: {staff_embeddings} embeddings từ {staff_count} staff")
            LOGGER.info(f"[Class {class_id}] Tổng cộng: {index_counter} embeddings")

            return True

        except Exception as e:
            LOGGER.error(f"[Class {class_id}] Lỗi tạo/lưu FAISS index: {str(e)}")
            return False
        
    def _get_list_cameras(self, data):
        """
        Trích xuất danh sách camera từ dữ liệu API và xử lý đầu vào camera:
        - Gán RTSP nếu chưa có
        - Gán self.camera_ids = list camera["id"]
        - Nếu 1 camera → trả về RTSP string
        - Nếu nhiều camera → tạo file device.txt và trả về 'device.txt'

        Args:
            data (dict): Dữ liệu từ API (response["data"])

        Returns:
            str: RTSP nếu chỉ có 1 camera, hoặc "device.txt" nếu nhiều
        """
        try:
            self.list_cameras = data.get("list_hardware", {}).get("cameras", [])
            camera_sources = []

            if not self.list_cameras:
                raise RuntimeError("Không tìm thấy camera nào trong dữ liệu từ API.")

            LOGGER.info(f"Phát hiện {len(self.list_cameras)} camera.")

            for cam in self.list_cameras:
                if "RTSP" not in cam or not cam["RTSP"]:
                    LOGGER.warning(f"Camera {cam.get('name')} không có RTSP.")
                    LOGGER.info(f"Đang thử tạo RTSP cho camera {cam.get('name')}...")
                    cam["RTSP"] = get_camera_rtsp_url(
                        ip=cam.get("ip"),
                        username=cam.get("username"),
                        password=cam.get("password"),
                        mac_address=cam.get("mac_address"),
                    )

                self.camera_ids.append(cam["id"])
                camera_sources.append(cam["RTSP"])
                LOGGER.info(f"Đã lấy RTSP cho camera {cam['name']} [ID: {cam['id']}] [RTSP: {cam['RTSP']}]")

            if len(camera_sources) == 1:
                self.camera_sources = camera_sources[0]

            with open("device.txt", "w") as f:
                for rtsp in camera_sources:
                    f.write(f"{rtsp}\n")

            LOGGER.info(f"Đã tạo file device.txt với {len(camera_sources)} camera sources")
            self.camera_sources = "device.txt"

        except Exception as e:
            LOGGER.error(f"Lỗi khi xử lý danh sách camera: {e}")

    def sync_staffs(self):
        response = self.api.get_staffs(self.server_id)
        if not response["data"]:
            LOGGER.warning(f"Không có staff nào trong server_id: {self.server_id}")
            return

        api_data = response["data"]
        new_ids = [s["id"] for s in api_data]

        collection = self.config.database["staffs"]
        
        # Lấy danh sách staff cần xóa trước khi thực hiện bulk operations
        to_delete_query = {"id": {"$nin": new_ids}}
        to_delete_docs = list(collection.find(to_delete_query, {"id": 1}))
        deleted_ids = [doc["id"] for doc in to_delete_docs]
        
        # Lấy existing data để so sánh
        existing_docs = collection.find({})
        existing_map = {doc["id"]: doc for doc in existing_docs}

        operations = []
        added_count = 0
        updated_count = 0

        print("-" * 100)
        LOGGER.info(f"Đang đồng bộ {len(api_data)} staffs")

        # Xử lý từng staff trong API
        for staff in api_data:
            staff_id = staff.get("id")
            print("-" * 100)
            LOGGER.info(f"Đang đồng bộ staff {staff_id}")

            existing = existing_map.get(staff_id)
            is_new = existing is None
            is_updated = False

            # Kiểm tra version với error handling (nếu có version field)
            if not is_new:
                existing_version = existing.get("version")
                staff_version = staff.get("version")
                
                if existing_version is not None and staff_version is not None:
                    try:
                        if not math.isclose(staff_version, existing_version, abs_tol=1e-6):
                            is_updated = True
                    except (TypeError, ValueError) as e:
                        LOGGER.warning(f"Error comparing versions for staff {staff_id}: {e}")
                        is_updated = True
                elif existing_version != staff_version:  # One is None, other is not
                    is_updated = True

            # Xử lý staff mới hoặc cần update
            if is_new or is_updated:
                try:
                    # Clean thư mục của staff này
                    staff_dir = f"users_data/staffs/{staff_id}"
                    if os.path.exists(staff_dir):
                        shutil.rmtree(staff_dir)
                        LOGGER.info(f"Cleaned folder for staff: {staff_id}")

                    identities = staff.get("identities", [])
                    
                    for identity in identities:
                        asset_type = identity.get("asset_type")
                        asset_url = identity.get("asset_url")
                        asset_name = identity.get("asset_name")

                        if not asset_type or not asset_url or not asset_name:
                            continue

                        if asset_type in {"image", "audio"}:
                            save_dir = f"users_data/staffs/{staff_id}/{asset_type}"
                            
                            try:
                                saved_path = self._download_file(
                                    asset_url,
                                    save_dir=save_dir,
                                    filename=asset_name
                                )

                                if saved_path:
                                    identity["local_path"] = saved_path

                                    if asset_type == "image":
                                        success, msg = self._generate_image_embedding(identity)
                                        if success:
                                            LOGGER.info(f"{saved_path}: {msg}")
                                        else:
                                            LOGGER.error(f"{saved_path}: {msg}")
                                    elif asset_type == "audio":
                                        success, msg = self._generate_audio_embedding(identity)
                                        if success:
                                            LOGGER.info(f"{saved_path}: {msg}")
                                        else:
                                            LOGGER.error(f"{saved_path}: {msg}")
                                else:
                                    LOGGER.error(f"Failed to download {asset_name}")
                            except Exception as e:
                                LOGGER.error(f"Error processing asset {asset_name}: {e}")

                    staff["synced_at"] = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%Y-%m-%d %H:%M:%S")
                    operations.append(ReplaceOne({"id": staff_id}, staff, upsert=True))

                    if is_new:
                        added_count += 1
                    elif is_updated:
                        updated_count += 1
                        
                except Exception as e:
                    LOGGER.error(f"Error processing staff {staff_id}: {e}")
                    continue

        # Thực hiện bulk operations nếu có
        if operations:
            try:
                collection.bulk_write(operations)
            except Exception as e:
                LOGGER.error(f"Error performing bulk write for staffs: {e}")

        # Xóa staff không còn trong API
        deleted_count = 0
        if deleted_ids:
            try:
                delete_result = collection.delete_many({"id": {"$nin": new_ids}})
                deleted_count = delete_result.deleted_count
                
                # Clean thư mục của staff đã xóa
                for deleted_id in deleted_ids:
                    try:
                        staff_dir = f"users_data/staffs/{deleted_id}"
                        if os.path.exists(staff_dir):
                            shutil.rmtree(staff_dir)
                            LOGGER.info(f"Cleaned folder for deleted staff: {deleted_id}")
                    except Exception as e:
                        LOGGER.error(f"Failed to clean folder for staff {deleted_id}: {e}")
                        
            except Exception as e:
                LOGGER.error(f"Error deleting staffs: {e}")

        LOGGER.info(
            f"Synced staffs → Added: {added_count}, Updated: {updated_count}, Deleted: {deleted_count}"
        )

    def _generate_audio_embedding(self, identity):
        audio_path = identity.get("local_path")
        if not audio_path:
            return False, "Missing local audio path."

        result, message = self.speaker_recognizer.extract_embedding(audio_path)
        if result is not None:
            identity["embedding"] = result.embedding.tolist()
            return True, message
        else:
            return False, message
