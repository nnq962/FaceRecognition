import faiss
import numpy as np
import pickle

def search_id(embedding, index_path="database/face_index.faiss", mapping_path="database/index_to_id.pkl", top_k=1, threshold=0.5):
    """
    Tìm kiếm ID và độ tương đồng trong cơ sở dữ liệu dựa trên một embedding, có ngưỡng độ tương đồng.

    Args:
        embedding (numpy.ndarray): Embedding đã chuẩn hóa (shape: (512,)).
        index_path (str): Đường dẫn tới FAISS index file.
        mapping_path (str): Đường dẫn tới file ánh xạ index -> ID.
        top_k (int): Số lượng kết quả gần nhất cần trả về.
        threshold (float): Ngưỡng độ tương đồng, loại bỏ kết quả có độ tương đồng thấp hơn ngưỡng.

    Returns:
        list of dict: Danh sách kết quả bao gồm ID, tên ảnh và độ tương đồng.
    """
    # Load FAISS index
    index = faiss.read_index(index_path)

    # Load ánh xạ index -> ID
    with open(mapping_path, "rb") as f:
        index_to_id = pickle.load(f)

    # Đảm bảo embedding là 2D để phù hợp với FAISS input
    query_embedding = np.array([embedding]).astype('float32')

    # Tìm kiếm với FAISS
    D, I = index.search(query_embedding, k=top_k)  # D: Độ tương đồng, I: Chỉ số

    results = []
    for i in range(top_k):
        idx = I[0][i]  # Chỉ số trong FAISS index
        similarity = D[0][i]
        if idx < 0 or similarity < threshold:  # Bỏ qua nếu không tìm thấy hoặc không đạt ngưỡng
            continue
        id_mapping = index_to_id[idx]
        results.append({
            "id": id_mapping["id"],
            "image": id_mapping["image"],
            "similarity": similarity
        })

    return results


import cv2
from insightface_detector import InsightFaceDetector

detector = InsightFaceDetector()
img = cv2.imread("datatest/nnq_test.png")
result = detector.get_face_detect(img)[0][0]  # Phát hiện khuôn mặt
query_embedding = detector.get_face_embedding(img, result[0], result[1], result[2])


# Tìm kiếm với ngưỡng 0.7
results = search_id(query_embedding, top_k=5, threshold=0.8)

# In kết quả
if results:
    for result in results:
        print(f"ID: {result['id']}, Image: {result['image']}, Similarity: {result['similarity']:.4f}")
else:
    print("No match found with the given threshold.")