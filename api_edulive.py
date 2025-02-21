import requests
import cv2
import io

def send_student_attendance_cv2(image_cv2, attendance_id, date=""):
    url = "https://beta.edulive.net/api/public/v1/schools/store-student-attendance"
    headers = {
        "Accept": "",
        "x-api-key": "eyJpdiI6IjcxS2pCMURjbk1oQU1KWkdqUmVJUXc9PSIsInZhbHVlIjoicE95Smt2Y0FnMXdUUmd1ZWtqQjVLTzJPTjAwQzBQZnJOODU2eDlGb0hCRT0iLCJtYWMiOiIwZDVlZDM0YTVhYjExNzhiNzFiZDljMzY5NzNkYzUwZDQ5YzUyNGFiNjBmZDk4N2I1OThiODJiOGJlZjVjN2UyIiwidGFnIjoiIn0="
    }

    # Chuyển đổi ảnh OpenCV (numpy.ndarray) thành dạng file bytes
    _, buffer = cv2.imencode(".jpg", image_cv2)  # Nén ảnh thành JPEG
    image_bytes = io.BytesIO(buffer)  # Đưa vào buffer để gửi đi

    files = {
        "image": ("image.jpg", image_bytes.getvalue(), "image/jpeg")
    }

    data = {
        "attendance_id": attendance_id,
        "date": date
    }

    try:
        response = requests.post(url, headers=headers, files=files, data=data)
        response.raise_for_status()  # Kiểm tra lỗi HTTP
        return response.json()  # Trả về JSON response từ API
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}