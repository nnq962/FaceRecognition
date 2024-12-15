from pathlib import Path
from utils.general import increment_path, check_file, check_imshow
from utils.dataloaders import LoadImages, LoadStreams, LoadScreenshots, IMG_FORMATS, VID_FORMATS


class MediaManager:
    def __init__(self,
                 source='0',
                 project='runs',
                 name='exp',
                 imgsz=(640, 640),
                 exist_ok=False,
                 nosave=False,
                 vid_stride=1,
                 view_img=True,  # show results
                 save_txt=False,  # save results to *.txt
                 save_conf=False,  # save confidences in --save-txt labels
                 save_crop=False,  # save cropped prediction boxes
                 line_thickness=3,
                 face_recognition=False,
                 hide_labels=False,
                 hide_conf=False,
                 face_emotion=False):
        """
        Khởi tạo MediaManager với thông tin về nguồn đầu vào và cấu hình thư mục lưu kết quả.
        """
        self.source = str(source)  # Chuyển source sang chuỗi
        self.project = project  # Thư mục gốc để lưu kết quả
        self.name = name  # Tên của thư mục lưu
        self.imgsz = imgsz  # Kích thước ảnh (h, w)
        self.exist_ok = exist_ok  # Cho phép ghi đè thư mục cũ
        self.save_txt = save_txt  # Có lưu kết quả vào file txt hay không
        self.nosave = nosave  # Có lưu kết quả ảnh/video hay không
        self.vid_stride = vid_stride  # Video frame-rate stride
        self.view_img = view_img # show results
        self.save_conf = save_conf # save confidences in --save-txt labels
        self.save_crop = save_crop # Lưu ảnh đã cắt mặt
        self.line_thickness = line_thickness
        self.face_recognition = face_recognition
        self.hide_labels = hide_labels
        self.hide_conf = hide_conf
        self.face_emotion = face_emotion

        # Thuộc tính sẽ được khởi tạo bởi các phương thức
        self.save_dir = None
        self.dataset = None
        self.webcam = None
        self.batch_size = 1
        self.vid_path = []
        self.vid_writer = []
        self.save_img = None

        self.prepare_dataloader()
        if not self.nosave:  # Chỉ tạo thư mục khi không có nosave
            self.prepare_directories()

    def prepare_directories(self):
        """
        Tạo thư mục lưu kết quả.
        """
        self.save_dir = increment_path(Path(self.project) / self.name, exist_ok=self.exist_ok)
        (self.save_dir / 'labels' if self.save_txt else self.save_dir).mkdir(parents=True, exist_ok=True)

    def prepare_dataloader(self):
        """
        Xử lý nguồn đầu vào và tạo dataloader tương ứng.
        """
        # Xác định loại nguồn đầu vào
        self.save_img = not self.nosave and not self.source.endswith('.txt')  # save inference images
        is_file = Path(self.source).suffix[1:] in (IMG_FORMATS + VID_FORMATS)
        is_url = self.source.lower().startswith(('rtsp://', 'rtmp://', 'http://', 'https://'))
        self.webcam = self.source.isnumeric() or self.source.endswith('.txt') or (is_url and not is_file)
        screenshot = self.source.lower().startswith('screen')

        # Xử lý URL trỏ đến tệp
        if is_url and is_file:
            self.source = check_file(self.source)  # Tải tệp nếu cần

        # Tạo dataloader dựa trên loại nguồn
        if self.webcam:
            check_imshow(warn=True)
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
        """
        Trả về dataloader đã chuẩn bị.
        """
        return self.dataset

    def get_save_directory(self):
        """
        Trả về đường dẫn thư mục lưu kết quả.
        """
        return self.save_dir


