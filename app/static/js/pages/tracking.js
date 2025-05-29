import API from '../core/api.js';
import { showToast } from '../utils/toast.js';
import * as trackingModal from '../utils/tracking-modal.js';
import User from "../utils/user.js";


import {
    ATTENDANCE_STATUS,
    TIME_CONFIG,
    STATUS_COLORS,
    WEEKLY_LATE_LIMIT,
    WEEKLY_LATE_FINE,
    formatDate,
    formatDateDisplay,
    formatTimeDisplay,
    showNoPhoto,
    showPhotoLoading,
    showPhotoError,
    showPhoto
} from '../utils/attendance-constants.js';


// Biến để lưu trạng thái hiện tại của lịch
let currentDate = new Date();
let attendanceData = []; // Sẽ lưu dữ liệu chấm công từ API

// Khởi tạo lịch
function setupTrackingPage() {
    // Hiển thị trạng thái loading ban đầu
    showLoadingCalendar();

    // Khởi tạo các event listener
    initEventListeners();

    // Tải dữ liệu chấm công từ API và render lịch
    loadAttendanceData().then(() => {
        renderCalendar(currentDate);
    });
}

// Event listener cho các nút điều hướng
function initEventListeners() {
    const prevMonthBtn = document.getElementById('prevMonth');
    const nextMonthBtn = document.getElementById('nextMonth');
    const todayBtn = document.getElementById('todayBtn');

    // Tháng cũ nhất được phép xem
    const oldestAllowedMonth = new Date(2025, 3, 1); // Tháng 4 năm 2025 (0-indexed)

    if (prevMonthBtn) {
        prevMonthBtn.addEventListener('click', () => {
            // Tạo bản sao ngày hiện tại để kiểm tra tháng trước
            const prevMonth = new Date(currentDate);
            prevMonth.setMonth(prevMonth.getMonth() - 1);

            // Chỉ cho phép lùi về đến tháng 04/2025
            if (prevMonth.getFullYear() > oldestAllowedMonth.getFullYear() ||
                (prevMonth.getFullYear() === oldestAllowedMonth.getFullYear() &&
                    prevMonth.getMonth() >= oldestAllowedMonth.getMonth())) {
                currentDate.setMonth(currentDate.getMonth() - 1);

                // Hiển thị loading trước khi tải dữ liệu mới
                showLoadingCalendar();

                // Tải dữ liệu chấm công từ API trước, sau đó mới render lịch
                loadAttendanceData().then(() => {
                    renderCalendar(currentDate);
                });
            } else {
                showToast('Thông báo', 'Không có dữ liệu trước tháng 04/2025', 'info');
            }
        });
    }

    if (nextMonthBtn) {
        nextMonthBtn.addEventListener('click', () => {
            // Tạo bản sao ngày hiện tại để kiểm tra tháng tiếp theo
            const nextMonth = new Date(currentDate);
            nextMonth.setMonth(nextMonth.getMonth() + 1);

            // Lấy tháng hiện tại (thời điểm thực)
            const currentRealMonth = new Date();

            // So sánh năm và tháng riêng biệt
            if (nextMonth.getFullYear() < currentRealMonth.getFullYear() ||
                (nextMonth.getFullYear() === currentRealMonth.getFullYear() &&
                    nextMonth.getMonth() <= currentRealMonth.getMonth())) {
                currentDate.setMonth(currentDate.getMonth() + 1);

                // Hiển thị loading trước khi tải dữ liệu mới
                showLoadingCalendar();

                // Tải dữ liệu chấm công từ API trước, sau đó mới render lịch
                loadAttendanceData().then(() => {
                    renderCalendar(currentDate);
                });
            } else {
                showToast('Thông báo', 'Không thể xem dữ liệu tương lai', 'info');
            }
        });
    }

    if (todayBtn) {
        todayBtn.addEventListener('click', () => {
            currentDate = new Date();

            // Hiển thị loading trước khi tải dữ liệu mới
            showLoadingCalendar();

            // Tải dữ liệu chấm công từ API trước, sau đó mới render lịch
            loadAttendanceData().then(() => {
                renderCalendar(currentDate);
            });
        });
    }
}

// Hiển thị hiệu ứng loading khi đang tải dữ liệu
function showLoadingCalendar() {
    const calendarGrid = document.getElementById('calendar-grid');
    if (calendarGrid) {
        calendarGrid.innerHTML = '<div class="col-span-7 py-12 flex justify-center items-center"><i class="fas fa-spinner fa-spin mr-2"></i>Đang tải dữ liệu...</div>';
    }
}

