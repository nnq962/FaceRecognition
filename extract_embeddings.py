import face_recognition
import cv2
import numpy as np

class FaceEmbeddingExtractor:
    def __init__(self):
        pass

    @staticmethod
    def extract_embeddings(frame, face_locations):
        """
        Lấy embedding cho nhiều khuôn mặt từ một khung hình, với thông tin về vị trí khuôn mặt đã có sẵn.
        :param frame: Khung hình chứa khuôn mặt (dạng BGR - OpenCV).
        :param face_locations: Danh sách các bounding boxes của khuôn mặt trong khung hình.
                              (Danh sách đang ở dạng [left, top, right, bottom])
        :return: Danh sách các vector embedding cho từng khuôn mặt.
        """
        if not face_locations:
            return []

        # Chuyển frame từ BGR sang RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # TODO: change to numpy

        # Đổi thứ tự từ [left, top, right, bottom] sang [top, right, bottom, left]
        converted_locations = [(top, right, bottom, left) for left, top, right, bottom in face_locations]

        # Lấy embedding cho tất cả các khuôn mặt dựa vào converted_locations
        embeddings = face_recognition.face_encodings(rgb_frame, converted_locations)

        return embeddings
