// attendance-constants.js

// Các class CSS cho trạng thái chấm công
export const ATTENDANCE_STATUS = {
    PRESENT: 'present',                    // Đúng giờ
    LATE: 'late',                          // Đi muộn nhẹ (8:10-8:30)
    VERY_LATE: 'very-late',                // Đi muộn nặng (sau 8:30)
    EARLY_LEAVE: 'early-leave',            // Về sớm
    HALF_DAY_MORNING: 'half-day-morning',  // Vắng nửa buổi sáng
    HALF_DAY_AFTERNOON: 'half-day-afternoon', // Vắng nửa buổi chiều
    ABSENT: 'absent'                       // Vắng mặt cả ngày
};

// Cấu hình thời gian
export const TIME_CONFIG = {
    WORK_START_TIME: '08:00:00',      // Giờ bắt đầu làm việc chuẩn
    LATE_THRESHOLD: '08:10:00',       // Giờ bắt đầu tính muộn nhẹ
    VERY_LATE_THRESHOLD: '08:30:00',  // Giờ bắt đầu tính muộn nặng
    AFTERNOON_START: '14:00:00',      // Giờ bắt đầu làm việc buổi chiều
    WORK_HOURS_REQUIRED: 8,           // Số giờ làm việc yêu cầu
    LUNCH_BREAK_HOURS: 1.5,           // Thời gian nghỉ trưa
    LATE_FINE: 30,                    // Tiền phạt đi muộn nhẹ
    VERY_LATE_FINE: 50                // Tiền phạt đi muộn nặng
};

// Số lần đi muộn tối đa trong tuần
export const WEEKLY_LATE_LIMIT = 3;

// Tiền phạt nếu vượt quá số lần đi muộn tối đa trong tuần
export const WEEKLY_LATE_FINE = 100;

// Các màu background cho trạng thái
export const STATUS_COLORS = {
    PRESENT: { bg: 'bg-green-50', dark: 'dark:bg-green-900/20', dot: 'bg-green-500' },
    LATE: { bg: 'bg-yellow-50', dark: 'dark:bg-yellow-900/20', dot: 'bg-yellow-500' },
    VERY_LATE: { bg: 'bg-amber-50', dark: 'dark:bg-amber-900/20', dot: 'bg-amber-500' },
    EARLY_LEAVE: { bg: 'bg-orange-50', dark: 'dark:bg-orange-900/20', dot: 'bg-orange-500' },
    HALF_DAY_MORNING: { bg: 'bg-blue-50', dark: 'dark:bg-blue-900/20', dot: 'bg-blue-500' },
    HALF_DAY_AFTERNOON: { bg: 'bg-purple-50', dark: 'dark:bg-purple-900/20', dot: 'bg-purple-500' },
    ABSENT: { bg: 'bg-red-50', dark: 'dark:bg-red-900/20', dot: 'bg-red-500' },
    WEEKEND: { bg: 'bg-gray-50', dark: 'dark:bg-gray-700', dot: 'bg-gray-400' }
};

// Các hàm tiện ích thường dùng
// Format ngày thành chuỗi YYYY-MM-DD
export function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// Format hiển thị ngày thân thiện (VD: Thứ Hai, ngày 20/05/2025)
export function formatDateDisplay(date) {
    const days = ['Chủ nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy'];
    const day = days[date.getDay()];

    const dayOfMonth = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();

    return `${day}, ngày ${dayOfMonth}/${month}/${year}`;
}

// Định dạng thời gian hiển thị (từ HH:MM:SS thành HH:MM)
export function formatTimeDisplay(timeString) {
    if (!timeString) return '--:--';
    return timeString.substring(0, 5);
}

// Lấy ID người dùng từ localStorage
export function getUserId() {
    return localStorage.getItem('userId') || '1'; // Mặc định là user ID 1 nếu không có
}

// Hiển thị khi không có ảnh - dùng cả trong modal và tracking
export function showNoPhoto(element, message = "Không có ảnh") {
    if (element) {
        element.innerHTML = `
            <div class="flex flex-col items-center justify-center h-full w-full">
                <svg class="w-12 h-12 text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                </svg>
                <p class="text-gray-500 dark:text-gray-400 text-center">${message}</p>
            </div>
        `;
    }
}

// Hiển thị loading cho ảnh
export function showPhotoLoading(element) {
    if (element) {
        element.innerHTML = `
            <div class="flex flex-col items-center justify-center h-full w-full">
                <svg class="animate-spin h-10 w-10 text-blue-500 mb-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <p class="text-gray-500 dark:text-gray-400 text-center">Đang tải ảnh...</p>
            </div>
        `;
    }
}

// Hiển thị lỗi khi tải ảnh
export function showPhotoError(element, message = "Không thể tải ảnh") {
    if (element) {
        element.innerHTML = `
            <div class="flex flex-col items-center justify-center h-full w-full">
                <svg class="w-12 h-12 text-red-500 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <p class="text-red-500 dark:text-red-400 text-center">${message}</p>
            </div>
        `;
    }
}

// Hiển thị ảnh khi tải thành công
export function showPhoto(element, imageUrl) {
    if (element) {
        element.innerHTML = `
            <img src="${imageUrl}" alt="Ảnh chấm công" class="w-full h-full object-cover" 
                onerror="this.onerror=null; this.parentNode.innerHTML='<div class=\\'flex flex-col items-center justify-center h-full w-full\\'><svg class=\\'w-12 h-12 text-red-500 mb-2\\' fill=\\'none\\' stroke=\\'currentColor\\' viewBox=\\'0 0 24 24\\' xmlns=\\'http://www.w3.org/2000/svg\\'><path stroke-linecap=\\'round\\' stroke-linejoin=\\'round\\' stroke-width=\\'2\\' d=\\'M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z\\'></path></svg><p class=\\'text-red-500 dark:text-red-400 text-center\\'>Không thể hiển thị ảnh</p></div>';">
        `;
    }
}