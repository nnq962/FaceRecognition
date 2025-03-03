import cv2
import os
import platform
from insightface.model_zoo import model_zoo
from ultralytics import YOLO
from pathlib import Path
from utils.plots import Annotator
from utils.general import LOGGER, Profile
from face_emotion import FERUtils
import insightface_utils
from hand_raise_detector import get_raising_hand
from websocket_server import send_notification
import time
import onnxruntime as ort
ort.set_default_logger_severity(3)
import numpy as np
from config import config
from qr_code.utils_qr import ARUCO_DICT, detect_aruco_answers


class InsightFaceDetector:
    def __init__(self, media_manager=None):
        self.det_model_path = os.path.expanduser("~/Models/det_10g.onnx")
        self.rec_model_path = os.path.expanduser("~/Models/w600k_r50.onnx")
        self.det_model = None
        self.rec_model = None
        self.previous_qr_results = {}
        self.previous_hand_states = {}
        self.media_manager = media_manager
        self.previous_aruco_marker_states = None
        self.arucoDictType = ARUCO_DICT.get("DICT_5X5_100", None)
        self.arucoDict = cv2.aruco.getPredefinedDictionary(self.arucoDictType)
        self.arucoParams = cv2.aruco.DetectorParameters()
        self.aruco_detector = cv2.aruco.ArucoDetector(self.arucoDict, self.arucoParams)

        if self.media_manager is not None:
            self.dataset = self.media_manager.get_dataloader()
            self.save_dir = self.media_manager.get_save_directory()
            if self.media_manager.face_emotion:
                self.fer_class = FERUtils(gpu_memory_limit=config.vram_limit_for_FER * 1024)

        self.load_model()

    def load_model(self):
        """Load detection and recognition models"""
        self.det_model = model_zoo.get_model(self.det_model_path)
        self.det_model.prepare(ctx_id=0, input_size=(640, 640))
        
        self.rec_model = model_zoo.get_model(self.rec_model_path)
        self.rec_model.prepare(ctx_id=0)

    def get_face_detects(self, imgs):
        """
        Detect faces for a list of images.

        Args:
            imgs (list of numpy.ndarray): List of images loaded using cv2.imread.

        Returns:
            list: A list of detection results for each image. Each detection result is a tuple:
                (bounding_boxes, keypoints), where:
                - bounding_boxes: numpy.ndarray of shape (n_faces, 5) containing [x1, y1, x2, y2, confidence].
                - keypoints: numpy.ndarray of shape (n_faces, 5, 2) containing facial landmarks.
                If no faces are detected, (array([], shape=(0, 5), dtype=float32), array([], shape=(0, 5, 2), dtype=float32)) is returned.
        """
        if not isinstance(imgs, list):
            imgs = [imgs]

        all_results = []
        for img in imgs:
            # Giả định self.det_model.detect(img) trả về tuple (bboxes, keypoints)
            result = self.det_model.detect(img)
            bboxes, keypoints = result  # Unpack kết quả từ model

            # Kiểm tra nếu không có khuôn mặt
            if bboxes.shape[0] == 0:
                # Tạo tuple rỗng với shape phù hợp
                empty_bboxes = np.array([], dtype=np.float32).reshape(0, 5)
                empty_keypoints = np.array([], dtype=np.float32).reshape(0, 5, 2)
                all_results.append((empty_bboxes, empty_keypoints))
            else:
                # Nếu có khuôn mặt, giữ nguyên kết quả
                all_results.append((bboxes, keypoints))

        return all_results

    def get_face_embeddings(self, cropped_images):
        if not cropped_images:  # Kiểm tra nếu danh sách rỗng
            return []

        embeddings = self.rec_model.get_feat(cropped_images)
        return insightface_utils.normalize_embeddings(embeddings)
        
    def get_frame(self, im0s, i, webcam=False):
        if webcam:
            return im0s[i]
        return im0s
    
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
        # Loại bỏ `conf` để chỉ giữ lại [x1, y1, x2, y2]
        clean_bboxes = [bbox[:4] for bbox in bounding_boxes]  
        
        # Phân tích cảm xúc
        emotions = self.fer_class.analyze_face(img, clean_bboxes)
        dominant_emotions = self.fer_class.get_dominant_emotions(emotions)

        return dominant_emotions
    
    def get_aruco_marker(self, img):
        corners, ids, _ = self.aruco_detector.detectMarkers(img)
        results = detect_aruco_answers(corners, ids)  # Nhận danh sách marker

        if not results:  # Không có marker nào được phát hiện
            return

        # Sắp xếp danh sách marker theo ID để đảm bảo so sánh chính xác
        sorted_markers = sorted(results, key=lambda x: x["ID"])

        return sorted_markers

    def _save_video(self, img_index, save_path, vid_cap, im0):
        """
        Function to save video frames
        """
        if self.media_manager.vid_path[img_index] != save_path:
            self.media_manager.vid_path[img_index] = save_path
            if isinstance(self.media_manager.vid_writer[img_index], cv2.VideoWriter):
                self.media_manager.vid_writer[img_index].release()
            fps = vid_cap.get(cv2.CAP_PROP_FPS) if vid_cap else 10
            w, h = (int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))) if vid_cap else (im0.shape[1], im0.shape[0])
            save_path = str(Path(save_path).with_suffix('.mp4'))
            self.media_manager.vid_writer[img_index] = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
        self.media_manager.vid_writer[img_index].write(im0)

    def _release_writers(self):
        """
        Function to release video writers
        """
        for writer in self.media_manager.vid_writer:
            if isinstance(writer, cv2.VideoWriter):
                writer.release()
                print("Video writer released successfully.")
        
    def run_inference(self):
        """
        Run inference on images/video and display results
        """
        windows = []
        start_time = time.time()

        for path, _, im0s, vid_cap, s in self.dataset:
            # Phát hiện khuôn mặt
            pred = self.get_face_detects(im0s)

            face_counts = []  # Lưu số lượng khuôn mặt trong từng ảnh để ghép lại sau này
            all_crop_faces = []  # Danh sách chứa toàn bộ khuôn mặt đã crop (dạng phẳng)
            all_emotions = []  # Danh sách chứa toàn bộ cảm xúc của khuôn mặt
            user_infos = []  # Danh sách chứa thông tin người dùng

            for i, det in enumerate(pred):
                # Lấy ảnh tương ứng
                im0 = self.get_frame(im0s, i, self.media_manager.webcam)

                # Unpack kết quả từ model
                bounding_boxes, keypoints = det

                if len(bounding_boxes) == 0:  # Không có khuôn mặt nào được phát hiện
                    face_counts.append(0)
                    continue
                
                face_counts.append(len(bounding_boxes))  # Ghi lại số lượng khuôn mặt đã cắt
                
                # Kiểm tra QR code
                if self.media_manager.qr_code:
                    qr_result = self.get_aruco_marker(im0)
                    camera_name = config.camera_names[i] if self.media_manager.webcam else "Photo"
                    previous_kq = self.previous_qr_results.get(camera_name, [])

                    if qr_result and qr_result != previous_kq:
                        self.previous_qr_results[camera_name] = qr_result  # Cập nhật kết quả mới
                        send_notification({
                            "timestamp": config.get_vietnam_time(),
                            "camera": camera_name,
                            "qr_code": qr_result
                        })

                # Phát hiện cảm xúc
                if self.media_manager.face_emotion:
                    emotions = self.get_face_emotions(im0, bounding_boxes)
                    all_emotions.extend(emotions)

                # Crop khuôn mặt và lấy embeddings
                if self.media_manager.face_recognition:
                    cropped_faces = insightface_utils.crop_and_align_faces(im0, bounding_boxes, keypoints, 0.55)
                    all_crop_faces.extend(cropped_faces)  # Thêm tất cả khuôn mặt vào danh sách chính (dạng phẳng)
        
            # Lấy embeddings và truy xuất thông tin
            if all_crop_faces:
                all_embeddings = self.get_face_embeddings(all_crop_faces)
                user_infos = insightface_utils.search_annoys(all_embeddings, threshold=0.5)
                # TODO: Replace search_annoys with sreach_ids
                # user_infos = insightface_utils.search_ids(all_embeddings, threshold=0.5)
            
            # Ghép kết quả
            results_per_image = []  # Danh sách kết quả theo từng ảnh
            start_idx = 0  # Dùng để lấy ID user theo thứ tự embeddings
            for det, face_count in zip(pred, face_counts):
                bounding_boxes, _ = det
                user_infos_for_image = user_infos[start_idx:start_idx + face_count] if self.media_manager.face_recognition else [None] * face_count
                emotions_for_image = all_emotions[start_idx:start_idx + face_count] if self.media_manager.face_emotion else [{"dominant_emotion": "Unknown", "probability": 0.0}] * face_count

                results = [
                    {
                        "bbox": bbox[:4],
                        "conf": bbox[4],
                        "id": id_info["id"] if id_info else "Unknown",
                        "full_name": id_info["full_name"] if id_info else "Unknown",
                        "similarity": f"{id_info['similarity'] * 100:.2f}%" if id_info else "",
                        "emotion": "Unknown" if id_info is None else (emotion["dominant_emotion"] if emotion else "unknown"),
                        "emotion_probability": "" if id_info is None else (f"{emotion['probability'] * 100:.2f}%" if emotion else "")
                    }
                    for bbox, id_info, emotion in zip(bounding_boxes, user_infos_for_image, emotions_for_image)
                ]

                results_per_image.append(results)  # Lưu kết quả cho từng ảnh
                start_idx += face_count  # Cập nhật index tiếp theo

            # Kiểm tra có xuất dữ liệu không
            should_export = self.media_manager.export_data and (time.time() - start_time > self.media_manager.time_to_save)
            export_data_list = []  # Danh sách chứa dữ liệu mới để gửi đi

            # Duyệt qua từng ảnh để hiển thị và thu thập dữ liệu
            for img_index, results in enumerate(results_per_image):
                p = path[img_index] if self.media_manager.webcam else path
                im0 = self.get_frame(im0s, img_index, self.media_manager.webcam)
                p = Path(p)
                save_path = str(self.save_dir / p.name) if (self.media_manager.save or self.media_manager.save_crop) else None
                imc = im0.copy() if self.media_manager.save_crop else im0
                annotator = Annotator(im0, line_width=self.media_manager.line_thickness)
                camera_name = config.camera_names[img_index] if self.media_manager.webcam else "Photo"

                # Nếu cần lưu trạng thái giơ tay, đảm bảo camera có trong dictionary
                if self.media_manager.raise_hand and camera_name not in self.previous_hand_states:
                    self.previous_hand_states[camera_name] = {}
                
                # Duyệt qua từng khuôn mặt trong ảnh
                for result in results:
                    bbox = result["bbox"]
                    conf = result["conf"]
                    name = result["full_name"]
                    similarity = result["similarity"]
                    id = result["id"]
                    emotion = result["emotion"]
                    emotion_probability = result["emotion_probability"]
                    
                    if self.media_manager.raise_hand and id != "Unknown":
                        hand_raised = get_raising_hand(im0, bbox)
                        previous_state = self.previous_hand_states[camera_name].get(id, None)

                        # Chỉ gửi nếu trạng thái thay đổi
                        if previous_state is None or previous_state != hand_raised:
                            # Cập nhật trạng thái mới vào dictionary theo camera
                            self.previous_hand_states[camera_name][id] = hand_raised
                            # Gửi dữ liệu giơ tay
                            send_notification({
                                "timestamp": config.get_vietnam_time(),
                                "camera": camera_name,
                                "id": id,
                                "hand_status": "up" if hand_raised else "down"
                            })

                    # Nếu cần export dữ liệu, thu thập thông tin
                    if should_export and id != "Unknown":
                        export_data_list.append({
                            "timestamp": config.get_vietnam_time(),
                            "id": id,
                            "similarity": float(similarity.replace('%', '')),
                            "emotion": emotion,
                            "emotion_probability": float(emotion_probability.replace('%', '')),
                            "camera": camera_name
                        })

                    if self.media_manager.face_emotion:
                        label = f"{name} {similarity} | {emotion} {emotion_probability}"
                    elif self.media_manager.face_recognition:
                        label = f"{name} {similarity}"
                    else:
                        label = None

                    # Hiển thị nhãn
                    if self.media_manager.save_img or self.media_manager.save_crop or self.media_manager.view_img:
                        if self.media_manager.hide_labels or self.media_manager.hide_conf:
                            label = None

                        color = (0, int(255 * conf), int(255 * (1 - conf)))
                        annotator.box_label(bbox, label, color=color)

                    # Lưu crop khuôn mặt
                    if self.media_manager.save_crop:
                        crops_dir = Path(self.save_dir) / 'crops'
                        crops_dir.mkdir(parents=True, exist_ok=True)
                        face_crop = insightface_utils.crop_image(imc, bbox[:4])
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

                # Lưu ảnh/video
                if self.media_manager.save_img and save_path:
                    if self.dataset.mode == 'image':
                        cv2.imwrite(save_path, im0)

                    else:  # 'video' or 'stream'
                        self._save_video(img_index, save_path, vid_cap, im0)
            
            # Lưu dữ liệu vào MongoDB
            if should_export and export_data_list:
                insightface_utils.save_data_to_mongo(export_data_list)
                export_data_list.clear()
                start_time = time.time()

        # Đảm bảo release sau khi xử lý tất cả các khung hình
        self._release_writers()