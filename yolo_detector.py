import cv2
import numpy as np
from ultralytics import YOLO
from rknn.api import RKNN
from pathlib import Path
from utils.plots import Annotator, save_one_box
import platform
import yolo_detector_utils

YOLO_RKNN_PATH = "yolov11n-face_rknn_model"
ARCFACE_RKNN_PATH = "arcface_rknn_model/arcface.rknn"

class YoloDetector:
    """
    A class for detecting faces using YOLO and extracting facial embeddings using ArcFace.
    """
    def __init__(self, imgsz=320, media_manager=None):
        """
        Initializes YOLO and ArcFace models.
        """
        self.imgsz = imgsz
        self.media_manager = media_manager

        if self.media_manager is not None:
            self.dataset = self.media_manager.get_dataloader()
            self.save_dir = self.media_manager.get_save_directory()

        self.load_models()

    def load_models(self):
        """ 
        Load YOLO and ArcFace rknn models. 
        """
        print("-" * 80)
        try:
            self.yolo_model = YOLO(YOLO_RKNN_PATH, task="detect")
            print("YOLO model loaded successfully!")
        except Exception as e:
            print(f"Error loading YOLO model: {e}")

        try:
            self.arcface_model = RKNN()
            self.arcface_model.load_rknn(ARCFACE_RKNN_PATH)
            self.arcface_model.init_runtime(target="rk3588")
            print("ArcFace model loaded successfully!")
        except Exception as e:
            print(f"Error loading ArcFace model: {e}")
        print("-" * 80)

    def get_face_detects(self, imgs, verbose=False, conf=0.6):
        """
        Detects faces in the given images using the YOLO model.

        Args:
            imgs (list or np.ndarray): A single image or a list of images.

        Returns:
            list of np.ndarray: A list containing detected faces for each input image.
            Each entry in the list is a NumPy array of shape (N, 5), where:
                - N is the number of detected faces.
                - The first four values represent the bounding box coordinates [x1, y1, x2, y2].
                - The last value represents the confidence score.
                - If no face is detected, an empty array of shape (0, 5) is returned.
        """
        if not isinstance(imgs, list):
            imgs = [imgs]

        results = []
        
        for img in imgs:
            result = self.yolo_model(img, imgsz=self.imgsz, verbose=verbose, conf=conf)[0]
            boxes = np.array(result.boxes.xyxy)
            scores = np.array(result.boxes.conf)

            if boxes.shape[0] > 0:
                faces = np.column_stack((boxes, scores))
            else:
                faces = np.empty((0, 5))

            results.append(faces)

        return results

    def get_face_embeddings(self, face_images):
        """
        Extracts and normalizes facial embeddings from detected face images using the ArcFace model.

        Args:
            face_images (list of np.ndarray): List of cropped face images.

        Returns:
            np.ndarray: A NumPy array of shape (N, 128) containing L2-normalized embeddings.
        """
        if not face_images:
            return np.empty((0, 128))

        embeddings = []
        
        for face in face_images:
            processed_face = self.preprocess_image(face)

            output = self.arcface_model.inference(inputs=[processed_face], data_format='nhwc')
            embedding = output[0][0]

            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

            embeddings.append(embedding)

        return np.array(embeddings)

    def preprocess_image(self, img_face):
        """
        Preprocesses a face image for ArcFace embedding extraction.

        Args:
            img_face (np.ndarray): Cropped face image.

        Returns:
            np.ndarray: Preprocessed face image ready for inference.
        """
        img_face = cv2.resize(img_face, (112, 112))
        img_face = cv2.cvtColor(img_face, cv2.COLOR_BGR2RGB)
        img_face = img_face.astype(np.float32)
        img_face = img_face[np.newaxis, ...]
        return img_face

    def get_frame(self, im0s, i, webcam=False):
        if webcam:
            return im0s[i]
        return im0s

    def crop_faces(self, img, bounding_boxes, margin=10):
        cropped_faces = []
        h, w, _ = img.shape

        for bbox in bounding_boxes:
            x1, y1, x2, y2, conf = bbox
            
            x1 = max(0, x1 - margin)
            y1 = max(0, y1 - margin)
            x2 = min(w, x2 + margin)
            y2 = min(h, y2 + margin)

            face_crop = img[int(y1):int(y2), int(x1):int(x2)].copy()
            
            if face_crop.shape[0] > 0 and face_crop.shape[1] > 0:
                cropped_faces.append(face_crop)

        return cropped_faces

    def get_ids(self, img, bounding_boxes, threshold=0.6):
        cropped_faces = self.crop_faces(img, bounding_boxes=bounding_boxes, margin=10)
        embeddings = self.get_face_embeddings(cropped_faces)
        ids = yolo_detector_utils.search_annoys(embeddings, threshold=threshold)
        return ids

    def run_inference(self):
        windows = []

        for path, _, im0s, vid_cap, s in self.dataset:
            pred = self.get_face_detects(im0s, verbose=False, conf=0.6)
            # pred = [faces_img_0, faces_img_1,...]

            for img_index, faces in enumerate(pred):
                # faces = [face_0, face_1,...]
                if self.media_manager.webcam:  
                    p = path[img_index]
                else:
                    p = path

                im0 = self.get_frame(im0s, img_index, self.media_manager.webcam)

                p = Path(p)
                if self.media_manager.save or self.media_manager.save_crop:
                    save_path = str(self.save_dir / p.name)
                imc = im0.copy() if self.media_manager.save_crop else im0
                annotator = Annotator(im0, line_width=self.media_manager.line_thickness)

                if self.media_manager.face_recognition:
                    ids = self.get_ids(img=im0, bounding_boxes=faces, threshold=0.7)

                if len(faces):  # fer face
                    for i, face in enumerate(faces):
                        bbox = face[:4]

                        id_info = ids[i]
                        if id_info and isinstance(id_info, list) and len(id_info) > 0:
                            id_data = id_info[0]
                            label = f"ID: {id_data['id']} {id_data['similarity']:.2f}"
                        else:
                            label = "ID: Unknown"

                        if self.media_manager.save_img or self.media_manager.save_crop or self.media_manager.view_img:
                            if label is None or self.media_manager.hide_labels or self.media_manager.hide_conf:
                                label = None

                            color = (0, int(255 * face[4]), int(255 * (1 - face[4])))
                            annotator.box_label(bbox, label, color=color)

                        if self.media_manager.save_crop:
                            x1, y1, x2, y2 = map(int, bbox)
                            face_crop = imc[y1:y2, x1:x2]
                            cv2.imwrite(str(self.save_dir / f'{p.stem}.jpg'), face_crop)
                                
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

