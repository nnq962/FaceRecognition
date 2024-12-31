import cv2
import mediapipe as mp
from hand_raise_detector import is_hand_opened_in_image, is_person_raising_hand_image

def main():
    cap = cv2.VideoCapture(0)
    while True:
        success, image = cap.read()
        if not success:
            print("Không thể đọc từ webcam!")
            break

        # Kiểm tra xem bàn tay này đang mở hay không
        if is_hand_opened_in_image(image) and is_person_raising_hand_image(image):
            text_status = f"Dang gio tay"
        else:
            text_status = f"Khong gio tay"

        print(text_status)

        cv2.imshow("Hand Detection", image)
        
        if cv2.waitKey(1) & 0xFF == 27:  # ESC để thoát
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()