// Hàm tạo và hiển thị lịch
function renderCalendar(date) {
    // Cập nhật tiêu đề tháng
    updateMonthTitle(date);

    // Tính toán các ngày cần hiển thị
    const { year, month, firstDayIndex, lastDay, prevMonthDays, nextMonthDays } = calculateCalendarDays(date);

    // Tạo các ô lịch
    const calendarGrid = document.getElementById('calendar-grid');
    if (!calendarGrid) return;

    // Xóa nội dung hiện tại
    calendarGrid.innerHTML = '';

    // Thêm các ô cho tháng trước
    renderPreviousMonthDays(calendarGrid, year, month, firstDayIndex);

    // Thêm các ô cho tháng hiện tại
    renderCurrentMonthDays(calendarGrid, year, month, lastDay);

    // Thêm các ô cho tháng sau
    renderNextMonthDays(calendarGrid, year, month, nextMonthDays);

    // Cập nhật số liệu tóm tắt
    updateAttendanceSummary();
}

// Cập nhật tiêu đề tháng
function updateMonthTitle(date) {
    const monthElement = document.getElementById('currentMonth');
    if (!monthElement) return;

    const year = date.getFullYear();
    const month = date.getMonth() + 1; // 1-indexed cho hiển thị

    monthElement.textContent = `Tháng ${month.toString().padStart(2, '0')}/${year}`;
}

// Tính toán các thông số của lịch
function calculateCalendarDays(date) {
    const year = date.getFullYear();
    const month = date.getMonth();

    // Ngày đầu tiên của tháng
    const firstDayOfMonth = new Date(year, month, 1);

    // Ngày cuối cùng của tháng
    const lastDayOfMonth = new Date(year, month + 1, 0);
    const lastDay = lastDayOfMonth.getDate();

    // Lấy thứ của ngày đầu tiên (0 = CN, 1 = T2, ...)
    let firstDayIndex = firstDayOfMonth.getDay();
    // Điều chỉnh để tuần bắt đầu từ T2 (0 = T2, ..., 6 = CN)
    firstDayIndex = firstDayIndex === 0 ? 6 : firstDayIndex - 1;

    // Tính số ngày cần hiển thị từ tháng trước
    const prevMonthDays = firstDayIndex;

    // Ngày cuối tháng là thứ mấy
    let lastDayIndex = lastDayOfMonth.getDay();
    // Điều chỉnh để tuần bắt đầu từ T2
    lastDayIndex = lastDayIndex === 0 ? 6 : lastDayIndex - 1;

    // Tính số ngày cần hiển thị từ tháng sau
    const nextMonthDays = 6 - lastDayIndex;

    return { year, month, firstDayIndex, lastDay, prevMonthDays, nextMonthDays };
}

// Hiển thị các ngày của tháng trước
function renderPreviousMonthDays(container, year, month, firstDayIndex) {
    if (firstDayIndex <= 0) return;

    // Ngày cuối cùng của tháng trước
    const prevMonth = month === 0 ? 11 : month - 1;
    const prevYear = month === 0 ? year - 1 : year;
    const prevMonthLastDay = new Date(prevYear, prevMonth + 1, 0).getDate();

    for (let i = 0; i < firstDayIndex; i++) {
        const day = prevMonthLastDay - firstDayIndex + i + 1;
        const cellElement = createEmptyDayCell(day, 'prev-month');
        container.appendChild(cellElement);
    }
}

// Hiển thị các ngày của tháng hiện tại
function renderCurrentMonthDays(container, year, month, lastDay) {
    const today = new Date();

    for (let day = 1; day <= lastDay; day++) {
        const date = new Date(year, month, day);
        const dateString = formatDate(date);
        const dayOfWeek = date.getDay(); // 0 = CN, 1 = T2, ...
        const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
        const isSunday = dayOfWeek === 0;

        // Kiểm tra xem có phải là ngày hiện tại không
        const isToday = date.getDate() === today.getDate() &&
            date.getMonth() === today.getMonth() &&
            date.getFullYear() === today.getFullYear();

        // Tìm kiếm dữ liệu điểm danh cho ngày này
        const dayData = findAttendanceDataForDay(dateString);

        // Tạo ô lịch với dữ liệu phù hợp
        const cell = createDayCell(day, dateString, dayData, isWeekend, isSunday, isToday);
        container.appendChild(cell);
    }
}

// Hiển thị các ngày của tháng sau
function renderNextMonthDays(container, year, month, nextMonthDays) {
    if (nextMonthDays <= 0) return;

    const nextMonth = month === 11 ? 0 : month + 1;
    const nextYear = month === 11 ? year + 1 : year;

    for (let day = 1; day <= nextMonthDays; day++) {
        const cellElement = createEmptyDayCell(day, 'next-month');
        container.appendChild(cellElement);
    }
}

// Tạo ô lịch trống (cho tháng trước và tháng sau)
function createEmptyDayCell(day, className) {
    const cellElement = document.createElement('div');
    cellElement.className = `macos-card p-1 sm:p-2 bg-gray-50/30 dark:bg-gray-800/20 w-full aspect-square sm:w-auto sm:aspect-auto`;

    // Nội dung là số ngày, được làm mờ
    cellElement.innerHTML = `
        <div class="text-right text-xs sm:text-sm font-medium text-gray-400 dark:text-gray-600">${day}</div>
    `;

    return cellElement;
}

