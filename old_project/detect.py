import argparse
import os
import platform
import sys
from pathlib import Path
import torch

from yolov9.models.common import DetectMultiBackend
from yolov9.utils.dataloaders import IMG_FORMATS, VID_FORMATS, LoadImages, LoadScreenshots, LoadStreams
from yolov9.utils.general import (LOGGER, Profile, check_file, check_img_size, check_imshow, check_requirements, colorstr, cv2,
                           increment_path, non_max_suppression, print_args, scale_boxes, strip_optimizer, xyxy2xywh)
from yolov9.utils.plots import Annotator, colors, save_one_box
from yolov9.utils.torch_utils import select_device, smart_inference_mode


class DetectionPipeline:
    def __init__(self, config):
        self.imgsz = None
        self.pt = None
        self.names = None
        self.stride = None
        self.config = config
        self.device = select_device(config.device)
        self.save_dir = increment_path(Path(config.project) / config.name, exist_ok=config.exist_ok)
        (self.save_dir / 'labels' if config.save_txt else self.save_dir).mkdir(parents=True, exist_ok=True)
        self.model = self.load_model()

    def load_model(self):
        model = DetectMultiBackend(self.config.weights, device=self.device, dnn=self.config.dnn, data=self.config.data, fp16=self.config.half)
        self.stride, self.names, self.pt = model.stride, model.names, model.pt
        self.imgsz = check_img_size(self.config.imgsz, s=self.stride)
        return model



def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', nargs='+', type=str, default='yolo.pt', help='model path or triton URL')
    parser.add_argument('--source', type=str, default='data/images', help='file/dir/URL/glob/screen/0(webcam)')
    parser.add_argument('--data', type=str, default='data/coco.yaml', help='dataset.yaml path')
    parser.add_argument('--imgsz', nargs='+', type=int, default=[640], help='inference size (h, w)')
    parser.add_argument('--conf-thres', type=float, default=0.25, help='confidence threshold')
    parser.add_argument('--iou-thres', type=float, default=0.45, help='NMS IOU threshold')
    parser.add_argument('--max-det', type=int, default=1000, help='maximum detections per image')
    parser.add_argument('--device', default='', help='cuda device or cpu')
    parser.add_argument('--view-img', action='store_true', help='view images during inference')
    parser.add_argument('--save-txt', action='store_true', help='save results to text file')
    parser.add_argument('--save-conf', action='store_true', help='save confidences in --save-txt labels')
    parser.add_argument('--nosave', action='store_true', help='do not save images/videos')
    parser.add_argument('--project', default='runs/detect', help='project directory')
    parser.add_argument('--name', default='exp', help='experiment name')
    parser.add_argument('--exist-ok', action='store_true', help='overwrite existing project')
    parser.add_argument('--augment', action='store_true', help='use augmented inference')
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    pipeline = DetectionPipeline(args)
    pipeline.run()
