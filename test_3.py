from TTS.utils.manage import ModelManager

# Tạo một đối tượng ModelManager
manager = ModelManager()

# Liệt kê danh sách các mô hình hỗ trợ
available_models = manager.list_models()

# In danh sách mô hình
print(available_models)