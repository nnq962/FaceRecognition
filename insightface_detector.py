import cv2
import os
import platform
from insightface.model_zoo import model_zoo
from pathlib import Path
import time
import numpy as np
import onnxruntime as ort
ort.set_default_logger_severity(3)

from utils.plots import Annotator
from face_emotion import FaceEmotion
from insightface_utils import normalize_embeddings, crop_and_align_faces, crop_faces_for_emotion, search_ids, crop_image
from hand_raise_detector import get_raising_hand
from services.websocket.answer_sender import send_data_to_server
from database_config import config
from qr_code.utils_qr import ARUCO_DICT, detect_aruco_answers
from services.notification.notification_server import send_notification
# import face_mask_detection
from pymongo.operations import InsertOne, UpdateOne
from utils.logger_config import LOGGER


class InsightFaceDetector:
    def __init__(self,
                media_manager=None,
                face_recognition=False,
                face_emotion=True,
                export_data=False,
                time_to_save=2,
                raise_hand=False,
                qr_code=False,
                face_mask=False,
                host=None,
                data2ws_url=None,
                notification=False,
                noti_control_port=None,
                noti_secret_key=None,
                is_running=True,
                ):
                
        self.det_model_path = os.path.expanduser("models/det_10g.onnx")
        self.rec_model_path = os.path.expanduser("models/w600k_r50.onnx")
        self.det_model = None
        self.rec_model = None
        self.camera_ids = None
        self.log_collection = None
        self.auto_attendance_check = None
        self.board_checkin = None
        self.class_id = None
        self.is_running = is_running

        self.face_recognition = face_recognition
        self.face_emotion = face_emotion
        self.export_data = export_data
        self.time_to_save = time_to_save
        self.qr_code = qr_code
        self.raise_hand = raise_hand
        self.face_mask = face_mask
        self.notification = notification
        self.data2ws_url = data2ws_url
        self.noti_control_port = noti_control_port
        self.noti_secret_key = noti_secret_key
        self.host = host

        self.previous_qr_results = {}
        self.previous_hand_states = {}
        self.mask_thresh = 30
        self.mask_detected_frames = 0
        self.hand_detected_frames = 0
        self.previous_aruco_marker_states = None
        self.arucoDictType = ARUCO_DICT.get("DICT_5X5_100", None)
        self.arucoDict = cv2.aruco.getPredefinedDictionary(self.arucoDictType)
        self.arucoParams = cv2.aruco.DetectorParameters()
        self.aruco_detector = cv2.aruco.ArucoDetector(self.arucoDict, self.arucoParams)
        self.hand_state_counters = {}  # Đếm số lần liên tiếp phát hiện cùng một trạng thái
        self.hand_state_threshold = 5  # Số lần tối thiểu để xác nhận trạng thái mới
        self.qr_state_counters = {}  # Đếm số lần liên tiếp phát hiện cùng một trạng thái
        self.qr_state_threshold = 5  # Số lần tối thiểu để xác nhận trạng thái mới

        self.qr_candidate_results = {}  # Lưu kết quả ứng viên đang được đếm
        self.qr_last_detection_time = {}  # Thời gian phát hiện gần nhất cho mỗi camera
        self.qr_reset_timeout = 10.0  # 10 giây không phát hiện thì reset

        if media_manager is not None:
            self.dataset = media_manager.get_dataloader()
            self.save_dir = media_manager.get_save_directory()
            self.view_img = media_manager.view_img
            self.line_thickness = media_manager.line_thickness
            self.webcam = media_manager.webcam
            self.save_img = media_manager.save_img
            self.save = media_manager.save
            self.save_crop = media_manager.save_crop
            self.vid_path = media_manager.vid_path
            self.vid_writer = media_manager.vid_writer

        if self.raise_hand:
            if self.webcam:
                for camera_id in self.camera_ids:
                    self.previous_hand_states[camera_id] = {}
            else:
                self.previous_hand_states["Photo"] = {}

        if self.face_emotion:
            self.fer = FaceEmotion()

        self.load_model()
        print("-" * 100)
        LOGGER.info("Khởi tạo InsightFaceDetector thành công.")
        print("-" * 100)

    def update_media_manager(self, media_manager, camera_ids):
        self.media_manager = media_manager
        self.dataset = media_manager.get_dataloader()
        self.save_dir = media_manager.get_save_directory()
        self.view_img = media_manager.view_img
        self.line_thickness = media_manager.line_thickness
        self.webcam = media_manager.webcam
        self.save_img = media_manager.save_img
        self.save = media_manager.save
        self.save_crop = media_manager.save_crop
        self.vid_path = media_manager.vid_path
        self.vid_writer = media_manager.vid_writer
        self.camera_ids = camera_ids

        # Cập nhật lại hand states nếu raise_hand đang bật
        if self.raise_hand:
            self.previous_hand_states.clear()
            if self.webcam:
                for camera_id in self.camera_ids:
                    self.previous_hand_states[camera_id] = {}
            else:
                self.previous_hand_states["Photo"] = {}

    def update_class_info(self, class_id, auto_attendance_check, board_checkin):
        """Update class information"""
        self.class_id = class_id
        self.log_collection = config.database[f"{self.class_id}_logs"]
        self.auto_attendance_check = auto_attendance_check
        self.board_checkin = board_checkin

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
        return normalize_embeddings(embeddings)
        
    def get_frame(self, im0s, i, webcam=False):
        if webcam:
            return im0s[i]
        return im0s
        
    def get_aruco_marker(self, img):
        corners, ids, _ = self.aruco_detector.detectMarkers(img)
        results = detect_aruco_answers(corners, ids)  # Nhận danh sách marker

        if not results:  # Không có marker nào được phát hiện
            return

        return results
    
    # def detect_face_masks(self, image):
    #     mask_count = face_mask_detection.inference(image, target_shape=(360, 360))
    #     if mask_count:
    #         self.mask_detected_frames += 1
    #     else:
    #         self.mask_detected_frames = 0
    #     if self.mask_detected_frames >= self.mask_thresh:
    #         self.mask_detected_frames = 0
    #         if self.notification:
    #             send_notification(
    #                 message="Vui lòng tháo khẩu trang", 
    #                 host=self.host, 
    #                 control_port=self.noti_control_port,
    #                 secret_key=self.noti_secret_key
    #             )
    #         else:
    #             LOGGER.info("Vui lòng tháo khẩu trang")

    def detect_qr_code(self, image, index):
        """
        Detects QR codes with stability threshold to avoid flickering results.
        Only updates state after detecting the same result 5 consecutive times.
        Resets counter after 10 seconds of no detection.
        """
        current_time = time.time()
        camera_id = self.camera_ids[index] if self.webcam else "Photo"
        
        # Get current QR detection results
        qr_result = self.get_aruco_marker(image)
        
        # Initialize tracking data for this camera if not exists
        if camera_id not in self.qr_state_counters:
            self.qr_state_counters[camera_id] = {}
            self.qr_candidate_results[camera_id] = {}
            self.qr_last_detection_time[camera_id] = current_time
        
        # Check if we should reset due to timeout (no detection for 10 seconds)
        if current_time - self.qr_last_detection_time[camera_id] > self.qr_reset_timeout:
            self._reset_camera_counters(camera_id)
        
        # If no QR codes detected in current frame
        if not qr_result:
            return
            
        # Update last detection time
        self.qr_last_detection_time[camera_id] = current_time
        
        # Get current confirmed results for this camera
        current_confirmed = self.previous_qr_results.get(camera_id, {})
        
        # Track newly stabilized markers in this frame
        newly_stabilized_markers = {}
        
        # Process each detected marker
        for marker_id, answer in qr_result.items():
            if self._process_marker_detection(camera_id, marker_id, answer, current_confirmed):
                newly_stabilized_markers[marker_id] = answer
        
        # Clean up counters for markers that are no longer detected
        self._cleanup_missing_markers(camera_id, qr_result)
        
        # Send all newly stabilized markers for this camera in one request
        if newly_stabilized_markers:
            self._send_stabilized_results(camera_id, newly_stabilized_markers)
    
    def _process_marker_detection(self, camera_id, marker_id, answer, current_confirmed):
        """Process detection of a single marker. Returns True if marker becomes stable."""
        current_confirmed_answer = current_confirmed.get(marker_id)
        
        # If this is the same as already confirmed result, reset counter
        if answer == current_confirmed_answer:
            self.qr_state_counters[camera_id][marker_id] = 0
            self.qr_candidate_results[camera_id][marker_id] = answer
            return False
        
        # If this is a new candidate answer
        candidate_answer = self.qr_candidate_results[camera_id].get(marker_id)
        
        if answer == candidate_answer:
            # Same candidate as before, increment counter
            self.qr_state_counters[camera_id][marker_id] += 1
        else:
            # New candidate answer, reset counter
            self.qr_state_counters[camera_id][marker_id] = 1
            self.qr_candidate_results[camera_id][marker_id] = answer
        
        # Check if we've reached the threshold
        if self.qr_state_counters[camera_id][marker_id] >= self.qr_state_threshold:
            # Update confirmed results
            if camera_id not in self.previous_qr_results:
                self.previous_qr_results[camera_id] = {}
            
            self.previous_qr_results[camera_id][marker_id] = answer
            
            # Reset counter after confirmation
            self.qr_state_counters[camera_id][marker_id] = 0
            
            return True  # This marker just became stable
        
        return False
    
    def _send_stabilized_results(self, camera_id, stabilized_markers):
        """Send all stabilized markers for this camera in one request"""
        send_data_to_server(
            data_type="qr_code",
            payload=stabilized_markers,  # Send all stabilized markers at once
            class_id=self.class_id,
            server_address=self.data2ws_url,
            meta={
                "camera_id": camera_id,
                "source": "classroom_system",
                "version": "2.1",
                "description": "Stable QR code detection with threshold filtering",
                "markers_count": len(stabilized_markers)
            }
        )
    
    def _cleanup_missing_markers(self, camera_id, current_results):
        """Clean up counters for markers that are no longer detected"""
        detected_markers = set(current_results.keys()) if current_results else set()
        tracked_markers = set(self.qr_state_counters[camera_id].keys())
        
        # Remove counters for markers that are no longer detected
        for marker_id in tracked_markers - detected_markers:
            if marker_id in self.qr_state_counters[camera_id]:
                del self.qr_state_counters[camera_id][marker_id]
            if marker_id in self.qr_candidate_results[camera_id]:
                del self.qr_candidate_results[camera_id][marker_id]
    
    def _reset_camera_counters(self, camera_id):
        """Reset all counters for a specific camera due to timeout"""
        self.qr_state_counters[camera_id] = {}
        self.qr_candidate_results[camera_id] = {}

    def detect_raise_hand(self, frame, bbox, user_id, camera_id):
        if user_id == "Unknown":
            return

        hand_raised = get_raising_hand(frame, bbox)

        # Khởi tạo counters cho user_id và camera này nếu chưa có
        if camera_id not in self.hand_state_counters:
            self.hand_state_counters[camera_id] = {}
        if user_id not in self.hand_state_counters[camera_id]:
            self.hand_state_counters[camera_id][user_id] = {'up': 0, 'down': 0}
        
        # Tăng counter cho trạng thái hiện tại
        if hand_raised:
            self.hand_state_counters[camera_id][user_id]['up'] += 1
            self.hand_state_counters[camera_id][user_id]['down'] = 0
        else:
            self.hand_state_counters[camera_id][user_id]['down'] += 1
            self.hand_state_counters[camera_id][user_id]['up'] = 0
        
        # Chỉ thay đổi trạng thái khi đạt ngưỡng
        previous_state = self.previous_hand_states[camera_id].get(user_id, None)
        
        # Kiểm tra ngưỡng để thay đổi trạng thái
        new_hand_raised = None
        if self.hand_state_counters[camera_id][user_id]['up'] >= self.hand_state_threshold:
            new_hand_raised = True
        elif self.hand_state_counters[camera_id][user_id]['down'] >= self.hand_state_threshold:
            new_hand_raised = False
        
        # Cập nhật và gửi thông báo nếu trạng thái thay đổi
        if new_hand_raised is not None and (previous_state is None or previous_state != new_hand_raised):
            # Cập nhật trạng thái mới vào dictionary theo camera
            self.previous_hand_states[camera_id][user_id] = new_hand_raised
            # Gửi dữ liệu giơ tay
            send_data_to_server(
                data_type="hand_status",
                payload={
                    user_id: "up" if new_hand_raised else "down"
                },
                class_id=self.class_id,
                server_address=self.data2ws_url,
                meta={
                    "camera_id": camera_id,
                    "source": "classroom_system",
                    "version": "2.0"
                }
            )

    def mock_board_checkin(self, frame, bbox, user_id, camera_id):
        """Hàm liên quan đến bảng"""
        pass

    def run_inference(self):
        """
        Run inference on images/video and display results
        """
        LOGGER.debug(f"Is running: {self.is_running}")
        if not self.is_running:
            return
        
        LOGGER.debug(f"View img: {self.view_img}")
        LOGGER.debug(f"Save img: {self.save_img}")
        LOGGER.debug(f"Save crop: {self.save_crop}")
        LOGGER.debug(f"Line thickness: {self.line_thickness}")  
        LOGGER.debug(f"Is running: {self.is_running}")
        LOGGER.debug(f"Face recognition: {self.face_recognition}")
        LOGGER.debug(f"Face emotion: {self.face_emotion}")
        LOGGER.debug(f"Raise hand: {self.raise_hand}")
        LOGGER.debug(f"QR code: {self.qr_code}")
        LOGGER.debug(f"Export data: {self.export_data}")
        LOGGER.debug(f"Time to save: {self.time_to_save}")
        LOGGER.debug(f"Notification: {self.notification}")
        
        windows = []
        start_time = time.time()

        for path, im0s, vid_cap, s in self.dataset:
            # Phát hiện khuôn mặt
            pred = self.get_face_detects(im0s)

            LOGGER.debug(f"Pred: {pred}")

            face_counts = []  # Lưu số lượng khuôn mặt trong từng ảnh để ghép lại sau này
            all_cropped_faces_recognition = []  # Danh sách chứa toàn bộ khuôn mặt đã crop (dạng phẳng) cho xác minh
            all_cropped_faces_emotion = [] # Danh sách chứa toàn bộ khuôn mặt đã crop (dạng phẳng) cho cảm xúc
            user_emotions = []  # Danh sách chứa toàn bộ cảm xúc của khuôn mặt
            user_infos = []  # Danh sách chứa thông tin người dùng

            for i, det in enumerate(pred):
                # Lấy ảnh tương ứng
                im0 = self.get_frame(im0s, i, self.webcam)
                
                # Unpack kết quả từ model
                bounding_boxes, keypoints = det

                if len(bounding_boxes) == 0:  # Không có khuôn mặt nào được phát hiện
                    face_counts.append(0)
                    continue
                
                face_counts.append(len(bounding_boxes))  # Ghi lại số lượng khuôn mặt

                # Phát hiện đeo khẩu trang
                if self.face_mask:
                    self.detect_face_masks(image=im0)
                        
                # Kiểm tra QR code
                if self.qr_code:
                    self.detect_qr_code(image=im0, index=i)

                # Crop khuôn mặt để phát hiện cảm xúc
                if self.face_emotion:
                    cropped_faces_emotion = crop_faces_for_emotion(im0, bounding_boxes, conf_threshold=0.55)
                    all_cropped_faces_emotion.extend(cropped_faces_emotion)

                # Crop khuôn mặt để embeddings
                if self.face_recognition:
                    cropped_faces_recognition = crop_and_align_faces(im0, bounding_boxes, keypoints, 0.55)
                    all_cropped_faces_recognition.extend(cropped_faces_recognition)  # Thêm tất cả khuôn mặt vào danh sách chính (dạng phẳng)

            # Lấy cảm xúc các khuôn mặt
            if all_cropped_faces_emotion:
                user_emotions = self.fer.get_emotions(all_cropped_faces_emotion)

            LOGGER.debug(f"Continue")
        
            # Lấy embeddings và truy xuất thông tin
            if all_cropped_faces_recognition:
                all_embeddings = self.get_face_embeddings(all_cropped_faces_recognition)
                user_infos = search_ids(class_id=self.class_id, embeddings=all_embeddings, threshold=0.4)
            
            # Ghép kết quả
            results_per_image = []  # Danh sách kết quả theo từng ảnh
            start_idx = 0  # Dùng để lấy ID user theo thứ tự embeddings
            for det, face_count in zip(pred, face_counts):
                bounding_boxes, _ = det
                user_infos_for_image = user_infos[start_idx:start_idx + face_count] if self.face_recognition else [None] * face_count
                emotions_for_image = user_emotions[start_idx:start_idx + face_count] if self.face_emotion else ["Unknown"] * face_count

                results = [
                    {
                        "bbox": bbox[:4],
                        "conf": bbox[4],
                        "id": user_info["id"] if user_info else "Unknown",
                        "name": user_info["name"] if user_info else "Unknown",
                        "type": user_info["type"] if user_info else "",
                        "similarity": f"{user_info['similarity'] * 100:.2f}%" if user_info else "",
                        "emotion": "Unknown" if user_info is None else emotion
                    }
                    for bbox, user_info, emotion in zip(bounding_boxes, user_infos_for_image, emotions_for_image)
                ]

                results_per_image.append(results)  # Lưu kết quả cho từng ảnh
                start_idx += face_count  # Cập nhật index tiếp theo

            # Kiểm tra có xuất dữ liệu không
            should_export = self.export_data and (time.time() - start_time > self.time_to_save)
            if should_export:
                current_time = config.get_vietnam_time()
                today_date, current_time_short = current_time.split()
                export_data_list = []  # Danh sách chứa dữ liệu mới để gửi đi

            # Duyệt qua từng ảnh để hiển thị và thu thập dữ liệu
            for img_index, results in enumerate(results_per_image):
                im0 = self.get_frame(im0s, img_index, self.webcam)
                p = path[img_index] if self.webcam else path
                p = Path(p)
                save_path = str(self.save_dir / p.name) if (self.save or self.save_crop) else None
                imc = im0.copy() if self.save_crop or should_export else None
                annotator = Annotator(im0, line_width=self.line_thickness)
                camera_id = self.camera_ids[img_index] if self.webcam else "Photo"
                
                # Duyệt qua từng khuôn mặt trong ảnh
                for result in results:
                    bbox = result["bbox"]
                    conf = result["conf"]
                    name = result["name"]
                    type = result["type"]
                    similarity = result["similarity"]
                    user_id = result["id"]
                    emotion = result["emotion"]

                    # Kiểm tra giơ tay
                    if self.raise_hand:
                        self.detect_raise_hand(im0, bbox, user_id, camera_id)

                    # Nếu cần export dữ liệu, thu thập thông tin
                    if should_export and user_id != "Unknown":
                        export_data_list.append({
                            "user_id": user_id,
                            "name": name,
                            "type": type,
                            "time": current_time_short,
                            "emotion": emotion,
                            "camera_id": camera_id,
                            "image": imc,
                            "bbox": bbox
                        })

                    if self.save_img or self.save_crop or self.view_img:
                        label = None
                        if self.face_emotion:
                            label = f"{type} {user_id} {similarity} | {emotion}"
                        elif self.face_recognition:
                            label = f"{type} {user_id} {similarity}"

                        color = (0, int(255 * conf), int(255 * (1 - conf)))
                        annotator.box_label(bbox, label, color=color)

                    # Lưu crop khuôn mặt
                    if self.save_crop:
                        crops_dir = Path(self.save_dir) / 'crops'
                        crops_dir.mkdir(parents=True, exist_ok=True)
                        face_crop = crop_image(imc, bbox[:4])
                        cv2.imwrite(str(crops_dir / f'{p.stem}.jpg'), face_crop)

                # Stream results
                im0 = annotator.result()
                if self.view_img:
                    if platform.system() == 'Linux' and p not in windows:
                        windows.append(p)
                        cv2.namedWindow(str(p), cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)  # allow window resize (Linux)
                        cv2.resizeWindow(str(p), im0.shape[1], im0.shape[0])

                    cv2.imshow(str(p), im0)
                    cv2.waitKey(1)

                # Lưu ảnh/video
                if self.save_img and save_path:
                    if self.dataset.mode == 'image':
                        cv2.imwrite(save_path, im0)

                    else:  # 'video' or 'stream'
                        self._save_video(img_index, save_path, vid_cap, im0)
            
            # Lưu dữ liệu vào MongoDB
            if should_export and export_data_list and self.auto_attendance_check:
                # self._process_data(export_data_list, today_date, current_time_short, self.notification)
                # TODO: Xử lý dữ liệu check-in
                LOGGER.warning("Chưa xử lý lưu dữ liệu")
                start_time = time.time()
                            
        # Đảm bảo release sau khi xử lý tất cả các khung hình
        self._release_writers()
    
    def _process_data(self, export_data_list, today_date, current_time_short, notification_enabled=False):
        if not export_data_list:
            return
        
        # Kiểm tra thời gian chỉ một lần
        is_after_1730 = self._is_after_time(current_time_short, 17, 30)
        
        # Tối ưu truy vấn MongoDB
        user_ids = list({data["user_id"] for data in export_data_list})
        records = self.log_collection.find(
            {"date": today_date, "user_id": {"$in": user_ids}},
            {"user_id": 1, "name": 1, "check_in_time": 1, "goodbye_noti": 1}
        )
        records_dict = {record["user_id"]: record for record in records}
        
        # Chuẩn bị các thao tác
        operations = []
        welcome_users = []
        goodbye_users = []
        
        for data in export_data_list:
            user_id = data["user_id"]
            timestamp_entry = {
                "time": data["time"],
                "emotion": data["emotion"],
                "camera_id": data["camera_id"]
            }
            
            if user_id not in records_dict:
                # Xử lý check-in mới
                image_folder = f"users_data/{user_id}/attendance_photos/{today_date.replace('-', '_')}"
                os.makedirs(image_folder, exist_ok=True)

                check_in_image_path = f"{image_folder}/check_in.png"
                welcome_noti = not is_after_1730
                
                new_record = {
                    "date": today_date,
                    "user_id": user_id,
                    "name": data["name"],
                    "check_in_time": data["time"],
                    "timestamps": [timestamp_entry],
                    "check_out_time": data["time"],
                    "goodbye_noti": False,
                    "welcome_noti": welcome_noti
                }
                operations.append(InsertOne(new_record))
                
                # Lưu ảnh
                img = data["image"].copy()
                x1, y1, x2, y2 = map(int, data["bbox"])
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.imwrite(check_in_image_path, img)
                
                if welcome_noti:
                    welcome_users.append(data["name"])
            else:
                # Cập nhật dữ liệu
                update_data = {
                    "$push": {"timestamps": timestamp_entry},
                    "$set": {"check_out_time": data["time"]}
                }
                
                record = records_dict[user_id]
                if is_after_1730 and not record.get("goodbye_noti", False):
                    goodbye_users.append(data["name"])
                    update_data["$set"]["goodbye_noti"] = True
                    # Lưu ảnh check-out
                    image_folder = f"users_data/{user_id}/attendance_photos/{today_date.replace('-', '_')}"
                    os.makedirs(image_folder, exist_ok=True)
                    check_out_image_path = f"{image_folder}/check_out.png"
                    img = data["image"].copy()
                    x1, y1, x2, y2 = map(int, data["bbox"])
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.imwrite(check_out_image_path, img)
                    
                operations.append(UpdateOne(
                    {"date": today_date, "user_id": user_id},
                    update_data
                ))        
        # Thực hiện bulk write một lần
        if operations:
            try:
                result = self.log_collection.bulk_write(operations)
                # Có thể log kết quả nếu cần
                # logger.info(f"MongoDB operations: {result.inserted_count} inserted, {result.modified_count} modified")
            except Exception as e:
                # Xử lý lỗi và log
                LOGGER.error(f"MongoDB bulk_write error: {e}")
        
        # Gửi thông báo
        # if notification_enabled:
        #     for name in welcome_users:
        #         # TODO: SAU NÀY SẼ THAY THẾ BẰNG BẢNG
        #         send_notification(
        #             message=f"Xin chào {name}",
        #             host=self.host,
        #             control_port=self.noti_control_port,
        #             secret_key=self.noti_secret_key
        #         )
        #     for name in goodbye_users:
        #         send_notification(
        #             message=f"Chào tạm biệt {name}",
        #             host=self.host,
        #             control_port=self.noti_control_port,
        #             secret_key=self.noti_secret_key
        #         )
        # else:
        #     if welcome_users:
        #         LOGGER.info(f"Xin chào {', '.join(welcome_users)}")
        #     if goodbye_users:
        #         LOGGER.info(f"Chào tạm biệt {', '.join(goodbye_users)}")
                
        # Xóa danh sách đã xử lý
        export_data_list.clear()
        
    def _is_after_time(self, time_str, hour_threshold, minute_threshold=0):
        hour, minute, _ = map(int, time_str.split(':'))
        return hour > hour_threshold or (hour == hour_threshold and minute >= minute_threshold)

    def _save_video(self, img_index, save_path, vid_cap, im0):
        """
        Function to save video frames
        """
        if self.vid_path[img_index] != save_path:
            self.vid_path[img_index] = save_path
            if isinstance(self.vid_writer[img_index], cv2.VideoWriter):
                self.vid_writer[img_index].release()
            fps = vid_cap.get(cv2.CAP_PROP_FPS) if vid_cap else 10
            w, h = (int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))) if vid_cap else (im0.shape[1], im0.shape[0])
            save_path = str(Path(save_path).with_suffix('.mp4'))
            self.vid_writer[img_index] = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
        self.vid_writer[img_index].write(im0)

    def _release_writers(self):
        """
        Function to release video writers
        """
        for writer in self.vid_writer:
            if isinstance(writer, cv2.VideoWriter):
                writer.release()
                LOGGER.info("Video writer released successfully.")
