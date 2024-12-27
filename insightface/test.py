import faiss
import numpy as np
from pymongo import MongoClient
from build_database import process_image

# Kết nối MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["my_database"]
users_collection = db["camera_users"]

# Tạo FAISS index với MongoDB ID và hỗ trợ Cosine Similarity
def create_faiss_index_with_mongo_id_cosine(output_path="face_index.faiss"):
    embeddings = []
    ids = []

    # Lấy tất cả người dùng từ MongoDB
    users = list(users_collection.find())
    for user in users:
        for image_data in user["images"]:
            embedding = image_data.get("embedding")
            if embedding:
                embeddings.append(embedding)
                ids.append(user["_id"])  # Sử dụng MongoDB `_id` làm ID

    # Chuyển embeddings thành numpy array
    embeddings_array = np.array(embeddings, dtype="float32")
    ids_array = np.array(ids, dtype=np.int64)  # FAISS yêu cầu ID là kiểu số nguyên

    # Tạo FAISS index với Inner Product (cho Cosine Similarity)
    dimension = embeddings_array.shape[1]
    index = faiss.IndexFlatIP(dimension)  # Inner Product để tính Cosine Similarity
    index_with_id = faiss.IndexIDMap(index)

    # Thêm embeddings và IDs vào FAISS
    index_with_id.add_with_ids(embeddings_array, ids_array)

    # Ghi FAISS index ra tệp
    faiss.write_index(index_with_id, output_path)
    print(f"FAISS index (Cosine Similarity) saved to {output_path}")



def search_faiss_with_mongo(query_embedding, index_path="face_index.faiss", k=5):
    # Đọc FAISS index
    index_with_id = faiss.read_index(index_path)

    # Tìm kiếm k lân cận gần nhất
    query_embedding = np.array(query_embedding, dtype="float32").reshape(1, -1)
    distances, ids = index_with_id.search(query_embedding, k)

    # Truy vấn MongoDB để lấy thông tin từ IDs
    results = []
    for idx, dist in zip(ids[0], distances[0]):
        if idx == -1:  # FAISS trả về -1 nếu không tìm thấy kết quả
            continue

        # Chuyển idx từ numpy.int64 sang int
        user = users_collection.find_one({"_id": int(idx)})
        if user:
            results.append({
                "distance": dist,
                "user": {
                    "user_id": user["_id"],
                    "full_name": user["full_name"],
                    "images": user["images"]
                }
            })

    return results


# create_faiss_index_with_mongo_id(output_path="face_index.faiss")
# Khởi tạo detector
from insightface_detector import InsightFaceDetector
detector = InsightFaceDetector()

# Xử lý ảnh và lấy embedding
embedding, error = process_image("data_test/nnq1.jpg", detector=detector)

# Kiểm tra lỗi
if error:
    raise ValueError(f"Failed to process image: {error}")

# Chuyển embedding thành định dạng numpy array
query_embedding = np.array(embedding, dtype="float32").reshape(1, -1)

# Tìm kiếm với FAISS
results = search_faiss_with_mongo(query_embedding, index_path="face_index.faiss", k=3)

# Hiển thị kết quả đẹp hơn
for result in results:
    user_info = result['user']
    print(f"Match found!")
    print(f" - Distance: {result['distance']:.4f}")
    print(f" - User ID: {user_info['user_id']}")
    print(f" - Full Name: {user_info['full_name']}")
    # print(" - Images:")
    # for image in user_info['images']:
    #     print(f"   * Path: {image['path']}")
        # Nếu cần, hiển thị một phần của embedding
        # print(f"     Embedding (truncated): {image['embedding'][:5]}...")