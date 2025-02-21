import os
import sys

def find_file(filename, search_path):
    """Tìm tệp trong thư mục cụ thể"""
    for root, dirs, files in os.walk(search_path):
        if filename in files:
            return os.path.join(root, filename)
    return None

# Tìm thư mục site-packages của môi trường Anaconda hiện tại
if hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix:
    # Nếu đang trong môi trường ảo (Anaconda hoặc venv)
    site_packages_path = os.path.join(sys.prefix, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
else:
    # Nếu không, lấy thư mục site-packages mặc định
    import site
    site_packages_path = site.getsitepackages()[0]

# Tìm tệp `degradations.py`
result = find_file("degradations.py", site_packages_path)

if result:
    print("📌 Tệp tìm thấy tại:", result)
else:
    print("⚠️ Không tìm thấy tệp `degradations.py` trong môi trường Anaconda.")
