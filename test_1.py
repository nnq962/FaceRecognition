def convert_angle_to_answer(angle):
    """
    Chuyển đổi góc từ 0 đến 360 độ thành đáp án A, B, C, D.
    
    Quy ước:
    - 0° → 90°  -> A
    - 90° → 180° -> B
    - 180° → 270° -> C
    - 270° → 360° -> D
    
    Nếu góc ngoài phạm vi, sẽ điều chỉnh về [0, 360] bằng mod 360.
    """
    angle = angle % 360  # Đảm bảo góc nằm trong phạm vi 0-360

    if 0 <= angle < 90:
        return "A"
    elif 90 <= angle < 180:
        return "B"
    elif 180 <= angle < 270:
        return "C"
    else:
        return "D"

# Ví dụ sử dụng
angles = [10, 95, 185, 275, 360, 450, -45]
answers = [convert_angle_to_answer(a) for a in angles]

for a, ans in zip(angles, answers):
    print(f"Góc {a}° -> Đáp án {ans}")
