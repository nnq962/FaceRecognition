import os

def update_import():
    # Đường dẫn tới tệp cần chỉnh sửa
    file_path = "/usr/local/lib/python3.10/dist-packages/basicsr/data/degradations.py"

    # Nội dung cũ và nội dung thay thế
    old_import = "from torchvision.transforms.functional_tensor import rgb_to_grayscale"
    new_import = "from torchvision.transforms.functional import rgb_to_grayscale"

    # Kiểm tra tệp có tồn tại không
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
    else:
        try:
            # Đọc nội dung tệp
            with open(file_path, "r") as file:
                lines = file.readlines()

            # Thay thế nội dung
            updated_lines = [line.replace(old_import, new_import) for line in lines]

            # Ghi lại tệp với nội dung đã cập nhật
            with open(file_path, "w") as file:
                file.writelines(updated_lines)

            print(f"✅ Successfully updated the import in {file_path}")
        except Exception as e:
            print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    update_import()