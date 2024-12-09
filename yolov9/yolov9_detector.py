import platform
import torch
import os
from pathlib import Path
from models.common import DetectMultiBackend
from utils.general import (LOGGER, Profile, check_img_size, check_requirements, colorstr, cv2,
                           increment_path, non_max_suppression, scale_boxes, strip_optimizer, xyxy2xywh)
from utils.plots import Annotator, colors, save_one_box
from utils.torch_utils import select_device
import gdown
import emotion_detector # deepface detector
import fer_detector # FER detector
from test_mtcnn import get_mtcnn_detector, check_single_face_quality
from check_bounding_box import is_valid_bounding_box
detector = get_mtcnn_detector()

def prepare_model(model_id='12Q-13lgEAu4nHb9cGchuipsSQYLc6pJN', model_name="yolov9_model.pt", model_dir="~/Models"):
    # Mở rộng đường dẫn thư mục (hỗ trợ ~)
    model_dir = os.path.expanduser(model_dir)

    # Tạo thư mục nếu chưa tồn tại
    if not os.path.exists(model_dir):
        print(f"Directory '{model_dir}' does not exist. Creating it...")
        os.makedirs(model_dir)

    # Đường dẫn đầy đủ đến tệp mô hình
    model_path = os.path.join(model_dir, model_name)

    # Kiểm tra nếu tệp mô hình chưa tồn tại thì tải
    if not os.path.exists(model_path):
        print(f"Model '{model_name}' not found in '{model_dir}'. Downloading...")
        url = f"https://drive.google.com/uc?id={model_id}"
        gdown.download(url, model_path, quiet=False)
        print(f"Model downloaded successfully to '{model_path}'.")
    else:
        print(f"Model '{model_name}' already exists in '{model_dir}'.")

    # Trả về đường dẫn mô hình
    return model_path

_model_path = prepare_model()

