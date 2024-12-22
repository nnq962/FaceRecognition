import cv2
from insightface.app.common import Face
from insightface.model_zoo import model_zoo
import os
import platform
from pathlib import Path
from utils.plots import Annotator, save_one_box
from utils.general import LOGGER, Profile
import torch
from face_emotion import FERUtils
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "GFPGAN"))
from GFPGAN.run_gfpgan import GFPGANInference
from insightface_utils import crop_image, expand_image, is_small_face, search_ids, crop_and_align_faces, normalize_embeddings
from export_data import save_to_pandas, parse_face_data
import time
import onnxruntime as ort
ort.set_default_logger_severity(3)

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
                self.fer_class = FERUtils(gpu_memory_limit=2048)
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
    
    def process_face(self, img, bbox, kps=None, conf=None):
        """
        Xử lý nhận diện và phân tích cảm xúc cho một khuôn mặt.
        Args:
            img (numpy.ndarray): Ảnh đầu vào.
            bbox (numpy.ndarray): Bounding box của khuôn mặt.
            kps (numpy.ndarray): Keypoints (tùy chọn).
            conf (float): Độ tin cậy phát hiện (tùy chọn).
        Returns:
            str or None: Nhãn kết quả (ID và cảm xúc) hoặc None.
        """
        if conf is None or conf < 0.7:
            return None

        if self.media_manager.face_recognition:
            embedding = self.get_face_embedding(img=img, bb=bbox, kps=kps, conf=conf)
            result = search_id(embedding=embedding, top_k=1, threshold=0.4)
            if result:
                similarity_percent = int(result[0]['similarity'] * 100)
                label = f"{result[0]['id'].capitalize()} {similarity_percent}%"
                if self.media_manager.face_emotion:
                    emotion = self.fer_class.get_dominant_emotion(self.fer_class.analyze_face(img, bbox))[0]
                    emotion_label = f"{emotion[0].capitalize()} {int(emotion[1] * 100)}%"
                    label += f" | {emotion_label}"                        
                return label
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

            # Process predictions
            # per image
            for i, det in enumerate(pred):
                if self.media_manager.webcam:  
                    im0 = im0s[i].copy()
                else:
                    im0 = im0s.copy()

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
                    cropped_faces = crop_and_align_faces(im0, bboxes, keypoints, 0.5)
                    all_cropped_faces.extend(cropped_faces)
                face_counts.append(len(bboxes))

            ids = []
            with dt[1]:
                if self.media_manager.face_recognition and all_cropped_faces:
                    all_embeddings = self.get_face_embeddings(all_cropped_faces)
                    ids = search_ids(all_embeddings, top_k=1, threshold=0.5)

            results_per_image = []
            start_idx = 0

            for count in face_counts:
                results = [
                    {
                        "bbox": meta["bbox"],
                        "keypoints": meta["keypoints"],
                        "id": id_info[0]["id"] if id_info else "unknown",
                        "similarity": id_info[0]["similarity"] if id_info else None
                    }
                    for meta, id_info in zip(metadata[start_idx:start_idx + count], ids[start_idx:start_idx + count])
                ]
                results_per_image.append(results)
                start_idx += count

            # per image
            for img_index, faces in enumerate(results_per_image):
                seen += 1
                if self.media_manager.webcam:  
                    p, im0 = path[img_index], im0s[img_index].copy()
                    s += f'{img_index}: '
                else:
                    p, im0 = path, im0s.copy()

                p = Path(p)  # to Path
                if not self.media_manager.nosave:
                    save_path = str(self.save_dir / p.name)
                s += f'[{im0.shape[1]}x{im0.shape[0]}] '
                imc = im0.copy() if self.media_manager.save_crop else im0
                annotator = Annotator(im0, line_width=self.media_manager.line_thickness)
                
                if len(faces):
                    n = len(faces)
                    s += f"{n} {'face' if n == 1 else 'faces'}, "  # add to string

                    for face in faces:
                        bbox = face['bbox']
                        ID = face['id']
                        Similarity = f"{face['similarity'] * 100:.2f}%" if face['similarity'] is not None else "N/A"

                        label = f"{ID} {Similarity}"
            
                        if self.media_manager.save_img or self.media_manager.save_crop or self.media_manager.view_img:
                            if label is None or self.media_manager.hide_labels or self.media_manager.hide_conf:
                                label = None
                            color = (0, int(255 * bbox[4]), int(255 * (1 - bbox[4])))
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

                # Streaming RTSP
                if self.media_manager.streaming:
                    self.media_manager.push_frame_to_stream(i, im0)
            
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