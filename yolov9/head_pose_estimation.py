import mediapipe as mp
import cv2
import numpy as np
import pandas as pd
import pickle

model = pickle.load(open('./head_pose_model.pkl', 'rb'))

cols = []
for pos in ['nose_', 'forehead_', 'left_eye_', 'mouth_left_', 'chin_', 'right_eye_', 'mouth_right_']:
    for dim in ('x', 'y'):
        cols.append(pos+dim)


def extract_features(img, face_mesh):
    NOSE = 1
    FOREHEAD = 10
    LEFT_EYE = 33
    MOUTH_LEFT = 61
    CHIN = 199
    RIGHT_EYE = 263
    MOUTH_RIGHT = 291

    result = face_mesh.process(img)
    face_features = []
    
    if result.multi_face_landmarks != None:
        for face_landmarks in result.multi_face_landmarks:
            for idx, lm in enumerate(face_landmarks.landmark):
                if idx in [FOREHEAD, NOSE, MOUTH_LEFT, MOUTH_RIGHT, CHIN, LEFT_EYE, RIGHT_EYE]:
                    face_features.append(lm.x)
                    face_features.append(lm.y)

    return face_features

def normalize(poses_df):
    normalized_df = poses_df.copy()
    
    for dim in ['x', 'y']:
        # Centerning around the nose 
        for feature in ['forehead_'+dim, 'nose_'+dim, 'mouth_left_'+dim, 'mouth_right_'+dim, 'left_eye_'+dim, 'chin_'+dim, 'right_eye_'+dim]:
            normalized_df[feature] = poses_df[feature] - poses_df['nose_'+dim]
        
        
        # Scaling
        diff = normalized_df['mouth_right_'+dim] - normalized_df['left_eye_'+dim]
        for feature in ['forehead_'+dim, 'nose_'+dim, 'mouth_left_'+dim, 'mouth_right_'+dim, 'left_eye_'+dim, 'chin_'+dim, 'right_eye_'+dim]:
            normalized_df[feature] = normalized_df[feature] / diff
    
    return normalized_df


def draw_axes(img, pitch, yaw, roll, tx, ty, size=50):
    yaw = -yaw
    rotation_matrix = cv2.Rodrigues(np.array([pitch, yaw, roll]))[0].astype(np.float64)
    axes_points = np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0]
    ], dtype=np.float64)
    axes_points = rotation_matrix @ axes_points
    axes_points = (axes_points[:2, :] * size).astype(int)
    axes_points[0, :] = axes_points[0, :] + tx
    axes_points[1, :] = axes_points[1, :] + ty
    
    new_img = img.copy()
    cv2.line(new_img, tuple(axes_points[:, 3].ravel()), tuple(axes_points[:, 0].ravel()), (255, 0, 0), 3)    
    cv2.line(new_img, tuple(axes_points[:, 3].ravel()), tuple(axes_points[:, 1].ravel()), (0, 255, 0), 3)    
    cv2.line(new_img, tuple(axes_points[:, 3].ravel()), tuple(axes_points[:, 2].ravel()), (0, 0, 255), 3)
    return new_img


face_mesh = mp.solutions.face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5)


def check_face_orientation(img):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    face_features = extract_features(img, face_mesh)
    
    if len(face_features):
        face_features_df = pd.DataFrame([face_features], columns=cols)
        face_features_normalized = normalize(face_features_df)
        pitch_pred, yaw_pred, roll_pred = model.predict(face_features_normalized.values).ravel()

        # Chuyển đổi từ radian sang độ
        pitch_deg = np.degrees(pitch_pred)
        yaw_deg = np.degrees(yaw_pred)
        roll_deg = np.degrees(roll_pred)

        # Kiểm tra các giới hạn nghiêng của khuôn mặt (đơn vị độ)
        pitch_min, pitch_max = -30, 30  # [-30, 30] độ
        yaw_min, yaw_max = -45, 45      # [-45, 45] độ

        if pitch_min <= pitch_deg <= pitch_max and yaw_min <= yaw_deg <= yaw_max:
            return True
        else:
            return False

    else:
        return False
