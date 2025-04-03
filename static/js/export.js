// Biến để lưu dữ liệu
let attendanceData = [];
let originalData = [];
let currentFilePath = '';
let currentMonth = '';  // Thêm biến này
const BASE_URL = 'https://3hinc.nnq962.pro/api';
const EXPORT_ATTENDANCE_API_URL = `${BASE_URL}/export_attendance`;
const GENERATE_EXCEL_API_URL = `${BASE_URL}/generate_excel`;
const DOWNLOAD_URL = `${BASE_URL}/download`;

// Toast notification elements
const toast = document.getElementById('toast');
const toastIcon = document.getElementById('toastIcon');
const toastMessage = document.getElementById('toastMessage');
const toastDescription = document.getElementById('toastDescription');

// Khởi tạo khi trang được tải
document.addEventListener('DOMContentLoaded', function() {
    setupYearOptions();
    updateDateTime();
    setupEventListeners();
});

// Thiết lập năm hiện tại và các năm trước
function setupYearOptions() {
    const yearSelect = document.getElementById('yearSelect');
    const currentYear = new Date().getFullYear();
    
    for (let year = currentYear; year >= currentYear - 5; year--) {
        const option = document.createElement('option');
        option.value = year.toString();
        option.textContent = `Năm ${year}`;
        yearSelect.appendChild(option);
    }
    
    // Chọn năm hiện tại
    yearSelect.value = currentYear.toString();
}

// Cập nhật ngày giờ hiện tại
function updateDateTime() {
    const now = new Date();
    
    // Lấy giờ và phút một cách trực tiếp
    const hours = now.getHours().toString().padStart(2, '0');
    const minutes = now.getMinutes().toString().padStart(2, '0');
    
    // Lấy ngày, tháng, năm
    const day = now.getDate();
    const month = now.getMonth() + 1; // getMonth() trả về 0-11
    const year = now.getFullYear();
    
    // Lấy tên thứ trong tuần
    const weekdayOptions = { weekday: 'long' };
    const weekday = now.toLocaleDateString('vi-VN', weekdayOptions);
    
    // Định dạng ngày tháng giống các trang khác
    document.getElementById('currentDateTime').textContent = 
        `Cập nhật lúc ${hours}:${minutes} ${weekday}, ${day} tháng ${month}, ${year}`;
}

// Hiển thị thông báo dạng toast
function showToast(type, title, message, duration = 3000) {
    // Set toast type
    toast.className = 'toast-notification ' + type;
    
    // Set icon
    if (type === 'success') {
        toastIcon.className = 'fas fa-check-circle';
    } else if (type === 'error') {
        toastIcon.className = 'fas fa-exclamation-circle';
    }
    
    // Set content
    toastMessage.textContent = title;
    toastDescription.textContent = message;
    
    // Show toast
    toast.classList.add('show');
    
    // Hide toast after duration
    setTimeout(() => {
        toast.classList.remove('show');
    }, duration);
}

// Thiết lập tất cả event listeners
function setupEventListeners() {
    // Form xuất dữ liệu
    document.getElementById('exportForm').addEventListener('submit', handleFormSubmit);
    
    // Nút tải xuống
    document.getElementById('downloadBtn').addEventListener('click', handleDownload);
}

// Xử lý sự kiện submit form
function handleFormSubmit(e) {
    e.preventDefault();
    e.stopPropagation(); // Ngăn chặn việc sự kiện truyền lên các phần tử cha
    
    const year = document.getElementById('yearSelect').value;
    const month = document.getElementById('monthSelect').value;
    
    if (!year || !month) {
        showToast('error', 'Lỗi', 'Vui lòng chọn cả năm và tháng!');
        return false;
    }
    
    // Hiển thị card xem trước
    document.getElementById('previewCard').style.display = 'block';
    
    // Hiện loading, ẩn nội dung
    document.getElementById('loading').style.display = 'block';
    document.getElementById('attendanceDataContainer').style.display = 'none';
    document.getElementById('emptyState').style.display = 'none';
    document.getElementById('errorMessage').style.display = 'none';
    
    // Gọi API để lấy dữ liệu
    fetchAttendanceData(year, month);
    
    return false;
}

