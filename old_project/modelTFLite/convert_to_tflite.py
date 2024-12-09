import tensorflow as tf
from tensorflow.keras.models import load_model
import pkg_resources

# Đường dẫn đến tệp .hdf5 trong thư viện "fer"
emotion_model_path = "emotion_model.hdf5"

# Bước 1: Tải mô hình HDF5
emotion_model = load_model(emotion_model_path, compile=False)

# Bước 2: Chuyển đổi sang định dạng TFLite
converter = tf.lite.TFLiteConverter.from_keras_model(emotion_model)
tflite_model = converter.convert()

# Bước 3: Lưu mô hình TFLite vào tệp
with open("emotion_model.tflite", "wb") as f:
    f.write(tflite_model)

print("Mô hình đã được chuyển đổi thành công sang định dạng .tflite")