// Cập nhật hàm getDayStatus
function getDayStatus(dayData, isWeekend, date) {
    // Kiểm tra ngày tương lai
    const todayString = formatDate(new Date());
    const isFuture = date > todayString;    

    // Nếu là ngày tương lai, không đánh dấu trạng thái
    if (isFuture) {
        return {
            bgClass: "bg-gray-50/50",
            darkClass: "dark:bg-gray-800/50",
            dotColors: [],
            checkIn: null,
            checkOut: null
        };
    }

    // Nếu không có dữ liệu và là cuối tuần, hiển thị là cuối tuần
    if ((!dayData || dayData.length === 0) && isWeekend) {
        return {
            bgClass: STATUS_COLORS.WEEKEND.bg,
            darkClass: STATUS_COLORS.WEEKEND.dark,
            dotColors: [], // Không hiển thị dot xám cho ngày cuối tuần
            checkIn: null,
            checkOut: null
        };
    }

    // Nếu không có dữ liệu và không phải cuối tuần, đánh dấu là vắng mặt
    if (!dayData || dayData.length === 0) {
        return {
            bgClass: STATUS_COLORS.ABSENT.bg,
            darkClass: STATUS_COLORS.ABSENT.dark,
            dotColors: [STATUS_COLORS.ABSENT.dot],
            checkIn: null,
            checkOut: null
        };
    }

    // Tìm dữ liệu check-in và check-out
    let checkIn = null;
    let checkOut = null;
    const dotColors = [];
    let bgClass = STATUS_COLORS.PRESENT.bg;
    let darkClass = STATUS_COLORS.PRESENT.dark;

    // Xác định trạng thái ưu tiên
    let hasPresent = false;
    let hasLate = false;
    let hasVeryLate = false;
    let hasEarlyLeave = false;
    let hasHalfDayMorning = false;
    let hasHalfDayAfternoon = false;
    let hasAbsent = false;

    dayData.forEach(record => {
        // Cập nhật thời gian check-in và check-out
        if (record.check_in_time && (!checkIn || record.check_in_time < checkIn)) {
            checkIn = record.check_in_time;
        }

        if (record.check_out_time && (!checkOut || record.check_out_time > checkOut)) {
            checkOut = record.check_out_time;
        }

        // Cập nhật trạng thái
        switch (record.status) {
            case ATTENDANCE_STATUS.PRESENT:
                hasPresent = true;
                if (!dotColors.includes(STATUS_COLORS.PRESENT.dot)) {
                    dotColors.push(STATUS_COLORS.PRESENT.dot);
                }
                break;
            case ATTENDANCE_STATUS.LATE:
                hasLate = true;
                if (!dotColors.includes(STATUS_COLORS.LATE.dot)) {
                    dotColors.push(STATUS_COLORS.LATE.dot);
                }
                break;
            case ATTENDANCE_STATUS.VERY_LATE:
                hasVeryLate = true;
                if (!dotColors.includes(STATUS_COLORS.VERY_LATE.dot)) {
                    dotColors.push(STATUS_COLORS.VERY_LATE.dot);
                }
                break;
            case ATTENDANCE_STATUS.EARLY_LEAVE:
                hasEarlyLeave = true;
                if (!dotColors.includes(STATUS_COLORS.EARLY_LEAVE.dot)) {
                    dotColors.push(STATUS_COLORS.EARLY_LEAVE.dot);
                }
                break;
            case ATTENDANCE_STATUS.HALF_DAY_MORNING:
                hasHalfDayMorning = true;
                if (!dotColors.includes(STATUS_COLORS.HALF_DAY_MORNING.dot)) {
                    dotColors.push(STATUS_COLORS.HALF_DAY_MORNING.dot);
                }
                break;
            case ATTENDANCE_STATUS.HALF_DAY_AFTERNOON:
                hasHalfDayAfternoon = true;
                if (!dotColors.includes(STATUS_COLORS.HALF_DAY_AFTERNOON.dot)) {
                    dotColors.push(STATUS_COLORS.HALF_DAY_AFTERNOON.dot);
                }
                break;
            case ATTENDANCE_STATUS.ABSENT:
                hasAbsent = true;
                if (!dotColors.includes(STATUS_COLORS.ABSENT.dot)) {
                    dotColors.push(STATUS_COLORS.ABSENT.dot);
                }
                break;
        }
    });

    // Xác định màu nền ưu tiên cho ô
    if (hasHalfDayMorning) {
        bgClass = STATUS_COLORS.HALF_DAY_MORNING.bg;
        darkClass = STATUS_COLORS.HALF_DAY_MORNING.dark;
    } else if (hasHalfDayAfternoon) {
        bgClass = STATUS_COLORS.HALF_DAY_AFTERNOON.bg;
        darkClass = STATUS_COLORS.HALF_DAY_AFTERNOON.dark;
    } else if (hasAbsent) {
        bgClass = STATUS_COLORS.ABSENT.bg;
        darkClass = STATUS_COLORS.ABSENT.dark;
    } else if (hasVeryLate) {
        bgClass = STATUS_COLORS.VERY_LATE.bg;
        darkClass = STATUS_COLORS.VERY_LATE.dark;
    } else if (hasLate) {
        bgClass = STATUS_COLORS.LATE.bg;
        darkClass = STATUS_COLORS.LATE.dark;
    } else if (hasEarlyLeave) {
        bgClass = STATUS_COLORS.EARLY_LEAVE.bg;
        darkClass = STATUS_COLORS.EARLY_LEAVE.dark;
    } else if (hasPresent) {
        bgClass = STATUS_COLORS.PRESENT.bg;
        darkClass = STATUS_COLORS.PRESENT.dark;
    }

    return {
        bgClass,
        darkClass,
        dotColors,
        checkIn,
        checkOut
    };
}

