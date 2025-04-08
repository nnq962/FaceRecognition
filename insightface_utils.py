import numpy as np
import cv2
from config import config
import os
from annoy import AnnoyIndex
import faiss
import pickle
import platform
from insightface.utils import face_align
from utils.logger_config import LOGGER

current_os = platform.system()

if current_os == "Darwin":  # macOS
    faiss.omp_set_num_threads(1)  # Limit FAISS to use 1 thread
elif current_os == "Linux":
    # Skip setting omp_set_num_threads
    pass

users_collection = config.users_collection
save_path = config.save_path

def search_ids(embeddings, top_k=1, threshold=0.5):
    """
    Tìm kiếm ID và độ tương đồng trong cơ sở dữ liệu dựa trên một mảng embeddings, với ngưỡng độ tương đồng.

    Args:
        embeddings (numpy.ndarray): Mảng các embeddings đã chuẩn hóa (shape: (n_embeddings, 512)).
        index_path (str): Đường dẫn tới FAISS index file.
        mapping_path (str): Đường dẫn tới file ánh xạ index -> ID.
        top_k (int): Số lượng kết quả gần nhất cần trả về cho mỗi embedding.
        threshold (float): Ngưỡng độ tương đồng, loại bỏ kết quả có độ tương đồng thấp hơn ngưỡng.

    Returns:
        list: Danh sách kết quả, với mỗi phần tử là một dictionary hoặc None nếu không có kết quả hợp lệ.
    """
    # Kiểm tra file tồn tại trước khi load
    if not os.path.exists(config.faiss_file):
        LOGGER.warning(f"Missing Faiss index file: {config.faiss_file}")
        return [None] * len(embeddings)

    if not os.path.exists(config.faiss_mapping_file):
        LOGGER.warning(f"Missing mapping file: {config.faiss_mapping_file}")
        return [None] * len(embeddings)

    # Load FAISS index
    index = faiss.read_index(config.faiss_file)

    # Load ánh xạ index -> ID
    with open(config.faiss_mapping_file, "rb") as f:
        index_to_id = pickle.load(f)

    # Chuyển đổi embeddings thành dạng float32
    query_embeddings = np.array(embeddings, dtype=np.float32)

    # Thực hiện tìm kiếm với FAISS
    D, I = index.search(query_embeddings, k=top_k)  # D: Độ tương đồng, I: Chỉ số index FAISS

    results = []
    for query_idx in range(len(query_embeddings)):
        query_results = [
            {
                "id": index_to_id[idx]["id"],
                "full_name": index_to_id[idx]["full_name"],
                "similarity": float(similarity)
            }
            for idx, similarity in zip(I[query_idx], D[query_idx])
            if idx != -1 and similarity >= threshold  # Lọc bỏ kết quả không hợp lệ
        ]
        # Nếu không có kết quả hợp lệ, trả về None
        results.append(query_results[0] if query_results else None)

    return results

def search_annoy(query_embedding, n_neighbors=1, threshold=None):
    """
    Tìm kiếm trong Annoy index sử dụng Euclidean Distance, và chuyển đổi về Cosine Similarity để so sánh với ngưỡng.

    Parameters:
        - query_embedding: Numpy array chứa vector cần tìm kiếm (đã chuẩn hóa trước).
        - n_neighbors: Số lượng hàng xóm gần nhất cần tìm.
        - threshold: Ngưỡng Cosine Similarity tối thiểu (nếu None, không áp dụng).

    Returns:
        - Dictionary chứa thông tin user nếu tìm thấy, None nếu không tìm thấy.
    """

    # Kiểm tra file tồn tại trước khi load
    if not os.path.exists(config.ann_file):
        LOGGER.warning(f"Missing Annoy index file: {config.ann_file}")
        return None

    if not os.path.exists(config.mapping_file):
        LOGGER.warning(f"Missing mapping file: {config.mapping_file}")
        return None

    # Load Annoy Index (sử dụng Euclidean thay vì Angular)
    annoy_index = AnnoyIndex(config.vector_dim, 'euclidean')
    annoy_index.load(config.ann_file)

    # Load Mapping từ file .npy
    id_mapping = np.load(config.mapping_file, allow_pickle=True).item()

    # Tìm n_neighbors gần nhất từ Annoy index
    indices, distances = annoy_index.get_nns_by_vector(query_embedding, n_neighbors, include_distances=True)

    # Chuyển đổi toàn bộ khoảng cách Euclidean sang Cosine Similarity
    cosine_similarities = 1 - (np.array(distances) ** 2) / 2  # Vectorized computation

    # Xây dựng danh sách kết quả
    results = []
    for i, index in enumerate(indices):
        if index in id_mapping:
            if threshold is None or cosine_similarities[i] >= threshold:
                results.append({
                    "id": id_mapping[index]["id"],
                    "full_name": id_mapping[index]["full_name"],
                    "similarity": cosine_similarities[i]
                })

    # Trả về dictionary nếu có 1 kết quả duy nhất, danh sách nếu có nhiều kết quả, None nếu không có kết quả
    if len(results) == 0:
        return None
    elif len(results) == 1:
        return results[0]  # Trả về dictionary thay vì list
    else:
        return results  # Trả về danh sách nếu có nhiều kết quả

