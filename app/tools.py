import os
import numpy as np
import faiss
import pickle
from annoy import AnnoyIndex
import re
import unicodedata
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config
from utils.insightface_utils import process_image
from utils.logger_config import LOGGER
from insightface_detector import InsightFaceDetector


def generate_all_user_embeddings():
    """
    Cập nhật toàn bộ face_embeddings trong MongoDB,
    nếu thư mục hình ảnh của các users bị thay đổi.
    """
    users = config.user_collection.find()
    detector = InsightFaceDetector()

    for user in users:
        user_id = user.get("user_id")
        photo_folder = user.get("photo_folder")

        LOGGER.info(f"Processing user_id: {user_id}...")

        if not photo_folder or not os.path.exists(photo_folder):
            LOGGER.warning(f"Photo folder does not exist for user_id {user_id}: {photo_folder}")
            continue

        face_embeddings = []
        photo_count = 0
        failed_photos = 0

        for file_name in os.listdir(photo_folder):
            file_path = os.path.join(photo_folder, file_name)

            if os.path.isfile(file_path):
                try:
                    # Gọi hàm xử lý để lấy face embedding và thông báo
                    face_embedding, processing_message = process_image(file_path, detector)

                    if face_embedding is not None:
                        face_embeddings.append({
                            "photo_name": file_name,
                            "embedding": face_embedding.tolist()
                        })

                        photo_count += 1
                        LOGGER.info(f"Added embedding for file {file_name} (user_id {user_id}): {processing_message}")
                    else:
                        failed_photos += 1
                        LOGGER.warning(f"Failed to process file {file_name} (user_id {user_id}): {processing_message}")

                except Exception as e:
                    failed_photos += 1
                    LOGGER.error(f"Error processing file {file_path}: {e}")

        # Cập nhật face_embeddings vào MongoDB theo user_id
        config.user_collection.update_one(
            {"user_id": user_id},
            {"$set": {"face_embeddings": face_embeddings}}
        )

        LOGGER.info(
            f"Completed processing user_id {user_id}. "
            f"Total photos processed: {photo_count}, Failed: {failed_photos}"
        )


def remove_accents(input_str):
    """
    Loại bỏ dấu tiếng Việt và chuyển Đ -> D, đ -> d
    """
    input_str = input_str.replace("Đ", "D").replace("đ", "d")  # Chuyển Đ -> D, đ -> d
    nfkd_form = unicodedata.normalize('NFKD', input_str)  # Chuẩn hóa Unicode
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])


def generate_username(full_name: str) -> str:
    """
    Tạo username từ họ tên theo format: tên + viết tắt họ và tên đệm
    Ví dụ: 
    - Nguyễn Văn Anh -> anhnv
    - Nguyễn Trung Lâm -> lamnt  
    - Nguyễn Đại -> dain
    - Nguyễn Thị Thuỳ An -> anntt
    """
    if not full_name or not isinstance(full_name, str):
        return ""
    
    parts = full_name.strip().split()
    
    if len(parts) == 0:
        return ""
    elif len(parts) == 1:
        # Chỉ có 1 từ thì dùng luôn từ đó
        name = parts[0]
        initials = ""
    else:
        # Tên là từ cuối cùng
        name = parts[-1]
        # Viết tắt từ các từ trước đó (họ và tên đệm)
        initials = ''.join([part[0] for part in parts[:-1]])
    
    # Loại bỏ dấu tiếng Việt
    name_no_accents = remove_accents(name)
    initials_no_accents = remove_accents(initials)
    
    # Chuyển sang chữ thường và loại bỏ ký tự không phải a-z
    clean_name = re.sub(r'[^a-z]', '', name_no_accents.lower())
    clean_initials = re.sub(r'[^a-z]', '', initials_no_accents.lower())
    
    # Kết hợp tên + viết tắt
    username = clean_name + clean_initials
    
    return username


def shorten_name(full_name):
    """
    Rút gọn tên thành dạng: N.N.Quyet (bỏ dấu và rút gọn)
    """
    full_name = remove_accents(full_name)  # Bỏ dấu trước khi rút gọn
    words = full_name.split()  # Tách tên theo khoảng trắng
    if len(words) >= 2:
        short_name = ".".join([w[0] for w in words[:-1]]) + "." + words[-1]
    else:
        short_name = words[0]  # Nếu chỉ có một từ, giữ nguyên
    return short_name