// Cập nhật hàm createDayCell để đảm bảo kích thước đồng nhất hoàn toàn
function createDayCell(day, dateString, dayData, isWeekend, isSunday, isToday) {
    // Xác định ngày tương lai
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const currentDate = new Date(dateString);
    currentDate.setHours(0, 0, 0, 0);
    const isFuture = currentDate > today;
    
    // Xác định trạng thái và màu sắc
    const { bgClass, darkClass, dotColors, checkIn, checkOut } = getDayStatus(dayData, isWeekend, dateString);
    
    // Tạo border đặc biệt cho ngày hiện tại
    const borderClass = isToday ? 'border-2 border-blue-500 dark:border-blue-400' : '';
    
    // Tạo phần tử div cho ô lịch
    const cellElement = document.createElement('div');
    cellElement.className = `macos-card p-1 sm:p-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-all duration-200 relative flex flex-col ${bgClass} ${darkClass} ${borderClass} w-full aspect-square sm:w-auto sm:aspect-auto justify-between`;
    cellElement.setAttribute('data-date', dateString);
    
    // Xác định nội dung hiển thị cho thời gian
    let timeContent = '';
    
    if (isFuture && isWeekend) {
        // Ngày cuối tuần trong tương lai: vẫn hiển thị "Cuối tuần"
        timeContent = `<div>Cuối tuần</div>`;
    } else if (isFuture) {
        // Ngày thường trong tương lai: không hiển thị gì cả
        timeContent = `<div class="opacity-0">00:00</div><div class="opacity-0">00:00</div>`;
    } else if (isWeekend && (!dayData || dayData.length === 0)) {
        // Ngày cuối tuần không có dữ liệu: hiển thị "Cuối tuần"
        timeContent = `<div>Cuối tuần</div>`;
    } else if (isToday && (!checkIn || !checkOut)) {
        // Ngày hiện tại chưa đủ dữ liệu: hiển thị "--:--"
        timeContent = `
            <div>${checkIn ? formatTimeDisplay(checkIn) : '--:--'}</div>
            <div>${checkOut ? formatTimeDisplay(checkOut) : '--:--'}</div>
        `;
    } else {
        // Ngày khác: hiển thị thời gian check-in/check-out nếu có
        timeContent = `
            <div>${checkIn ? formatTimeDisplay(checkIn) : '--:--'}</div>
            <div>${checkOut ? formatTimeDisplay(checkOut) : '--:--'}</div>
        `;
    }
    
    // Tạo dots HTML, luôn thêm ít nhất một dot dù có thể tàng hình
    let dotsHTML = '';
    if (dotColors.length > 0) {
        dotsHTML = dotColors.map(color => `<span class="w-2 h-2 ${color} rounded-full"></span>`).join('');
    } else {
        // Thêm một dot trống tàng hình để giữ kích thước
        dotsHTML = `<span class="w-2 h-2 opacity-0 bg-gray-300 rounded-full"></span>`;
    }
    
    // Tạo nội dung HTML cho ô lịch - luôn giữ cấu trúc đồng nhất
    cellElement.innerHTML = `
        <div class="text-right text-xs sm:text-sm font-medium ${isSunday ? 'text-red-500 dark:text-red-400' : 'text-gray-700 dark:text-gray-300'}">${day}</div>
        <div class="mt-1 flex-grow flex flex-col justify-center items-center text-center">
            <div class="hidden sm:inline-block bg-gray-100 dark:bg-gray-600 text-gray-700 dark:text-gray-300 px-3 py-1 rounded text-xs font-medium leading-tight ${isFuture && !isWeekend ? 'opacity-0' : ''}">
                ${timeContent}
            </div>
        </div>
        <div class="flex items-center justify-center h-1/3 sm:h-auto sm:mt-2 sm:-translate-y-[3px] sm:relative">
            <div class="flex justify-center gap-1">
                ${dotsHTML}
            </div>
        </div>
    `;
    
    // Thêm sự kiện click
    cellElement.addEventListener('click', () => onDayClick(dateString, dayData));
    
    return cellElement;
}

