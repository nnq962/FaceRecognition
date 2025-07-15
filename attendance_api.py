from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from utils.logger_config import LOGGER
from database_config import config

app = FastAPI(title="Class Attendance API", version="1.0.0")

# Database collections
all_classes = config.database["list_classes_mock"]
class_7 = config.database["7_mock"]
class_19 = config.database["19_mock"]

def get_current_time():
    """Get current time in Vietnam timezone"""
    return config.get_vietnam_time()

def parse_time(time_str: str) -> datetime:
    """Parse time string to datetime object - Vietnam format"""
    try:
        # Handle different time formats, convert all to Vietnam format
        if 'T' in time_str and time_str.endswith('Z'):
            # Convert UTC to Vietnam time
            utc_dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            # Convert to Vietnam time (UTC+7) - remove timezone info for comparison
            vietnam_dt = utc_dt.replace(tzinfo=None) + timedelta(hours=7)
            return vietnam_dt
        elif 'T' in time_str:
            # ISO format without Z
            dt = datetime.fromisoformat(time_str.replace('T', ' ').split('.')[0])
            return dt
        else:
            # Handle format like "2025-06-23 00:00:00" (Vietnam time)
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    except Exception as e:
        LOGGER.error(f"Error parsing time {time_str}: {e}")
        raise ValueError(f"Invalid time format: {time_str}")

def is_time_in_range(current_time_str: str, start_time: str, end_time: str) -> bool:
    """Check if current time is within the given time range"""
    try:
        current_dt = datetime.strptime(current_time_str, "%Y-%m-%d %H:%M:%S")
        start_dt = parse_time(start_time)
        end_dt = parse_time(end_time)
        return start_dt <= current_dt <= end_dt
    except Exception as e:
        LOGGER.error(f"Error checking time range: {e}")
        return False

def get_class_data(class_id: int) -> List[Dict]:
    """Get student data for a specific class"""
    if class_id == 7:
        return class_7.find({})
    elif class_id == 19:
        return class_19.find({})
    else:
        LOGGER.warning(f"Class {class_id} not found in available classes")
        return []

def find_current_class(current_time: str) -> Optional[Dict]:
    """Find the class that is currently in session"""
    try:
        for class_info in all_classes.find({}):
            time_tables = class_info.get("time_tables", [])
            for time_table in time_tables:
                if is_time_in_range(current_time, time_table["start_time"], time_table["end_time"]):
                    LOGGER.info(f"Found current class: {class_info['class_name']} (ID: {class_info['id']})")
                    return class_info
        return None
    except Exception as e:
        LOGGER.error(f"Error finding current class: {e}")
        return None

def find_next_class(current_time: str) -> Optional[Dict]:
    """Find the next upcoming class"""
    try:
        current_dt = datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S")
        upcoming_classes = []
        
        for class_info in all_classes.find({}):
            time_tables = class_info.get("time_tables", [])
            for time_table in time_tables:
                start_time = parse_time(time_table["start_time"])
                if start_time > current_dt:
                    upcoming_classes.append({
                        "class_info": class_info,
                        "time_table": time_table,
                        "start_time": start_time
                    })
        
        if upcoming_classes:
            # Sort by start time and get the earliest one
            next_class = min(upcoming_classes, key=lambda x: x["start_time"])
            LOGGER.info(f"Found next class: {next_class['class_info']['class_name']} (ID: {next_class['class_info']['id']})")
            return {
                "class_info": next_class["class_info"],
                "time_table": next_class["time_table"]
            }
        
        return None
    except Exception as e:
        LOGGER.error(f"Error finding next class: {e}")
        return None