class Yolov9Detector:
    def __init__(self,
                 weights=_model_path,
                 data='data/coco128.yaml',
                 device=None,
                 half=False,
                 dnn=False,
                 augment=False,
                 visualize=False,
                 conf_thres=0.25,  # confidence threshold
                 iou_thres=0.45,  # NMS IOU threshold
                 max_det=1000,  # maximum detections per image
                 classes=None,  # filter by class: --class 0, or --class 0 2 3
                 agnostic_nms=False,  # class-agnostic NMS
                 line_thickness=3,  # bounding box thickness (pixels)
                 hide_labels=False,  # hide labels
                 hide_conf=False,  # hide confidences
                 update=False,  # update all models
                 mediamanager=None, # class MediaManager
                 emotion=True):

        self.device = select_device(device)
        self.weights = weights
        self.data = data
        self.half = half
        self.dnn = dnn
        self.augment = augment
        self.visualize = visualize
        self.conf_thres = conf_thres
        self.iou_thres = iou_thres
        self.max_det = max_det
        self.classes = classes
        self.agnostic_nms = agnostic_nms
        self.line_thickness = line_thickness
        self.hide_labels = hide_labels
        self.hide_conf = hide_conf
        self.update = update
        self.mediamanager = mediamanager
        self.imgsz = self.mediamanager.imgsz
        self.emotion = emotion

        self.stride = None
        self.names = None
        self.pt = None
        self.dataset = self.mediamanager.get_dataloader()
        self.webcam = self.mediamanager.webcam
        self.save_dir = self.mediamanager.get_save_directory()

        check_requirements(exclude=('tensorboard', 'thop'))
        self.model = self.load_model()

    def load_model(self):
        model = DetectMultiBackend(self.weights, device=self.device, dnn=self.dnn, data=self.data, fp16=self.half)
        self.stride, self.names, self.pt = model.stride, model.names, model.pt
        self.imgsz = check_img_size(self.imgsz, s=self.stride)
        return model

    def run_inference(self):
        batch_size = 1
        self.model.warmup(imgsz=(1 if self.pt or self.model.triton else batch_size, 3, *self.imgsz))  # warmup
        seen, windows, dt = 0, [], (Profile(), Profile(), Profile())
        for path, im, im0s, vid_cap, s in self.dataset:
            with dt[0]:
                im = torch.from_numpy(im).to(self.model.device)
                im = im.half() if self.model.fp16 else im.float()  # uint8 to fp16/32
                im /= 255  # 0 - 255 to 0.0 - 1.0
                if len(im.shape) == 3:
                    im = im[None]  # expand for batch dim

            # Inference
            with dt[1]:
                self.visualize = increment_path(self.save_dir / Path(path).stem, mkdir=True) if self.visualize else False
                pred = self.model(im,
                                  augment=self.augment,
                                  visualize=self.visualize)

            # NMS
            with dt[2]:
                pred = non_max_suppression(pred,
                                           self.conf_thres,
                                           self.iou_thres,
                                           self.classes,
                                           self.agnostic_nms,
                                           max_det=self.max_det)

            # Process predictions
            det = None # global
            result = None # global

            for i, det in enumerate(pred):  # per image
                seen += 1
                if self.webcam:  # batch_size >= 1
                    p, im0, frame = path[i], im0s[i].copy(), self.dataset.count
                    s += f'{i}: '
                else:
                    p, im0, frame = path, im0s.copy(), getattr(self.dataset, 'frame', 0)

                p = Path(p)  # to Path
                save_path = str(self.save_dir / p.name)  # im.jpg
                txt_path = str(self.save_dir / 'labels' / p.stem) + ('' if self.dataset.mode == 'image' else f'_{frame}')  # im.txt
                s += '%gx%g ' % im.shape[2:]  # print string
                gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
                imc = im0.copy() if self.mediamanager.save_crop else im0  # for save_crop
                annotator = Annotator(im0, line_width=self.line_thickness, example=str(self.names))
                if len(det):
                    # Rescale boxes from img_size to im0 size
                    det[:, :4] = scale_boxes(im.shape[2:], det[:, :4], im0.shape).round()

                    # Print results
                    for c in det[:, 5].unique():
                        n = (det[:, 5] == c).sum()  # detections per class
                        s += f"{n} {self.names[int(c)]}{'s' * (n > 1)}, "  # add to string

                    # Write results
                    for *xyxy, conf, cls in reversed(det):
                        if self.mediamanager.save_txt:  # Write to file
                            xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(
                                -1).tolist()  # normalized xywh
                            line = (cls, *xywh, conf) if self.mediamanager.save_conf else (cls, *xywh)  # label format
                            with open(f'{txt_path}.txt', 'a') as f:
                                f.write(('%g ' * len(line)).rstrip() % line + '\n')

                        c = None # global

                        # Use deepface detector
                        # if self.emotion:
                        #     xyxy_e = torch.tensor(xyxy).view(-1, 4)
                        #     xyxy_e = xyxy_e[0].int().tolist()  # Chuyển sang danh sách số nguyên
                        #     x1, y1, x2, y2 = xyxy_e  # Tách tọa độ
                        #     cropped_face = imc[y1:y2, x1:x2]
                        #     result = emotion_detector.get_dominant_emotion(emotion_detector.analyze_face(cropped_face))

                        # Use FER detector
                        if self.emotion:
                            xywh_e = xyxy2xywh(torch.tensor(xyxy).view(1, 4))
                            xywh_e = xywh_e[0].int().tolist()
                            if is_valid_bounding_box(xywh_e, min_size=50):
                                xyxy_e = torch.tensor(xyxy).view(-1, 4)
                                xyxy_e = xyxy_e[0].int().tolist()  # Chuyển sang danh sách số nguyên
                                result = fer_detector.get_dominant_emotion(fer_detector.analyze_face(imc, [xyxy_e]))[0]

                        # Add MTCNN
                        # if self.emotion:
                        #     xyxy_e = torch.tensor(xyxy).view(-1, 4)
                        #     xyxy_e = xyxy_e[0].int().tolist()  # Chuyển sang danh sách số nguyên
                        #     result_check = check_single_face_quality(detector, imc, xyxy_e)
                        #     if result_check["is_valid"]:
                        #         # Nếu khuôn mặt đạt yêu cầu, tiếp tục phân tích cảm xúc
                        #         result = fer_detector.get_dominant_emotion(
                        #             fer_detector.analyze_face(imc, [xyxy_e])
                        #         )[0]

                        if self.mediamanager.save_img or self.mediamanager.save_crop or self.mediamanager.view_img:  # Add bbox to image
                            c = int(cls)  # integer class
                            # label = None if self.hide_labels else (self.names[c] if self.hide_conf else f'{self.names[c]} {conf:.2f}')
                            label = None if self.hide_labels else (
                                self.names[c] if self.hide_conf else (
                                    f'{self.names[c]} {conf:.2f}' if result is None else f'{self.names[c]} {conf:.2f} | {result[0]} {result[1]:.2f}'
                                )
                            )
                            annotator.box_label(xyxy, label, color=colors(c, True))

                        if self.mediamanager.save_crop:
                            save_one_box(xyxy, imc, file=self.save_dir / 'crops' / self.names[c] / f'{p.stem}.jpg', BGR=True)

                # Stream results
                im0 = annotator.result()
                if self.mediamanager.view_img:
                    if platform.system() == 'Linux' and p not in windows:
                        windows.append(p)
                        cv2.namedWindow(str(p),
                                        cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)  # allow window resize (Linux)
                        cv2.resizeWindow(str(p), im0.shape[1], im0.shape[0])
                    cv2.imshow(str(p), im0)
                    cv2.waitKey(1)  # 1 millisecond

                # Save results (image with detections)
                if self.mediamanager.save_img:
                    if self.dataset.mode == 'image':
                        cv2.imwrite(save_path, im0)
                    else:  # 'video' or 'stream'
                        if self.mediamanager.vid_path[i] != save_path:  # new video
                            self.mediamanager.vid_path[i] = save_path
                            if isinstance(self.mediamanager.vid_writer[i], cv2.VideoWriter):
                                self.mediamanager.vid_writer[i].release()  # release previous video writer
                            if vid_cap:  # video
                                fps = vid_cap.get(cv2.CAP_PROP_FPS)
                                w = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                                h = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            else:  # stream
                                fps, w, h = 30, im0.shape[1], im0.shape[0]
                            save_path = str(
                                Path(save_path).with_suffix('.mp4'))  # force *.mp4 suffix on results videos
                            self.mediamanager.vid_writer[i] = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
                        self.mediamanager.vid_writer[i].write(im0)

            # Print time (inference-only)
            LOGGER.info(f"{s}{'' if len(det) else '(no detections), '}{dt[1].dt * 1E3:.1f}ms")


        # Print results
        t = tuple(x.t / seen * 1E3 for x in dt)  # speeds per image
        LOGGER.info(
            f'Speed: %.1fms pre-process, %.1fms inference, %.1fms NMS per image at shape {(1, 3, *self.imgsz)}' % t)
        if self.mediamanager.save_txt or self.mediamanager.save_img:
            s = f"\n{len(list(self.save_dir.glob('labels/*.txt')))} labels saved to {self.save_dir / 'labels'}" if self.mediamanager.save_txt else ''
            LOGGER.info(f"Results saved to {colorstr('bold', self.save_dir)}{s}")
        if self.update:
            strip_optimizer(self.weights[0])  # update model (to fix SourceChangeWarning)