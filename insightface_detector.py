import cv2
import os
import platform
from insightface.model_zoo import model_zoo
from pathlib import Path
from utils.plots import Annotator
from face_emotion import FaceEmotion
import insightface_utils
from hand_raise_detector import get_raising_hand
from websocket_server import send_notification
import time
import onnxruntime as ort
ort.set_default_logger_severity(3)
import numpy as np
from config import config
from qr_code.utils_qr import ARUCO_DICT, detect_aruco_answers
from notification_server import send_notification as ns_send_notification
import face_mask_detection
from pymongo.operations import InsertOne, UpdateOne


class InsightFaceDetector:
    def __init__(self, media_manager=None):
        self.det_model_path = os.path.expanduser("~/Models/det_10g.onnx")
        self.rec_model_path = os.path.expanduser("~/Models/w600k_r50.onnx")
        self.det_model = None
        self.rec_model = None
        self.previous_qr_results = {}
        self.previous_hand_states = {}
        self.mask_thresh = 40
        self.mask_detected_frames = 0
        self.hand_detected_frames = 0
        self.count = 0
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
        return insightface_utils.normalize_embeddings(embeddings)
        
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
            all_cropped_faces_recognition = []  # Danh sách chứa toàn bộ khuôn mặt đã crop (dạng phẳng)
            all_cropped_faces_emotion = []
            user_emotions = []  # Danh sách chứa toàn bộ cảm xúc của khuôn mặt
            user_infos = []  # Danh sách chứa thông tin người dùng

            for i, det in enumerate(pred):
                # Lấy ảnh tương ứng
                im0 = self.get_frame(im0s, i, self.media_manager.webcam)
                
                # Unpack kết quả từ model
                bounding_boxes, keypoints = det

                if len(bounding_boxes) == 0:  # Không có khuôn mặt nào được phát hiện
                    face_counts.append(0)
                    continue
                
                face_counts.append(len(bounding_boxes))  # Ghi lại số lượng khuôn mặt

                # Đếm số người đeo khẩu trang
                if self.media_manager.face_mask:
                    mask_count = face_mask_detection.inference(im0, target_shape=(360, 360))
                    if mask_count:
                        self.mask_detected_frames += 1
                    else:
                        self.mask_detected_frames = 0
                    if self.mask_detected_frames >= self.mask_thresh:
                        self.mask_detected_frames = 0
                        ns_send_notification("Vui lòng tháo khẩu trang")
                        
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

                # Crop khuôn mặt để phát hiện cảm xúc
                if self.media_manager.face_emotion:
                    cropped_faces_emotion = insightface_utils.crop_faces_for_emotion(im0, bounding_boxes, conf_threshold=0.55)
                    all_cropped_faces_emotion.extend(cropped_faces_emotion)

                # Crop khuôn mặt để embeddings
                if self.media_manager.face_recognition:
                    cropped_faces_recognition = insightface_utils.crop_and_align_faces(im0, bounding_boxes, keypoints, 0.55)
                    all_cropped_faces_recognition.extend(cropped_faces_recognition)  # Thêm tất cả khuôn mặt vào danh sách chính (dạng phẳng)

            # Lấy cảm xúc các khuôn mặt
            if all_cropped_faces_emotion:
                user_emotions = self.fer.get_emotions(all_cropped_faces_emotion)
        
            # Lấy embeddings và truy xuất thông tin
            if all_cropped_faces_recognition:
                all_embeddings = self.get_face_embeddings(all_cropped_faces_recognition)
                user_infos = insightface_utils.search_ids(all_embeddings, threshold=0.5)
            
            # Ghép kết quả
            results_per_image = []  # Danh sách kết quả theo từng ảnh
            start_idx = 0  # Dùng để lấy ID user theo thứ tự embeddings
            for det, face_count in zip(pred, face_counts):
                bounding_boxes, _ = det
                user_infos_for_image = user_infos[start_idx:start_idx + face_count] if self.media_manager.face_recognition else [None] * face_count
                emotions_for_image = user_emotions[start_idx:start_idx + face_count] if self.media_manager.face_emotion else ["Unknown"] * face_count

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
            should_export = self.media_manager.export_data and (time.time() - start_time > self.media_manager.time_to_save)
            if should_export:
                current_time = config.get_vietnam_time()
                today_date, current_time_short = current_time.split()
                export_data_list = []  # Danh sách chứa dữ liệu mới để gửi đi

            # Duyệt qua từng ảnh để hiển thị và thu thập dữ liệu
            for img_index, results in enumerate(results_per_image):
                p = path[img_index] if self.media_manager.webcam else path
                im0 = self.get_frame(im0s, img_index, self.media_manager.webcam)
                p = Path(p)
                save_path = str(self.save_dir / p.name) if (self.media_manager.save or self.media_manager.save_crop) else None
                imc = im0.copy() if self.media_manager.save_crop or self.media_manager.export_data else im0
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
                    user_id = result["id"]
                    emotion = result["emotion"]

                    # Test backend
                    if user_id == 1 and get_raising_hand(im0, bbox):
                        self.hand_detected_frames += 1
                        if self.hand_detected_frames >= 30:
                            self.hand_detected_frames = 0
                            ns_send_notification("Ok sếp ơi")
                    
                    if self.media_manager.raise_hand and user_id != "Unknown":
                        hand_raised = get_raising_hand(im0, bbox)
                        previous_state = self.previous_hand_states[camera_name].get(user_id, None)

                        # Chỉ gửi nếu trạng thái thay đổi
                        if previous_state is None or previous_state != hand_raised:
                            # Cập nhật trạng thái mới vào dictionary theo camera
                            self.previous_hand_states[camera_name][user_id] = hand_raised
                            # Gửi dữ liệu giơ tay
                            send_notification({
                                "timestamp": config.get_vietnam_time(),
                                "camera": camera_name,
                                "id": user_id,
                                "hand_status": "up" if hand_raised else "down"
                            })

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

                    if self.media_manager.face_emotion:
                        label = f"{user_id} {similarity} | {emotion}"
                    elif self.media_manager.face_recognition:
                        label = f"{user_id} {similarity}"
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
                # Lấy danh sách user_id duy nhất để truy vấn
                user_ids = list(set(data["user_id"] for data in export_data_list))
                records = config.data_collection.find({"date": today_date, "user_id": {"$in": user_ids}})
                records_dict = {record["user_id"]: record for record in records}

                operations = []
                welcome_users = []
                goodbye_users = []

                # Tạo thư mục nếu chưa tồn tại
                image_folder = f"attendance_images/{today_date.replace('-', '_')}"
                os.makedirs(image_folder, exist_ok=True)

                # Tách giờ và phút từ current_time_short để kiểm tra
                current_hour, current_minute, _ = map(int, current_time_short.split(':'))
                is_after_1730 = current_hour > 17 or (current_hour == 17 and current_minute >= 30)

                for data in export_data_list:
                    user_id = data["user_id"]
                    record = records_dict.get(user_id)
                    timestamp_entry = {
                        "time": data["time"],
                        "emotion": data["emotion"],
                        "camera": data["camera"]
                    }

                    if not record:    
                        # Đường dẫn ảnh
                        image_path = f"{image_folder}/{user_id}_{data['time'].replace(':', '_')}_check_in.jpg"
                        
                        # Tạo bản ghi mới cho check-in
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

                        # Lưu ảnh check-in với khung bbox
                        img = data["image"].copy()
                        x1, y1, x2, y2 = map(int, data["bbox"])
                        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.imwrite(image_path, img)

                        # Lưu tên để xin chào
                        welcome_users.append(data["name"])
                    else:
                        # Cập nhật bản ghi cũ
                        update_operation = {
                            "$push": {"timestamps": timestamp_entry},
                            "$set": {"check_out_time": data["time"]}
                        }
                        
                        # Kiểm tra và chào tạm biệt nếu sau 17:30 và chưa chào
                        if is_after_1730 and not record.get("has_been_goodbye", False):
                            goodbye_users.append(data["name"])
                            update_operation["$set"]["has_been_goodbye"] = True  # Đánh dấu đã chào

                        operations.append(UpdateOne(
                            {"date": today_date, "user_id": user_id},
                            update_operation
                        ))

                # Thực hiện batch update
                if operations:
                    config.data_collection.bulk_write(operations)

                export_data_list.clear()
                start_time = time.time()

                # Gửi thông báo
                if welcome_users:
                    message = f"Xin chào {', '.join(welcome_users)}"
                    ns_send_notification(message)
                if goodbye_users:
                    message = f"Chào tạm biệt {', '.join(goodbye_users)}"
                    ns_send_notification(message)
                    
        # Đảm bảo release sau khi xử lý tất cả các khung hình
        self._release_writers()

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