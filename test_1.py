from yolo_detector import YoloDetector
import yolo_detector_utils
import cv2

img1 = cv2.imread("data_test/2person.jpg")
img2 = cv2.imread("data_test/2person.jpg")
img3 = cv2.imread("data_test/nnq1.jpg")

imgs = [img1, img2, img3]

detector = YoloDetector()

pred = detector.get_face_detects(imgs, verbose=True, conf=0.65)

face_counts = []  # Lưu số lượng khuôn mặt trong từng ảnh để ghép lại sau này
all_crop_faces = []  # Danh sách chứa toàn bộ khuôn mặt đã crop (dạng phẳng)

# Crop all faces
for i, faces in enumerate(pred):
    im0 = imgs[i]

    if not faces:  # Không có khuôn mặt nào được phát hiện
        face_counts.append(0)
        continue
    
    cropped_faces = detector.crop_faces(im0, faces=faces, margin=10)  # Cắt khuôn mặt
    
    all_crop_faces.extend(cropped_faces)  # Thêm tất cả khuôn mặt vào danh sách chính (dạng phẳng)
    face_counts.append(len(faces))  # Ghi lại số lượng khuôn mặt đã cắt

    # Phân tích cảm xúc
    all_emotions = []
    for i, faces in enumerate(pred):
        im0 = imgs[i]  # Lấy ảnh tương ứng
        emotions = detector.get_face_emotions(im0, faces)
        all_emotions.extend(emotions)

print("DEBUG:", all_emotions)
print(len(all_emotions))

