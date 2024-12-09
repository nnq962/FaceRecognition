import os
import numpy as np
import pandas as pd
import mtcnn_detect
import extract_embeddings
import cv2

# Khởi tạo mô hình để lấy embeddings
mtcnn = mtcnn_detect.MTCNNFaceDetector()
get_embs = extract_embeddings.FaceEmbeddingExtractor()

def get_image_embeddings(image_path):
    image = cv2.imread(image_path)
    boxes = mtcnn.detect_faces(image)

    if len(boxes) == 0:
        return None

    embedding = get_embs.extract_embeddings(image, boxes)
    return embedding[0]
    

def process_database(database_path, embedding_file, metadata_file):
    """
    Duyệt qua thư mục database, tính toán embeddings và lưu lại metadata.
    """
    embeddings = []
    metadata = []

    # Duyệt qua tất cả thư mục con (tên người) và các ảnh trong đó
    for person_name in os.listdir(database_path):
        person_folder = os.path.join(database_path, person_name)
        
        if os.path.isdir(person_folder):
            for image_name in os.listdir(person_folder):
                image_path = os.path.join(person_folder, image_name)
                
                # Tính embedding cho ảnh
                embedding = get_image_embeddings(image_path)
                if embedding is not None:
                    embeddings.append(embedding)

                    # Lưu thông tin metadata
                    metadata.append({
                        'name': person_name,
                        'image_path': image_path
                    })
        print("Saved:", person_name)
    
    # Lưu embeddings vào file .npy
    np.save(embedding_file, np.array(embeddings))

    # Lưu metadata vào file .csv
    pd.DataFrame(metadata).to_csv(metadata_file, index=False)

# Gọi hàm để xử lý database
database_path = 'database'  # Đường dẫn đến thư mục chứa ảnh
embedding_file = 'embeddings_data/embeddings.npy'  # Nơi lưu embeddings
metadata_file = 'embeddings_data/metadata.csv'  # Nơi lưu thông tin metadata

process_database(database_path, embedding_file, metadata_file)

