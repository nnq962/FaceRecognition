import cv2
from pymongo import MongoClient
import numpy as np
import faiss

client = MongoClient("mongodb://localhost:27017/") 
db = client["my_database"] 
users_collection = db["camera_users"]

def process_image(image_path, detector):
    img = cv2.imread(image_path)
    if img is None:
        return None, f"Failed to read image {image_path}."
    try:
        result = detector.get_face_detect(img)
        if not result or not result[0]:
            return None, f"No face detected in {image_path}."
        result = result[0][0]
        embedding = detector.get_face_embedding(img, result[0], result[1], result[2])
        return embedding, None
    except Exception as e:
        return None, f"Error processing {image_path}: {e}"

def update_embeddings_for_all_users(detector):
    users = list(users_collection.find())  # Lấy tất cả người dùng
    user_results = []  # Lưu kết quả từng người dùng
    total_images_updated = 0

    for user in users:
        user_id = user["_id"]
        updated_images = []
        images_updated_count = 0

        print(f"\nProcessing user: {user['full_name']} (ID: {user_id})")

        # Lặp qua các ảnh trong danh sách
        for image_data in user["images"]:
            # Lấy đường dẫn ảnh
            image_path = image_data.get("path")
            # Kiểm tra xem ảnh đã có embedding chưa
            embedding = image_data.get("embedding")

            # Nếu đã có embedding, bỏ qua (không xử lý lại)
            if embedding:
                updated_images.append(image_data)
                continue

            # Tạo embedding mới
            embedding, error = process_image(image_path, detector)
            if error:
                print(f"Warning: {error}")
                updated_images.append({"path": image_path})  # Giữ nguyên nếu không xử lý được
                continue

            # Thêm ảnh với embedding mới
            updated_images.append({
                "path": image_path,
                "embedding": embedding.tolist()
            })
            images_updated_count += 1

        # Cập nhật danh sách images vào MongoDB
        users_collection.update_one(
            {"_id": user_id},
            {"$set": {"images": updated_images}}
        )

        print(f"Updated {images_updated_count} images for user {user['full_name']} (ID: {user_id})")
        total_images_updated += images_updated_count

        # Ghi lại kết quả cho từng người dùng
        user_results.append(f"User '{user['full_name']}' (ID: {user_id}) - {images_updated_count} images updated")

    # Tạo thông báo tổng kết
    summary = f"\nTotal users processed: {len(user_results)}\n" \
              f"Total images updated: {total_images_updated}\n" \
              "Details:\n" + \
              "\n".join(user_results)

    return summary

def create_faiss_index_with_mongo_id_cosine(output_path="data_base/face_index_new.faiss"):
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