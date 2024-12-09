import torch


def check_mps_support():
    if torch.backends.mps.is_available():
        print("MPS backend is available and ready to use with PyTorch!")
        # Kiểm tra thiết bị MPS
        device = torch.device("mps")
        print(f"PyTorch is set to use device: {device}")

        # Thử tạo một tensor trên MPS
        try:
            x = torch.ones((3, 3), device=device)
            print("Successfully created a tensor on MPS!")
            print("Tensor:", x)
        except Exception as e:
            print("An error occurred while creating a tensor on MPS:", e)
    else:
        print("MPS backend is not available on this machine.")


# Chạy kiểm tra
check_mps_support()
