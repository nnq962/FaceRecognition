from pathlib import Path
from utils.general import increment_path, check_file, check_imshow
from utils.dataloaders import LoadImages, LoadStreams, LoadScreenshots, IMG_FORMATS, VID_FORMATS
import subprocess
import cv2


def ffmpeg2rtsp(rtsp_url, width, height, fps):
    command = [
        'ffmpeg',
        '-y',  # Ghi đè nếu cần
        '-f', 'rawvideo',  # Định dạng video đầu vào
        '-vcodec', 'rawvideo',
        '-pix_fmt', 'bgr24',  # OpenCV sử dụng định dạng BGR24
        '-s', f'{width}x{height}',  # Kích thước video
        '-r', str(fps),  # Tốc độ khung hình
        '-i', '-',  # Đọc từ stdin
        '-c:v', 'libx264',
        '-preset', 'ultrafast',  # Preset để cân bằng hiệu suất và chất lượng
        '-tune', 'zerolatency',  # Tối ưu hóa độ trễ thấp
        '-b:v', '1M',  # Giới hạn bitrate video (1Mbps)
        '-maxrate', '1M',  # Bitrate tối đa
        '-bufsize', '2M',  # Kích thước bộ đệm
        '-f', 'rtsp',  # Định dạng stream RTSP
        rtsp_url  # URL đích
    ]
    return subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

def generate_name_names(source):
    # Kiểm tra loại nguồn
    is_url = source.lower().startswith(('rtsp://', 'rtmp://', 'http://', 'https://'))
    is_webcam = source.isnumeric() or source.lower().startswith('screen')  # Webcam

    names = []

    # Nếu là tệp chứa danh sách
    if source.endswith(".txt"):
        with open(source, "r") as file:
            lines = file.readlines()
            for index, line in enumerate(lines):
                line = line.strip()  # Loại bỏ ký tự xuống dòng
                if line.isnumeric():  # Nếu là webcam (số 0, 1, ...)
                    names.append(f"webcam_{line}")
                elif line.lower().startswith("rtsp://"):  # Nếu là đường dẫn RTSP
                    names.append(f"rtsp_camera_{index + 1}")
    elif is_webcam:  # Nếu là webcam
        names.append(f"webcam_{source}")
    elif is_url:  # Nếu là URL RTSP
        names.append(f"rtsp_camera_1")

    return names

class MediaManager:
    def __init__(self,
                 source='0',
                 project='runs',
                 name='exp',
                 imgsz=(640, 640),
                 exist_ok=False,
                 save=False,
                 vid_stride=1,
                 view_img=False,  # show results
                 save_txt=False,  # save results to *.txt
                 save_conf=False,  # save confidences in --save-txt labels
                 save_crop=False,  # save cropped prediction boxes
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
                 raise_hand=False,
                 qr_code=False):
        """
        Khởi tạo MediaManager với thông tin về nguồn đầu vào và cấu hình thư mục lưu kết quả.
        """
        self.source = str(source)  # Chuyển source sang chuỗi
        self.project = project  # Thư mục gốc để lưu kết quả
        self.name = name  # Tên của thư mục lưu
        self.imgsz = imgsz  # Kích thước ảnh (h, w)
        self.exist_ok = exist_ok  # Cho phép ghi đè thư mục cũ
        self.save_txt = save_txt  # Có lưu kết quả vào file txt hay không
        self.save = save  # Có lưu kết quả ảnh/video hay không
        self.vid_stride = vid_stride  # Video frame-rate stride
        self.view_img = view_img # show results
        self.save_conf = save_conf # save confidences in --save-txt labels
        self.save_crop = save_crop # Lưu ảnh đã cắt mặt
        self.line_thickness = line_thickness
        self.face_recognition = face_recognition
        self.hide_labels = hide_labels
        self.hide_conf = hide_conf
        self.face_emotion = face_emotion
        self.check_small_face = check_small_face
        self.streaming = streaming
        self.export_data = export_data  # Có export dữ liệu khuôn mặt vào file CSV hay không
        self.time_to_save = time_to_save
        self.show_time_process = show_time_process
        self.raise_hand = raise_hand
        self.qr_code = qr_code

        # Thuộc tính sẽ được khởi tạo bởi các phương thức
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
        """
        Trả về dataloader đã chuẩn bị.
        """
        return self.dataset

    def get_save_directory(self):
        """
        Trả về đường dẫn thư mục lưu kết quả.
        """
        return self.save_dir
    
    def init_stream(self):
        """
        Tạo các tiến trình FFmpeg dựa theo số lượng batch_size (số webcam).
        """
        if not self.streaming:
            print("Streaming is disabled.")
            return

        if not self.webcam:
            print("Source is not a webcam; streaming not supported for this source.")
            return

        self.ffmpeg_procs = []  # Danh sách lưu các tiến trình FFmpeg cho từng webcam

        # Duyệt qua từng webcam (self.dataset)
        for i in range(self.batch_size):
            rtsp_url = f"rtsp://localhost:8554/stream{i + 1}"

            # Lấy thông số cho từng webcam từ dataset
            frame = self.dataset.imgs[i]  # Frame mẫu từ webcam i
            original_height, original_width = frame.shape[:2]
            
            # Giảm độ phân giải và FPS (thay đổi kích thước nếu cần)
            target_width = 1280  # Độ phân giải mong muốn (VD: 1280x720)
            target_height = 720
            target_fps = 15  # FPS giảm xuống (nếu cần)

            print(f"Webcam {i + 1} - Original Width: {original_width}, Original Height: {original_height}, FPS: {self.dataset.fps[i]}")
            print(f"Stream {i + 1} - Target Width: {target_width}, Target Height: {target_height}, Target FPS: {target_fps}")
            print(f"Initializing stream {i + 1} at {rtsp_url}...")

            # Khởi tạo tiến trình FFmpeg với thông số giảm
            ffmpeg_proc = ffmpeg2rtsp(rtsp_url, target_width, target_height, target_fps)
            self.ffmpeg_procs.append(ffmpeg_proc)

        print(f"{len(self.ffmpeg_procs)} streaming processes initialized.")

    def push_frame_to_stream(self, index, frame):
        """
        Đẩy một frame vào tiến trình FFmpeg tương ứng.

        Args:
            index (int): Chỉ số của tiến trình FFmpeg (stream index).
            frame (numpy.ndarray): Frame cần đẩy vào tiến trình.
        """
        if not hasattr(self, 'ffmpeg_procs') or not self.ffmpeg_procs:
            print("No FFmpeg processes initialized. Call init_stream first.")
            return

        if index >= len(self.ffmpeg_procs):
            raise ValueError(f"Stream index {index} out of range. Total streams: {len(self.ffmpeg_procs)}.")

        proc = self.ffmpeg_procs[index]  # Lấy tiến trình FFmpeg tương ứng với chỉ số
        if proc and proc.stdin:
            try:
                # Giảm độ phân giải trước khi đẩy vào tiến trình FFmpeg
                target_width = 1280  # Độ phân giải mục tiêu
                target_height = 720
                frame_resized = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)

                proc.stdin.write(frame_resized.tobytes())
            except BrokenPipeError:
                print(f"Stream {index + 1} has ended unexpectedly. Restarting process...")
                # Khởi động lại tiến trình nếu gặp lỗi
                rtsp_url = f"rtsp://localhost:8554/stream{index + 1}"
                height, width = frame.shape[:2]
                fps = 30  # Hoặc lấy từ dataset nếu cần
                self.ffmpeg_procs[index] = ffmpeg2rtsp(rtsp_url, width, height, fps)