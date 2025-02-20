from pathlib import Path
from utils.general import increment_path, check_file
from utils.dataloaders import LoadImages, LoadStreams, LoadScreenshots, IMG_FORMATS, VID_FORMATS


class MediaManager:
    def __init__(self,
                 source='0',
                 project='runs',
                 name='exp',
                 imgsz=(640, 640),
                 exist_ok=False,
                 save=False,
                 vid_stride=1,
                 view_img=False,
                 save_txt=False,
                 save_conf=False,
                 save_crop=False,
                 line_thickness=3,
                 face_recognition=False,
                 hide_labels=False,
                 hide_conf=False,
                 face_emotion=False,
                 check_small_face=False,
                 streaming=False,
                 export_data=False,
                 time_to_save=5,
                 show_time_process=False,
                 raise_hand=False):
        """
        Khởi tạo MediaManager với thông tin về nguồn đầu vào và cấu hình thư mục lưu kết quả.
        """
        self.source = str(source)
        self.project = project
        self.name = name
        self.imgsz = imgsz
        self.exist_ok = exist_ok
        self.save_txt = save_txt
        self.save = save
        self.vid_stride = vid_stride
        self.view_img = view_img
        self.save_conf = save_conf
        self.save_crop = save_crop
        self.line_thickness = line_thickness
        self.face_recognition = face_recognition
        self.hide_labels = hide_labels
        self.hide_conf = hide_conf
        self.face_emotion = face_emotion
        self.check_small_face = check_small_face
        self.streaming = streaming
        self.export_data = export_data
        self.time_to_save = time_to_save
        self.show_time_process = show_time_process
        self.raise_hand = raise_hand

        self.save_dir = None
        self.dataset = None
        self.webcam = None
        self.batch_size = 1
        self.vid_path = []
        self.vid_writer = []
        self.save_img = None

        self.prepare_dataloader()
        if self.save or self.save_crop:
            self.prepare_directories()

    def prepare_directories(self):
        self.save_dir = increment_path(Path(self.project) / self.name, exist_ok=self.exist_ok)
        (self.save_dir / 'labels' if self.save_txt else self.save_dir).mkdir(parents=True, exist_ok=True)

    def prepare_dataloader(self):
        """
        Xử lý nguồn đầu vào và tạo dataloader tương ứng.
        """
        # Xác định loại nguồn đầu vào
        self.save_img = self.save
        is_file = Path(self.source).suffix[1:] in (IMG_FORMATS + VID_FORMATS)
        is_url = self.source.lower().startswith(('rtsp://', 'rtmp://', 'http://', 'https://'))
        self.webcam = self.source.isnumeric() or self.source.endswith('.txt') or (is_url and not is_file)
        screenshot = self.source.lower().startswith('screen')

        # Xử lý URL trỏ đến tệp
        if is_url and is_file:
            self.source = check_file(self.source)  # Tải tệp nếu cần

        # Tạo dataloader dựa trên loại nguồn
        if self.webcam:
            # check_imshow(warn=True)
            self.dataset = LoadStreams(self.source, img_size=self.imgsz, stride=32, auto=True, vid_stride=self.vid_stride)
            self.batch_size = len(self.dataset)
        elif screenshot:
            self.dataset = LoadScreenshots(self.source, img_size=self.imgsz, stride=32, auto=True)
        else:
            self.dataset = LoadImages(self.source, img_size=self.imgsz, stride=32, auto=True, vid_stride=self.vid_stride)

        # Chuẩn bị danh sách video writer và path
        self.vid_path = [None] * self.batch_size
        self.vid_writer = [None] * self.batch_size

    def get_dataloader(self):
        return self.dataset

    def get_save_directory(self):
        return self.save_dir