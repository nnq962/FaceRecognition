import cv2

# Đọc ảnh gốc
img = cv2.imread('photo_test/happyandsad.jpg')
img_with_boxes = img.copy()

bbox_1 = [150, 176, 106, 149]
bbox_2 = [97, 102, 106, 149]

# Vẽ bounding boxes
cv2.rectangle(img_with_boxes, (bbox_1[0], bbox_1[1]),
              (bbox_1[0] + bbox_1[2], bbox_1[1] + bbox_1[3]),
              (0, 255, 0), 2)  # Màu xanh lá cho bbox_1

cv2.rectangle(img_with_boxes, (bbox_2[0], bbox_2[1]),
              (bbox_2[0] + bbox_2[2], bbox_2[1] + bbox_2[3]),
              (0, 0, 255), 2)  # Màu đỏ cho bbox_2

# Hiển thị ảnh
cv2.imshow("Bounding Boxes", img_with_boxes)
cv2.waitKey(0)
cv2.destroyAllWindows()
