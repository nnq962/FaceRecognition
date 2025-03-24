import socket
import os
from gtts import gTTS
import subprocess
from utils.logger_config import LOGGER

host = '192.168.1.142'

class NotificationClient:
    def __init__(self, host=host, port=9999):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect_to_server()

    def connect_to_server(self):
        """Kết nối tới server"""
        try:
            self.client_socket.connect((self.host, self.port))
            LOGGER.info(f"Đã kết nối tới server {self.host}:{self.port}")
        except Exception as e:
            LOGGER.error(f"Không thể kết nối tới server: {e}")
            raise

    def play_audio(self, text):
        """Phát âm thanh từ text"""
        try:
            tts = gTTS(text=text, lang='vi')
            audio_file = "output.mp3"
            tts.save(audio_file)
            subprocess.run(['ffmpeg', '-i', audio_file, '-f', 'alsa', 'default'],
                         check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(audio_file):
                os.remove(audio_file)
        except Exception as e:
            LOGGER.error(f"Lỗi khi phát âm thanh: {e}")

    def listen(self):
        """Luôn lắng nghe thông báo từ server"""
        try:
            while True:
                data = self.client_socket.recv(1024).decode('utf-8')
                if not data:
                    LOGGER.error("Mất kết nối với server")
                    break
                if data.lower() == "exit":
                    LOGGER.info("Nhận lệnh thoát từ server")
                    break
                LOGGER.info(f"Nhận được thông báo: {data}")
                self.play_audio(data)
        except Exception as e:
            LOGGER.error(f"Lỗi khi nhận thông báo: {e}")
        finally:
            self.client_socket.close()
            LOGGER.info("Đã đóng kết nối")

if __name__ == "__main__":
    client = NotificationClient()
    client.listen()