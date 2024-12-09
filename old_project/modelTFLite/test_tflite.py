import tensorflow as tf
from typing import Sequence, Tuple, Union
import numpy as np
import os
import cv2
import requests
import logging
import base64
from PIL import Image


logging.basicConfig(level=logging.INFO)
log = logging.getLogger("fer")
PADDING = 40
NumpyRects = Union[np.ndarray, Sequence[Tuple[int, int, int, int]]]

class InvalidImage(Exception):
    pass

def loadBase64Img(uri):
    encoded_data = uri.split(",")[1]
    nparr = np.fromstring(base64.b64decode(encoded_data), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

def pil_to_bgr(pil_image):
    return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

def load_image(img):
    """Modified from github.com/serengil/deepface. Returns bgr (opencv-style) numpy array."""
    is_exact_image = is_base64_img = is_url_img = False

    if type(img).__module__ == np.__name__:
        is_exact_image = True
    elif img is None:
        raise InvalidImage("Image not valid.")
    elif len(img) > 11 and img[0:11] == "data:image/":
        is_base64_img = True
    elif len(img) > 11 and img.startswith("http"):
        is_url_img = True

    if is_base64_img:
        img = loadBase64Img(img)
    elif is_url_img:
        img = pil_to_bgr(Image.open(requests.get(img, stream=True).raw))
    elif not is_exact_image:  # image path passed as input
        if not os.path.isfile(img):
            raise ValueError(f"Confirm that {img} exists")
        img = cv2.imread(img)

    if img is None or not hasattr(img, "shape"):
        raise InvalidImage("Image not valid.")

    return img

class FERMINI:
    def __init__(self,
                 offsets: tuple = (10, 10)):
        
        self.emotions = None
        self.__offsets = offsets
        self._initialize_model()

    @staticmethod
    def _get_labels():
        return {
            0: "angry",
            1: "disgust",
            2: "fear",
            3: "happy",
            4: "sad",
            5: "surprise",
            6: "neutral",
        }
    
    @staticmethod
    def pad(image):
        """Pad image."""
        row, col = image.shape[:2]
        bottom = image[row - 2 : row, 0:col]
        mean = cv2.mean(bottom)[0]

        padded_image = cv2.copyMakeBorder(
            image,
            top=PADDING,
            bottom=PADDING,
            left=PADDING,
            right=PADDING,
            borderType=cv2.BORDER_CONSTANT,
            value=[mean, mean, mean],
        )
        return padded_image
    
    @staticmethod
    def tosquare(bbox):
        """Convert bounding box to square by elongating shorter side."""
        x, y, w, h = bbox
        if h > w:
            diff = h - w
            x -= diff // 2
            w += diff
        elif w > h:
            diff = w - h
            y -= diff // 2
            h += diff
        if w != h:
            log.debug(f"{w} is not {h}")

        return x, y, w, h

    def __apply_offsets(self, face_coordinates):
        """Offset face coordinates with padding before classification.
        x1, x2, y1, y2 = 0, 100, 0, 100 becomes -10, 110, -10, 110
        """
        x, y, width, height = face_coordinates
        x_off, y_off = self.__offsets
        x1 = x - x_off
        x2 = x + width + x_off
        y1 = y - y_off
        y2 = y + height + y_off
        return x1, x2, y1, y2

    def _initialize_model(self):
        # Đường dẫn xác định đến tệp TFLite
        emotion_model_path = "emotion_model.tflite"
        log.debug("Emotion model TFLite: {}".format(emotion_model_path))

        # Tải mô hình TFLite
        self.__emotion_classifier = tf.lite.Interpreter(model_path=emotion_model_path)
        self.__emotion_classifier.allocate_tensors()

        # Lấy thông tin đầu vào và đầu ra của mô hình
        self.__input_details = self.__emotion_classifier.get_input_details()
        self.__output_details = self.__emotion_classifier.get_output_details()

        # Xác định kích thước đầu vào cần thiết cho mô hình TFLite
        self.__emotion_target_size = self.__input_details[0]['shape'][1:3]
        return

    @staticmethod
    def __preprocess_input(x, v2=False):
        x = x.astype("float32")
        x = x / 255.0
        if v2:
            x = x - 0.5
            x = x * 2.0
        return x

    def _classify_emotions(self, gray_faces):
        # Đảm bảo rằng gray_faces có kích thước đúng như yêu cầu của mô hình TFLite
        gray_faces_resized = [face.reshape(self.__input_details[0]['shape']).astype(np.float32) for face in gray_faces]

        predictions = []
        for face in gray_faces_resized:
            # Đặt tensor đầu vào cho mô hình TFLite
            self.__emotion_classifier.set_tensor(self.__input_details[0]['index'], face)

            # Thực hiện suy luận
            self.__emotion_classifier.invoke()

            # Lấy kết quả từ tensor đầu ra
            emotion_prediction = self.__emotion_classifier.get_tensor(self.__output_details[0]['index'])
            predictions.append(emotion_prediction)

        return predictions

    def detect_emotions(self, img, face_rectangles) -> list:
        # Load BGR image
        img = load_image(img)

        emotion_labels = self._get_labels()

        # Convert BGR to GRAY image
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray_img = self.pad(gray_img)

        emotions = []
        gray_faces = []

        if face_rectangles is not None:
            for face_coordinates in face_rectangles:
                face_coordinates = self.tosquare(face_coordinates)

                # offset to expand bounding box
                # Note: x1 and y1 can be negative
                x1, x2, y1, y2 = self.__apply_offsets(face_coordinates)

                # account for padding in bounding box coordinates
                x1 += PADDING
                y1 += PADDING
                x2 += PADDING
                y2 += PADDING
                x1 = np.clip(x1, a_min=0, a_max=None)
                y1 = np.clip(y1, a_min=0, a_max=None)

                gray_face = gray_img[max(0, y1) : y2, max(0, x1) : x2]

                try:
                    gray_face = cv2.resize(gray_face, self.__emotion_target_size)
                except Exception as e:
                    log.warning("{} resize failed: {}".format(gray_face.shape, e))
                    continue

                gray_face = self.__preprocess_input(gray_face, True)
                gray_faces.append(gray_face)

        # predict all faces
        if not len(gray_faces):
            return emotions  # no valid faces

        # classify emotions
        emotion_predictions = self._classify_emotions(np.array(gray_faces))

        # label scores
        for face_idx, face in enumerate(emotion_predictions):
            # Đảm bảo lấy toàn bộ 7 giá trị đầu ra cho mỗi cảm xúc
            labelled_emotions = {
                emotion_labels[idx]: round(float(score), 2)
                for idx, score in enumerate(face[0])  # Lấy toàn bộ 7 giá trị trong mảng đầu ra
            }

            emotions.append(
                dict(box=face_rectangles[face_idx], emotions=labelled_emotions)
            )

        self.emotions = emotions
        return emotions


