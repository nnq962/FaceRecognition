import cv2
import numpy as np
from qr_code.utils_qr import ARUCO_DICT

def generate_aruco_marker(dictionary_name: str, marker_id: int, size: int):
    arucoDictType = ARUCO_DICT.get(dictionary_name)
    if arucoDictType is None:
        raise ValueError(f"Invalid dictionary name: '{dictionary_name}'. Please check your input.")

    aruco_dict = cv2.aruco.getPredefinedDictionary(arucoDictType)
    num_markers = aruco_dict.bytesList.shape[0]

    if marker_id < 0 or marker_id >= num_markers:
        raise ValueError(
            f"Marker ID '{marker_id}' is out of range. Dictionary '{dictionary_name}' supports IDs from 0 to {num_markers - 1}."
        )

    marker_image = np.zeros((size, size, 1), dtype=np.uint8)
    cv2.aruco.generateImageMarker(aruco_dict, marker_id, size, marker_image, 1)
    return marker_image[:, :, 0]