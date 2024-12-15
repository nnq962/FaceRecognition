import os
import numpy as np
import faiss
import cv2
import pickle
from insightface_detector import InsightFaceDetector

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

def build_database(dataset_dir, detector, output_dir="database/"):
    os.makedirs(output_dir, exist_ok=True)

    embeddings = []
    index_to_id = []

    for person_id in os.listdir(dataset_dir):  # Mỗi folder tương ứng với ID
        person_path = os.path.join(dataset_dir, person_id)
        if os.path.isdir(person_path):
            for image_name in os.listdir(person_path):
                image_path = os.path.join(person_path, image_name)
                if image_path.endswith(('.jpg', '.png')):
                    print(f"Processing {image_path}...")
                    embedding, error = process_image(image_path, detector)
                    if embedding is not None:
                        embeddings.append(embedding)
                        index_to_id.append({"id": person_id, "image": image_name})
                    else:
                        print(f"Failed: {error}")

    embeddings = np.array(embeddings).astype('float32')

    if embeddings.size > 0:
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)

        # Đường dẫn tới các tệp trong thư mục database
        index_path = os.path.join(output_dir, "face_index.faiss")
        mapping_path = os.path.join(output_dir, "index_to_id.pkl")

        # Lưu FAISS index
        faiss.write_index(index, index_path)

        # Lưu ánh xạ index -> ID
        with open(mapping_path, "wb") as f:
            pickle.dump(index_to_id, f)

        print(f"Database built successfully! Processed {len(embeddings)} embeddings.")
        print(f"Files saved to {output_dir}.")
    else:
        print("No embeddings were generated. Please check the dataset.")

dataset_dir = "dataset/"
detector = InsightFaceDetector()
build_database(dataset_dir, detector, output_dir="database")