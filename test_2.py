import onnx
from onnx import helper
import os
model_path = os.path.expanduser("~/Models/det_10g.onnx")
model = onnx.load(model_path)

graph = model.graph
input_tensor = graph.input[0]
input_tensor.type.tensor_type.shape.dim[0].dim_param = ''  # Đặt batch size thành dynamic
onnx.save(model, "retinaface_batch.onnx")