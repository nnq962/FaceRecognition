from gtts import gTTS
import subprocess
import os

# Nội dung thông báo
text = "Xin chào, đây là thông báo bằng tiếng Việt!"

# Tạo tệp âm thanh từ văn bản
tts = gTTS(text=text, lang='vi')
tts.save("notification.mp3")

# Phát âm thanh bằng ffmpeg
subprocess.run(["ffplay", "-nodisp", "-autoexit", "notification.mp3"])

# Xóa file sau khi phát xong (nếu muốn)
os.remove("notification.mp3")