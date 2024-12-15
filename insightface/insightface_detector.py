import cv2
import numpy as np
from insightface.app.common import Face
from insightface.model_zoo import model_zoo
import os
import platform
from pathlib import Path
from utils.plots import Annotator, colors, save_one_box
from utils.general import LOGGER, Profile
import torch
import pickle
import faiss
import fer_detector # FER detector

det_model_path = os.path.expanduser("~/Models/det_10g.onnx")
rec_model_path = os.path.expanduser("~/Models/w600k_r50.onnx")


class InsightFaceDetector:
    """
    InsightFaceDetector is a class for detecting and recognizing faces using InsightFace models.
    
    Args:
        media_manager: An optional media manager object for handling datasets.
    """
    def __init__(self, media_manager=None):
        self.det_model = None
        self.rec_model = None
        self.media_manager = media_manager

        if self.media_manager is not None:
            self.dataset = self.media_manager.get_dataloader()
            self.save_dir = self.media_manager.get_save_directory()
        
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
            
            results = [[box[:4], kp, box[4]] for box, kp in zip(bboxes, kpss)]
            all_results.append(results)
        
        return all_results

    def get_face_embedding(self, img, bb, kps, conf):
        face = Face(bbox=bb, kps=kps, det_score=conf)
        self.rec_model.get(img, face)
        return face.normed_embedding
    
    @staticmethod
    def search_id(embedding, index_path="database/face_index.faiss", mapping_path="database/index_to_id.pkl", top_k=1, threshold=0.5):
        """
        Tìm kiếm ID và độ tương đồng trong cơ sở dữ liệu dựa trên một embedding, có ngưỡng độ tương đồng.

        Args:
            embedding (numpy.ndarray): Embedding đã chuẩn hóa (shape: (512,)).
            index_path (str): Đường dẫn tới FAISS index file.
            mapping_path (str): Đường dẫn tới file ánh xạ index -> ID.
            top_k (int): Số lượng kết quả gần nhất cần trả về.
            threshold (float): Ngưỡng độ tương đồng, loại bỏ kết quả có độ tương đồng thấp hơn ngưỡng.

        Returns:
            list of dict: Danh sách kết quả bao gồm ID, tên ảnh và độ tương đồng.
        """
        # Load FAISS index
        index = faiss.read_index(index_path)

        # Load ánh xạ index -> ID
        with open(mapping_path, "rb") as f:
            index_to_id = pickle.load(f)

        # Đảm bảo embedding là 2D để phù hợp với FAISS input
        query_embedding = np.array([embedding]).astype('float32')

        # Tìm kiếm với FAISS
        D, I = index.search(query_embedding, k=top_k)  # D: Độ tương đồng, I: Chỉ số

        results = []
        for i in range(top_k):
            idx = I[0][i]  # Chỉ số trong FAISS index
            similarity = D[0][i]
            if idx < 0 or similarity < threshold:  # Bỏ qua nếu không tìm thấy hoặc không đạt ngưỡng
                continue
            id_mapping = index_to_id[idx]
            results.append({
                "id": id_mapping["id"],
                "image": id_mapping["image"],
                "similarity": similarity
            })

        return results
    
    def run_inference(self):
        """
        Run inference on images/video and display results
        """
        windows = []
        seen, dt = 0, (Profile(), Profile(), Profile()) 

        for path, _, im0s, vid_cap, s in self.dataset:
            
            # Inference
            with dt[0]:  # Thời gian inference
                pred = self.get_face_detect(im0s)

            # Process predictions
            result = None # global
            
            for i, det in enumerate(pred):  # per image
                seen += 1
                if self.media_manager.webcam:  
                    p, im0 = path[i], im0s[i].copy()
                    s += f'{i}: '
                else:
                    p, im0 = path, im0s.copy()
                
                p = Path(p)  # to Path
                if not self.media_manager.nosave:
                    save_path = str(self.save_dir / p.name)  # im.jpg
                s += f'[{im0.shape[1]}x{im0.shape[0]}] '  # width x height của ảnh hiện tại
                imc = im0.copy() if self.media_manager.save_crop else im0  # for save_crop
                annotator = Annotator(im0, line_width=self.media_manager.line_thickness) # for draw results

                if len(det):

                    # Print results
                    n = len(det)  # số lượng khuôn mặt phát hiện được
                    s += f"{n} {'face' if n == 1 else 'faces'}, "  # add to string

                    # Write results
                    for bbox, kps, conf in det:
                        # check bb & lam net
                        # if face_recognition and bb small

                        if self.media_manager.face_recognition:
                            embedding = self.get_face_embedding(img=im0, bb=bbox, kps=kps, conf=conf)
                            result = self.search_id(embedding=embedding, top_k=1, threshold=0.5)  
                            if result: 
                                similarity_percent = int(result[0]['similarity'] * 100)
                                label = f"{result[0]['id']} {similarity_percent}%"
                                if self.media_manager.face_emotion:
                                    emotion = fer_detector.get_dominant_emotion(fer_detector.analyze_face(imc, bbox))[0]
                                    emotion_label = f"{emotion[0].capitalize()} {int(emotion[1] * 100)}%"  # Định dạng cảm xúc
                                    label += f" | {emotion_label}"  
                            else:
                                label = None
                        else:
                            label = None

                        if self.media_manager.save_img or self.media_manager.save_crop or self.media_manager.view_img:  # Add bbox to image
                            if label is None or self.media_manager.hide_labels or self.media_manager.hide_conf:  # Không hiển thị nhãn nếu các điều kiện này đúng
                                label = None
                            color = (0, int(255 * conf), int(255 * (1 - conf)))
                            annotator.box_label(bbox, label, color=color)

                        if self.media_manager.save_crop:
                            save_one_box(torch.tensor(bbox), imc, file=self.save_dir / 'crops' / f'{p.stem}.jpg',BGR=True)

                # Stream results
                im0 = annotator.result()
                if self.media_manager.view_img:
                    if platform.system() == 'Linux' and p not in windows:
                        windows.append(p)
                        cv2.namedWindow(str(p), cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)  # allow window resize (Linux)
                        cv2.resizeWindow(str(p), im0.shape[1], im0.shape[0])
                    cv2.imshow(str(p), im0)
                    cv2.waitKey(1)  # 1 millisecond
                
                # Save results (image with detections)
                if self.media_manager.save_img:
                    if self.dataset.mode == 'image':
                        cv2.imwrite(save_path, im0)
                    else:  # 'video' or 'stream'
                        if self.media_manager.vid_path[i] != save_path:  # new video
                            self.media_manager.vid_path[i] = save_path
                            if isinstance(self.media_manager.vid_writer[i], cv2.VideoWriter):
                                self.media_manager.vid_writer[i].release()  # release previous video writer
                            if vid_cap:  # video
                                fps = vid_cap.get(cv2.CAP_PROP_FPS)
                                w = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                                h = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            else:  # stream
                                fps, w, h = 30, im0.shape[1], im0.shape[0]
                            save_path = str(
                                Path(save_path).with_suffix('.mp4'))  # force *.mp4 suffix on results videos
                            self.media_manager.vid_writer[i] = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
                        self.media_manager.vid_writer[i].write(im0)

            # Print time (inference-only)
            LOGGER.info(f"{s}{'' if len(det) else '(no detections), '}{dt[0].dt * 1E3:.1f}ms")

        t = dt[0].t / seen * 1E3  # Thời gian trung bình inference trên mỗi ảnh (ms)
        LOGGER.info(f'Speed: %.1fms inference per image.' % t)