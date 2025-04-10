from PIL import Image
import pillow_heif
import os
import sys
import time

def convert_heic_to_png(input_path, output_path=None):
    """
    Chuyển đổi ảnh từ định dạng HEIC sang PNG
    
    Parameters:
        input_path (str): Đường dẫn đến file HEIC
        output_path (str, optional): Đường dẫn lưu file PNG. Nếu None, sẽ tạo dựa trên input_path
    
    Returns:
        str: Đường dẫn đến file PNG đã chuyển đổi
    """
    try:
        # Kiểm tra file đầu vào
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # Kiểm tra định dạng file
        if not input_path.lower().endswith(('.heic', '.heif')):
            raise ValueError(f"Input file is not a HEIC/HEIF file: {input_path}")
        
        # Tạo đường dẫn đầu ra nếu không được cung cấp
        if output_path is None:
            base_name = os.path.splitext(input_path)[0]
            output_path = f"{base_name}.png"
        
        # Đo thời gian chuyển đổi
        start_time = time.time()
        
        # Đăng ký bộ xử lý HEIF
        pillow_heif.register_heif_opener()
        
        # Mở file HEIC
        print(f"Opening HEIC file: {input_path}")
        heic_image = Image.open(input_path)
        
        # Lưu thành file PNG
        print(f"Converting to PNG and saving to: {output_path}")
        heic_image.save(output_path, format="PNG")
        
        # Tính thời gian chuyển đổi
        conversion_time = time.time() - start_time
        
        # Kiểm tra kích thước file
        original_size = os.path.getsize(input_path) / 1024  # KB
        converted_size = os.path.getsize(output_path) / 1024  # KB
        
        print(f"Conversion completed successfully in {conversion_time:.2f} seconds")
        print(f"Original file size: {original_size:.2f} KB")
        print(f"Converted file size: {converted_size:.2f} KB")
        print(f"Size ratio (PNG/HEIC): {converted_size/original_size:.2f}")
        
        return output_path
    
    except Exception as e:
        print(f"Error converting HEIC to PNG: {str(e)}")
        raise

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python heic_to_png.py <input_heic_file> [output_png_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        output_path = convert_heic_to_png(input_file, output_file)
        print(f"Successfully converted {input_file} to {output_path}")
    except Exception as e:
        print(f"Conversion failed: {str(e)}")
        sys.exit(1)