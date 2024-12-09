import cv2
import matplotlib.pyplot as plt

# Hàm pad từ đề bài
def pad(image):
    """Pad image."""
    row, col = image.shape[:2]
    bottom = image[row - 2 : row, 0:col]
    mean = cv2.mean(bottom)[0]

    padded_image = cv2.copyMakeBorder(
        image,
        top=PADDING,
        bottom=PADDING,
        left=PADDING,
        right=PADDING,
        borderType=cv2.BORDER_CONSTANT,
        value=[mean],
    )
    return padded_image

# Đọc ảnh gốc (BGR)
image = cv2.imread("photo_test/smile.jpg")

# Chuyển sang ảnh grayscale
gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Áp dụng hàm pad
PADDING = 40
padded_image = pad(gray_image)

# Hiển thị ảnh trước và sau khi pad
plt.figure(figsize=(10, 5))
plt.subplot(1, 2, 1)
plt.title("Original Grayscale Image")
plt.imshow(gray_image, cmap="gray")
plt.axis("off")

plt.subplot(1, 2, 2)
plt.title("Padded Image")
plt.imshow(padded_image, cmap="gray")
plt.axis("off")

plt.show()