def build_faiss_index():
    """
    Tạo FAISS index (.faiss) và tệp ánh xạ index → user từ MongoDB.
    Lưu thông tin user_id, name và room_id trong tệp ánh xạ.
    """
    embeddings = []
    id_mapping = {}  # Lưu mapping từ FAISS index → user (user_id, name, room_id)
    index_counter = 0
    
    # Tạo thư mục chứa nếu chưa tồn tại
    os.makedirs(os.path.dirname(config.faiss_file), exist_ok=True)
    
    # Lấy thông tin từ MongoDB - tất cả người dùng
    users = config.user_collection.find(
        {}, 
        {"user_id": 1, "name": 1, "room_id": 1, "face_embeddings": 1}
    )
    
    user_count = 0
    for user in users:
        user_id = user.get("user_id")
        name = user.get("name", "Unknown")
        room_id = user.get("room_id")
        face_embeddings = user.get("face_embeddings", [])
        
        if not isinstance(face_embeddings, list) or not face_embeddings:
            LOGGER.warning(f"Bỏ qua user {user_id}: không có embeddings hoặc định dạng không đúng")
            continue
            
        user_count += 1
        for face_entry in face_embeddings:
            embedding = face_entry.get("embedding")
            if embedding and isinstance(embedding, list):
                try:
                    # Kiểm tra vector embedding hợp lệ
                    if len(embedding) < 128:  # Giả sử chiều vector là 128, điều chỉnh theo thực tế
                        LOGGER.warning(f"Bỏ qua embedding không hợp lệ của user {user_id}: độ dài {len(embedding)}")
                        continue
                        
                    embeddings.append(embedding)
                    id_mapping[index_counter] = {
                        "user_id": user_id,
                        "name": name,
                        "room_id": room_id
                    }
                    index_counter += 1
                except Exception as e:
                    LOGGER.error(f"Lỗi xử lý embedding cho user {user_id}: {str(e)}")
    
    if not embeddings:
        LOGGER.warning("Không có embeddings nào trong MongoDB!")
        return False
        
    # Convert sang numpy
    embeddings_array = np.array(embeddings, dtype=np.float32)
    vector_dim = embeddings_array.shape[1]
    
    try:
        # FAISS Inner Product index với chuẩn hóa vectors
        index = faiss.IndexFlatIP(vector_dim)
        index.add(embeddings_array)
        
        # Lưu FAISS index
        faiss.write_index(index, config.faiss_file)
        
        # Lưu ánh xạ index → user info
        with open(config.faiss_mapping_file, "wb") as f:
            pickle.dump(id_mapping, f)
            
        LOGGER.info(f"FAISS index đã được tạo và lưu vào {config.faiss_file}")
        LOGGER.info(f"Mapping index → user info đã được lưu vào {config.faiss_mapping_file}")
        LOGGER.info(f"Đã xử lý tổng cộng {index_counter} embeddings cho {user_count} người dùng")
        return True
    except Exception as e:
        LOGGER.error(f"Lỗi khi tạo hoặc lưu FAISS index: {str(e)}")
        return False


def build_ann_index():
    """
    Tạo tệp ann và tệp ánh xạ
    """
    embeddings = []
    id_mapping = {}  # Lưu mapping từ Annoy index → user (_id, full_name)

    index_counter = 0  # Đếm số embeddings

    # Lấy thông tin _id, full_name và embeddings từ MongoDB
    users = config.user_collection.find({}, {"_id": 1, "full_name": 1, "face_embeddings": 1})
    
    for user in users:
        user_id = user["_id"]
        full_name = user.get("full_name", "Unknown")  # Nếu không có full_name thì gán "Unknown"

        for face_entry in user.get("face_embeddings", []):  # Duyệt qua từng embedding
            embeddings.append(face_entry["embedding"])
            id_mapping[index_counter] = {
                "id": user_id,  # Sử dụng _id thay vì user_id
                "full_name": full_name  # Lưu full_name thay vì photo_name
            }
            index_counter += 1

    # Kiểm tra nếu không có embeddings
    if not embeddings:
        LOGGER.warning("Không có embeddings nào trong MongoDB!")
        return

    # Chuyển thành NumPy array để xử lý nhanh hơn
    embeddings = np.array(embeddings, dtype=np.float32)

    # Xác định số chiều của vector embedding
    vector_dim = len(embeddings[0])

    # Khởi tạo Annoy Index
    t = AnnoyIndex(vector_dim, 'euclidean')

    # Thêm từng embedding vào Annoy Index
    for i, emb in enumerate(embeddings):
        t.add_item(i, emb)

    # Xây dựng Annoy Index với 10 cây
    t.build(10)

    # Lưu file .ann
    t.save(config.ann_file)

    # Lưu id_mapping thành file .npy
    np.save(config.mapping_file, id_mapping)

    LOGGER.info(f"Annoy index has been successfully created and saved to {config.ann_file}.")
    LOGGER.info(f"Mapping index → user has been saved to {config.mapping_file}.")


def calculate_work_hours_new(attendance_data):
    """Tính tổng giờ công trong ngày, ghi chú và trừ KPI theo cấu trúc dữ liệu mới."""
    if not attendance_data:  # Không có dữ liệu
        return None, None, None, "Nghỉ", ""
    
    check_in_time = attendance_data.get("check_in_time")
    check_out_time = attendance_data.get("check_out_time")
    
    if not check_in_time or not check_out_time:
        return check_in_time, check_out_time, None, "Nghỉ", ""
    
    # Chuyển đổi định dạng thời gian
    from datetime import datetime
    check_in_dt = datetime.strptime(check_in_time, "%H:%M:%S")
    check_out_dt = datetime.strptime(check_out_time, "%H:%M:%S")
    
    # Tính tổng giờ công (để đơn giản, giả sử cùng ngày)
    total_hours = round((check_out_dt - check_in_dt).total_seconds() / 3600, 2)
    
    # Thời gian chuẩn để so sánh
    start_time = datetime.strptime("08:00:00", "%H:%M:%S")
    late_threshold = datetime.strptime("08:10:00", "%H:%M:%S")
    noon_deadline = datetime.strptime("11:30:00", "%H:%M:%S")
    lunch_end = datetime.strptime("12:30:00", "%H:%M:%S")
    end_time = datetime.strptime("17:30:00", "%H:%M:%S")
    
    # Kiểm tra các điều kiện
    is_late = check_in_dt > late_threshold
    is_early_leave = check_out_dt < end_time
    missing_morning = check_in_dt > noon_deadline
    missing_afternoon = check_out_dt < lunch_end
    
    # Xác định ghi chú
    note = ""
    if missing_morning:
        note = "Thiếu công sáng"
    elif missing_afternoon:
        note = "Thiếu công chiều"
    elif is_late and is_early_leave:
        note = "Đi muộn & về sớm"
    elif is_late:
        note = "Đi muộn"
    elif is_early_leave:
        note = "Về sớm"
    
    # Xác định trừ KPI - chỉ trừ khi đi muộn quá 10 phút
    kpi_deduction = 1 if is_late else ""
    
    return check_in_time, check_out_time, total_hours, note, kpi_deduction