// Cập nhật hàm updateAttendanceSummary để không tính ngày vắng mặt cho tương lai
function updateAttendanceSummary() {
    // Tập hợp các ngày duy nhất cho mỗi trạng thái
    const uniqueDays = {
        present: new Set(),
        late: new Set(),
        veryLate: new Set(),
        earlyLeave: new Set(),
        halfDayMorning: new Set(),
        halfDayAfternoon: new Set(),
        absent: new Set(),
        weeklyLateFine: 0
    };

    // Tập hợp các ngày có dữ liệu điểm danh
    const daysWithAttendance = new Set();

    // Ngày hiện tại (thời điểm thực)
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // Duyệt qua dữ liệu điểm danh và thêm vào tập hợp tương ứng
    attendanceData.forEach(record => {
        // Chỉ tính những ngày có dữ liệu điểm danh
        daysWithAttendance.add(record.date);

        switch (record.status) {
            case ATTENDANCE_STATUS.PRESENT:
                uniqueDays.present.add(record.date);
                break;
            case ATTENDANCE_STATUS.LATE:
                uniqueDays.late.add(record.date);
                break;
            case ATTENDANCE_STATUS.VERY_LATE:
                uniqueDays.veryLate.add(record.date);
                break;
            case ATTENDANCE_STATUS.EARLY_LEAVE:
                uniqueDays.earlyLeave.add(record.date);
                break;
            case ATTENDANCE_STATUS.HALF_DAY_MORNING:
                uniqueDays.halfDayMorning.add(record.date);
                break;
            case ATTENDANCE_STATUS.HALF_DAY_AFTERNOON:
                uniqueDays.halfDayAfternoon.add(record.date);
                break;
            case ATTENDANCE_STATUS.ABSENT:
                uniqueDays.absent.add(record.date);
                break;
            case 'weekly-late-fine':
                uniqueDays.weeklyLateFine += record.weeklyLateFine || 0;
                break;
        }
    });

    // Tính ngày làm việc trong tháng đã qua (không tính T7, CN và tương lai)
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const lastDay = new Date(year, month + 1, 0).getDate();

    let workdays = 0;
    let absentDays = new Set();

    for (let i = 1; i <= lastDay; i++) {
        const date = new Date(year, month, i);
        const dayOfWeek = date.getDay();
        const dateString = formatDate(date);

        // Bỏ qua ngày cuối tuần và ngày tương lai
        if (dayOfWeek !== 0 && dayOfWeek !== 6 && date <= today) {
            workdays++;

            // Kiểm tra xem ngày này có dữ liệu điểm danh không
            if (!daysWithAttendance.has(dateString) && !uniqueDays.absent.has(dateString)) {
                // Thêm vào tập hợp vắng mặt nếu không có dữ liệu điểm danh
                absentDays.add(dateString);
            }
        }
    }

    // Thêm các ngày vắng mặt tự động vào tập hợp vắng mặt
    absentDays.forEach(date => {
        uniqueDays.absent.add(date);
    });

    // Tính tiền phạt
    const lateFine = uniqueDays.late.size * TIME_CONFIG.LATE_FINE;
    const veryLateFine = uniqueDays.veryLate.size * TIME_CONFIG.VERY_LATE_FINE;
    const totalFine = lateFine + veryLateFine + uniqueDays.weeklyLateFine;

    // Cập nhật hiển thị
    updateSummaryElements({
        workdayCount: workdays,
        checkedDays: daysWithAttendance.size,
        onTimeCount: uniqueDays.present.size,
        lateCount: uniqueDays.late.size,
        veryLateCount: uniqueDays.veryLate.size,
        earlyLeaveCount: uniqueDays.earlyLeave.size,
        halfDayMorningCount: uniqueDays.halfDayMorning.size,
        halfDayAfternoonCount: uniqueDays.halfDayAfternoon.size,
        absentCount: uniqueDays.absent.size,
        fineAmount: totalFine.toLocaleString('vi-VN') + 'K'
    });
}


// Tìm dữ liệu chấm công cho một ngày cụ thể
function findAttendanceDataForDay(dateString) {
    return attendanceData.filter(record => record.date === dateString);
}

// Xử lý sự kiện click vào ngày
function onDayClick(dateString, dayData) {
    trackingModal.showAttendanceModal(dateString, dayData);
}

// Cập nhật các phần tử hiển thị tóm tắt
function updateSummaryElements(data) {
    Object.entries(data).forEach(([key, value]) => {
        const element = document.getElementById(key);
        if (element) {
            element.textContent = value;
        }
    });
}

