#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import subprocess
import datetime
from gtts import gTTS
import pandas as pd

# Văn bản tiếng Việt để chuyển thành âm thanh
van_ban = "Xin chào, đây là một thông báo tiếng Việt được tạo bởi Google Text-to-Speech. Chúng ta đang kiểm tra hiệu suất của các trình phát âm thanh khác nhau trên hệ điều hành Linux."

# Đường dẫn file âm thanh
output_file = "thong_bao_tieng_viet.mp3"

# Tạo file âm thanh từ văn bản tiếng Việt
def tao_am_thanh():
    print("Đang tạo file âm thanh tiếng Việt...")
    tts = gTTS(text=van_ban, lang='vi', slow=False)
    tts.save(output_file)
    print(f"Đã tạo file âm thanh: {output_file}")

# Hàm thực thi lệnh và trả về thời gian thực thi
def chay_lenh(lenh):
    print(f"\nĐang thực hiện lệnh: {' '.join(lenh)}")
    
    bat_dau = datetime.datetime.now()
    print(f"Bắt đầu phát âm thanh lúc: {bat_dau.strftime('%H:%M:%S.%f')[:-3]}")
    
    # Thực thi lệnh và đợi cho đến khi kết thúc
    process = subprocess.Popen(lenh, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    
    ket_thuc = datetime.datetime.now()
    print(f"Kết thúc phát âm thanh lúc: {ket_thuc.strftime('%H:%M:%S.%f')[:-3]}")
    
    # Tính thời gian thực thi
    thoi_gian = (ket_thuc - bat_dau).total_seconds()
    print(f"Tổng thời gian phát: {thoi_gian:.3f} giây")
    
    return {
        'Trình phát': lenh[0],
        'Thời gian bắt đầu': bat_dau.strftime('%H:%M:%S.%f')[:-3],
        'Thời gian kết thúc': ket_thuc.strftime('%H:%M:%S.%f')[:-3],
        'Tổng thời gian (giây)': round(thoi_gian, 3),
        'Lệnh đầy đủ': ' '.join(lenh)
    }

# Hàm chính để so sánh các trình phát âm thanh
def so_sanh_trinh_phat():
    # Tạo file âm thanh nếu chưa tồn tại
    if not os.path.exists(output_file):
        tao_am_thanh()
    
    # Danh sách các trình phát âm thanh và lệnh tương ứng
    trinh_phat = [
        ["ffmpeg", "-i", output_file, "-nodisp", "-autoexit", "-"],
        ["ffplay", "-nodisp", "-autoexit", output_file],
        ["mplayer", output_file],
        ["mpv", "--no-video", output_file],
        ["aplay", "-q", output_file],
        ["paplay", output_file],
        ["cvlc", "--play-and-exit", "--quiet", output_file],
        ["gst-play-1.0", output_file]
    ]
    
    ket_qua = []
    
    print("\n" + "="*50)
    print("BẮT ĐẦU SO SÁNH CÁC TRÌNH PHÁT ÂM THANH")
    print("="*50)
    
    # Thực hiện phát âm thanh bằng từng trình phát
    for lenh in trinh_phat:
        try:
            # Đảm bảo trình phát tồn tại trên hệ thống
            if subprocess.run(["which", lenh[0]], stdout=subprocess.PIPE).returncode == 0:
                ket_qua.append(chay_lenh(lenh))
                # Chờ một chút giữa các lần phát để đảm bảo hệ thống âm thanh được giải phóng
                time.sleep(1)
            else:
                print(f"\nTrình phát {lenh[0]} không được cài đặt trên hệ thống.")
        except Exception as e:
            print(f"\nLỗi khi sử dụng trình phát {lenh[0]}: {str(e)}")
    
    print("\n" + "="*50)
    print("KẾT QUẢ SO SÁNH")
    print("="*50)
    
    # Tạo DataFrame để hiển thị kết quả
    if ket_qua:
        df = pd.DataFrame(ket_qua)
        # Sắp xếp theo thời gian tăng dần
        df_sorted = df.sort_values(by='Tổng thời gian (giây)')
        print(df_sorted[['Trình phát', 'Tổng thời gian (giây)', 'Thời gian bắt đầu', 'Thời gian kết thúc']])
        
        # Lưu kết quả vào file CSV
        csv_file = "ket_qua_so_sanh_trinh_phat.csv"
        df_sorted.to_csv(csv_file, index=False)
        print(f"\nĐã lưu kết quả chi tiết vào file: {csv_file}")
        
        # Hiển thị trình phát nhanh nhất
        fastest = df_sorted.iloc[0]
        print(f"\nTrình phát nhanh nhất: {fastest['Trình phát']} với thời gian: {fastest['Tổng thời gian (giây)']} giây")
    else:
        print("Không có kết quả nào được ghi nhận. Vui lòng cài đặt các trình phát âm thanh.")

# Hàm cài đặt các gói phụ thuộc
def cai_dat_phu_thuoc():
    print("Cài đặt các gói phụ thuộc...")
    
    # Cài đặt gTTS và pandas
    subprocess.run(["pip", "install", "gtts", "pandas"])
    
    # Kiểm tra và gợi ý cài đặt các trình phát
    trinh_phat = ["ffmpeg", "mplayer", "mpv", "aplay", "paplay", "vlc", "gstreamer1.0-tools"]
    missing = []
    
    for tp in trinh_phat:
        if subprocess.run(["which", tp.split("-")[0]], stdout=subprocess.PIPE).returncode != 0:
            missing.append(tp)
    
    if missing:
        print("\nCác trình phát sau chưa được cài đặt:")
        for tp in missing:
            print(f"  - {tp}")
        
        print("\nBạn có thể cài đặt chúng bằng lệnh:")
        print(f"sudo apt-get install {' '.join(missing)}")

if __name__ == "__main__":
    # Kiểm tra xem script có đang chạy trên Linux không
    if os.name != "posix":
        print("Script này chỉ hoạt động trên hệ điều hành Linux.")
        exit(1)
    
    # Cài đặt các gói phụ thuộc nếu cần
    cai_dat_phu_thuoc()
    
    # Thực hiện so sánh
    so_sanh_trinh_phat()