from insightface.model_zoo import model_zoo

def load_models(det_model_path, rec_model_path, det_ctx_id=0, rec_ctx_id=0, input_size=(640, 640)):
    """
    Load detection and recognition models.

    Args:
        det_model_path (str): Đường dẫn tới mô hình phát hiện khuôn mặt.
        rec_model_path (str): Đường dẫn tới mô hình nhận diện khuôn mặt.
        det_ctx_id (int): Context ID cho GPU của mô hình phát hiện (mặc định: 0).
        rec_ctx_id (int): Context ID cho GPU của mô hình nhận diện (mặc định: 0).
        input_size (tuple): Kích thước đầu vào của mô hình phát hiện (mặc định: (640, 640)).

    Returns:
        tuple: (det_model, rec_model)
            - det_model: Mô hình phát hiện khuôn mặt.
            - rec_model: Mô hình nhận diện khuôn mặt.
    """
    # Load detection model
    print("Loading detection model...")
    det_model = model_zoo.get_model(det_model_path)
    det_model.prepare(ctx_id=det_ctx_id, input_size=input_size)
    print("Detection model loaded successfully.")

    # Load recognition model
    print("Loading recognition model...")
    rec_model = model_zoo.get_model(rec_model_path)
    rec_model.prepare(ctx_id=rec_ctx_id)
    print("Recognition model loaded successfully.")

    return det_model, rec_model


# Đường dẫn tới các mô hình
det_model_path = "~/Models/det_10g.onnx"
rec_model_path = "~/Models/w600k_r50.onnx"

# Gọi hàm để tải mô hình
det_model, rec_model = load_models(det_model_path, rec_model_path)

# Kiểm tra mô hình
print(det_model)
print(rec_model)