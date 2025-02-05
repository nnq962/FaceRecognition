from fer import FER
import numpy as np
import tensorflow as tf


class FERUtils: 
    """
    A class to handle emotion detection using FER library with optional GPU VRAM configuration.
    """

    def __init__(self, gpu_memory_limit=None):
        """
        Initialize the FERDetector class and configure GPU VRAM usage.

        Args:
            gpu_memory_limit (int, optional): Maximum GPU memory in MB. If None, TensorFlow will use the default settings.
        """
        self.configure_gpu(gpu_memory_limit)
        print("Loading FER model...")
        self.model = FER()
        print("FER model loaded successfully!\n")

    @staticmethod
    def configure_gpu(gpu_memory_limit):
        """
        Configure TensorFlow to limit GPU memory usage.

        Args:
            gpu_memory_limit (int, optional): Maximum GPU memory in MB. If None, no limit is applied.
        """
        gpus = tf.config.experimental.list_physical_devices('GPU')
        if gpus:
            try:
                for gpu in gpus:
                    if gpu_memory_limit is not None:
                        tf.config.experimental.set_virtual_device_configuration(
                            gpu,
                            [tf.config.experimental.VirtualDeviceConfiguration(memory_limit=gpu_memory_limit)]
                        )
                        print(f"Configured TensorFlow to use a maximum of {gpu_memory_limit} MB GPU memory.")
                    else:
                        tf.config.experimental.set_memory_growth(gpu, True)
                        print("Enabled TensorFlow memory growth for GPU.")
            except RuntimeError as e:
                print(f"Failed to configure TensorFlow GPU settings: {e}")

    @staticmethod
    def xyxy2xywh(boxes):
        """
        Convert bounding boxes from [x1, y1, x2, y2] to [x, y, w, h] with integer outputs.

        Args:
            boxes (numpy.ndarray or list or tuple): Input bounding boxes.

        Returns:
            numpy.ndarray: Converted bounding boxes in [x, y, w, h] format.
        """
        if isinstance(boxes, (list, tuple)):
            boxes = np.array(boxes)

        if not isinstance(boxes, np.ndarray):
            raise TypeError(f"Expected input to be a numpy.ndarray, got {type(boxes)}")

        if boxes.ndim == 1:  # Single bounding box
            if boxes.shape[0] != 4:
                raise ValueError(f"Expected input shape to be [4], got {boxes.shape}")
            x1, y1, x2, y2 = boxes
            w = max(0, x2 - x1)
            h = max(0, y2 - y1)
            return np.array([x1, y1, w, h], dtype=np.int32)

        elif boxes.ndim == 2:  # Multiple bounding boxes
            if boxes.shape[1] != 4:
                raise ValueError(f"Expected input shape to be [N, 4], got {boxes.shape}")
            x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
            w = np.maximum(0, x2 - x1)
            h = np.maximum(0, y2 - y1)
            return np.stack((x1, y1, w, h), axis=1).astype(np.int32)

        else:
            raise ValueError(f"Expected input to have 1 or 2 dimensions, got {boxes.ndim}")

    def analyze_face(self, img, face_rectangles):
        """
        Analyze emotions from an image and bounding boxes.

        Args:
            img (numpy.ndarray): Input image.
            face_rectangles (numpy.ndarray): Bounding boxes in [x1, y1, x2, y2] format.

        Returns:
            list: Emotion detection results for each face.
        """
        # Convert bounding boxes to [x, y, w, h] format
        converted_boxes = self.xyxy2xywh(face_rectangles)
        return self.model.detect_emotions(img, converted_boxes)

    @staticmethod
    def get_dominant_emotions(batch_emotions):
        """
        Lấy cảm xúc có xác suất lớn nhất từ batch emotions.

        Args:
            batch_emotions (list): Danh sách các kết quả cảm xúc dạng:
                [{'box': [x1, y1, x2, y2], 'emotions': {'emotion1': prob1, ...}}, ...]

        Returns:
            list: Danh sách cảm xúc chiếm ưu thế với xác suất tương ứng,
                [{'dominant_emotion': 'emotion_name', 'probability': prob}, ...]
        """
        results = []
        for face in batch_emotions:
            emotions = face['emotions']
            dominant_emotion = max(emotions, key=emotions.get)  # Lấy cảm xúc có xác suất lớn nhất
            probability = emotions[dominant_emotion]  # Xác suất tương ứng
            results.append({
                'dominant_emotion': dominant_emotion,
                'probability': probability
            })
        return results