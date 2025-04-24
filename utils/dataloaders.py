import glob
import math
import os
import sys
import time
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse
import cv2
import numpy as np
import re
from utils.logger_config import LOGGER
import json
import subprocess

# Parameters
IMG_FORMATS = 'bmp', 'dng', 'jpeg', 'jpg', 'mpo', 'png', 'tif', 'tiff', 'webp', 'pfm'  # include image suffixes
VID_FORMATS = 'asf', 'avi', 'gif', 'm4v', 'mkv', 'mov', 'mp4', 'mpeg', 'mpg', 'ts', 'wmv'  # include video suffixes


def clean_str(s):
    # Cleans a string by replacing special characters with underscore _
    return re.sub(pattern="[|@#!¡·$€%&()=?¿^*;:,¨´><+]", repl="_", string=s)


def is_colab():
    # Is environment a Google Colab instance?
    return 'google.colab' in sys.modules


def is_kaggle():
    # Is environment a Kaggle Notebook?
    return os.environ.get('PWD') == '/kaggle/working' and os.environ.get('KAGGLE_URL_BASE') == 'https://www.kaggle.com'


class LoadImages:
    def __init__(self, path, vid_stride=1):
        files = []
        for p in sorted(path) if isinstance(path, (list, tuple)) else [path]:
            p = str(Path(p).resolve())
            if '*' in p:
                files.extend(sorted(glob.glob(p, recursive=True)))  # glob
            elif os.path.isdir(p):
                files.extend(sorted(glob.glob(os.path.join(p, '*.*'))))  # dir
            elif os.path.isfile(p):
                files.append(p)  # files
            else:
                raise FileNotFoundError(f'{p} does not exist')

        images = [x for x in files if x.split('.')[-1].lower() in IMG_FORMATS]
        videos = [x for x in files if x.split('.')[-1].lower() in VID_FORMATS]
        ni, nv = len(images), len(videos)

        self.files = images + videos
        self.nf = ni + nv  # number of files
        self.video_flag = [False] * ni + [True] * nv
        self.mode = 'image'
        self.vid_stride = vid_stride  # video frame-rate stride
        if any(videos):
            self._new_video(videos[0])  # new video
        else:
            self.cap = None
        assert self.nf > 0, f'No images or videos found in {p}. ' \
                            f'Supported formats are:\nimages: {IMG_FORMATS}\nvideos: {VID_FORMATS}'

    def __iter__(self):
        self.count = 0
        return self

    def __next__(self):
        if self.count == self.nf:
            raise StopIteration
        path = self.files[self.count]

        if self.video_flag[self.count]:
            # Read video
            self.mode = 'video'
            for _ in range(self.vid_stride):
                self.cap.grab()
            ret_val, im0 = self.cap.retrieve()
            while not ret_val:
                self.count += 1
                self.cap.release()
                if self.count == self.nf:  # last video
                    raise StopIteration
                path = self.files[self.count]
                self._new_video(path)
                ret_val, im0 = self.cap.read()

            self.frame += 1
            # im0 = self._cv2_rotate(im0)  # for use if cv2 autorotation is False
            s = f'video {self.count + 1}/{self.nf} ({self.frame}/{self.frames}) {path}: '

        else:
            # Read image
            self.count += 1
            im0 = cv2.imread(path)  # BGR
            assert im0 is not None, f'Image Not Found {path}'
            s = f'image {self.count}/{self.nf} {path}: '

        return path, im0, self.cap, s

    def _new_video(self, path):
        # Create a new video capture object
        self.frame = 0
        self.cap = cv2.VideoCapture(path)
        self.frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) / self.vid_stride)
        self.orientation = int(self.cap.get(cv2.CAP_PROP_ORIENTATION_META))  # rotation degrees
        # self.cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 0)  # disable https://github.com/ultralytics/yolov5/issues/8493

    def _cv2_rotate(self, im):
        # Rotate a cv2 video manually
        if self.orientation == 0:
            return cv2.rotate(im, cv2.ROTATE_90_CLOCKWISE)
        elif self.orientation == 180:
            return cv2.rotate(im, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif self.orientation == 90:
            return cv2.rotate(im, cv2.ROTATE_180)
        return im

    def __len__(self):
        return self.nf  # number of files


class LoadStreams:
    def __init__(self, sources='streams.txt',
                 vid_stride=1,
                 reconnect_attempts=10, 
                 reconnect_delay=5, 
                 timeout=30,
                 use_gstreamer=True):
        
        LOGGER.info(
            f"Initializing LoadStreams with parameters:\n"
            f"→ sources: {sources}\n"
            f"→ vid_stride: {vid_stride}\n"
            f"→ reconnect_attempts: {reconnect_attempts}\n"
            f"→ reconnect_delay: {reconnect_delay}\n"
            f"→ timeout: {timeout}\n"
            f"→ use_gstreamer: {use_gstreamer}"
        )

        self.mode = 'stream'
        self.vid_stride = vid_stride  # video frame-rate stride
        self.has_gstreamer = False
        if use_gstreamer:
            self.has_gstreamer = cv2.videoio_registry.hasBackend(cv2.CAP_GSTREAMER)
            if not self.has_gstreamer:
                LOGGER.warning("OpenCV is not built with GStreamer support. Falling back to standard method.")
        
        # Thêm các tham số cho khả năng phục hồi
        self.reconnect_attempts = reconnect_attempts  # Số lần thử kết nối lại
        self.reconnect_delay = reconnect_delay  # Thời gian chờ giữa các lần kết nối lại (giây)
        self.timeout = timeout  # Timeout cho kết nối (giây)
        self.connection_status = []  # Trạng thái kết nối cho mỗi stream
        self.last_frame_time = []  # Thời gian nhận frame cuối cùng
        self.reconnecting = []  # Trạng thái đang thử kết nối lại
        
        sources = Path(sources).read_text().rsplit() if os.path.isfile(sources) else [sources]
        n = len(sources)
        self.sources = [clean_str(x) for x in sources]  # clean source names for later
        self.original_sources = sources.copy()  # Lưu lại URL gốc để kết nối lại khi cần
        self.imgs, self.fps, self.frames, self.threads = [None] * n, [0] * n, [0] * n, [None] * n
        self.connection_status = [True] * n  # Ban đầu giả định tất cả đều kết nối thành công
        self.last_frame_time = [time.time()] * n  # Thời gian nhận frame cuối
        self.reconnecting = [False] * n  # Không stream nào đang kết nối lại ban đầu
        self.caps = [None] * n  # Lưu lại các đối tượng VideoCapture
        
        for i, s in enumerate(sources):  # index, source
            # Start thread to read frames from video stream
            st = f'{i + 1}/{n}: {s}... '
            if urlparse(s).hostname in ('www.youtube.com', 'youtube.com', 'youtu.be'):  # if source is YouTube video
                # YouTube format i.e. 'https://www.youtube.com/watch?v=Zgi9g1ksQHc' or 'https://youtu.be/Zgi9g1ksQHc'
                # check_requirements(('pafy', 'youtube_dl==2020.12.2'))
                import pafy
                s = pafy.new(s).getbest(preftype="mp4").url  # YouTube URL
            s = eval(s) if s.isnumeric() else s  # i.e. s = '0' local webcam
            if s == 0:
                assert not is_colab(), '--source 0 webcam unsupported on Colab. Rerun command in a local environment.'
                assert not is_kaggle(), '--source 0 webcam unsupported on Kaggle. Rerun command in a local environment.'
            
            # Khởi tạo kết nối video
            success, cap = self.create_capture(s, i)
            
            if not success:
                LOGGER.warning(f'{st}Failed to open {s}. Will retry in background.')
                self.connection_status[i] = False
                self.imgs[i] = np.zeros((640, 640, 3), dtype=np.uint8)  # Tạo khung hình trống
            else:
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)  # warning: may return 0 or nan
                LOGGER.info(f"Stream {i}: FPS: {fps}")

                self.frames[i] = max(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), 0) or float('inf')  # infinite stream fallback
                self.fps[i] = max((fps if math.isfinite(fps) else 0) % 100, 0) or 30  # 30 FPS fallback

                _, self.imgs[i] = cap.read()  # guarantee first frame
                self.caps[i] = cap
                LOGGER.info(f"{st} Success ({self.frames[i]} frames {w}x{h} at {self.fps[i]:.2f} FPS)")
            
            # Luôn tạo thread, ngay cả khi kết nối ban đầu thất bại
            self.threads[i] = Thread(target=self.update, args=([i, cap, s]), daemon=True)
            self.threads[i].start()

    def detect_codec_ffmpeg(self, rtsp_url):
        """
        Sử dụng ffprobe để phát hiện codec của luồng RTSP
        
        Args:
            rtsp_url (str): URL của luồng RTSP
            
        Returns:
            str: 'h264', 'h265', hoặc None nếu không phát hiện được
        """
        try:
            LOGGER.info(f"Đang phát hiện codec cho {rtsp_url}...")
            # Chạy ffprobe để lấy thông tin codec
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_streams",
                "-select_streams", "v:0",
                "-print_format", "json",
                rtsp_url
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            data = json.loads(result.stdout)
            
            # Lấy tên codec từ luồng video
            codec_name = data.get("streams", [{}])[0].get("codec_name", "").lower()
            LOGGER.info(f"Phát hiện codec: {codec_name}")
            
            if codec_name in ["h264", "avc", "avc1"]:
                return "h264"
            elif codec_name in ["h265", "hevc"]:
                return "h265"
            else:
                LOGGER.warning(f"Không hỗ trợ codec: {codec_name}")
                return None
                
        except subprocess.TimeoutExpired:
            LOGGER.error(f"Hết thời gian chờ khi phát hiện codec cho {rtsp_url}")
            return None
        except Exception as e:
            LOGGER.error(f"Lỗi khi phát hiện codec: {str(e)}")
            return None

    def create_pipeline_for_codec(self, rtsp_url, codec=None):
        """
        Tạo pipeline GStreamer phù hợp với codec
        
        Args:
            rtsp_url (str): URL của luồng RTSP
            codec (str): 'h264', 'h265' hoặc None để tự động phát hiện
            
        Returns:
            str: Pipeline GStreamer hoàn chỉnh
        """
        # Nếu codec chưa được xác định, tiến hành phát hiện
        if codec is None:
            codec = self.detect_codec_ffmpeg(rtsp_url)
        
        # Phần đầu của pipeline là giống nhau
        base_pipeline = f"rtspsrc location={rtsp_url} latency=0 protocols=tcp drop-on-latency=true ! "
        
        # Tạo pipeline dựa trên codec
        if codec == "h264":
            pipeline = (
                f"{base_pipeline}rtph264depay ! h264parse ! avdec_h264 max-threads=4 ! "
                "videoconvert ! video/x-raw, format=BGR ! "
                "appsink drop=1 max-buffers=1 max-lateness=0 sync=false"
            )
            LOGGER.info(f"Sử dụng pipeline H264: {pipeline}")
        elif codec == "h265":
            pipeline = (
                f"{base_pipeline}rtph265depay ! h265parse ! avdec_h265 max-threads=4 ! "
                "videoconvert ! video/x-raw, format=BGR ! "
                "appsink drop=1 max-buffers=1 max-lateness=0 sync=false"
            )
            LOGGER.info(f"Sử dụng pipeline H265: {pipeline}")
        else:
            # Mặc định sử dụng H264 nếu không phát hiện được codec
            LOGGER.warning(f"Không phát hiện được codec, sử dụng H264 làm mặc định")
            pipeline = (
                f"{base_pipeline}rtph264depay ! h264parse ! avdec_h264 max-threads=4 ! "
                "videoconvert ! video/x-raw, format=BGR ! "
                "appsink drop=1 max-buffers=1 max-lateness=0 sync=false"
            )
        
        return pipeline

    def create_gstreamer_pipeline(self, source, index):
        """
        Tạo pipeline GStreamer tối ưu cho độ trễ thấp và tự động phát hiện codec
        """
        try:
            # Kiểm tra xem source có phải là RTSP hay không
            if isinstance(source, str) and source.startswith('rtsp://'):
                rtsp_url = source
                
                # Phát hiện codec và tạo pipeline phù hợp
                pipeline = self.create_pipeline_for_codec(rtsp_url)
                
                LOGGER.info(f"Using GStreamer pipeline for RTSP stream {index}: {source}")
                
                # Tạo VideoCapture với GStreamer backend
                cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
                
                # Kiểm tra xem GStreamer có hoạt động không
                if not cap.isOpened():
                    LOGGER.warning(f"GStreamer pipeline failed for stream {index}. Falling back to standard pipeline.")
                    return False, None
                    
                # Đọc thử một frame để xác nhận pipeline hoạt động
                ret, _ = cap.read()
                if not ret:
                    LOGGER.warning(f"Could not read frame from stream {index}. Pipeline may be incorrect.")
                    cap.release()
                    return False, None
                    
                return True, cap
            else:
                # Nếu không phải RTSP, không sử dụng GStreamer
                LOGGER.info(f"Stream {index} is not RTSP. Using standard pipeline.")
                return False, None
                    
        except Exception as e:
            LOGGER.error(f"Error creating GStreamer pipeline for stream {index}: {str(e)}")
            return False, None
                
    def create_capture(self, source, index):
        """Tạo và cấu hình VideoCapture với khả năng tự động phát hiện độ phân giải tối ưu"""
        try:
            LOGGER.info(f"Attempting to connect to stream: {source}")
            
            # Thử sử dụng GStreamer nếu được kích hoạt và source là RTSP
            if self.has_gstreamer and isinstance(source, str) and source.startswith('rtsp://'):
                success, cap = self.create_gstreamer_pipeline(source, index)
                if success:
                    LOGGER.info(f"Successfully connected to stream {index} using GStreamer")
                    return True, cap
                else:
                    LOGGER.warning(f"GStreamer connection failed for stream {index}. Falling back to standard method.")

            cap = cv2.VideoCapture(source)
            
            # Kiểm tra xem camera có được mở thành công không
            if not cap.isOpened():
                LOGGER.error(f"Cannot open stream {index}: {source}")
                return False, None
            
            # Thiết lập thông số kỹ thuật timeout cho RTSP, HTTP streams
            if isinstance(source, str) and ('rtsp:' in source or 'http:' in source or 'https:' in source):
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, self.timeout * 1000)
                cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, self.timeout * 1000)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Thiết lập MJPG để đạt FPS cao
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            
            # Lưu lại độ phân giải mặc định trước khi thử nghiệm
            default_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            default_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            LOGGER.info(f"Default resolution for stream {index}: {default_width}x{default_height}")
            
            # Đọc một frame để xác nhận độ phân giải mặc định
            ret, frame = cap.read()
            if ret:
                default_frame_width = frame.shape[1]
                default_frame_height = frame.shape[0]
                LOGGER.info(f"Default frame size for stream {index}: {default_frame_width}x{default_frame_height}")
            
            # Danh sách các độ phân giải tiêu chuẩn để thử, từ cao đến thấp
            standard_resolutions = [
                (3840, 2160),  # 4K
                (2560, 1440),  # 2K
                (1920, 1080),  # Full HD
                (1280, 720),   # HD
                (640, 480)     # VGA
            ]
            
            # Danh sách độ phân giải tùy chỉnh phổ biến
            custom_resolutions = [
                (1552, 1552),  # MacBook FaceTime HD
                (1760, 1328),  # MacBook FaceTime HD khác
            ]
            
            # Biến để lưu các độ phân giải hỗ trợ được tìm thấy
            supported_resolutions = []
            
            # Thử từng độ phân giải tiêu chuẩn trước
            for width, height in standard_resolutions:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                
                # Đọc độ phân giải thực tế sau khi thiết lập
                actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                # Đọc một frame để xác nhận
                ret, test_frame = cap.read()
                if not ret:
                    continue
                
                frame_height, frame_width = test_frame.shape[:2]
                
                # Lưu lại độ phân giải thực tế và tính tỷ lệ khung hình
                aspect_ratio = frame_width / frame_height
                resolution_info = {
                    'requested': (width, height),
                    'actual': (frame_width, frame_height),
                    'area': frame_width * frame_height,
                    'aspect_ratio': aspect_ratio
                }
                
                # Kiểm tra xem độ phân giải này đã được thêm vào chưa
                is_duplicate = False
                for res in supported_resolutions:
                    if res['actual'] == (frame_width, frame_height):
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    supported_resolutions.append(resolution_info)
                    LOGGER.info(f"Found supported resolution: {frame_width}x{frame_height} (AR: {aspect_ratio:.2f}) for stream {index}")
            
            # Thử các độ phân giải tùy chỉnh
            for width, height in custom_resolutions:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                
                ret, test_frame = cap.read()
                if not ret:
                    continue
                
                frame_height, frame_width = test_frame.shape[:2]
                aspect_ratio = frame_width / frame_height
                
                resolution_info = {
                    'requested': (width, height),
                    'actual': (frame_width, frame_height),
                    'area': frame_width * frame_height,
                    'aspect_ratio': aspect_ratio
                }
                
                # Kiểm tra trùng lặp
                is_duplicate = False
                for res in supported_resolutions:
                    if res['actual'] == (frame_width, frame_height):
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    supported_resolutions.append(resolution_info)
                    LOGGER.info(f"Found custom resolution: {frame_width}x{frame_height} (AR: {aspect_ratio:.2f}) for stream {index}")
            
            # Nếu không tìm thấy độ phân giải nào
            if not supported_resolutions:
                LOGGER.warning(f"No valid resolutions found for stream {index}. Using default.")
                return True, cap
            
            # Phân loại các độ phân giải theo các nhóm tỷ lệ khung hình
            aspect_ratio_groups = {
                '16:9': [],  # ~1.78
                '4:3': [],   # ~1.33
                '1:1': [],   # ~1.0
                'other': []
            }
            
            for res in supported_resolutions:
                ar = res['aspect_ratio']
                if 1.7 <= ar <= 1.8:  # 16:9
                    aspect_ratio_groups['16:9'].append(res)
                elif 1.3 <= ar <= 1.4:  # 4:3
                    aspect_ratio_groups['4:3'].append(res)
                elif 0.95 <= ar <= 1.05:  # 1:1
                    aspect_ratio_groups['1:1'].append(res)
                else:
                    aspect_ratio_groups['other'].append(res)
            
            # Sắp xếp mỗi nhóm theo diện tích (từ lớn đến nhỏ)
            for group in aspect_ratio_groups.values():
                group.sort(key=lambda x: x['area'], reverse=True)
            
            # Ưu tiên tìm độ phân giải tốt nhất theo thứ tự: 16:9, 4:3, 1:1, other
            best_resolution = None
            for ratio in ['16:9', '4:3', '1:1', 'other']:
                if aspect_ratio_groups[ratio]:
                    best_resolution = aspect_ratio_groups[ratio][0]
                    LOGGER.info(f"Selected best resolution with {ratio} aspect ratio: {best_resolution['actual']}")
                    break
            
            # Nếu vẫn không tìm được độ phân giải tốt nhất, sử dụng độ phân giải có diện tích lớn nhất
            if best_resolution is None:
                all_resolutions = sorted(supported_resolutions, key=lambda x: x['area'], reverse=True)
                if all_resolutions:
                    best_resolution = all_resolutions[0]
                    LOGGER.info(f"Selected resolution with largest area: {best_resolution['actual']}")
            
            # Thiết lập camera với độ phân giải tốt nhất
            if best_resolution:
                requested_width, requested_height = best_resolution['requested']
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, requested_width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, requested_height)
                
                # Kiểm tra lại để đảm bảo
                actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                # Thiết lập FPS mong muốn
                target_fps = 30
                cap.set(cv2.CAP_PROP_FPS, target_fps)
                actual_fps = cap.get(cv2.CAP_PROP_FPS)
                
                LOGGER.info(f"Final resolution for stream {index}: {actual_width}x{actual_height}, FPS: {actual_fps}")
            
            return True, cap
            
        except Exception as e:
            LOGGER.error(f"Error creating capture for stream {index}: {source}. Error: {str(e)}")
            return False, None
    
    def reconnect_stream(self, index, source):
        """Thử kết nối lại với stream"""
        if self.reconnecting[index]:
            return False, None  # Đã có thread đang thử kết nối lại
            
        self.reconnecting[index] = True
        LOGGER.warning(f"Attempting to reconnect to stream {index}: {source}")
        
        # Đóng kết nối cũ nếu còn tồn tại
        if self.caps[index] is not None:
            try:
                self.caps[index].release()
            except:
                pass
        
        # Thử kết nối lại với số lần thử xác định
        for attempt in range(self.reconnect_attempts):
            LOGGER.info(f"Reconnection attempt {attempt+1}/{self.reconnect_attempts} for stream {index}")
            success, cap = self.create_capture(source, index)
            
            if success and cap.isOpened():
                # Đọc frame đầu tiên để kiểm tra
                ret, frame = cap.read()
                if ret:
                    LOGGER.info(f"Successfully reconnected to stream {index}")
                    self.reconnecting[index] = False
                    self.connection_status[index] = True
                    self.last_frame_time[index] = time.time()
                    return True, cap
            
            # Chờ trước khi thử lại
            time.sleep(self.reconnect_delay)
        
        # Nếu tất cả các lần thử đều thất bại
        LOGGER.error(f"Failed to reconnect to stream {index} after {self.reconnect_attempts} attempts")
        self.reconnecting[index] = False
        return False, None

    def update(self, i, cap, stream):
        # Read stream `i` frames in daemon thread
        n, _ = 0, self.frames[i]  # frame number, frame array
        max_failures_before_reconnect = 5
        consecutive_failures = 0
        
        while True:  # Bỏ điều kiện dừng để luôn cố gắng duy trì kết nối
            try:
                if not self.connection_status[i]:
                    # Thử kết nối lại nếu mất kết nối
                    success, new_cap = self.reconnect_stream(i, self.original_sources[i])
                    if success:
                        cap = new_cap
                        self.caps[i] = cap
                        consecutive_failures = 0
                    else:
                        # Nếu không thể kết nối lại, chờ và thử lại
                        time.sleep(self.reconnect_delay)
                        continue
                
                # Kiểm tra xem kết nối có còn hoạt động không
                if cap is None or not cap.isOpened():
                    LOGGER.warning(f"Stream {i} connection lost. Attempting to reconnect...")
                    self.connection_status[i] = False
                    continue
                
                # Kiểm tra thời gian từ frame cuối cùng để phát hiện đóng băng
                current_time = time.time()
                if current_time - self.last_frame_time[i] > self.timeout and not self.reconnecting[i]:
                    LOGGER.warning(f"Stream {i} appears frozen (no frames for {self.timeout}s). Attempting to reconnect...")
                    self.connection_status[i] = False
                    continue
                
                # Đọc frame
                n += 1
                grab_success = cap.grab()  # .read() = .grab() followed by .retrieve()
                
                if not grab_success:
                    consecutive_failures += 1
                    LOGGER.warning(f"Failed to grab frame from stream {i}. Failure count: {consecutive_failures}/{max_failures_before_reconnect}")
                    
                    if consecutive_failures >= max_failures_before_reconnect:
                        LOGGER.warning(f"Stream {i} consistently failing. Attempting to reconnect...")
                        self.connection_status[i] = False
                        consecutive_failures = 0
                        continue
                    
                    # Chờ một chút trước khi thử lại
                    time.sleep(0.5)
                    continue
                
                # Reset bộ đếm lỗi nếu grab thành công
                consecutive_failures = 0
                
                # Chỉ xử lý mỗi vid_stride frame để giảm tải
                if n % self.vid_stride == 0:
                    success, im = cap.retrieve()
                    if success:
                        self.imgs[i] = im
                        self.last_frame_time[i] = time.time()  # Cập nhật thời gian frame cuối
                    else:
                        LOGGER.warning(f"WARNING ⚠️ Failed to retrieve frame from stream {i}")
                        # Không đặt ngay lập tức connection_status = False,
                        # cho phép một số lần thất bại trước khi thử kết nối lại
                        consecutive_failures += 1
                        if consecutive_failures >= max_failures_before_reconnect:
                            LOGGER.warning(f"Stream {i} consistently failing on retrieve. Attempting to reconnect...")
                            self.connection_status[i] = False
                            consecutive_failures = 0
                
                # Thêm short sleep để tránh đóng băng CPU
                time.sleep(0.001)
                
            except Exception as e:
                LOGGER.error(f"Error in stream {i} update: {str(e)}")
                self.connection_status[i] = False
                # Chờ trước khi thử lại để tránh vòng lặp lỗi quá nhanh
                time.sleep(1)

    def __iter__(self):
        self.count = -1
        return self

    def __next__(self):
        self.count += 1
        if not any(x.is_alive() for x in self.threads) or cv2.waitKey(1) == ord('q'):  # q to quit
            cv2.destroyAllWindows()
            raise StopIteration

        # Hiển thị trạng thái kết nối cho user
        for i, status in enumerate(self.connection_status):
            if not status and not self.reconnecting[i]:
                LOGGER.info(f"Stream {i} disconnected. Reconnection in progress...")
        
        # Tạo bản sao của hình ảnh hiện tại
        im0 = self.imgs.copy()
        
        # Thêm thông tin trạng thái kết nối
        connection_info = {i: {'status': self.connection_status[i], 
                              'reconnecting': self.reconnecting[i], 
                              'last_frame': self.last_frame_time[i]} 
                          for i in range(len(self.sources))}

        return self.sources, im0, None, connection_info

    def __len__(self):
        return len(self.sources)  # 1E12 frames = 32 streams at 30 FPS for 30 years
    
    def close(self):
        """Đóng tất cả các kết nối và giải phóng tài nguyên"""
        for i, cap in enumerate(self.caps):
            if cap is not None:
                cap.release()
        
        # Chờ tất cả các thread kết thúc
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=1.0)
