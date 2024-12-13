import cv2
import numpy as np
from insightface.app.common import Face
from insightface.model_zoo import model_zoo
import os

import platform
from pathlib import Path
from utils.plots import Annotator, colors, save_one_box


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
        self.save_dir = self.media_manager.get_save_directory()

        self.names = {0: 'face'}
        self.hide_labels = False
        self.hide_conf = False
        

        self.load_model()

    def load_model(self):
        """Load detection and recognition models"""
        self.det_model = model_zoo.get_model(det_model_path)
        self.det_model.prepare(ctx_id=0, input_size=(640, 640))
        
        self.rec_model = model_zoo.get_model(rec_model_path)
        self.rec_model.prepare(ctx_id=0)

    def get_face_detect(self, imgs):
        """
        Detect faces in multiple input images
        Args:
            imgs: List of input images [img1, img2, ...] (BGR format)
        Returns:
            List of results for each image, where each result has format:
            [
                [bbox_array, confidence, keypoints_array],
                [bbox_array, confidence, keypoints_array],
                ...
            ]
            - bbox_array: numpy array [x1, y1, x2, y2]
            - confidence: float value
            - keypoints_array: numpy array of facial landmarks
        """
        if not isinstance(imgs, list):
            imgs = [imgs]
        
        all_results = []
        
        for img in imgs:
            bboxes, kpss = self.det_model.detect(img)
            
            if not len(bboxes):  # thay thế cho: if bboxes is None or bboxes.size == 0
                all_results.append([])
                continue
            
            results = [[box[:4], box[4], kp] for box, kp in zip(bboxes, kpss)]
            all_results.append(results)
        
        return all_results

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
        Run inference on images/video and display results
        """
        for path, im, im0s, vid_cap, s in self.dataset:
            
            # Inference
            pred = self.get_face_detect(im0s)

            # Process predictions
            windows = []
            
            for i, det in enumerate(pred):  # per image
                if self.media_manager.webcam:  
                    p, im0 = path[i], im0s[i].copy()
                    s += f'{i}: '
                else:
                    p, im0 = path, im0s.copy()

                if len(det):
                    # Draw boxes
                    for bbox, conf, kps in det:  # bbox là array chứa [x_min, y_min, x_max, y_max]
                        # Chuyển bbox thành integer
                        x1, y1, x2, y2 = bbox.astype(int)
                        
                        # Draw bbox
                        color = (0, int(255 * conf), int(255 * (1 - conf)))
                        cv2.rectangle(im0, (x1, y1), (x2, y2), color, 2)
                        
                        # Add label with confidence
                        if not self.hide_labels:
                            label = f'face {conf:.2f}' if not self.hide_conf else 'face'
                            cv2.putText(im0, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 
                                      0.6, color, 2)

                        # Draw keypoints
                        if kps is not None:
                            for point in kps.astype(np.int32):
                                cv2.circle(im0, tuple(point), 3, color, -1)
                
                # Show image
                if self.media_manager.view_img:
                    if platform.system() == 'Linux' and p not in windows:
                        windows.append(p)
                        cv2.namedWindow(str(p), cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)  
                        cv2.resizeWindow(str(p), im0.shape[1], im0.shape[0])
                    cv2.imshow(str(p), im0)
                    cv2.waitKey(1)

                # Save results
                if self.media_manager.save_img:
                    if self.dataset.mode == 'image':
                        cv2.imwrite(str(self.save_dir / Path(p).name), im0)
                    else:  # video
                        if vid_cap:
                            if not hasattr(self, 'vid_writer'):
                                fps = vid_cap.get(cv2.CAP_PROP_FPS)
                                w = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                                h = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                                self.vid_writer = cv2.VideoWriter(str(self.save_dir), 
                                                                cv2.VideoWriter_fourcc(*'mp4v'), 
                                                                fps, (w, h))
                            self.vid_writer.write(im0)

       