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


def search_flatten(known_embeddings, known_names, unknown_embeddings, threshold=0.5):
    pred_names = []
    for emb  in unknown_embeddings:
        scores = np.dot(emb, known_embeddings.T)
        scores = np.clip(scores, 0., 1.)

        idx = np.argmax(scores)
        score = scores[idx]
        if score > threshold:
            pred_names.append(known_names[idx])
        else:
            pred_names.append(None)
    
    return pred_names



def get_averages(names, scores):
    d = defaultdict(list)
    for n, s in zip(names, scores):
        d[n].append(s)

    averages = {}
    for n, s in d.items():
        averages[n] = np.mean(s)
    
    return averages

def search_average(known_embeddings, known_names, unknown_embeddings, threshold=0.5):
    pred_names = []
    for emb in unknown_embeddings:
        scores = np.dot(emb, known_embeddings.T)
        scores = np.clip(scores, 0., 1.)

        averages = get_averages(known_names, scores)
        pred = sorted(averages, key=lambda x: averages[x], reverse=True)[0]
        score = averages[pred]

        if score > threshold:
            pred_names.append(pred)
        else:
            pred_names.append(None)
    
    return pred_names

def evaluate(true_names, pred_names):
    coverage = np.mean([n is not None for n in pred_names]) * 100.

    is_corrects = []
    for t, p in zip(true_names, pred_names):
        if p is None: continue
        is_corrects.append(t == p)
    
    if not is_corrects:
        is_corrects.append(False)

    accuracy = np.mean(is_corrects) * 100.
    return accuracy, coverage

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
    sim_score = np.dot(face1.normed_embedding, face2.normed_embedding)
    sim_score = np.clip(sim_score, 0., 1.)

    # So sánh với ngưỡng
    is_same = sim_score > threshold

    return is_same, sim_score, "Success"

# Ví dụ sử dụng:
# face_img1 = cv2.imread("photo_test/nnq1.jpg")
# face_img1 = face_img1[158:448, 199:416]  # Cắt với [y1:y2, x1:x2]

# face_img2 = cv2.imread("photo_test/image_1.jpg")
# face_img2 = face_img2[259:729, 367:752]  # Cắt với [y1:y2, x1:x2]

# is_same, score, message = verify_faces(face_img1, face_img2, threshold=0.5)
# print(f"Verification result: {is_same}")
# print(f"Similarity score: {score:.3f}")
# print(f"Message: {message}")

img_test = cv2.imread("photo_test/nnq1.jpg")

bboxes1, kpss1 = det_model.detect(img_test)

print(bboxes1)
