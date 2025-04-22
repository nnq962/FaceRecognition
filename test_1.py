from config import config
from pymongo import MongoClient
from bson import ObjectId

users_collection = config.database['3hinc_users']
temp_collection = config.database['users']  # Collection tạm để lưu dữ liệu mới

# Xóa collection tạm nếu đã tồn tại
temp_collection.drop()

# Lấy tất cả user từ collection hiện tại (bao gồm cả face_embeddings)
users = list(users_collection.find({}))  # Không loại trừ trường face_embeddings

# Chuyển đổi dữ liệu và thêm vào collection tạm
for index, user in enumerate(users, 1):
    new_user = {
        # MongoDB tự tạo _id kiểu ObjectId
        "name": user.get("full_name"),               # Đổi full_name thành name
        "room_id": user.get("department_id"),        # Đổi department_id thành room_id
        "user_id": f"3HINC{index}",                  # Thêm user_id với format 3HINCx
        "created_at": user.get("created_at"),        # Giữ nguyên created_at
        "photo_folder": f"/home/pc/user_data/3HINC{index}",    # Giữ nguyên photo_folder
        "avatar_url": None,                          # Thêm avatar_url = null
        "active": True,                            # Thêm activate = true
        "access_level": None,                        # Thêm access_level = null
        "updated_at": None,                            # Thêm update_at = null
        "telegram_id": None,                        # Thêm telegram_id = null
    }
    
    # Giữ nguyên face_embeddings nếu có
    if "face_embeddings" in user:
        new_user["face_embeddings"] = user["face_embeddings"]
    
    temp_collection.insert_one(new_user)

# Xác nhận kết quả
print("Dữ liệu mới đã được tạo trong collection 'temp_users'")
print("Mẫu dữ liệu mới (không hiển thị face_embeddings do kích thước lớn):")
for user in temp_collection.find({}, {"face_embeddings": 0}).limit(2):
    print(user)

# # Hỏi người dùng trước khi thay thế collection gốc
# answer = input("Bạn có muốn thay thế collection gốc '3hinc_users' bằng dữ liệu mới? (y/n): ")
# if answer.lower() == 'y':
#     # Đổi tên các collection để thay thế
#     users_collection.rename('3hinc_users_backup')  # Backup collection cũ
#     temp_collection.rename('3hinc_users')          # Đổi tên collection tạm thành tên chính
#     print("Đã thay thế collection gốc. Collection cũ được lưu trong '3hinc_users_backup'")
# else:
#     print("Dữ liệu mới vẫn được lưu trong collection 'temp_users'")