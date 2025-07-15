import argparse
import os
import yaml
import threading
import time
from datetime import datetime
from typing import Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
import pytz

from insightface_detector import InsightFaceDetector
from media_manager import MediaManager
from utils.logger_config import LOGGER
from sync import Sync
from speaker_recognition.speaker_recognition import SpeakerRecognition


class TrackingSystem:
    """
    Hệ thống tracking học sinh với khả năng tự động đồng bộ dữ liệu và chuyển đổi lớp học
    """
    
    def __init__(self, config_name: str):
        self.config_name = config_name
        self.main_config = self._load_config(config_name)
        self.features_config = self.main_config.get('features', {})
        self.network_config = self.main_config.get('network', {})
        self.server_id = self.main_config.get("server_id")
        
        # Timezone configuration
        self.timezone = pytz.timezone('Asia/Ho_Chi_Minh')
        
        # Core components
        self.face_recognizer = None
        self.sync_manager = None
        self.speaker_recognizer = None
        
        # Scheduler cho background tasks
        self.scheduler = BackgroundScheduler(
            executors={'default': ThreadPoolExecutor(max_workers=3)},
            timezone=self.timezone
        )
        
        # Runtime state
        self.current_class_id = None
        self.is_running = False
        self.last_sync_time = None
        self.system_running = False
        self.main_thread = None
        
        # Schedule management
        self.current_schedule = None
        self.scheduled_jobs = {}  # Track scheduled class jobs
        
        # Khởi tạo các thành phần
        self._initialize_components()
        
    def _load_config(self, config_name: str) -> Dict[str, Any]:
        """Load and validate configuration from config.yaml"""
        try:
            config_path = "config.yaml"
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"File cấu hình '{config_path}' không tìm thấy")
                
            with open(config_path, "r", encoding="utf-8") as f:
                try:
                    all_configs = yaml.safe_load(f)
                except yaml.YAMLError as e:
                    raise ValueError(f"File '{config_path}' không phải là YAML hợp lệ: {str(e)}")
            
            if config_name not in all_configs:
                available_configs = ", ".join(all_configs.keys())
                raise ValueError(f"'{config_name}' không có trong config.yaml. "
                               f"Các cấu hình có sẵn: {available_configs}")
            
            main_config = all_configs[config_name]
            LOGGER.info(f"Đã tải cấu hình '{config_name}' thành công từ config.yaml")
            return main_config
            
        except Exception as e:
            LOGGER.error(f"Lỗi khi tải cấu hình: {str(e)}")
            raise
    
    def _initialize_speaker_recognizer(self):
        """Khởi tạo speaker recognizer không cần tham số"""
        self.speaker_recognizer = SpeakerRecognition()
    
    def _initialize_face_recognizer(self):
        """Khởi tạo face recognizer với các tham số từ config (không có media manager)"""
        network_config = self._extract_network_config()
        self._log_network_config(network_config)
        self._log_features_config()

        self.face_recognizer = InsightFaceDetector(
            media_manager=None,
            face_recognition=self.features_config.get("face_recognition", False),
            face_emotion=self.features_config.get("face_emotion", False),
            raise_hand=self.features_config.get("raise_hand", False),
            qr_code=self.features_config.get("qr_code", False),
            export_data=self.features_config.get("export_data", False),
            time_to_save=self.features_config.get("time_to_save", 5),
            notification=self.features_config.get("notification", False),

            host=network_config["host"],
            data2ws_url=network_config["data2ws_url"],
            noti_control_port=network_config["noti_control_port"],
            noti_secret_key=network_config["noti_secret_key"]
        )
    
    def _extract_network_config(self) -> Dict[str, Any]:
        """Hàm trích xuất cấu hình mạng cho khởi tạo face recognizer ban đầu"""
        host = self.network_config.get("host", "localhost")
        websocket_port = self.network_config.get("websocket_port", 3000)
        
        return {
            "host": host,
            "websocket_port": self.main_config.get("websocket_port", 3000),
            "data2ws_url": f"http://{host}:{websocket_port}",
            "noti_control_port": self.main_config.get("noti_control_port"),
            "noti_secret_key": self.main_config.get("noti_secret_key")
        }
    
    def _log_network_config(self, network_config: Dict[str, Any]):
        """Log cấu hình face recognizer ban đầu"""
        print("-" * 100)
        LOGGER.info(f"Server ID: {self.server_id}")
        LOGGER.info(f"Host: {network_config['host']}")
        LOGGER.info(f"WebSocket Port: {network_config['websocket_port']}")
        LOGGER.info(f"Notification Control Port: {network_config['noti_control_port']}")
        LOGGER.info(f"Data2WS URL: {network_config['data2ws_url']}")

    def _log_features_config(self):
        """Log cấu hình features"""
        LOGGER.info(f"Face recognition: {self.features_config.get('face_recognition', False)}")
        LOGGER.info(f"Face emotion: {self.features_config.get('face_emotion', False)}")
        LOGGER.info(f"Raise hand: {self.features_config.get('raise_hand', False)}")
        LOGGER.info(f"QR code: {self.features_config.get('qr_code', False)}")
        LOGGER.info(f"Export data: {self.features_config.get('export_data', False)}")
        LOGGER.info(f"Time to save: {self.features_config.get('time_to_save', 5)}")
        LOGGER.info(f"Notification: {self.features_config.get('notification', False)}")
        LOGGER.info(f"Save: {self.features_config.get('save', False)}")
        LOGGER.info(f"View img: {self.features_config.get('view_img', False)}")
        LOGGER.info(f"Line thickness: {self.features_config.get('line_thickness', 3)}")
        print("-" * 100)

    def _initialize_sync_manager(self) -> Sync:
        """Khởi tạo sync manager"""
        if not self.face_recognizer:
            raise RuntimeError("Face recognizer phải được khởi tạo trước sync manager")
        
        if not self.speaker_recognizer:
            raise RuntimeError("Speaker recognizer phải được khởi tạo trước sync manager")
            
        self.sync_manager = Sync(
            face_recognizer=self.face_recognizer, 
            speaker_recognizer=self.speaker_recognizer, 
            server_id=self.server_id
        )

    def _initialize_media_manager(self):
        """Khởi tạo media manager, phải có sync manager trước"""
        media_manager = MediaManager(
            source=self.sync_manager.camera_sources,
            save=self.features_config.get("save", False),
            view_img=self.features_config.get("view_img", False),
            line_thickness=self.features_config.get("line_thickness", 3)
        )
        return media_manager
    
    def _initialize_components(self):
        """Khởi tạo các thành phần hệ thống"""
        # Khởi tạo speaker recognizer
        self._initialize_speaker_recognizer()
        # Khởi tạo face recognizer (không có media manager)
        self._initialize_face_recognizer()
        # Khởi tạo sync manager
        self._initialize_sync_manager()
        
        # Sync data lần đầu để lấy dữ liệu camera
        try:
            LOGGER.info("Đồng bộ dữ liệu ban đầu để lấy thông tin camera...")
            self.sync_manager.sync_all()
            self.last_sync_time = datetime.now(self.timezone)
            LOGGER.info("Đồng bộ dữ liệu camera thành công")
        except Exception as e:
            LOGGER.error(f"Lỗi khi đồng bộ dữ liệu camera ban đầu: {str(e)}")
            raise
        
        # Khởi tạo media manager với dữ liệu camera
        try:
            media_manager = self._initialize_media_manager()
            LOGGER.info("Khởi tạo media manager thành công")
        except Exception as e:
            LOGGER.error(f"Lỗi khi khởi tạo media manager: {str(e)}")
            raise
        
        # Update face recognizer với media manager và camera IDs
        try:
            self.face_recognizer.update_media_manager(
                media_manager=media_manager, 
                camera_ids=self.sync_manager.camera_ids
            )
            LOGGER.info("Cập nhật face recognizer với media manager thành công")
        except Exception as e:
            LOGGER.error(f"Lỗi khi cập nhật face recognizer: {str(e)}")
            raise

    def switch_class(self, class_id: int, auto_attendance_check: bool, board_checkin: bool):
        """Chuyển lớp học"""
        try:
            self.face_recognizer.update_class_info(
                class_id=class_id, 
                auto_attendance_check=auto_attendance_check,
                board_checkin=board_checkin
            )
            self.current_class_id = class_id
            LOGGER.info(f"Đã chuyển sang lớp {class_id}, auto_attendance: {auto_attendance_check}, board_checkin: {board_checkin}")
        except Exception as e:
            LOGGER.error(f"Lỗi khi chuyển lớp {class_id}: {str(e)}")
            raise

    def disable_recognition(self):
        """Tắt tính năng nhận diện"""
        try:
            self.face_recognizer.is_running = False
            self.current_class_id = None
            LOGGER.info("Đã tắt tính năng nhận diện")
        except Exception as e:
            LOGGER.error(f"Lỗi khi tắt nhận diện: {str(e)}")
            raise

    def enable_recognition(self):
        """Bật tính năng nhận diện"""
        try:
            self.face_recognizer.is_running = True
            LOGGER.info("Đã bật tính năng nhận diện")
        except Exception as e:
            LOGGER.error(f"Lỗi khi bật nhận diện: {str(e)}")
            raise
    
    def get_schedule(self):
        """Lấy lịch sử dụng từ sync manager"""
        try:
            schedule = self.sync_manager.schedule
            LOGGER.info("Đã lấy lịch học thành công")
            return schedule
        except Exception as e:
            LOGGER.error(f"Lỗi khi lấy lịch học: {str(e)}")
            raise
    
    def sync_data(self):
        """Đồng bộ dữ liệu và cập nhật lịch học"""
        try:
            LOGGER.info("Bắt đầu đồng bộ dữ liệu...")
            self.sync_manager.sync_all()
            self.last_sync_time = datetime.now(self.timezone)
            LOGGER.info(f"Đồng bộ dữ liệu thành công lúc {self.last_sync_time.strftime('%H:%M:%S')}")
            
            # Cập nhật lịch học sau khi sync
            self._update_schedule()
            
        except Exception as e:
            LOGGER.error(f"Lỗi khi đồng bộ dữ liệu: {str(e)}")
            raise

    def _setup_sync_schedule(self):
        """Thiết lập lịch đồng bộ dữ liệu mỗi giờ đúng"""
        try:
            # Chạy sync_data mỗi giờ đúng (phút 0)
            self.scheduler.add_job(
                func=self.sync_data,
                trigger=CronTrigger(minute=0, timezone=self.timezone),
                id='sync_data_job',
                name='Sync Data Hourly',
                replace_existing=True
            )
            LOGGER.info("Đã thiết lập lịch đồng bộ dữ liệu mỗi giờ đúng")
        except Exception as e:
            LOGGER.error(f"Lỗi khi thiết lập lịch đồng bộ: {str(e)}")
            raise

    def _update_schedule(self):
        """Cập nhật lịch học và thiết lập các job tương ứng"""
        try:
            # Lấy lịch học mới
            self.current_schedule = self.get_schedule()
            
            # Xóa các job cũ
            self._clear_class_jobs()
            
            # Thiết lập các job mới
            self._setup_class_schedule()
            
            # Kiểm tra trạng thái hiện tại
            self._check_current_class_status()
            
        except Exception as e:
            LOGGER.error(f"Lỗi khi cập nhật lịch học: {str(e)}")
            raise

    def _clear_class_jobs(self):
        """Xóa tất cả các job lớp học cũ"""
        for job_id in list(self.scheduled_jobs.keys()):
            try:
                self.scheduler.remove_job(job_id)
                del self.scheduled_jobs[job_id]
            except Exception as e:
                LOGGER.warning(f"Không thể xóa job {job_id}: {str(e)}")

    def _setup_class_schedule(self):
        """Thiết lập lịch cho các lớp học"""
        if not self.current_schedule or 'active_periods' not in self.current_schedule:
            LOGGER.warning("Không có lịch học để thiết lập")
            return

        current_date = datetime.now(self.timezone).date()
        
        for period in self.current_schedule['active_periods']:
            try:
                # Parse thời gian
                start_time = datetime.strptime(period['start_time'], '%H:%M:%S').time()
                end_time = datetime.strptime(period['end_time'], '%H:%M:%S').time()
                
                # Tạo datetime đầy đủ cho hôm nay
                start_datetime = datetime.combine(current_date, start_time)
                end_datetime = datetime.combine(current_date, end_time)
                
                # Thêm timezone info
                start_datetime = self.timezone.localize(start_datetime)
                end_datetime = self.timezone.localize(end_datetime)
                
                # Chỉ schedule cho các lớp trong tương lai
                now = datetime.now(self.timezone)
                if end_datetime > now:
                    # Job bắt đầu lớp
                    if start_datetime > now:
                        start_job_id = f"start_class_{period['period_id']}"
                        self.scheduler.add_job(
                            func=self._start_class,
                            trigger=DateTrigger(run_date=start_datetime),
                            args=[period],
                            id=start_job_id,
                            name=f"Start Class {period['class_id']}",
                            replace_existing=True
                        )
                        self.scheduled_jobs[start_job_id] = period
                    
                    # Job kết thúc lớp
                    end_job_id = f"end_class_{period['period_id']}"
                    self.scheduler.add_job(
                        func=self._end_class,
                        trigger=DateTrigger(run_date=end_datetime),
                        args=[period],
                        id=end_job_id,
                        name=f"End Class {period['class_id']}",
                        replace_existing=True
                    )
                    self.scheduled_jobs[end_job_id] = period
                    
                    LOGGER.info(f"Đã lên lịch cho lớp {period['class_id']}: {start_time} - {end_time}")
                    
            except Exception as e:
                LOGGER.error(f"Lỗi khi thiết lập lịch cho period {period.get('period_id', 'unknown')}: {str(e)}")

    def _start_class(self, period: Dict[str, Any]):
        """Bắt đầu lớp học"""
        try:
            LOGGER.info(f"Bắt đầu lớp {period['class_id']} lúc {datetime.now(self.timezone).strftime('%H:%M:%S')}")
            
            # Bật nhận diện
            self.enable_recognition()
            
            # Chuyển sang lớp học
            self.switch_class(
                class_id=period['class_id'],
                auto_attendance_check=period['auto_attendance_check'],
                board_checkin=period['board_checkin']
            )
            
        except Exception as e:
            LOGGER.error(f"Lỗi khi bắt đầu lớp {period['class_id']}: {str(e)}")
            raise

    def _end_class(self, period: Dict[str, Any]):
        """Kết thúc lớp học"""
        try:
            LOGGER.info(f"Kết thúc lớp {period['class_id']} lúc {datetime.now(self.timezone).strftime('%H:%M:%S')}")
            
            # Tắt nhận diện
            self.disable_recognition()
            
        except Exception as e:
            LOGGER.error(f"Lỗi khi kết thúc lớp {period['class_id']}: {str(e)}")
            raise

    def _check_current_class_status(self):
        """Kiểm tra trạng thái lớp học hiện tại khi khởi động"""
        if not self.current_schedule:
            return
            
        current_active = self.current_schedule.get('current_active')
        if current_active:
            try:
                LOGGER.info(f"Phát hiện lớp đang hoạt động: {current_active['class_id']}")
                
                # Bật nhận diện
                self.enable_recognition()
                
                # Chuyển sang lớp hiện tại
                self.switch_class(
                    class_id=current_active['class_id'],
                    auto_attendance_check=current_active['auto_attendance_check'],
                    board_checkin=current_active['board_checkin']
                )
                
            except Exception as e:
                LOGGER.error(f"Lỗi khi thiết lập lớp hiện tại: {str(e)}")
                raise
        else:
            LOGGER.info("Không có lớp nào đang hoạt động")
            self.disable_recognition()

    def start_system(self):
        """Khởi động hệ thống"""
        try:
            LOGGER.info("Bắt đầu khởi động hệ thống...")
            
            # Đồng bộ dữ liệu lịch học (không phải camera data)
            self._update_schedule()
            
            # Thiết lập lịch đồng bộ
            self._setup_sync_schedule()
            
            # Khởi động scheduler
            self.scheduler.start()
            LOGGER.info("Đã khởi động scheduler")
            
            # Đánh dấu hệ thống đang chạy
            self.system_running = True
            
            # Khởi động thread chính cho face recognizer
            self.main_thread = threading.Thread(target=self._run_face_recognizer, daemon=True)
            self.main_thread.start()
            
            LOGGER.info("Hệ thống đã khởi động thành công!")
            
        except Exception as e:
            LOGGER.error(f"Lỗi khi khởi động hệ thống: {str(e)}")
            raise

    def _run_face_recognizer(self):
        """Chạy face recognizer trong thread riêng"""
        try:
            LOGGER.info("Bắt đầu chạy face recognizer...")
            self.face_recognizer.run_inference()
        except Exception as e:
            LOGGER.error(f"Lỗi trong face recognizer: {str(e)}")
            self.system_running = False
            raise

    def stop_system(self):
        """Dừng hệ thống"""
        try:
            LOGGER.info("Bắt đầu dừng hệ thống...")
            
            # Đánh dấu hệ thống dừng
            self.system_running = False
            
            # Dừng scheduler
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                LOGGER.info("Đã dừng scheduler")
            
            # Tắt nhận diện
            self.disable_recognition()
            
            LOGGER.info("Hệ thống đã dừng hoàn toàn!")
            
        except Exception as e:
            LOGGER.error(f"Lỗi khi dừng hệ thống: {str(e)}")

    def run(self):
        """Hàm chạy hệ thống - entry point chính"""
        try:
            # Khởi động hệ thống
            self.start_system()
            
            # Chờ cho đến khi hệ thống dừng
            while self.system_running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            LOGGER.info("Nhận tín hiệu dừng từ người dùng")
        except Exception as e:
            LOGGER.error(f"Lỗi trong quá trình chạy: {str(e)}")
        finally:
            self.stop_system()


# Usage example
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tracking System")
    parser.add_argument("--config", required=True, help="Tên cấu hình trong config.yaml")
    args = parser.parse_args()
    
    system = TrackingSystem(args.config)
    system.run()