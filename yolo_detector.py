import cv2
import os
import platform
from insightface.model_zoo import model_zoo
from ultralytics import YOLO
from pathlib import Path
from utils.plots import Annotator
from utils.general import LOGGER, Profile
from face_emotion import FERUtils
import yolo_detector_utils
import hand_raise_detector
from websocket_server import send_notification
import time
import onnxruntime as ort
ort.set_default_logger_severity(3)
import numpy as np
from config import config


class YoloDetector:
    def __init__(self, media_manager=None):
        self.det_model_path = os.path.expanduser("~/Models/yolov11-face.pt")
        self.rec_model_path = os.path.expanduser("~/Models/w600k_r50.onnx")
        self.det_model = None
        self.rec_model = None
        self.previous_states = {}
        self.media_manager = media_manager

        if self.media_manager is not None:
            self.dataset = self.media_manager.get_dataloader()
            self.save_dir = self.media_manager.get_save_directory()
            if self.media_manager.face_emotion:
                self.fer_class = FERUtils(gpu_memory_limit=config.vram_limit_for_FER * 1024)

        self.load_model()

    def load_model(self):
        """Load detection and recognition models"""
        self.det_model = YOLO(self.det_model_path)
        
        self.rec_model = model_zoo.get_model(self.rec_model_path)
        self.rec_model.prepare(ctx_id=0)

    def get_face_detects(self, imgs, verbose=False, conf=0.7):
        if not isinstance(imgs, list):
            imgs = [imgs]
        
        results = self.det_model(imgs, verbose=verbose, conf=conf)
        
        detections = []
        for res in results:
            faces = []
            if res.boxes is not None:
                for box in res.boxes.data.cpu().numpy():
                    x1, y1, x2, y2, conf = box[:5]
                    faces.append(np.array([x1, y1, x2, y2, conf], dtype=np.float32))
            detections.append(faces)

        return detections

    def get_face_embeddings(self, cropped_images):
        if not cropped_images:  # Kiểm tra nếu danh sách rỗng
            return []

        embeddings = self.rec_model.get_feat(cropped_images)
        return yolo_detector_utils.normalize_embeddings(embeddings)
    
    def crop_faces(self, img, faces, margin=10):
        cropped_faces = []
        h, w, _ = img.shape  # Lấy kích thước ảnh gốc

        for bbox in faces:
            x1, y1, x2, y2, conf = bbox  # Lấy tọa độ khuôn mặt
            
            # Thêm margin (đảm bảo không vượt quá kích thước ảnh)
            x1 = max(0, x1 - margin)
            y1 = max(0, y1 - margin)
            x2 = min(w, x2 + margin)
            y2 = min(h, y2 + margin)

            # Cắt khuôn mặt từ ảnh
            face_crop = img[int(y1):int(y2), int(x1):int(x2)].copy()
            
            # Chỉ thêm nếu ảnh cắt hợp lệ (tránh trường hợp lỗi)
            if face_crop.shape[0] > 0 and face_crop.shape[1] > 0:
                cropped_faces.append(face_crop)

        return cropped_faces  # Trả về danh sách khuôn mặt đã cắt
    
    def get_frame(self, im0s, i, webcam=False):
        if webcam:
            return im0s[i]
        return im0s
    
    def check_raising_hand(self, frame, bbox, timestamp, camera_name):
        """
        Kiểm tra xem người trong bounding box có giơ tay không.

        Args:
            frame (numpy.ndarray): Ảnh gốc.
            bbox (list): Bounding box của người (x1, y1, x2, y2).
            timestamp (str): Thời gian chụp ảnh.
            camera_name (str): Tên camera hoặc "Photo".

        Returns:
            dict: Trả về dict chứa trạng thái tay (luôn luôn trả về, không phụ thuộc vào thay đổi trạng thái).
        """
        cropped_expand_image = hand_raise_detector.expand_and_crop_image(
            frame, bbox, left=2.6, right=2.6, top=1.6, bottom=2.6
        )

        hand_open = hand_raise_detector.is_hand_opened_in_image(cropped_expand_image)
        hand_raised = hand_raise_detector.is_person_raising_hand_image(cropped_expand_image)
        new_state = "up" if hand_open and hand_raised else "down"

        # Luôn trả về trạng thái tay, không kiểm tra thay đổi
        result = {
            "state": new_state,
            "time": timestamp,
            "camera": camera_name
        }

        # Cập nhật trạng thái vào previous_states (có thể dùng nếu cần theo dõi thay đổi)
        self.previous_states[str(bbox)] = new_state

        return result

    def get_face_emotions(self, img, bounding_boxes):
        """
        Analyze emotions of faces in an image.

        This method detects emotions for faces using the provided bounding boxes 
        (in [x1, y1, x2, y2, conf] format) and returns the dominant emotion with its probability.

        Args:
            img (numpy.ndarray): Input image containing faces.
            bounding_boxes (list or numpy.ndarray): Face bounding boxes in [x1, y1, x2, y2, conf] format.

        Returns:
            list: A list of dictionaries with the dominant emotion and its probability,
                or an empty list if `bounding_boxes` is empty.
        """
        if not bounding_boxes:
            return []

        # Loại bỏ `conf` để chỉ giữ lại [x1, y1, x2, y2]
        clean_bboxes = [bbox[:4] for bbox in bounding_boxes]  
        
        # Phân tích cảm xúc
        emotions = self.fer_class.analyze_face(img, clean_bboxes)
        dominant_emotions = self.fer_class.get_dominant_emotions(emotions)

        return dominant_emotions
        
    def run_inference(self):
        """
        Run inference on images/video and display results
        """
        windows = []
        start_time = time.time()

        for path, _, im0s, vid_cap, s in self.dataset:
            # Inference
            pred = self.get_face_detects(im0s, verbose=False, conf=0.65)

            face_counts = []  # Lưu số lượng khuôn mặt trong từng ảnh để ghép lại sau này
            all_crop_faces = []  # Danh sách chứa toàn bộ khuôn mặt đã crop (dạng phẳng)

            for i, faces in enumerate(pred):
                im0 = self.get_frame(im0s, i, self.media_manager.webcam)  # Lấy ảnh tương ứng

                if not faces:  # Không có khuôn mặt nào được phát hiện
                    face_counts.append(0)
                    continue

                face_counts.append(len(faces))  # Ghi lại số lượng khuôn mặt đã cắt
                
                # Crop all faces
                if self.media_manager.face_recognition:
                    cropped_faces = self.crop_faces(im0, faces=faces, margin=10)  # Cắt khuôn mặt
                    all_crop_faces.extend(cropped_faces)  # Thêm tất cả khuôn mặt vào danh sách chính (dạng phẳng)

            if self.media_manager.face_recognition:
                all_embeddings = self.get_face_embeddings(all_crop_faces)
                user_infos = yolo_detector_utils.search_annoys(all_embeddings, threshold=0.5)

            # Lấy embeddings & tìm user
            user_infos = (
                yolo_detector_utils.search_ids(self.get_face_embeddings(all_crop_faces), threshold=0.5)
                if self.media_manager.face_recognition else None
            )

            # Phân tích cảm xúc
            if self.media_manager.face_emotion:
                all_emotions = []
                for i, faces in enumerate(pred):
                    im0 = self.get_frame(im0s, i, self.media_manager.webcam)  # Lấy ảnh tương ứng
                    emotions = self.get_face_emotions(im0, faces)
                    all_emotions.extend(emotions)
            
            # Kiểm tra dơ tay
            if self.media_manager.raise_hand:
                all_hand_states = []
                for i, faces in enumerate(pred):
                    im0 = self.get_frame(im0s, i, self.media_manager.webcam)  # Lấy ảnh tương ứng
                    for bbox in faces:
                        hand_state = self.check_raising_hand(im0, bbox[:4], config.get_vietnam_time(), config.camera_names[i] if self.media_manager.webcam else "Photo")
                        if hand_state:
                            all_hand_states.append(hand_state)

            # Ghép kết quả
            results_per_image = []  # Danh sách kết quả theo từng ảnh
            start_idx = 0  # Dùng để lấy ID user theo thứ tự embeddings

            for faces, face_count in zip(pred, face_counts):
                if self.media_manager.face_recognition:
                    user_infos_for_image = user_infos[start_idx:start_idx + face_count]  # Lấy đúng số lượng user info
                else:
                    user_infos_for_image = [None] * face_count  # Nếu tắt nhận diện, gán toàn bộ là "Unknown"

                if self.media_manager.face_emotion:
                    emotions_for_image = all_emotions[start_idx:start_idx + face_count]  # Lấy đúng số lượng cảm xúc
                else:
                    emotions_for_image = [{"dominant_emotion": "unknown", "probability": "N/A"}] * face_count  # Gán mặc định

                results = [
                    {
                        "bbox": face[:4].tolist(),
                        "conf": face[4],
                        "id": id_info["id"] if id_info else "Unknown",
                        "full_name": id_info["full_name"] if id_info else "Unknown",
                        "similarity": f"{id_info['similarity'] * 100:.2f}%" if id_info else "N/A",
                        "emotion": emotion["dominant_emotion"],
                        "emotion_probability": f"{float(emotion['probability']) * 100:.2f}%" if isinstance(emotion["probability"], (int, float)) else "N/A"
                    }
                    for face, id_info, emotion in zip(faces, user_infos_for_image, emotions_for_image)
                ]

                results_per_image.append(results)  # Lưu kết quả cho từng ảnh
                start_idx += face_count  # Cập nhật index tiếp theo

            # Display results
            for img_index, results in enumerate(results_per_image):                
                if self.media_manager.webcam:  
                    p = path[img_index]
                    s += f'{img_index}: '
                else:
                    p = path

                im0 = self.get_frame(im0s, img_index, self.media_manager.webcam)
                p = Path(p)
                if self.media_manager.save or self.media_manager.save_crop:
                    save_path = str(self.save_dir / p.name)
                s += f'[{im0.shape[1]}x{im0.shape[0]}] '
                imc = im0.copy() if self.media_manager.save_crop else im0
                annotator = Annotator(im0, line_width=self.media_manager.line_thickness)
                
                if len(results):
                    for result in results:
                        bbox = result["bbox"]
                        conf = result["conf"]
                        name = result["full_name"]
                        similarity = result["similarity"]
                        id = result["id"]
                        emotion = result["emotion"]
                        emotion_probability = result["emotion_probability"]
                        
                        if self.media_manager.face_emotion:
                            label = f"{name} {similarity} | {emotion} {emotion_probability}"
                        elif self.media_manager.face_recognition:
                            label = f"{name} {similarity}"
                        else:
                            label = None
                                        
                        if self.media_manager.save_img or self.media_manager.save_crop or self.media_manager.view_img:
                            if label is None or self.media_manager.hide_labels or self.media_manager.hide_conf:
                                label = None

                            color = (0, int(255 * conf), int(255 * (1 - conf)))
                            annotator.box_label(bbox, label, color=color)

                        if self.media_manager.save_crop:
                            crops_dir = Path(self.save_dir) / 'crops'
                            crops_dir.mkdir(parents=True, exist_ok=True)
                            face_crop = yolo_detector_utils.crop_image(imc, bbox[:4])
                            cv2.imwrite(str(crops_dir / f'{p.stem}.jpg'), face_crop)
                
                # Stream results
                im0 = annotator.result()
                if self.media_manager.view_img:
                    if platform.system() == 'Linux' and p not in windows:
                        windows.append(p)
                        cv2.namedWindow(str(p), cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)  # allow window resize (Linux)
                        cv2.resizeWindow(str(p), im0.shape[1], im0.shape[0])

                    cv2.imshow(str(p), im0)
                    cv2.waitKey(1)

                # Save results (image with detections)
                if self.media_manager.save_img:
                    if self.dataset.mode == 'image':
                        cv2.imwrite(save_path, im0)

                    else:  # 'video' or 'stream'
                        if self.media_manager.vid_path[img_index] != save_path:  # new video
                            self.media_manager.vid_path[img_index] = save_path

                            if isinstance(self.media_manager.vid_writer[img_index], cv2.VideoWriter):
                                self.media_manager.vid_writer[img_index].release()  # release previous video writer

                            if vid_cap:  # video
                                fps = vid_cap.get(cv2.CAP_PROP_FPS)
                                w = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                                h = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            else:  # stream
                                fps, w, h = 10, im0.shape[1], im0.shape[0]

                            save_path = str(Path(save_path).with_suffix('.mp4'))  # force *.mp4 suffix on results videos
                            self.media_manager.vid_writer[img_index] = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))

                        self.media_manager.vid_writer[img_index].write(im0)

        # Ensure release after all frames processed
        for writer in self.media_manager.vid_writer:
            if isinstance(writer, cv2.VideoWriter):
                writer.release()
                print("Video writer released successfully.")