// Tải dữ liệu chấm công từ API
async function loadAttendanceData() {
    // Reset dữ liệu hiện tại
    attendanceData = [];
    resetAttendanceSummary();
    
    // Lấy ngày đầu tiên và cuối cùng của tháng hiện tại
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    
    // Format ngày để truyền vào API
    const startDate = formatDate(firstDay);
    const endDate = formatDate(lastDay);
    
    // Lấy ID người dùng từ localStorage
    const userId = User.getUserId();
    if (!userId) {
        showToast('Lỗi xác thực', 'Vui lòng đăng nhập lại', 'error');
        attendanceData = getAttendanceDemoData();
        return Promise.resolve();
    }

    try {
        // Gọi API với endpoint cũ (giữ nguyên)
        const response = await fetchAndNotifyAttendance(userId, startDate, endDate);
        
        // THAY ĐỔI: Kiểm tra response theo format mới
        if (response && response.status === 'success' && response.data && response.data.attendance_records) {
            
            // Xử lý dữ liệu từ API
            processAttendanceData(response.data.attendance_records);
            
            // Log thông tin bổ sung từ response mới
            if (response.data.total_records !== undefined) {
            }
            
        } else {            
            // Hiển thị thông báo lỗi cụ thể từ API nếu có
            const errorMessage = response?.message || 'Không thể tải dữ liệu chấm công, sử dụng dữ liệu mẫu';
            showToast('Dữ liệu không đầy đủ', errorMessage, 'warning');
            
            // Sử dụng dữ liệu mẫu nếu API không trả về dữ liệu
            attendanceData = getAttendanceDemoData();
        }
        
    } catch (error) {        
        // Cải thiện error handling
        let errorMessage = 'Không thể kết nối đến máy chủ. Vui lòng thử lại sau.';
        
        // Kiểm tra nếu error có status từ API
        if (error.status === 400) {
            errorMessage = 'Dữ liệu đầu vào không hợp lệ';
        } else if (error.status === 500) {
            errorMessage = 'Lỗi máy chủ. Vui lòng liên hệ quản trị viên';
        } else if (error.message) {
            errorMessage = error.message;
        }
        
        showToast('Lỗi kết nối', errorMessage, 'error');
        
        // Sử dụng dữ liệu mẫu nếu API gặp lỗi
        attendanceData = getAttendanceDemoData();
    }
    
    return Promise.resolve();
}