@app.get("/attendance/current")
def get_current_attendance():
    """
    Get current class attendance information and next upcoming class
    
    Returns:
    - Current class attendance info if there's a class in session
    - Next upcoming class schedule information
    """
    try:
        current_time = get_current_time()
        LOGGER.info(f"Checking attendance at {current_time} (Vietnam time)")
        
        data = {
            "current_class": None,
            "next_class": None
        }
        
        response = {
            "status": "success",
            "message": "Attendance data retrieved successfully",
            "timestamp": current_time,
            "data": data
        }
        
        # Find current class
        current_class = find_current_class(current_time)
        
        if current_class:
            # Get student attendance data
            students = list(get_class_data(current_class["id"]))
            
            # Format student data with check-in times
            student_attendance = []
            for student in students:
                student_info = {
                    "id": student.get("id"),
                    "code": student.get("code"),
                    "name": student.get("name"),
                    "check_in_time": student.get("check_in_time"),
                    "active_status": student.get("active_status", True)
                }
                student_attendance.append(student_info)
            
            data["current_class"] = {
                "class_id": current_class["id"],
                "class_name": current_class["class_name"],
                "year_name": current_class["year_name"],
                "main_teacher": {
                    "id": current_class["main_teacher_id"],
                    "name": f"{current_class['main_teacher_first_name']} {current_class['main_teacher_middle_name']} {current_class['main_teacher_last_name']}"
                },
                "co_teacher": {
                    "id": current_class["co_teacher_id"],
                    "name": f"{current_class['co_teacher_first_name']} {current_class['co_teacher_middle_name']} {current_class['co_teacher_last_name']}"
                },
                "auto_attendance_check": current_class["auto_attendance_check"],
                "board_checkin": current_class["board_checkin"],
                "student_count": len(student_attendance),
                "students": student_attendance
            }
        
        # Find next class
        next_class_info = find_next_class(current_time)
        
        if next_class_info:
            class_info = next_class_info["class_info"]
            time_table = next_class_info["time_table"]
            
            data["next_class"] = {
                "class_id": class_info["id"],
                "class_name": class_info["class_name"],
                "year_name": class_info["year_name"],
                "main_teacher": {
                    "id": class_info["main_teacher_id"],
                    "name": f"{class_info['main_teacher_first_name']} {class_info['main_teacher_middle_name']} {class_info['main_teacher_last_name']}"
                },
                "co_teacher": {
                    "id": class_info["co_teacher_id"],
                    "name": f"{class_info['co_teacher_first_name']} {class_info['co_teacher_middle_name']} {class_info['co_teacher_last_name']}"
                },
                "schedule": {
                    "start_time": time_table["start_time"],
                    "end_time": time_table["end_time"]
                }
            }
        
        LOGGER.info(f"Response prepared successfully")
        return response
        
    except Exception as e:
        LOGGER.error(f"Error in get_current_attendance: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/attendance/class/{class_id}")
def get_class_attendance(class_id: int):
    """
    Get attendance information for a specific class
    
    Args:
        class_id: The ID of the class
    
    Returns:
        Class information with student attendance data
    """
    try:
        LOGGER.info(f"Getting attendance for class ID: {class_id}")
        
        # Find class info
        class_info = None
        for cls in all_classes.find({}):
            if cls["id"] == class_id:
                class_info = cls
                break
        
        if not class_info:
            raise HTTPException(status_code=404, detail=f"Class with ID {class_id} not found")
        
        # Get student data
        students = list(get_class_data(class_id))
        
        if not students:
            LOGGER.warning(f"No student data found for class {class_id}")
        
        # Format response
        student_attendance = []
        for student in students:
            student_info = {
                "id": student.get("id"),
                "code": student.get("code"),
                "name": student.get("name"),
                "check_in_time": student.get("check_in_time"),
                "active_status": student.get("active_status", True),
                "phone": student.get("phone"),
                "gender_text": student.get("gender_text")
            }
            student_attendance.append(student_info)
        
        class_data = {
            "class_id": class_info["id"],
            "class_name": class_info["class_name"],
            "year_name": class_info["year_name"],
            "main_teacher": {
                "id": class_info["main_teacher_id"],
                "name": f"{class_info['main_teacher_first_name']} {class_info['main_teacher_middle_name']} {class_info['main_teacher_last_name']}"
            },
            "co_teacher": {
                "id": class_info["co_teacher_id"],
                "name": f"{class_info['co_teacher_first_name']} {class_info['co_teacher_middle_name']} {class_info['co_teacher_last_name']}"
            },
            "auto_attendance_check": class_info["auto_attendance_check"],
            "board_checkin": class_info["board_checkin"],
            "time_tables": class_info["time_tables"],
            "time_attendances": class_info["time_attendances"],
            "student_count": len(student_attendance),
            "students": student_attendance
        }

        response = {
            "status": "success",
            "message": "Class attendance data retrieved successfully",
            "timestamp": config.get_vietnam_time(),
            "data": class_data
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.error(f"Error in get_class_attendance: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "success", 
        "message": "API is healthy",
        "timestamp": config.get_vietnam_time(),
        "data": {
            "service": "Class Attendance API",
            "version": "1.0.0"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)