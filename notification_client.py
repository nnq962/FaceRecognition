import socket
import os
from gtts import gTTS
import subprocess

class NotificationClient:
    def __init__(self, host='192.168.1.58', port=9999):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect_to_server()

    def connect_to_server(self):
        """Kết nối tới server"""
        try:
            self.client_socket.connect((self.host, self.port))
            print(f"Đã kết nối tới server {self.host}:{self.port}")
        except Exception as e:
            print(f"Không thể kết nối tới server: {e}")
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
            print(f"Lỗi khi phát âm thanh: {e}")

    def listen(self):
        """Luôn lắng nghe thông báo từ server"""
        try:
            while True:
                data = self.client_socket.recv(1024).decode('utf-8')
                if not data:
                    print("Mất kết nối với server")
                    break
                if data.lower() == "exit":
                    print("Nhận lệnh thoát từ server")
                    break
                print(f"Nhận được thông báo: {data}")
                self.play_audio(data)
        except Exception as e:
            print(f"Lỗi khi nhận thông báo: {e}")
        finally:
            self.client_socket.close()
            print("Đã đóng kết nối")

if __name__ == "__main__":
    client = NotificationClient()
    client.listen()