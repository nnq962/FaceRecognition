import argparse
import os
import platform
import sys
from pathlib import Path

import torch

FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]  # Thư mục gốc YOLO
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))  # thêm ROOT vào PATH
ROOT = Path(os.path.relpath(ROOT, Path.cwd()))  # tương đối

from models.common import DetectMultiBackend
from utils.dataloaders import IMG_FORMATS, VID_FORMATS, LoadImages, LoadScreenshots, LoadStreams
from utils.general import (LOGGER, Profile, check_file, check_img_size, check_imshow, check_requirements, colorstr, cv2,
                           increment_path, non_max_suppression, print_args, scale_boxes, strip_optimizer, xyxy2xywh)
from utils.plots import Annotator, colors, save_one_box
from utils.torch_utils import select_device, smart_inference_mode


class Detector:
    @smart_inference_mode()
    def __init__(self,
                 weights=ROOT / 'yolo.pt',
                 data=ROOT / 'data/coco.yaml',
                 device='',
                 half=False,
                 dnn=False,
                 imgsz=(640, 640),
                 conf_thres=0.25,
                 iou_thres=0.45,
                 max_det=1000,
                 classes=None,
                 agnostic_nms=False,
                 augment=False,
                 visualize=False,
                 line_thickness=3,
                 hide_labels=False,
                 hide_conf=False):
        # Khởi tạo và tải mô hình
        self.weights = weights
        self.data = data
        self.device = select_device(device)
        self.half = half
        self.dnn = dnn
        self.imgsz = check_img_size(imgsz, s=32)  # sẽ được đặt sau khi tải mô hình
        self.conf_thres = conf_thres
        self.iou_thres = iou_thres
        self.max_det = max_det
        self.classes = classes
        self.agnostic_nms = agnostic_nms
        self.augment = augment
        self.visualize = visualize
        self.line_thickness = line_thickness
        self.hide_labels = hide_labels
        self.hide_conf = hide_conf

        # Tải mô hình
        self.model = DetectMultiBackend(self.weights, device=self.device, dnn=self.dnn, data=self.data, fp16=self.half)
        self.stride, self.names, self.pt = self.model.stride, self.model.names, self.model.pt
        self.imgsz = check_img_size(self.imgsz, s=self.stride)  # kiểm tra kích thước ảnh

    @smart_inference_mode()
    def run(self,
            source=ROOT / 'data/images',
            save_txt=False,
            save_conf=False,
            save_crop=False,
            nosave=True,
            view_img=False,
            vid_stride=1,
            project=ROOT / 'runs/detect',
            name='exp',
            exist_ok=False,
            update=False):
        source = str(source)
        save_img = not nosave and not source.endswith('.txt')  # lưu ảnh suy luận
        is_file = Path(source).suffix[1:] in (IMG_FORMATS + VID_FORMATS)
        is_url = source.lower().startswith(('rtsp://', 'rtmp://', 'http://', 'https://'))
        webcam = source.isnumeric() or source.endswith('.txt') or (is_url and not is_file)
        screenshot = source.lower().startswith('screen')
        if is_url and is_file:
            source = check_file(source)  # tải xuống nếu là URL

        # Thư mục
        save_dir = increment_path(Path(project) / name, exist_ok=exist_ok)  # tăng tên thư mục
        (save_dir / 'labels' if save_txt else save_dir).mkdir(parents=True, exist_ok=True)  # tạo thư mục

        # Dataloader
        bs = 1  # kích thước batch
        if webcam:
            view_img = check_imshow(warn=True)
            dataset = LoadStreams(source, img_size=self.imgsz, stride=self.stride, auto=self.pt, vid_stride=vid_stride)
            bs = len(dataset)
        elif screenshot:
            dataset = LoadScreenshots(source, img_size=self.imgsz, stride=self.stride, auto=self.pt)
        else:
            dataset = LoadImages(source, img_size=self.imgsz, stride=self.stride, auto=self.pt, vid_stride=vid_stride)
        vid_path, vid_writer = [None] * bs, [None] * bs

        # Chạy suy luận
        self.model.warmup(imgsz=(1 if self.pt or self.model.triton else bs, 3, *self.imgsz))  # khởi động
        seen, windows, dt = 0, [], (Profile(), Profile(), Profile())
        for path, im, im0s, vid_cap, s in dataset:
            with dt[0]:
                im = torch.from_numpy(im).to(self.model.device)
                im = im.half() if self.model.fp16 else im.float()  # chuyển đổi uint8 sang fp16/32
                im /= 255  # chuẩn hóa 0 - 255 thành 0.0 - 1.0
                if len(im.shape) == 3:
                    im = im[None]  # mở rộng cho batch dim

            # Suy luận
            with dt[1]:
                visualize = increment_path(save_dir / Path(path).stem, mkdir=True) if self.visualize else False
                pred = self.model(im, augment=self.augment, visualize=visualize)

            # NMS
            with dt[2]:
                pred = non_max_suppression(pred, self.conf_thres, self.iou_thres, self.classes, self.agnostic_nms, max_det=self.max_det)

            # Xử lý dự đoán
            for i, det in enumerate(pred):  # mỗi ảnh
                seen += 1
                if webcam:  # batch_size >= 1
                    p, im0, frame = path[i], im0s[i].copy(), dataset.count
                    s += f'{i}: '
                else:
                    p, im0, frame = path, im0s.copy(), getattr(dataset, 'frame', 0)

                p = Path(p)  # chuyển thành Path
                save_path = str(save_dir / p.name)  # đường dẫn lưu ảnh
                txt_path = str(save_dir / 'labels' / p.stem) + ('' if dataset.mode == 'image' else f'_{frame}')  # đường dẫn lưu txt
                s += '%gx%g ' % im.shape[2:]  # chuỗi in
                gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # hệ số chuẩn hóa whwh
                imc = im0.copy() if save_crop else im0  # cho save_crop
                annotator = Annotator(im0, line_width=self.line_thickness, example=str(self.names))
                if len(det):
                    # Chuyển đổi hộp từ img_size sang kích thước im0
                    det[:, :4] = scale_boxes(im.shape[2:], det[:, :4], im0.shape).round()

                    # In kết quả
                    for c in det[:, 5].unique():
                        n = (det[:, 5] == c).sum()  # số lượng phát hiện mỗi lớp
                        s += f"{n} {self.names[int(c)]}{'s' * (n > 1)}, "  # thêm vào chuỗi

                    # Ghi kết quả
                    for *xyxy, conf, cls in reversed(det):
                        if save_txt:  # Ghi vào file
                            xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # xywh chuẩn hóa
                            line = (cls, *xywh, conf) if save_conf else (cls, *xywh)  # định dạng nhãn
                            with open(f'{txt_path}.txt', 'a') as f:
                                f.write(('%g ' * len(line)).rstrip() % line + '\n')

                        if save_img or save_crop or view_img:  # Thêm bbox vào ảnh
                            c = int(cls)  # lớp dưới dạng số nguyên
                            label = None if self.hide_labels else (self.names[c] if self.hide_conf else f'{self.names[c]} {conf:.2f}')
                            annotator.box_label(xyxy, label, color=colors(c, True))
                        if save_crop:
                            save_one_box(xyxy, imc, file=save_dir / 'crops' / self.names[c] / f'{p.stem}.jpg', BGR=True)

                # Hiển thị kết quả
                im0 = annotator.result()
                if view_img:
                    if platform.system() == 'Linux' and p not in windows:
                        windows.append(p)
                        cv2.namedWindow(str(p), cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)  # cho phép thay đổi kích thước cửa sổ (Linux)
                        cv2.resizeWindow(str(p), im0.shape[1], im0.shape[0])
                    cv2.imshow(str(p), im0)
                    cv2.waitKey(1)  # 1 millisecond

                # Lưu kết quả (ảnh với phát hiện)
                if save_img:
                    if dataset.mode == 'image':
                        cv2.imwrite(save_path, im0)
                    else:  # 'video' hoặc 'stream'
                        if vid_path[i] != save_path:  # video mới
                            vid_path[i] = save_path
                            if isinstance(vid_writer[i], cv2.VideoWriter):
                                vid_writer[i].release()  # giải phóng bộ ghi video trước đó
                            if vid_cap:  # video
                                fps = vid_cap.get(cv2.CAP_PROP_FPS)
                                w = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                                h = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            else:  # stream
                                fps, w, h = 30, im0.shape[1], im0.shape[0]
                            save_path = str(Path(save_path).with_suffix('.mp4'))  # ép đuôi *.mp4 cho video kết quả
                            vid_writer[i] = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
                        vid_writer[i].write(im0)

            # In thời gian (chỉ suy luận)
            LOGGER.info(f"{s}{'' if len(det) else '(không có phát hiện), '}{dt[1].dt * 1E3:.1f}ms")

        # In kết quả
        t = tuple(x.t / seen * 1E3 for x in dt)  # tốc độ mỗi ảnh
        LOGGER.info(f'Tốc độ: %.1fms tiền xử lý, %.1fms suy luận, %.1fms NMS mỗi ảnh với hình dạng {(1, 3, *self.imgsz)}' % t)
        if save_txt or save_img:
            s = f"\n{len(list(save_dir.glob('labels/*.txt')))} nhãn đã lưu vào {save_dir / 'labels'}" if save_txt else ''
            LOGGER.info(f"Kết quả đã lưu vào {colorstr('bold', save_dir)}{s}")
        if update:
            strip_optimizer(self.weights[0])  # cập nhật mô hình (để sửa SourceChangeWarning)


