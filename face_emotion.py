from emotiefflib.facial_analysis import EmotiEffLibRecognizer

class FaceEmotion:
    """
    Phân tích cảm xúc khuôn mặt
    """
    def __init__(self, model_name="enet_b2_8", device=None):
        """
        Khởi tạo nhận diện cảm xúc.
        
        Args:
            model_name (str): Tên mô hình để sử dụng ['enet_b0_8_best_vgaf', 'enet_b0_8_best_afew', 'enet_b2_8', 'enet_b0_8_va_mtl', 'enet_b2_7']
            device (str, optional): Thiết bị để chạy mô hình. Nếu None, sẽ tự động chọn 'cuda' nếu có, ngược lại chọn 'cpu'
        """
        # Tự động phát hiện thiết bị
        if device is None:
            import torch
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        self.device = device
        self.fer = EmotiEffLibRecognizer(engine="torch", model_name=model_name, device=device)
    
    def get_emotions(self, crop_faces):
        multi_emotions, _ = self.fer.predict_emotions(crop_faces, logits=True)
        return multi_emotions