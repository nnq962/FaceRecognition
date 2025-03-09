import sys
import torch
import warnings
from torch.serialization import SourceChangeWarning

# Tắt cảnh báo SourceChangeWarning
warnings.filterwarnings("ignore", category=SourceChangeWarning)

sys.path.append('Face_mask_detection/')

def load_pytorch_model(model_path):
    model = torch.load(model_path, weights_only=False)
    return model

def pytorch_inference(model, img_arr):
    if torch.cuda.is_available():
        dev = 'cuda:0'
    else:
        dev = 'cpu'
    device = torch.device(dev)
    model.to(device)
    input_tensor = torch.tensor(img_arr).float().to(device)
    y_bboxes, y_scores, = model.forward(input_tensor)
    return y_bboxes.detach().cpu().numpy(), y_scores.detach().cpu().numpy()
