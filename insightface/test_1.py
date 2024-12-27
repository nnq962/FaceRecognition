import faiss

def inspect_faiss_index(index_path):
    # Đọc FAISS index từ tệp
    index = faiss.read_index(index_path)
    
    print("FAISS Index Details:")
    print(f" - Total Vectors: {index.ntotal}")  # Số lượng vector trong index
    
    # Kiểm tra kích thước vector (nếu không dùng IDMap)
    if hasattr(index, "d"):
        print(f" - Vector Dimension: {index.d}")  # Kích thước vector
    
    # Nếu dùng IndexIDMap, kiểm tra ID
    if isinstance(index, faiss.IndexIDMap):
        print(" - Using IDMap")
        ids = index.id_map
        print(f" - ID Map Length: {len(ids)}")
    
    return index

index = inspect_faiss_index("face_index.faiss")