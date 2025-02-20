import cv2
from insightface.app.common import Face
from insightface.model_zoo import model_zoo
import os
import platform
from pathlib import Path
from utils.plots import Annotator
from utils.general import LOGGER, Profile
from face_emotion import FERUtils
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "GFPGAN"))
from GFPGAN.run_gfpgan import GFPGANInference
from insightface_utils import crop_image, expand_image, is_small_face, search_ids, crop_and_align_faces, normalize_embeddings, search_ids_mongoDB, save_data_to_mongo
from hand_raise_detector import is_person_raising_hand_image, is_hand_opened_in_image, expand_and_crop_image
from websocket_server import send_notification
import time
import onnxruntime as ort
ort.set_default_logger_severity(3)
import numpy as np
from config import config


class InsightFaceDetector:
    """
    InsightFaceDetector is a class for detecting and recognizing faces using InsightFace models.
    
    Args:
        media_manager: An optional media manager object for handling datasets.
    """
    def __init__(self, media_manager=None):
        self.det_model_path = os.path.expanduser("~/Models/det_10g.onnx")
        self.rec_model_path = os.path.expanduser("~/Models/w600k_r50.onnx")
        self.det_model = None
        self.rec_model = None
        self.media_manager = media_manager

        if self.media_manager is not None:
            self.dataset = self.media_manager.get_dataloader()
            self.save_dir = self.media_manager.get_save_directory()
            if self.media_manager.face_emotion:
                self.fer_class = FERUtils(gpu_memory_limit=config.vram_limit_for_FER * 1024)
            if self.media_manager.check_small_face:
                self.gfpgan_model = GFPGANInference(upscale=2)
            if self.media_manager.streaming:
                self.media_manager.init_stream()

        self.load_model()

    def load_model(self):
        """Load detection and recognition models"""
        self.det_model = model_zoo.get_model(self.det_model_path)
        self.det_model.prepare(ctx_id=0, input_size=(640, 640))
        
        self.rec_model = model_zoo.get_model(self.rec_model_path)
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
    
    def get_face_detects(self, imgs):
        """
        Detect faces for a list of images.

        Args:
            imgs (list of numpy.ndarray): List of images loaded using cv2.imread.

        Returns:
            list: A list of detection results for each image. If no faces are detected in an image,
                None is added to the list. Each detection result is a tuple:
                (bounding_boxes, keypoints), where:
                - bounding_boxes: numpy.ndarray of shape (n_faces, 5) containing [x1, y1, x2, y2, confidence].
                - keypoints: numpy.ndarray of shape (n_faces, 5, 2) containing facial landmarks.
                If no faces are detected, (array([], shape=(0, 5), dtype=float32), array([], shape=(0, 5, 2), dtype=float32)) is returned.
        """
        if not isinstance(imgs, list):
            imgs = [imgs]

        all_results = []
        for img in imgs:
            result = self.det_model.detect(img)
            if result[0].shape[0] == 0:
                all_results.append(None)
            else:
                all_results.append(result)
        return all_results

    def get_face_embeddings(self, cropped_images):
        embeddings = self.rec_model.get_feat(cropped_images)
        return normalize_embeddings(embeddings)
    
    def get_frame(self, im0s, i, webcam=False):
        if webcam:
            return im0s[i]
        return im0s
    
    def check_raising_hand(self, frame, bbox, id, timestamp, camera_name):
        if not self.media_manager.raise_hand:
            return
        cropped_expand_image = expand_and_crop_image(frame, bbox, left=2.6, right=2.6, top=1.6, bottom=2.6)

        hand_open = is_hand_opened_in_image(cropped_expand_image)
        hand_raised = is_person_raising_hand_image(cropped_expand_image)

        if hand_open and hand_raised:
            message = {
                "user_id": id,
                "type": "up",
                "time": timestamp,
                "camera": camera_name
            }
            send_notification(message)
        else:
            message = {
                "user_id": id,
                "type": "down",
                "time": timestamp,
                "camera": camera_name
            }
            send_notification(message)

    def get_face_emotions(self, img, bounding_boxes):
        """
        Analyze emotions of faces in an image.

        This method detects emotions for faces using the provided bounding boxes 
        (in [x1, y1, x2, y2] format) and returns the dominant emotion with its probability.

        Args:
            img (numpy.ndarray): Input image containing faces.
            bounding_boxes (list or numpy.ndarray): Face bounding boxes in [x1, y1, x2, y2] format.

        Returns:
            list: A list of dictionaries with the dominant emotion and its probability,
                or an empty list if `bounding_boxes` is empty.
        """
        if not bounding_boxes:
            return []

        if not self.media_manager.face_emotion:
            return []

        emotions = self.fer_class.analyze_face(img, bounding_boxes)
        dominant_emotions = self.fer_class.get_dominant_emotions(emotions)
        return dominant_emotions
    
    def restored_image(self, img, bounding_box, min_size=50):
        """
        Restore a small face using GFPGAN if it meets the size criteria.

        Args:
            img (numpy.ndarray): Input image containing the face.
            bounding_box (list or numpy.ndarray): Bounding box in [x1, y1, x2, y2] format.
            min_size (int): Minimum size threshold for detecting a small face (default: 50).

        Returns:
            numpy.ndarray or None: Restored image if the face is small; otherwise, None.
        """
        if self.media_manager.check_small_face and is_small_face(bounding_box, min_size):
            cropped_image = crop_image(img, bounding_box)
            restored_img = self.gfpgan_model.inference(cropped_image)
            return restored_img
        
        return None
        
    def run_inference(self):
        """
        Run inference on images/video and display results
        """
        windows = []
        seen, dt = 0, (Profile(), Profile(), Profile())
        start_time = time.time()

        for path, _, im0s, vid_cap, s in self.dataset:
            # Inference
            with dt[0]:
                pred = self.get_face_detects(im0s)

            all_cropped_faces = []
            metadata = []
            face_counts = []

            # Crop all faces
            for i, det in enumerate(pred):
                im0 = self.get_frame(im0s, i, self.media_manager.webcam)

                if det is None:
                    face_counts.append(0)
                    continue
                
                bboxes, keypoints = det
                for bbox, kps in zip(bboxes, keypoints):
                    metadata.append({
                        "image_index": i,
                        "bbox": bbox,
                        "keypoints": kps
                    })

                if self.media_manager.face_recognition:
                    cropped_faces = crop_and_align_faces(im0, bboxes, keypoints, 0.7)
                    all_cropped_faces.extend(cropped_faces)

                face_counts.append(len(bboxes))
            
            # for crop in all_cropped_faces:
            #     print(len(all_cropped_faces))
            #     print(is_real_face(img=crop, threshold=0.65))

            # Search ids, emotion analysis, check raising hand, check small face (beta)
            ids = []
            emotions = []

            with dt[1]:
                if self.media_manager.face_recognition and all_cropped_faces:
                    all_embeddings = self.get_face_embeddings(all_cropped_faces)
                    ids = search_ids_mongoDB(all_embeddings, top_k=1, threshold=0.5)

                    if self.media_manager.face_emotion or self.media_manager.raise_hand:
                        start_idx = 0

                        for img_index, im0 in enumerate(im0s):
                            im0 = self.get_frame(im0s, img_index, self.media_manager.webcam)
                            
                            metadata_for_image = [meta for meta in metadata if meta["image_index"] == img_index]
                            ids_for_image = ids[start_idx:start_idx + len(metadata_for_image)] if self.media_manager.face_recognition else []
                            
                            # Prepare for emotion analysis
                            bboxes_emotion = []
                            emotion_indices = []
                            dominant_emotions = [{"dominant_emotion": "unknown", "probability": "N/A"}] * len(metadata_for_image)

                            for meta_idx, (meta, id_info) in enumerate(zip(metadata_for_image, ids_for_image)):
                                bbox = np.array(meta["bbox"][:4], dtype=int)
                                
                                if id_info:
                                    bboxes_emotion.append(bbox)
                                    emotion_indices.append(meta_idx)

                                    self.check_raising_hand(im0, bbox, id_info[0]['id'], config.get_vietnam_time(), config.camera_names[img_index] if self.media_manager.webcam else "Photo")
                                
                                else:
                                    restored_img = self.restored_image(im0, bbox, min_size=50)

                                    if restored_img:
                                        embedding = self.get_face_embeddings(restored_img)
                                        new_id = search_ids_mongoDB(embedding, top_k=1, threshold=0.1)
                                
                                        if new_id:
                                            ids[start_idx + meta_idx] = new_id[0]
                                
                            emotions_batch = self.get_face_emotions(im0, bboxes_emotion)

                            for idx, emotion in zip(emotion_indices, emotions_batch):
                                dominant_emotions[idx] = {"dominant_emotion": emotion["dominant_emotion"], "probability": emotion["probability"]}

                            emotions.extend(dominant_emotions)
                            start_idx += len(metadata_for_image)
                            
            # Return result
            results_per_image = []
            start_idx = 0

            for count in face_counts:
                if self.media_manager.face_recognition and ids:
                    ids_for_image = ids[start_idx:start_idx + count]
                else:
                    ids_for_image = [None] * count

                if self.media_manager.face_emotion and emotions:
                    emotions_for_image = [
                        {
                            "emotion": emotion["dominant_emotion"],
                            "probability": f"{float(emotion['probability']) * 100:.2f}%" if isinstance(emotion["probability"], (int, float)) else "N/A"
                        }
                        for emotion in emotions[start_idx:start_idx + count]
                    ]
                else:
                    emotions_for_image = [{"emotion": "unknown", "probability": "N/A"}] * count

                results = [
                    {
                        "bbox": meta["bbox"],
                        "keypoints": meta["keypoints"],
                        "id": id_info[0]["id"] if id_info else "unknown",
                        "similarity": f"{id_info[0]['similarity'] * 100:.2f}%" if id_info else "N/A",
                        "emotion": emotion["emotion"],
                        "emotion_probability": emotion["probability"]
                    }
                    for meta, id_info, emotion in zip(
                        metadata[start_idx:start_idx + count],
                        ids_for_image,
                        emotions_for_image
                    )
                ]

                results_per_image.append(results)
                start_idx += count

            # Export data to MongoDB
            if self.media_manager.export_data:
                current_time = time.time()

                if current_time - start_time > self.media_manager.time_to_save:
                    for img_index, faces in enumerate(results_per_image):
                        data_to_save = []
                        camera_name = config.camera_names[img_index]

                        for face in faces:
                            if face["id"] != "unknown":
                                name = face["id"]
                                recognition_prob = float(face["similarity"].replace("%", "")) if face["similarity"] != "N/A" else None
                                emotion = face["emotion"] if face["emotion"] else "unknown"
                                emotion_prob = float(face["emotion_probability"].replace("%", "")) if face["emotion_probability"] != "N/A" else None

                                data_to_save.append({
                                    "timestamp": config.get_vietnam_time(),
                                    "id": name,
                                    "similarity": recognition_prob,
                                    "emotion": emotion,
                                    "emotion_prob": emotion_prob,
                                    "camera_name": camera_name
                                })

                        if data_to_save:
                            save_data_to_mongo(data_to_save)

                    start_time = current_time
                
            # Display results
            for img_index, faces in enumerate(results_per_image):
                seen += 1
                
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
                
                if len(faces):
                    n = len(faces)
                    s += f"{n} {'face' if n == 1 else 'faces'}, "

                    for face in faces:
                        bbox = face['bbox']
                        id = face["id"]
                        similarity = face["similarity"]
                        emotion = face["emotion"]
                        emotion_prob = face["emotion_probability"]

                        label = f"{id} {similarity} | {emotion} {emotion_prob}"
            
                        if self.media_manager.save_img or self.media_manager.save_crop or self.media_manager.view_img:
                            if label is None or self.media_manager.hide_labels or self.media_manager.hide_conf:
                                label = None

                            color = (0, int(255 * bbox[4]), int(255 * (1 - bbox[4])))
                            annotator.box_label(bbox, label, color=color)

                        if self.media_manager.save_crop:
                            crops_dir = Path(self.save_dir) / 'crops'
                            crops_dir.mkdir(parents=True, exist_ok=True)
                            face_crop = crop_image(imc, bbox[:4])
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

            if self.media_manager.show_time_process:
                # Total processing time for a single frame (inference + processing)
                frame_time = (dt[0].dt + dt[1].dt) * 1E3  # Frame processing time in milliseconds
                # Calculate instantaneous FPS for the current frame
                fps_instant = 1000 / frame_time if frame_time > 0 else float('inf')
                # Print processing time (inference + processing) and instantaneous FPS
                LOGGER.info(f"{s}{'' if len(faces) else '(no detections), '}"
                            f"Inference: {dt[0].dt * 1E3:.1f}ms, Processing: {dt[1].dt * 1E3:.1f}ms, "
                            f"FPS: {fps_instant:.2f}")

        # Ensure release after all frames processed
        for writer in self.media_manager.vid_writer:
            if isinstance(writer, cv2.VideoWriter):
                writer.release()
                print("Video writer released successfully.")

        t = dt[0].t / seen * 1E3
        LOGGER.info(f'Speed: %.1fms inference per image.' % t)