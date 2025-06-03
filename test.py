import pandas as pd
from config import config
from datetime import datetime

user_collection = config.user_collection

def export_user_credentials(exclude_usernames=None, output_file=None):
    """
    Export danh sách name, username, password của users ra file Excel
    
    Args:
        exclude_usernames (list): Danh sách username cần bỏ qua
        output_file (str): Tên file output (mặc định sẽ tự động tạo)
    """
    
    if exclude_usernames is None:
        exclude_usernames = []
    
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"user_credentials_{timestamp}.xlsx"
    
    try:
        print("🔄 Đang lấy dữ liệu từ database...")
        
        # Lấy users từ database
        query = {}
        if exclude_usernames:
            query = {"username": {"$nin": exclude_usernames}}
        
        users = list(user_collection.find(
            query,
            {"name": 1, "username": 1, "_id": 0}  # Chỉ lấy name và username
        ))
        
        if not users:
            print("❌ Không tìm thấy user nào!")
            return
        
        print(f"📊 Tìm thấy {len(users)} users")
        
        if exclude_usernames:
            print(f"🚫 Đã bỏ qua {len(exclude_usernames)} usernames: {', '.join(exclude_usernames)}")
        
        # Tạo DataFrame
        df_data = []
        for user in users:
            df_data.append({
                'Họ và tên': user.get('name', ''),
                'Tên đăng nhập': user.get('username', ''),
                'Mật khẩu': '123456'  # Password mặc định
            })
        
        df = pd.DataFrame(df_data)
        
        # Sắp xếp theo tên
        df = df.sort_values('Họ và tên').reset_index(drop=True)
        
        # Thêm số thứ tự
        df.insert(0, 'STT', range(1, len(df) + 1))
        
        # Export ra Excel
        print(f"💾 Đang xuất ra file: {output_file}")
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Danh sách tài khoản', index=False)
            
            # Định dạng Excel
            worksheet = writer.sheets['Danh sách tài khoản']
            
            # Tự động điều chỉnh độ rộng cột
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                
                adjusted_width = min(max_length + 2, 50)  # Tối đa 50 ký tự
                worksheet.column_dimensions[column_letter].width = adjusted_width
            
            # Định dạng header
            from openpyxl.styles import Font, PatternFill, Alignment
            
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            center_alignment = Alignment(horizontal="center", vertical="center")
            
            for cell in worksheet[1]:  # Hàng đầu tiên (header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = center_alignment
        
        print(f"✅ Đã xuất thành công {len(df)} users ra file: {output_file}")
        
        # Hiển thị preview
        print(f"\n📋 Preview (5 dòng đầu):")
        print(df.head().to_string(index=False))
        
        return output_file
        
    except Exception as e:
        print(f"❌ Lỗi khi export: {e}")
        return None

def main():
    """
    Ví dụ sử dụng
    """
    print("=" * 60)
    print("EXPORT USER CREDENTIALS")
    print("=" * 60)
    
    # Ví dụ 1: Export tất cả users
    print("\n1️⃣ Export tất cả users:")
    export_user_credentials()
    
    # Ví dụ 2: Export với exclude một số usernames
    print("\n2️⃣ Export với exclude usernames:")
    exclude_list = ['admin', 'test', 'demo']  # Danh sách username cần bỏ qua
    export_user_credentials(
        exclude_usernames=exclude_list,
        output_file="user_credentials_staff_only.xlsx"
    )
    
    # Ví dụ 3: Interactive - cho phép nhập exclude list
    print("\n3️⃣ Interactive mode:")
    interactive_export()

def interactive_export():
    """
    Chế độ tương tác cho phép nhập exclude usernames
    """
    print("\n📝 Nhập danh sách username cần bỏ qua (cách nhau bởi dấu phẩy):")
    print("   Ví dụ: admin,test,demo")
    print("   Hoặc để trống để export tất cả:")
    
    user_input = input("👉 Nhập: ").strip()
    
    exclude_usernames = []
    if user_input:
        exclude_usernames = [username.strip() for username in user_input.split(',') if username.strip()]
    
    print(f"\n📤 Nhập tên file output (để trống sẽ tự động tạo):")
    output_file = input("👉 Nhập: ").strip()
    
    if not output_file:
        output_file = None
    
    # Thực hiện export
    result = export_user_credentials(
        exclude_usernames=exclude_usernames,
        output_file=output_file
    )
    
    if result:
        print(f"\n🎉 Hoàn thành! File đã được tạo: {result}")

if __name__ == "__main__":
    # Uncomment dòng bạn muốn chạy:
    
    # Chạy tất cả ví dụ
    # main()
    
    # Hoặc chỉ chạy interactive mode
    interactive_export()
    
    # Hoặc chạy trực tiếp với exclude list
    # exclude_list = ['admin', 'superuser']  # Thay đổi theo nhu cầu
    # export_user_credentials(exclude_usernames=exclude_list)