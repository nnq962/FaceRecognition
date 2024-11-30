import torch

# Kiểm tra xem MPS có khả dụng không
if torch.backends.mps.is_available():
    device = torch.device("mps")  # Chọn MPS làm thiết bị
    print("MPS backend is available")
else:
    print("MPS backend is not available")
