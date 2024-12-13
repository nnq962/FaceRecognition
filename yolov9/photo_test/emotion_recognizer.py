from fer import FER

class EmotionRecognizer:
    def __init__(self):
        self.detector = FER()

    def get_emotion(self, image, face_rectangles):
        # Chuyển đổi face_rectangles từ (x1, y1, x2, y2) sang (x, y, w, h)
        converted_rectangles = [[x1, y1, x2 - x1, y2 - y1] for (x1, y1, x2, y2) in face_rectangles]

        # Gọi detect_emotions và lấy kết quả
        results = self.detector.detect_emotions(image, converted_rectangles)

        # Tạo danh sách lưu cảm xúc chiếm ưu thế của mỗi khuôn mặt
        dominant_emotions = []

        # Duyệt qua mỗi khuôn mặt trong kết quả
        for face_data in results:
            emotions = face_data['emotions']
            dominant_emotion = max(emotions, key=emotions.get)
            dominant_emotions.append(dominant_emotion)
        
        return dominant_emotions
