from gtts import gTTS

text = "Xin chào, đây là một thông báo từ hệ thống."
tts = gTTS(text=text, lang="vi")
tts.save("thong_bao.mp3")

print("File MP3 đã được tạo: thong_bao.mp3")