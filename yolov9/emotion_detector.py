from deepface import DeepFace

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
    return [dominant_emotion, int(normalized_probability * 100) / 100]