import time
import subprocess
from gtts import gTTS
import os

TEXT = "Xin chào! Đây là một đoạn kiểm tra với gTTS và ffmpeg."
TTS_PATH = "output.mp3"

# Task 1: Tạo file âm thanh bằng gTTS và phát bằng ffmpeg
# start_time_1 = time.time()

# # Sinh giọng nói từ văn bản
# tts = gTTS(TEXT, lang='vi')
# tts.save(TTS_PATH)

# # Phát file vừa tạo bằng ffmpeg (ẩn log, không hiển thị đầu ra)
# subprocess.run(["ffplay", "-nodisp", "-autoexit", "output.mp3"])

# end_time_1 = time.time()
# duration_1 = end_time_1 - start_time_1

# print(f"Tác vụ 1 (tạo và phát âm thanh) mất {duration_1:.3f} giây.")

# Task 2: Phát lại file đã có sẵn
start_time_2 = time.time()

subprocess.run(["ffplay", "-nodisp", "-autoexit", "output.mp3"])

end_time_2 = time.time()
duration_2 = end_time_2 - start_time_2

print(f"Tác vụ 2 (phát lại file đã có) mất {duration_2:.3f} giây.")