def search_annoys(query_embeddings, n_neighbors=1, threshold=None):
    """
    Tìm kiếm trong Annoy index với danh sách query_embeddings.

    Parameters:
        - query_embeddings: List các numpy array chứa các query embeddings.
        - n_neighbors: Số lượng hàng xóm gần nhất cần tìm.
        - threshold: Ngưỡng khoảng cách tối đa (nếu None, không áp dụng).

    Returns:
        - Danh sách kết quả [None, result1, None, result2, ...] (giữ nguyên thứ tự input).
    """
    return [search_annoy(query, n_neighbors, threshold) for query in query_embeddings]

def crop_image(image, bbox):
    """
    Crop một vùng ảnh dựa trên bounding box.

    Args:
        image (numpy.ndarray): Ảnh đầu vào (đọc từ cv2.imread).
        bbox (numpy.ndarray or list): Bounding box 1D dạng float [x1, y1, x2, y2].

    Returns:
        numpy.ndarray: Ảnh đã crop.
    """
    if not isinstance(image, np.ndarray):
        raise ValueError("Input image must be a numpy array.")
    
    if not isinstance(bbox, (np.ndarray, list)) or len(bbox) != 4:
        raise ValueError("Bounding box must be a list or numpy array with 4 elements [x1, y1, x2, y2].")
    
    # Lấy tọa độ bounding box, chuyển thành số nguyên
    x1, y1, x2, y2 = map(int, bbox)

    # Đảm bảo tọa độ nằm trong phạm vi ảnh
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(image.shape[1], x2)
    y2 = min(image.shape[0], y2)

    # Crop ảnh
    cropped_image = image[y1:y2, x1:x2]

    return cropped_image

def expand_image(image, padding_size=50, padding_color=(0, 0, 0)):
    """
    Mở rộng toàn bộ ảnh bằng cách thêm viền xung quanh.

    Args:
        image (numpy.ndarray): Ảnh cần mở rộng.
        padding_size (int): Kích thước viền (số pixel) cần thêm ở mỗi cạnh.
        padding_color (tuple): Màu của viền (BGR format, default là màu đen).

    Returns:
        numpy.ndarray: Ảnh đã được mở rộng.
    """
    # Thêm padding bằng OpenCV
    expanded_image = cv2.copyMakeBorder(
        image,
        top=padding_size,
        bottom=padding_size,
        left=padding_size,
        right=padding_size,
        borderType=cv2.BORDER_CONSTANT,
        value=padding_color
    )
    return expanded_image

def is_small_face(bbox, min_size=50):
    """
    Kiểm tra xem khuôn mặt có kích thước nhỏ hơn ngưỡng cho phép hay không.

    Args:
        bbox (list or numpy.ndarray): Bounding box 1D ở dạng [x1, y1, x2, y2].
        min_size (int): Ngưỡng tối thiểu cho chiều rộng hoặc chiều cao (default: 50).

    Returns:
        bool: True nếu khuôn mặt là nhỏ, False nếu ngược lại.
    """
    if not isinstance(bbox, (list, np.ndarray)) or len(bbox) != 4:
        raise ValueError(f"Expected bbox to be a list or numpy array of length 4, got {type(bbox)} with shape {len(bbox)}")

    x1, y1, x2, y2 = bbox
    width = x2 - x1
    height = y2 - y1

    return width < min_size or height < min_size

def normalize_embeddings(embeddings):
    """
    Chuẩn hóa danh sách các embedding.

    Args:
        embeddings (numpy.ndarray): Mảng các embedding (shape: n_faces x embedding_dim).

    Returns:
        numpy.ndarray: Mảng các embedding đã chuẩn hóa (cùng shape với đầu vào).
    """
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    return embeddings / np.maximum(norms, 1e-8)  # Tránh chia cho 0