// Lấy dữ liệu chấm công từ API
function fetchAttendanceData(year, month) {
    // Tạo URL với tham số năm-tháng
    const monthStr = `${year}-${month}`;
    
    // Hiện loading
    document.getElementById('loading').style.display = 'block';
    
    fetch(EXPORT_ATTENDANCE_API_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            month: monthStr
        }),
    })
    .then(response => response.json())
    .then(data => {
        handleApiResponse(data, monthStr);
    })
    .catch(error => {
        showError('Không thể kết nối đến máy chủ. Vui lòng kiểm tra kết nối mạng và thử lại sau.');
        console.error('Lỗi kết nối:', error);
    });
}

// Xử lý phản hồi từ API
function handleApiResponse(response, monthStr) {
    document.getElementById('loading').style.display = 'none';
    
    if (response.error) {
        showError(response.error);
        return;
    }
    
    // Lưu tháng hiện tại để sử dụng khi xuất Excel
    currentMonth = monthStr;
    
    // Sử dụng dữ liệu từ phản hồi API
    attendanceData = response.data || [];
    originalData = JSON.parse(JSON.stringify(attendanceData));
    
    if (attendanceData.length === 0) {
        document.getElementById('emptyState').style.display = 'flex';
    } else {
        displayAttendanceData(attendanceData);
        document.getElementById('attendanceDataContainer').style.display = 'block';
        showToast('success', 'Thành công', 'Đã tải dữ liệu chấm công thành công');
    }
}

// Hiển thị dữ liệu chấm công
function displayAttendanceData(data) {
    const tbody = document.getElementById('attendanceData');
    tbody.innerHTML = '';
    
    data.forEach((item, index) => {
        const row = document.createElement('tr');
        
        // Thêm các cột dữ liệu
        row.innerHTML = `
            <td>${item.ID || ''}</td>
            <td>${item['Tên nhân viên'] || ''}</td>
            <td>${item.Ngày || ''}</td>
            <td>${item.Thứ || ''}</td>
            <td>${item['Thời gian vào'] || '-'}</td>
            <td>${item['Thời gian ra'] || '-'}</td>
            <td>${item['Tổng giờ công'] !== null ? item['Tổng giờ công'] : '-'}</td>
            <td>${item['Trừ KPI'] || ''}</td>
            <td>
                <input type="text" class="edit-note" 
                       data-index="${index}" 
                       value="${item['Ghi chú'] || ''}" 
                       placeholder="Thêm ghi chú...">
            </td>
        `;
        
        tbody.appendChild(row);
    });
    
    // Thêm sự kiện cho các ô input ghi chú
    document.querySelectorAll('.edit-note').forEach(input => {
        input.addEventListener('change', function() {
            const index = parseInt(this.getAttribute('data-index'));
            attendanceData[index]['Ghi chú'] = this.value;
            // Thông báo khi thay đổi ghi chú
            showToast('success', 'Đã cập nhật', 'Ghi chú đã được cập nhật');
        });
    });
}

// Hiển thị thông báo lỗi
function showError(message) {
    const errorElement = document.getElementById('errorMessage');
    document.getElementById('errorText').textContent = message;
    errorElement.style.display = 'flex';
    document.getElementById('attendanceDataContainer').style.display = 'none';
    document.getElementById('emptyState').style.display = 'none';
    
    // Hiển thị thông báo lỗi qua toast
    showToast('error', 'Lỗi', message);
}

// Xử lý sự kiện nút Tải Xuống
function handleDownload() {
    if (attendanceData.length === 0) {
        showToast('error', 'Lỗi', 'Không có dữ liệu để tải xuống');
        return;
    }
    
    showToast('success', 'Đang xử lý', 'Đang tạo tệp Excel...');
    
    // Gửi dữ liệu đã chỉnh sửa để tạo Excel
    fetch(GENERATE_EXCEL_API_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            data: attendanceData,
            month: currentMonth
        }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.file) {
            // Tạo Excel thành công, tiến hành tải xuống
            setTimeout(() => {
                window.location.href = `${DOWNLOAD_URL}?file=${encodeURIComponent(data.file)}`;
                showToast('success', 'Thành công', 'Đang tải xuống tệp Excel...');
            }, 500);
        } else {
            showToast('error', 'Lỗi', data.error || 'Không thể tạo tệp Excel');
        }
    })
    .catch(error => {
        showToast('error', 'Lỗi', 'Không thể kết nối đến máy chủ. Vui lòng thử lại sau.');
        console.error('Lỗi kết nối:', error);
    });
}

