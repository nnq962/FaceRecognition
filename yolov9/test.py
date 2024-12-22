from insightface.app.common import Face
from insightface.model_zoo import model_zoo
import os
import numpy as np
import tqdm
import cv2
import glob
from collections import defaultdict



det_model_path = os.path.expanduser("~/Models/det_10g.onnx")
rec_model_path = os.path.expanduser("~/Models/w600k_r50.onnx")

BASE_DIR = '/Users/quyetnguyen/Models'

det_model = model_zoo.get_model(det_model_path)
rec_model = model_zoo.get_model(rec_model_path)

det_model.prepare(ctx_id=0, input_size=(640, 640), det_thres=0.5)

known_names, unknown_names = [], []
known_embeddings, unknown_embeddings = [], []

# players = os.listdir(f'{BASE_DIR}/data/raw')
# for player in tqdm(players):
#     player_embeddings, player_names = [], []

#     img_paths = glob(f'{BASE_DIR}/data/raw/{player}/*')
#     for img_path in img_paths:
#         img = cv2.imread(img_path)
#         if img is None: continue

#         bboxes, kpss = det_model.detect(img, max_num=0, metric='defualt')
#         if len(bboxes) != 1: continue

#         bbox = bboxes[0, :4]
#         det_score = bboxes[0, 4]
#         kps = kpss[0]
#         face = Face(bbox=bbox, kps=kps, det_score=det_score)

#         rec_model.get(img, face)
#         player_embeddings.append(face.normed_embedding)
#         player_names.append(player)
#         if len(player_embeddings) == 10: break
    
#     player_embeddings = np.stack(player_embeddings, axis=0)
#     known_embeddings.append(player_embeddings[0:5])
#     unknown_embeddings.append(player_embeddings[5:10])
#     known_names += player_names[0:5]
#     unknown_names += player_names[5:10]

# known_embeddings = np.concatenate(known_embeddings, axis=0)
# unknown_embeddings = np.concatenate(unknown_embeddings, axis=0)


def verify_faces(face_img1, face_img2, threshold=0.5):
    """
    Verify two pre-cropped face images
    Args:
        face_img1: First cropped face image
        face_img2: Second cropped face image
        threshold: Similarity threshold
    Returns:
        tuple: (is_same, similarity_score, message)
    """
    if face_img1 is None or face_img2 is None:
        return False, 0.0, "Error reading images"

    # Detect faces để lấy bbox và keypoints
    bboxes1, kpss1 = det_model.detect(face_img1, max_num=1)
    bboxes2, kpss2 = det_model.detect(face_img2, max_num=1)
    
    if len(bboxes1) == 0 or len(bboxes2) == 0:
        return False, 0.0, "No face detected"

    # Tạo đối tượng Face với đầy đủ thông tin
    face1 = Face(bbox=bboxes1[0,:4], kps=kpss1[0], det_score=bboxes1[0,4])
    face2 = Face(bbox=bboxes2[0,:4], kps=kpss2[0], det_score=bboxes2[0,4])

    # Trích xuất embedding
    rec_model.get(face_img1, face1)
    rec_model.get(face_img2, face2)

    # Tính similarity score
    print("embedding1:", face1.normed_embedding)
    sim_score = np.dot(face1.normed_embedding, face2.normed_embedding.T)
    sim_score = np.clip(sim_score, 0., 1.)

    # So sánh với ngưỡng
    is_same = sim_score > threshold

    return is_same, sim_score, "Success"

# Ví dụ sử dụng:
face_img1 = cv2.imread("photo_test/nnq1.jpg")

face_img2 = cv2.imread("photo_test/image_1.jpg")

is_same, score, message = verify_faces(face_img1, face_img2, threshold=0.5)
print(f"Verification result: {is_same}")
print(f"Similarity score: {score:.3f}")
print(f"Message: {message}")

print(np.get_printoptions())
