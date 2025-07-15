from datetime import datetime
from typing import Dict, Optional


def create_schedule(api_data: Dict) -> Dict:
    """
    Tạo lịch sử dụng từ dữ liệu API
    
    Args:
        api_data: Dữ liệu trả về từ API với format:
        {
            "result": true,
            "data": {
                "list_classes": [...],
                "list_hardware": {...}
            }
        }
    
    Returns:
        Dict: Lịch sử dụng với format đã định nghĩa
    """
    
    # Khởi tạo cấu trúc lịch
    schedule = {
        "schedule_id": f"schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "generated_at": datetime.now().isoformat(),
        "school_id": None,
        "active_periods": [],
        "current_active": None,
        "next_active": None
    }
    
    # Kiểm tra dữ liệu đầu vào
    if not api_data.get("result") or not api_data.get("data"):
        return schedule
    
    data = api_data["data"]
    list_classes = data.get("list_classes", [])
    
    # Lấy school_id từ class đầu tiên
    if list_classes:
        schedule["school_id"] = list_classes[0].get("school_id")
    
    # Tạo danh sách active_periods từ tất cả classes
    active_periods = []
    
    for class_info in list_classes:
        class_id = class_info["id"]
        time_attendances = class_info.get("time_attendances", [])
        
        for time_slot in time_attendances:
            start_time = time_slot["start_time"]
            end_time = time_slot["end_time"]
            
            # Tạo period
            period = {
                "period_id": f"{class_id}_{start_time}_{end_time}",
                "class_id": class_id,
                "start_time": start_time,
                "end_time": end_time,
                "is_active": False
            }
            
            active_periods.append(period)
    
    # Sắp xếp periods theo thời gian
    active_periods.sort(key=lambda x: x["start_time"])
    
    # Gán vào schedule
    schedule["active_periods"] = active_periods
    
    # Cập nhật trạng thái active
    schedule = update_active_status(schedule)
    
    return schedule


def update_active_status(schedule: Dict) -> Dict:
    """
    Cập nhật trạng thái active cho schedule dựa trên thời gian hiện tại
    
    Args:
        schedule: Lịch sử dụng
        
    Returns:
        Dict: Lịch đã được cập nhật trạng thái
    """
    current_time = datetime.now().strftime("%H:%M:%S")
    
    # Reset tất cả periods
    for period in schedule["active_periods"]:
        period["is_active"] = False
    
    # Tìm current_active
    current_active = None
    for period in schedule["active_periods"]:
        if period["start_time"] <= current_time <= period["end_time"]:
            period["is_active"] = True
            current_active = {
                "period_id": period["period_id"],
                "class_id": period["class_id"],
                "start_time": period["start_time"],
                "end_time": period["end_time"]
            }
            break
    
    schedule["current_active"] = current_active
    
    # Tìm next_active
    next_active = None
    for period in schedule["active_periods"]:
        if period["start_time"] > current_time:
            next_active = {
                "period_id": period["period_id"],
                "class_id": period["class_id"],
                "start_time": period["start_time"],
                "end_time": period["end_time"]
            }
            break
    
    schedule["next_active"] = next_active
    
    return schedule


def get_active_class_id(schedule: Dict) -> Optional[int]:
    """
    Lấy class_id của lớp đang active
    
    Args:
        schedule: Lịch sử dụng
        
    Returns:
        Optional[int]: class_id nếu có lớp đang active, None nếu không
    """
    if schedule.get("current_active"):
        return schedule["current_active"]["class_id"]
    return None


# Example usage
if __name__ == "__main__":
    # Dữ liệu mẫu từ API
    api_response = {
        "result": True,
        "data": {
            "list_classes": [
                {
                    "id": 19,
                    "class_name": "Lớp 2",
                    "year_name": "2025",
                    "auto_attendance_check": True,
                    "school_id": 10,
                    "co_teacher_id": 17,
                    "co_teacher_first_name": "Phan",
                    "co_teacher_middle_name": "Hữu",
                    "co_teacher_last_name": "Toại",
                    "main_teacher_id": 17,
                    "main_teacher_first_name": "Phan",
                    "main_teacher_middle_name": "Hữu",
                    "main_teacher_last_name": "Toại",
                    "board_checkin": False,
                    "time_attendances": [
                        {"start_time": "09:00:00", "end_time": "10:00:00"},
                        {"start_time": "12:00:00", "end_time": "13:00:00"}
                    ]
                },
                {
                    "id": 4,
                    "class_name": "Lớp 2",
                    "year_name": "2025",
                    "auto_attendance_check": True,
                    "school_id": 10,
                    "co_teacher_id": 33,
                    "co_teacher_first_name": "M",
                    "co_teacher_middle_name": "V",
                    "co_teacher_last_name": "D",
                    "main_teacher_id": 17,
                    "main_teacher_first_name": "Phan",
                    "main_teacher_middle_name": "Hữu",
                    "main_teacher_last_name": "Toại",
                    "board_checkin": False,
                    "time_attendances": [
                        {"start_time": "14:00:00", "end_time": "15:00:00"}
                    ]
                },
                {
                    "id": 7,
                    "class_name": "Vu Minh Quang (TEST PARENTS - MVD MARKED)",
                    "year_name": "2030",
                    "auto_attendance_check": False,
                    "school_id": 10,
                    "co_teacher_id": 17,
                    "co_teacher_first_name": "Phan",
                    "co_teacher_middle_name": "Hữu",
                    "co_teacher_last_name": "Toại",
                    "main_teacher_id": 17,
                    "main_teacher_first_name": "Phan",
                    "main_teacher_middle_name": "Hữu",
                    "main_teacher_last_name": "Toại",
                    "board_checkin": False,
                    "time_attendances": [
                        {"start_time": "17:00:00", "end_time": "19:00:00"},
                        {"start_time": "19:30:00", "end_time": "21:00:00"}
                    ]
                }
            ],
            "list_hardware": {
                "cameras": [
                    {
                        "id": 1,
                        "name": "Camera T2 1",
                        "mac_address": "a8:31:62:c0:3b:2a",
                        "ip": "192.168.1.40",
                        "username": "admin",
                        "password": "L2B92F47"
                    }
                ],
                "boards": [
                    {
                        "id": 3,
                        "name": "Bảng 2",
                        "board_id": "Bảng"
                    },
                    {
                        "id": 2,
                        "name": "Bảng 1",
                        "board_id": "BOARD11111"
                    }
                ]
            }
        }
    }
    
    # Tạo lịch
    schedule = create_schedule(api_response)
    
    # In kết quả
    import json
    print(json.dumps(schedule, indent=2, ensure_ascii=False))
    
    # Kiểm tra lớp đang active
    active_class = get_active_class_id(schedule)
    if active_class:
        print(f"\nLớp đang active: {active_class}")
    else:
        print("\nKhông có lớp nào đang active")