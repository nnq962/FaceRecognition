import cv2
import numpy as np
from insightface.app.common import Face
from insightface.model_zoo import model_zoo
import os

det_model_path = os.path.expanduser("~/Models/det_10g.onnx")
rec_model_path = os.path.expanduser("~/Models/w600k_r50.onnx")


class InsightFaceDetector:
    """
    InsightFaceDetector is a class for detecting and recognizing faces using InsightFace models.
    
    Args:
        media_manager: An optional media manager object for handling datasets.
    """
    def __init__(self,
                media_manager=None) -> None:
        self.det_model = None
        self.rec_model = None
        self.media_manager = media_manager
        self.dataset = self.media_manager.get_dataloader() 

        self.load_model()

    def load_model(self):
        """Load detection and recognition models"""
        self.det_model = model_zoo.get_model(det_model_path)
        self.det_model.prepare(ctx_id=0, input_size=(640, 640))
        
        self.rec_model = model_zoo.get_model(rec_model_path)
        self.rec_model.prepare(ctx_id=0)

    def get_face_detect(self, img):
        """
        Detect faces in the input image
        Args:
            img: Input image (BGR format)
        Returns:
            List of tuples, each containing (bbox, confidence, keypoints)
            - bbox: numpy array [x1, y1, x2, y2]
            - confidence: float value
            - keypoints: numpy array of facial landmarks
        """
        bboxes, kpss = self.det_model.detect(img)
        if bboxes is None:
            return []
        
        results = []
        for bbox, kps in zip(bboxes, kpss):
            bbox_coords = bbox[:4]  # [x1, y1, x2, y2]
            confidence = bbox[4]
            
            results.append((bbox_coords, confidence, kps))
        return results

    def get_face_embedding(self, img, face):
        """
        Get face embedding for recognition
        Args:
            img: Input image (BGR format)
            face: Face object containing bbox and landmarks
        Returns:
            Face embedding vector (numpy array)
        """
        aimg = Face.align_face(img, face.landmark)
        embedding = self.rec_model.get_feat(aimg)
        return embedding

    def draw_detection(self, img, faces):
        """
        Draw detection results on image
        Args:
            img: Input image
            faces: List of Face objects
        Returns:
            Image with drawn detections
        """
        dimg = img.copy()
        for face in faces:
            box = face.bbox.astype(np.int32)
            # Lấy điểm tin cậy từ bbox
            conf = face.bbox[4]
            
            # Màu dựa vào độ tin cậy (đỏ -> xanh lá)
            color = (0, int(255 * conf), int(255 * (1 - conf)))
            
            # Vẽ bbox
            cv2.rectangle(dimg, (box[0], box[1]), (box[2], box[3]), color, 2)
            
            # Hiển thị điểm tin cậy
            conf_text = f'{conf:.2f}'
            cv2.putText(dimg, conf_text, (box[0], box[1] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Chỉ vẽ các điểm keypoint
            if face.kps is not None:
                kps = face.kps.astype(np.int32)
                for point in kps:
                    cv2.circle(dimg, tuple(point), 3, color, -1)
                    
        return dimg
    
    def run_inference(self):
        """
        Run face detection on video stream and display results with stats
        """

        for path, im, im0s, vid_cap, s in self.dataset:
            
            # Inference
            pred = self.get_face_detect(im0s)

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
                            if is_valid_bounding_box(xywh_e, min_size=50) and check_face_orientation(imc):
                                xyxy_e = torch.tensor(xyxy).view(-1, 4)
                                xyxy_e = xyxy_e[0].int().tolist()  # Chuyển sang danh sách số nguyên
                                result = fer_detector.get_dominant_emotion(fer_detector.analyze_face(imc, [xyxy_e]))[0]
                            else: 
                                print("skip emotion detect")


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