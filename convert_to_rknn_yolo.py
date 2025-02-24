from ultralytics import YOLO

# Load the YOLO11 model
model = YOLO("yolov11s-face.pt")

# Export the model to RKNN format
# 'name' can be one of rk3588, rk3576, rk3566, rk3568, rk3562, rv1103, rv1106, rv1103b, rv1106b, rk2118
model.export(format="rknn", name="rk3588", imgsz=320)  # creates '/yolo11n_rknn_model'