// Xử lý dữ liệu chấm công từ API
function processAttendanceData(records) {
    // Mảng mới để lưu dữ liệu đã xử lý
    const processedData = [];

    // Thêm đếm số lần đi muộn theo tuần
    const lateCountByWeek = {};

    records.forEach(record => {
        // Mặc định là không có trạng thái
        let statuses = [];

        // Tạo key tuần từ ngày (YYYY-WW format)
        const recordDate = new Date(record.date);
        const weekNumber = getWeekNumber(recordDate);
        const weekKey = `${recordDate.getFullYear()}-${weekNumber}`;

        // Nếu không có check-in và check-out, đánh dấu là vắng mặt
        if (!record.check_in_time && !record.check_out_time) {
            statuses.push(ATTENDANCE_STATUS.ABSENT);
        }
        else {
            // Kiểm tra check-in time để xác định đi muộn và vắng buổi sáng
            if (record.check_in_time) {
                const checkInTime = new Date(`2000-01-01T${record.check_in_time}`);
                const lateThreshold = new Date(`2000-01-01T${TIME_CONFIG.LATE_THRESHOLD}`);
                const veryLateThreshold = new Date(`2000-01-01T${TIME_CONFIG.VERY_LATE_THRESHOLD}`);
                const afternoonStart = new Date(`2000-01-01T${TIME_CONFIG.AFTERNOON_START}`);

                // Kiểm tra thời gian check-in
                if (checkInTime >= afternoonStart) {
                    // Nếu check-in sau 14:00, chỉ đánh dấu là vắng buổi sáng
                    statuses.push(ATTENDANCE_STATUS.HALF_DAY_MORNING);
                }
                else if (checkInTime >= veryLateThreshold && checkInTime < afternoonStart) {
                    // Check-in sau 8:30 nhưng trước 14:00, đi muộn nặng
                    statuses.push(ATTENDANCE_STATUS.VERY_LATE);

                    // Cập nhật đếm đi muộn theo tuần
                    if (!lateCountByWeek[weekKey]) lateCountByWeek[weekKey] = 0;
                    lateCountByWeek[weekKey]++;
                }
                else if (checkInTime >= lateThreshold && checkInTime < veryLateThreshold) {
                    // Check-in từ 8:10-8:30, đi muộn nhẹ
                    statuses.push(ATTENDANCE_STATUS.LATE);

                    // Cập nhật đếm đi muộn theo tuần
                    if (!lateCountByWeek[weekKey]) lateCountByWeek[weekKey] = 0;
                    lateCountByWeek[weekKey]++;
                }
            } else {
                // Không có check-in, vắng cả ngày
                statuses.push(ATTENDANCE_STATUS.ABSENT);
            }

            // Kiểm tra check-out time để xác định vắng buổi chiều
            if (record.check_out_time) {
                const afternoonStart = new Date(`2000-01-01T${TIME_CONFIG.AFTERNOON_START}`);
                const checkOutTime = new Date(`2000-01-01T${record.check_out_time}`);

                if (checkOutTime < afternoonStart) {
                    // Nếu check-out trước 14:00, đánh dấu là vắng buổi chiều
                    statuses.push(ATTENDANCE_STATUS.HALF_DAY_AFTERNOON);
                }
            }

            // Kiểm tra thời gian làm việc
            if (record.check_in_time && record.check_out_time) {
                const checkInTime = new Date(`2000-01-01T${record.check_in_time}`);
                const checkOutTime = new Date(`2000-01-01T${record.check_out_time}`);
                const afternoonStart = new Date(`2000-01-01T${TIME_CONFIG.AFTERNOON_START}`);

                // Tính tổng thời gian làm việc (tính bằng giờ)
                let hoursWorked = (checkOutTime - checkInTime) / (1000 * 60 * 60);

                // Không tính thời gian nghỉ trưa nếu check-in sau 14:00 hoặc check-out trước 14:00
                if (checkInTime < afternoonStart && checkOutTime > afternoonStart) {
                    // Trừ đi thời gian nghỉ trưa chỉ khi làm việc cả sáng và chiều
                    hoursWorked -= TIME_CONFIG.LUNCH_BREAK_HOURS;
                }

                // Nếu tổng thời gian làm việc < 8 giờ và không phải vắng nửa buổi, đánh dấu là về sớm
                if (hoursWorked < TIME_CONFIG.WORK_HOURS_REQUIRED &&
                    !statuses.includes(ATTENDANCE_STATUS.HALF_DAY_MORNING) &&
                    !statuses.includes(ATTENDANCE_STATUS.HALF_DAY_AFTERNOON)) {
                    statuses.push(ATTENDANCE_STATUS.EARLY_LEAVE);
                }
            }

            // Nếu không có trạng thái nào khác và có đủ check-in và check-out, đánh dấu là có mặt
            if (statuses.length === 0 && record.check_in_time && record.check_out_time) {
                statuses.push(ATTENDANCE_STATUS.PRESENT);
            }
        }

        // Thêm mỗi trạng thái như một bản ghi riêng biệt
        statuses.forEach(status => {
            processedData.push({
                date: record.date,
                status: status,
                check_in_time: record.check_in_time,
                check_out_time: record.check_out_time
            });
        });
    });

    // Xử lý phạt đi muộn quá 3 lần/tuần
    Object.entries(lateCountByWeek).forEach(([weekKey, count]) => {
        if (count > WEEKLY_LATE_LIMIT) {
            // Lấy năm và số tuần từ weekKey
            const [year, week] = weekKey.split('-').map(Number);

            // Tìm ngày cuối cùng của tuần đó để gắn thêm thông báo phạt
            const lastDayOfWeek = getLastDayOfWeek(year, week);
            const lastDayFormatted = formatDate(lastDayOfWeek);

            // Thêm bản ghi phạt cho tuần > 3 lần đi muộn
            processedData.push({
                date: lastDayFormatted,
                status: 'weekly-late-fine',  // status đặc biệt để đánh dấu phạt tuần
                check_in_time: null,
                check_out_time: null,
                lateCount: count,
                weeklyLateFine: WEEKLY_LATE_FINE
            });
        }
    });

    // Lưu dữ liệu đã xử lý
    attendanceData = processedData;
}

// Hàm lấy số tuần trong năm
function getWeekNumber(d) {
    // Copy date để không ảnh hưởng đến tham số
    d = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    // Đặt về ngày đầu tuần (thứ 2)
    d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7));
    // Lấy ngày đầu năm
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    // Tính số tuần
    const weekNo = Math.ceil(((d - yearStart) / 86400000 + 1) / 7);
    return weekNo;
}

// Hàm lấy ngày cuối cùng của tuần (Chủ nhật)
function getLastDayOfWeek(year, weekNumber) {
    // Lấy ngày đầu năm
    const firstDayOfYear = new Date(year, 0, 1);
    // Tính ngày thứ 2 đầu tiên của năm
    const firstMonday = new Date(firstDayOfYear);
    firstMonday.setDate(firstDayOfYear.getDate() + (8 - firstDayOfYear.getDay()) % 7);

    // Tính ngày thứ 2 của tuần cần tìm
    const targetMonday = new Date(firstMonday);
    targetMonday.setDate(firstMonday.getDate() + (weekNumber - 1) * 7);

    // Tính ngày chủ nhật (ngày cuối tuần)
    const targetSunday = new Date(targetMonday);
    targetSunday.setDate(targetMonday.getDate() + 6);

    return targetSunday;
}

// Hàm reset tóm tắt chấm công
function resetAttendanceSummary() {
    const elements = [
        'onTimeCount',
        'lateCount',
        'veryLateCount',
        'earlyLeaveCount',
        'halfDayMorningCount',
        'halfDayAfternoonCount',
        'absentCount',
        'checkedDays',
        'workdayCount',
        'fineAmount'
    ];

    elements.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = id === 'fineAmount' ? '0K' : '0';
        }
    });
}