def parse_opt():
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', nargs='+', type=str, default=ROOT / 'yolov9_model.pt', help='đường dẫn mô hình hoặc URL triton')
    parser.add_argument('--source', type=str, default=ROOT / 'data/images', help='file/dir/URL/glob/screen/0(webcam)')
    parser.add_argument('--data', type=str, default=ROOT / 'data/coco128.yaml', help='(tùy chọn) đường dẫn dataset.yaml')
    parser.add_argument('--imgsz', '--img', '--img-size', nargs='+', type=int, default=[640], help='kích thước suy luận h,w')
    parser.add_argument('--conf-thres', type=float, default=0.25, help='ngưỡng tin cậy')
    parser.add_argument('--iou-thres', type=float, default=0.45, help='ngưỡng IoU NMS')
    parser.add_argument('--max-det', type=int, default=200, help='số lượng phát hiện tối đa mỗi ảnh')
    parser.add_argument('--device', default='', help='thiết bị cuda, ví dụ 0 hoặc 0,1,2,3 hoặc cpu')
    parser.add_argument('--view-img', action='store_true', help='hiển thị kết quả')
    parser.add_argument('--save-txt', action='store_true', help='lưu kết quả vào *.txt')
    parser.add_argument('--save-conf', action='store_true', help='lưu độ tin cậy trong nhãn --save-txt')
    parser.add_argument('--save-crop', action='store_true', help='lưu các hộp dự đoán đã cắt')
    parser.add_argument('--nosave', action='store_true', help='không lưu ảnh/video')
    parser.add_argument('--classes', nargs='+', type=int, help='lọc theo lớp: --classes 0, hoặc --classes 0 2 3')
    parser.add_argument('--agnostic-nms', action='store_true', help='NMS không phân biệt lớp')
    parser.add_argument('--augment', action='store_true', help='suy luận tăng cường')
    parser.add_argument('--visualize', action='store_true', help='trực quan hóa các đặc trưng')
    parser.add_argument('--update', action='store_true', help='cập nhật tất cả các mô hình')
    parser.add_argument('--project', default=ROOT / 'runs/detect', help='lưu kết quả vào project/name')
    parser.add_argument('--name', default='exp', help='lưu kết quả vào project/name')
    parser.add_argument('--exist-ok', action='store_true', help='cho phép project/name đã tồn tại, không tăng số')
    parser.add_argument('--line-thickness', default=1, type=int, help='độ dày khung bao (pixel)')
    parser.add_argument('--hide-labels', default=False, action='store_true', help='ẩn nhãn')
    parser.add_argument('--hide-conf', default=False, action='store_true', help='ẩn độ tin cậy')
    parser.add_argument('--half', action='store_true', help='sử dụng suy luận FP16 nửa chính xác')
    parser.add_argument('--dnn', action='store_true', help='sử dụng OpenCV DNN cho suy luận ONNX')
    parser.add_argument('--vid-stride', type=int, default=1, help='bước khung hình video')
    opt = parser.parse_args()
    opt.imgsz *= 2 if len(opt.imgsz) == 1 else 1  # mở rộng
    print_args(vars(opt))
    return opt


def main(opt):
    check_requirements(exclude=('tensorboard', 'thop'))
    detector = Detector(weights=opt.weights,
                        data=opt.data,
                        device=opt.device,
                        half=opt.half,
                        dnn=opt.dnn,
                        imgsz=opt.imgsz,
                        conf_thres=opt.conf_thres,
                        iou_thres=opt.iou_thres,
                        max_det=opt.max_det,
                        classes=opt.classes,
                        agnostic_nms=opt.agnostic_nms,
                        augment=opt.augment,
                        visualize=opt.visualize,
                        line_thickness=opt.line_thickness,
                        hide_labels=opt.hide_labels,
                        hide_conf=opt.hide_conf)
    detector.run(source=opt.source,
                 save_txt=opt.save_txt,
                 save_conf=opt.save_conf,
                 save_crop=opt.save_crop,
                 nosave=opt.nosave,
                 view_img=opt.view_img,
                 vid_stride=opt.vid_stride,
                 project=opt.project,
                 name=opt.name,
                 exist_ok=opt.exist_ok,
                 update=opt.update)


if __name__ == "__main__":
    opt = parse_opt()
    main(opt)
