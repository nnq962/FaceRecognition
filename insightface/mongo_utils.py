from pymongo import MongoClient

def save_data_to_mongo(data, db_name="my_database", collection_name="my_collection", mongo_url="mongodb://localhost:27017/"):
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
        # Kết nối tới MongoDB
        client = MongoClient(mongo_url)
        db = client[db_name]
        collection = db[collection_name]

        # Lưu dữ liệu
        if isinstance(data, list):
            result = collection.insert_many(data)
            return {"status": "success", "inserted_ids": result.inserted_ids}
        elif isinstance(data, dict):
            result = collection.insert_one(data)
            return {"status": "success", "inserted_id": result.inserted_id}
        else:
            return {"status": "error", "message": "Data must be a dictionary or a list of dictionaries"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