// Tạo dữ liệu mẫu để xem trước (chỉ trong phiên bản demo)
function generateSampleData(year, month) {
    const daysInMonth = new Date(year, month, 0).getDate();
    const data = [];
    
    const employees = [
        { id: 1, name: 'Nguyễn Văn A' },
        { id: 2, name: 'Trần Thị B' },
        { id: 3, name: 'Lê Văn C' },
        { id: 4, name: 'Phạm Thị D' }
    ];
    
    const weekdayMap = {
        0: 'Chủ nhật',
        1: 'Thứ 2',
        2: 'Thứ 3',
        3: 'Thứ 4',
        4: 'Thứ 5',
        5: 'Thứ 6',
        6: 'Thứ 7'
    };
    
    for (let employee of employees) {
        for (let day = 1; day <= daysInMonth; day++) {
            // Chỉ lấy ngày trong tuần (thứ 2 đến thứ 6)
            const currentDate = new Date(year, month - 1, day);
            const weekDay = currentDate.getDay();
            
            if (weekDay >= 1 && weekDay <= 5) { // Thứ 2 đến thứ 6
                const formattedDay = day.toString().padStart(2, '0');
                const dateStr = `${year}-${month}-${formattedDay}`;
                
                // Tạo giờ vào, giờ ra ngẫu nhiên
                const isPresent = Math.random() > 0.1; // 10% cơ hội nghỉ
                
                if (isPresent) {
                    // Random check-in time (7:30 - 8:30)
                    const checkInHour = Math.floor(Math.random() * 2) + 7;
                    const checkInMinute = Math.floor(Math.random() * 60);
                    const checkInTime = `${checkInHour.toString().padStart(2, '0')}:${checkInMinute.toString().padStart(2, '0')}:00`;
                    
                    // Random check-out time (17:00 - 18:30)
                    const checkOutHour = Math.floor(Math.random() * 2) + 17;
                    const checkOutMinute = Math.floor(Math.random() * 60);
                    const checkOutTime = `${checkOutHour.toString().padStart(2, '0')}:${checkOutMinute.toString().padStart(2, '0')}:00`;
                    
                    // Tính tổng giờ công và làm tròn đến 2 chữ số thập phân
                    const checkInDate = new Date(`${dateStr} ${checkInTime}`);
                    const checkOutDate = new Date(`${dateStr} ${checkOutTime}`);
                    const totalHours = Math.round(((checkOutDate - checkInDate) / 3600000) * 100) / 100;
                    
                    // Xác định ghi chú và trừ KPI
                    let note = '';
                    let kpiDeduction = '';
                    
                    // Đi muộn nếu vào sau 8:10
                    if (checkInHour === 8 && checkInMinute > 10) {
                        note = 'Đi muộn';
                        kpiDeduction = '1';
                    } 
                    // Về sớm nếu ra trước 17:30
                    else if (checkOutHour === 17 && checkOutMinute < 30) {
                        note = 'Về sớm';
                    }
                    
                    data.push({
                        'ID': employee.id,
                        'Tên nhân viên': employee.name,
                        'Ngày': dateStr,
                        'Thứ': weekdayMap[weekDay],
                        'Thời gian vào': checkInTime,
                        'Thời gian ra': checkOutTime,
                        'Tổng giờ công': totalHours,
                        'Trừ KPI': kpiDeduction,
                        'Ghi chú': note
                    });
                } else {
                    // Nghỉ
                    data.push({
                        'ID': employee.id,
                        'Tên nhân viên': employee.name,
                        'Ngày': dateStr,
                        'Thứ': weekdayMap[weekDay],
                        'Thời gian vào': null,
                        'Thời gian ra': null,
                        'Tổng giờ công': null,
                        'Trừ KPI': '',
                        'Ghi chú': 'Nghỉ'
                    });
                }
            }
        }
    }
    
    return data;
}