def save_data_to_mongo(data):
    """
    Hàm lưu dữ liệu vào MongoDB.

    Parameters:
        data (dict or list): Dữ liệu cần lưu, có thể là một tài liệu hoặc danh sách tài liệu.
        db_name (str): Tên cơ sở dữ liệu.
        collection_name (str): Tên collection.
        mongo_url (str): Chuỗi kết nối MongoDB.

    Returns:
        dict: Thông tin phản hồi sau khi chèn dữ liệu.
    """
    try:
        # Lưu dữ liệu
        if isinstance(data, list):
            result = config.data_collection.insert_many(data)
            return {"status": "success", "inserted_ids": result.inserted_ids}
        elif isinstance(data, dict):
            result = config.data_collection.insert_one(data)
            return {"status": "success", "inserted_id": result.inserted_id}
        else:
            return {"status": "error", "message": "Data must be a dictionary or a list of dictionaries"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def crop_and_align_faces(img, bboxes, keypoints, conf_threshold=0.5, image_size=112):
    """
    Cắt và chuẩn hóa các khuôn mặt từ ảnh gốc dựa trên bounding boxes và keypoints.
    
    Args:
        img (numpy.ndarray): Ảnh gốc.
        bboxes (numpy.ndarray): Bounding boxes, mỗi box có định dạng [x1, y1, x2, y2, conf].
        keypoints (numpy.ndarray): Landmarks (keypoints) của khuôn mặt.
        conf_threshold (float): Ngưỡng độ tin cậy (confidence) để lọc khuôn mặt.
        image_size (int): Kích thước ảnh sau khi chuẩn hóa (ví dụ: 112x112).
        
    Returns:
        list: Danh sách các ảnh khuôn mặt đã cắt và chuẩn hóa.
    """
    cropped_faces = []

    for bbox, kps in zip(bboxes, keypoints):
        if bbox[4] >= conf_threshold:
            cropped_face = face_align.norm_crop(img, landmark=kps, image_size=image_size)
            cropped_faces.append(cropped_face)
    
    return cropped_faces

def process_image(image_path, detector):
    """
    Trích xuất embedding từ hình ảnh.

    Parameters:
        - image_path: Đường dẫn đến ảnh cần xử lý.
        - detector: Đối tượng chứa các hàm `get_face_detect` và `get_face_embedding`.

    Returns:
        - tuple: (embedding, message) trong đó:
            - embedding: Mảng numpy chứa embedding của khuôn mặt (hoặc None nếu có lỗi).
            - message: Thông báo kết quả bằng tiếng Anh.
    """
    img = cv2.imread(image_path)
    if img is None:
        message = f"Failed to read image {image_path}."
        LOGGER.warning(message)
        return None, message

    try:
        result = detector.get_face_detects(img)

        # Lấy bounding boxes và keypoints (luôn có thể unpack)
        bounding_boxes, keypoints = result[0]
        num_faces = len(bounding_boxes)

        if num_faces == 0:
            message = "No face detected in this image."
            LOGGER.warning(message)
            return None, message
        elif num_faces > 1:
            message = f"Multiple faces detected in this image ({num_faces} faces)."
            LOGGER.warning(message)
            return None, message

        # Gọi hàm crop_and_align_faces với khuôn mặt đầu tiên
        cropped_faces = crop_and_align_faces(
            img,
            bboxes=bounding_boxes[:1],
            keypoints=keypoints[:1],
            conf_threshold=0.65,
            image_size=112
        )

        if not cropped_faces:
            message = "No face passed the confidence threshold."
            LOGGER.warning(message)
            return None, message

        # Trích xuất embedding
        embedding = detector.get_face_embeddings(cropped_faces)
        message = "Face embedding extracted successfully."
        return embedding[0], message

    except Exception as e:
        message = f"Failed to process {image_path}: {str(e)}"
        LOGGER.error(message)
        return None, message
    
def crop_faces_for_emotion(frame, bboxes, conf_threshold=0.5):
    """
    Cắt khuôn mặt từ frame và điều chỉnh kích thước cho mô hình cảm xúc
    
    Args:
        frame (numpy.ndarray): Ảnh đầu vào (BGR từ OpenCV)
        bboxes (numpy.ndarray): Bounding boxes, định dạng [x1, y1, x2, y2, conf]
        conf_threshold (float): Ngưỡng tin cậy để lọc bboxes
        
    Returns:
        list: Danh sách các ảnh khuôn mặt đã cắt (định dạng RGB, kích thước target_size x target_size)
    """
    cropped_faces = []
    
    # Chuyển từ BGR sang RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    for bbox in bboxes:
        if bbox[4] >= conf_threshold:
            # Lấy tọa độ
            x1, y1, x2, y2 = map(int, bbox[:4])
            
            # Đảm bảo tọa độ nằm trong giới hạn ảnh
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
            
            # Cắt khuôn mặt từ ảnh RGB
            face = frame_rgb[y1:y2, x1:x2]
            
            cropped_faces.append(face)
    
    return cropped_faces