import cv2
from deepface import DeepFace

# Đọc ảnh gốc
img = cv2.imread('photo_test/happyandsad.jpg')

# Bounding boxes (trước và sau khi mở rộng)
bounding_boxes = [
    {"original": [404, 101, 510, 247], "expanded": [397, 94, 516, 253]},
    {"original": [97, 102, 203, 251], "expanded": [90, 95, 209, 257]},
]

# Hàm crop và phân tích cảm xúc
def analyze_face(cropped_face):
    return DeepFace.analyze(
        img_path=cropped_face,
        actions=["emotion"],
        detector_backend="skip",
        align=False
    )

def get_dominant_emotion(result):
    if not result or 'emotion' not in result[0]:
        return None, None  # Trả về None nếu kết quả không hợp lệ

    emotions = result[0]['emotion']
    dominant_emotion = max(emotions, key=emotions.get)  # Cảm xúc có xác suất lớn nhất
    dominant_probability = emotions[dominant_emotion]  # Xác suất tương ứng

    # Chuẩn hóa xác suất về khoảng [0, 1]
    normalized_probability = dominant_probability / 100
    return dominant_emotion, int(normalized_probability * 100) / 100

# Kết quả phân tích cảm xúc
results = []

for bbox in bounding_boxes:
    result_entry = {}

    # Crop vùng bounding box gốc (original)
    original_crop = img[bbox["original"][1]:bbox["original"][3], bbox["original"][0]:bbox["original"][2]]
    original_result = analyze_face(original_crop)
    emotion, probability = get_dominant_emotion(original_result)
    result_entry["original"] = {"emotion": emotion, "probability": probability}

    # Crop vùng bounding box mở rộng (expanded)
    expanded_crop = img[bbox["expanded"][1]:bbox["expanded"][3], bbox["expanded"][0]:bbox["expanded"][2]]
    expanded_result = analyze_face(expanded_crop)
    emotion, probability = get_dominant_emotion(expanded_result)
    result_entry["expanded"] = {"emotion": emotion, "probability": probability}

    results.append(result_entry)

print(results)
