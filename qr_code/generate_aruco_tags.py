'''
Cách chạy:
python generate_aruco_tags.py --id 24 --type DICT_5X5_100 -o tags/
'''

import numpy as np
import argparse
import os
import sys
import cv2
from utils import ARUCO_DICT

def generate_marker(aruco_dict, marker_id, marker_size=200, border_size=1):
    """ Tạo marker ArUco thủ công nếu OpenCV không có `drawMarker()`. """
    marker_bits = aruco_dict.markerSize
    bits = np.unpackbits(aruco_dict.bytesList[marker_id], axis=None)[:marker_bits * marker_bits]
    marker_matrix = bits.reshape((marker_bits, marker_bits))

    marker_with_border = np.ones((marker_bits + 2 * border_size, marker_bits + 2 * border_size), dtype=np.uint8)
    marker_with_border[border_size:-border_size, border_size:-border_size] = marker_matrix

    cell_size = marker_size // (marker_bits + 2 * border_size)
    marker_img = cv2.resize(marker_with_border, (marker_size, marker_size), interpolation=cv2.INTER_NEAREST)

    return marker_img * 255  # Chuyển 0/1 → 0/255

# Nhận tham số dòng lệnh
ap = argparse.ArgumentParser()
ap.add_argument("-o", "--output", required=True, help="Thư mục lưu ArUCo tag")
ap.add_argument("-i", "--id", type=int, required=True, help="ID của ArUCo tag")
ap.add_argument("-t", "--type", type=str, default="DICT_ARUCO_ORIGINAL", help="Loại ArUCo tag")
ap.add_argument("-s", "--size", type=int, default=2000, help="Kích thước của ArUCo tag")
args = vars(ap.parse_args())

# Kiểm tra dictionary hợp lệ
if args["type"] not in ARUCO_DICT:
    print(f"❌ Loại ArUCo '{args['type']}' không được hỗ trợ!")
    sys.exit(1)

arucoDict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT[args["type"]])

# Kiểm tra ID hợp lệ
max_markers = int(args["type"].split("_")[-1])
if not (0 <= args["id"] < max_markers):
    print(f"❌ ID {args['id']} không hợp lệ! Chỉ có thể chọn từ 0 đến {max_markers-1}.")
    sys.exit(1)

print(f"✅ Đang tạo ArUCo tag loại '{args['type']}' với ID '{args['id']}'")

# Tạo ảnh marker (Chạy trên OpenCV mới)
try:
    tag = arucoDict.generateImageMarker(args["id"], args["size"])  # OpenCV 4.11+
except AttributeError:
    tag = generate_marker(arucoDict, args["id"], args["size"])  # Dùng cách thủ công nếu lỗi

# Tạo thư mục nếu chưa có
os.makedirs(args["output"], exist_ok=True)

# Lưu marker
tag_name = os.path.join(args["output"], f"{args['type']}_id_{args['id']}.png")
cv2.imwrite(tag_name, tag)

# Hiển thị marker
cv2.imshow("ArUCo Tag", tag)
cv2.waitKey(0)
cv2.destroyAllWindows()

print(f"✅ Marker đã được lưu tại: {tag_name}")