// Hàm lấy dữ liệu chấm công từ API
async function fetchAndNotifyAttendance(user_id, startDate, endDate) {
    try {
        const data = await API.getAttendance(user_id, startDate, endDate);
        showToast('Lấy dữ liệu thành công', '', 'success');
        return data;
    } catch (error) {
        showToast('Lỗi khi lấy dữ liệu', error.message, 'error');
        return null;
    }
}

// Demo data (để test trước khi kết nối API)
function getAttendanceDemoData() {
    const currentYear = currentDate.getFullYear();
    const currentMonth = currentDate.getMonth();
    const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();

    const demoData = [];

    // Tạo dữ liệu mẫu cho các ngày trong tháng
    for (let i = 1; i <= Math.min(daysInMonth, 28); i++) {
        // Bỏ qua ngày thứ 7 và chủ nhật
        const date = new Date(currentYear, currentMonth, i);
        const dayOfWeek = date.getDay();
        if (dayOfWeek === 0 || dayOfWeek === 6) continue;

        const formattedDate = formatDate(date);
        const randomValue = Math.random();

        // 60% xác suất đi làm đúng giờ
        if (randomValue < 0.6) {
            demoData.push({
                date: formattedDate,
                status: ATTENDANCE_STATUS.PRESENT,
                check_in_time: '08:00:00',
                check_out_time: '17:30:00'
            });
        }
        // 10% xác suất đi muộn nhẹ (8:10-8:30)
        else if (randomValue < 0.7) {
            demoData.push({
                date: formattedDate,
                status: ATTENDANCE_STATUS.LATE,
                check_in_time: '08:20:00',
                check_out_time: '17:30:00'
            });
        }
        // 5% xác suất đi muộn nặng (sau 8:30)
        else if (randomValue < 0.75) {
            demoData.push({
                date: formattedDate,
                status: ATTENDANCE_STATUS.VERY_LATE,
                check_in_time: '08:40:00',
                check_out_time: '17:30:00'
            });
            demoData.push({
                date: formattedDate,
                status: ATTENDANCE_STATUS.HALF_DAY_MORNING,
                check_in_time: '08:40:00',
                check_out_time: '17:30:00'
            });
        }
        // 5% xác suất về sớm
        else if (randomValue < 0.8) {
            demoData.push({
                date: formattedDate,
                status: ATTENDANCE_STATUS.EARLY_LEAVE,
                check_in_time: '08:00:00',
                check_out_time: '16:00:00'
            });
        }
        // 5% xác suất vừa đi muộn vừa về sớm
        else if (randomValue < 0.85) {
            demoData.push({
                date: formattedDate,
                status: ATTENDANCE_STATUS.LATE,
                check_in_time: '08:20:00',
                check_out_time: '16:00:00'
            });
            demoData.push({
                date: formattedDate,
                status: ATTENDANCE_STATUS.EARLY_LEAVE,
                check_in_time: '08:20:00',
                check_out_time: '16:00:00'
            });
        }
        // 5% xác suất vắng nửa buổi chiều
        else if (randomValue < 0.9) {
            demoData.push({
                date: formattedDate,
                status: ATTENDANCE_STATUS.HALF_DAY_AFTERNOON,
                check_in_time: '08:00:00',
                check_out_time: '12:00:00'
            });
        }
        // 5% xác suất vắng nửa buổi sáng
        else if (randomValue < 0.95) {
            demoData.push({
                date: formattedDate,
                status: ATTENDANCE_STATUS.HALF_DAY_MORNING,
                check_in_time: '14:00:00',
                check_out_time: '17:30:00'
            });
        }
        // 5% xác suất vắng mặt
        else {
            demoData.push({
                date: formattedDate,
                status: ATTENDANCE_STATUS.ABSENT,
                check_in_time: null,
                check_out_time: null
            });
        }
    }

    // Thêm dữ liệu đặc biệt - ngày hiện tại nếu trong tháng được chọn
    const now = new Date();
    if (now.getMonth() === currentMonth && now.getFullYear() === currentYear) {
        const today = formatDate(now);

        // Xóa dữ liệu cũ cho ngày hiện tại nếu có
        const filteredData = demoData.filter(record => record.date !== today);

        // Thêm dữ liệu mới cho ngày hiện tại - đánh dấu là hôm nay và đúng giờ
        filteredData.push({
            date: today,
            status: ATTENDANCE_STATUS.PRESENT,
            check_in_time: '08:00:00',
            check_out_time: '17:30:00'
        });

        return filteredData;
    }

    return demoData;
}

// Khởi tạo trang theo DOM content loaded
document.addEventListener('DOMContentLoaded', setupTrackingPage);

// Xuất các hàm cần thiết
export { setupTrackingPage };