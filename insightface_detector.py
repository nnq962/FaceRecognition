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
from websocket_server import send_notification
from config import config
from qr_code.utils_qr import ARUCO_DICT, detect_aruco_answers
from notification_server import send_notification as ns_send_notification
import face_mask_detection
from pymongo.operations import InsertOne, UpdateOne
from utils.logger_config import LOGGER


class InsightFaceDetector:
    def __init__(self,
                media_manager=None,
                face_recognition=False,
                face_emotion=False,
                export_data=False,
                time_to_save=2,
                raise_hand=False,
                qr_code=False,
                face_mask=False,
                notification=False):
        
        self.det_model_path = os.path.expanduser("~/Models/det_10g.onnx")
        self.rec_model_path = os.path.expanduser("~/Models/w600k_r50.onnx")
        self.det_model = None
        self.rec_model = None

        self.face_recognition = face_recognition
        self.face_emotion = face_emotion
        self.export_data = export_data
        self.time_to_save = time_to_save
        self.qr_code = qr_code
        self.raise_hand = raise_hand
        self.face_mask = face_mask
        self.notification = notification

        if self.raise_hand:
            if self.webcam:
                for camera_name in config.camera_names:
                    self.previous_hand_states[camera_name] = {}
            else:
                self.previous_hand_states["Photo"] = {}

        self.previous_qr_results = {}
        self.previous_hand_states = {}
        self.mask_thresh = 30
        self.mask_detected_frames = 0
        self.hand_detected_frames = 0
        self.count = 0
        self.previous_aruco_marker_states = None
        self.arucoDictType = ARUCO_DICT.get("DICT_5X5_100", None)
        self.arucoDict = cv2.aruco.getPredefinedDictionary(self.arucoDictType)
        self.arucoParams = cv2.aruco.DetectorParameters()
        self.aruco_detector = cv2.aruco.ArucoDetector(self.arucoDict, self.arucoParams)

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

        if self.face_emotion:
            self.fer = FaceEmotion()

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

        # Sắp xếp danh sách marker theo ID để đảm bảo so sánh chính xác
        sorted_markers = sorted(results, key=lambda x: x["ID"])

        return sorted_markers
    
    def detect_face_masks(self, image):
        mask_count = face_mask_detection.inference(image, target_shape=(360, 360))
        if mask_count:
            self.mask_detected_frames += 1
        else:
            self.mask_detected_frames = 0
        if self.mask_detected_frames >= self.mask_thresh:
            self.mask_detected_frames = 0
            if self.notification:
                ns_send_notification("Vui lòng tháo khẩu trang")
            else:
                LOGGER.info("Vui lòng tháo khẩu trang")

    def detect_qr_code(self, image, index):
        """
        Detects QR codes in the given image and sends a notification if a new QR code is detected.
        Args:
            image (numpy.ndarray): The input image in which to detect QR codes. 
                       It should be a valid numpy array representing the image.
            index (int): The index of the image, used to determine the corresponding camera name.
        Behavior:
            - Uses the `get_aruco_marker` method to detect QR codes in the image.
            - Compares the detected QR code with previously detected results for the corresponding camera.
            - If a new QR code is detected, updates the previous results and sends a notification 
              containing the timestamp, camera name, and QR code data.
        Note:
            - The camera name is determined based on the index `i` and whether the input is from a webcam or a photo.
    
        """
        qr_result = self.get_aruco_marker(image)
        camera_name = config.camera_names[index] if self.webcam else "Photo"
        previous_kq = self.previous_qr_results.get(camera_name, [])

        if qr_result and qr_result != previous_kq:
            self.previous_qr_results[camera_name] = qr_result  # Cập nhật kết quả mới
            send_notification({
                "timestamp": config.get_vietnam_time(),
                "camera": camera_name,
                "qr_code": qr_result
            })

    def detect_raise_hand(self, frame, bbox, user_id, camera_name):
        if user_id == "Unknown":
            return

        hand_raised = get_raising_hand(frame, bbox)
        previous_state = self.previous_hand_states[camera_name].get(user_id, None)

        # Chỉ gửi nếu trạng thái thay đổi
        if previous_state is None or previous_state != hand_raised:
            # Cập nhật trạng thái mới vào dictionary
            self.previous_hand_states[camera_name][user_id] = hand_raised
            
            # Ghi log và gửi thông báo
            LOGGER.debug(f"timestamp: {config.get_vietnam_time()}, camera: {camera_name}, id: {user_id}, hand_status: {'up' if hand_raised else 'down'}")
            
            # Code gửi thông báo nếu cần
            # send_notification({
            #     "timestamp": config.get_vietnam_time(),
            #     "camera": camera_name,
            #     "id": user_id,
            #     "hand_status": "up" if hand_raised else "down"
            # })

    def run_inference(self):
        """
        Run inference on images/video and display results
        """
        windows = []
        start_time = time.time()

        for path, im0s, vid_cap, s in self.dataset:
            # Phát hiện khuôn mặt
            pred = self.get_face_detects(im0s)

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
        
            # Lấy embeddings và truy xuất thông tin
            if all_cropped_faces_recognition:
                all_embeddings = self.get_face_embeddings(all_cropped_faces_recognition)
                user_infos = search_ids(all_embeddings, threshold=0.5)
            
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
                        "id": id_info["id"] if id_info else "Unknown",
                        "full_name": id_info["full_name"] if id_info else "Unknown",
                        "similarity": f"{id_info['similarity'] * 100:.2f}%" if id_info else "",
                        "emotion": "Unknown" if id_info is None else emotion
                    }
                    for bbox, id_info, emotion in zip(bounding_boxes, user_infos_for_image, emotions_for_image)
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
                camera_name = config.camera_names[img_index] if self.webcam else "Photo"
                
                # Duyệt qua từng khuôn mặt trong ảnh
                for result in results:
                    bbox = result["bbox"]
                    conf = result["conf"]
                    name = result["full_name"]
                    similarity = result["similarity"]
                    user_id = result["id"]
                    emotion = result["emotion"]

                    # Test backend
                    if user_id == 1:
                        if get_raising_hand(im0, bbox):
                            self.hand_detected_frames += 1
                            if self.hand_detected_frames >= 20:
                                self.hand_detected_frames = 0
                                if self.notification:
                                    ns_send_notification("Ok sếp ơi")
                                else:
                                    LOGGER.info("Ok sếp ơi")
                    
                    # Kiểm tra giơ tay
                    if self.raise_hand:
                        self.detect_raise_hand(im0, bbox, user_id, camera_name)

                    # Nếu cần export dữ liệu, thu thập thông tin
                    if should_export and user_id != "Unknown":
                        export_data_list.append({
                            "user_id": user_id,
                            "name": name,
                            "time": current_time_short,
                            "emotion": emotion,
                            "camera": camera_name,
                            "image": imc,  # Lưu ảnh để dùng cho check-in nếu cần
                            "bbox": bbox   # Lưu bbox để vẽ hình chữ nhật trên ảnh check-in
                        })

                    if self.save_img or self.save_crop or self.view_img:
                        label = None
                        if self.face_emotion:
                            label = f"{user_id} {similarity} | {emotion}"
                        elif self.face_recognition:
                            label = f"{user_id} {similarity}"

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
            if should_export and export_data_list:
                self._process_attendance_data(export_data_list, today_date, current_time_short, self.notification)
                start_time = time.time()
                            
        # Đảm bảo release sau khi xử lý tất cả các khung hình
        self._release_writers()
    
    def _process_attendance_data(self, export_data_list, today_date, current_time_short, notification_enabled=False):
        if not export_data_list:
            return
            
        # Tạo thư mục lưu ảnh
        image_folder = f"attendance_images/{today_date.replace('-', '_')}"
        os.makedirs(image_folder, exist_ok=True)
        
        # Kiểm tra thời gian chỉ một lần
        is_after_1730 = self._is_after_time(current_time_short, 17, 30)
        
        # Tối ưu truy vấn MongoDB
        user_ids = list({data["user_id"] for data in export_data_list})
        records = config.data_collection.find(
            {"date": today_date, "user_id": {"$in": user_ids}},
            {"user_id": 1, "name": 1, "check_in_time": 1, "has_been_goodbye": 1}
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
                "camera": data["camera"]
            }
            
            if user_id not in records_dict:
                # Xử lý check-in mới
                image_path = f"{image_folder}/{user_id}_{data['time'].replace(':', '_')}_check_in.jpg"
                
                new_record = {
                    "date": today_date,
                    "user_id": user_id,
                    "name": data["name"],
                    "check_in_time": data["time"],
                    "check_in_image": image_path,
                    "timestamps": [timestamp_entry],
                    "check_out_time": data["time"],
                    "has_been_goodbye": False
                }
                operations.append(InsertOne(new_record))
                
                # Lưu ảnh (có thể chuyển thành xử lý đồng thời)
                img = data["image"].copy()
                x1, y1, x2, y2 = map(int, data["bbox"])
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.imwrite(image_path, img, [cv2.IMWRITE_JPEG_QUALITY, 90])
                
                welcome_users.append(data["name"])
            else:
                # Cập nhật dữ liệu
                update_data = {
                    "$push": {"timestamps": timestamp_entry},
                    "$set": {"check_out_time": data["time"]}
                }
                
                record = records_dict[user_id]
                if is_after_1730 and not record.get("has_been_goodbye", False):
                    goodbye_users.append(data["name"])
                    update_data["$set"]["has_been_goodbye"] = True
                    
                operations.append(UpdateOne(
                    {"date": today_date, "user_id": user_id},
                    update_data
                ))
        
        # Thực hiện bulk write một lần
        if operations:
            try:
                result = config.data_collection.bulk_write(operations)
                # Có thể log kết quả nếu cần
                # logger.info(f"MongoDB operations: {result.inserted_count} inserted, {result.modified_count} modified")
            except Exception as e:
                # Xử lý lỗi và log
                LOGGER.error(f"MongoDB bulk_write error: {e}")
        
        # Gửi thông báo
        if notification_enabled:
            if welcome_users:
                ns_send_notification(f"Xin chào {', '.join(welcome_users)}")
            if goodbye_users:
                ns_send_notification(f"Chào tạm biệt {', '.join(goodbye_users)}")
        else:
            if welcome_users:
                LOGGER.info(f"Xin chào {', '.join(welcome_users)}")
            if goodbye_users:
                LOGGER.info(f"Chào tạm biệt {', '.join(goodbye_users)}")
                
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