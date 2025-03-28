// Biến để lưu dữ liệu
let attendanceData = [];
let originalData = [];
let currentFilePath = '';
let currentMonth = '';  // Thêm biến này
const BASE_URL = 'http://localhost:6123';
const EXPORT_ATTENDANCE_API_URL = `${BASE_URL}/get_all_users?without_face_embeddings=1`;
const GENERATE_EXCEL_API_URL = `${BASE_URL}/api/generate_excel`;
const DOWNLOAD_URL = `${BASE_URL}/download`;

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
    const options = { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    document.getElementById('currentDateTime').textContent = now.toLocaleDateString('vi-VN', options);
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
    
    const year = document.getElementById('yearSelect').value;
    const month = document.getElementById('monthSelect').value;
    
    if (!year || !month) {
        alert('Vui lòng chọn cả năm và tháng!');
        return;
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
}

// Lấy dữ liệu chấm công từ API
function fetchAttendanceData(year, month) {
    // Tạo URL với tham số năm-tháng
    const monthStr = `${year}-${month}`;
    
    // Hiện loading
    document.getElementById('loading').style.display = 'block';
    
    fetch(ATTENDANCE_API_URL, {
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
        showError('Không thể kết nối đến máy chủ: ' + error.message);
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
        });
    });
}

// Đã xóa hàm handleSaveChanges()

// Xử lý sự kiện nút Tải Xuống
function handleDownload() {
    if (attendanceData.length === 0) {
        showError('Không có dữ liệu để tải xuống');
        return;
    }
    
    showSuccessToast('Đang tạo tệp Excel...');
    
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
            window.location.href = `${DOWNLOAD_URL}?file=${encodeURIComponent(data.file)}`;
            showSuccessToast('Đang tải xuống tệp Excel...');
        } else {
            showError(data.error || 'Không thể tạo tệp Excel');
        }
    })
    .catch(error => {
        showError('Lỗi kết nối: ' + error.message);
    });
}

// Hiển thị thông báo lỗi
function showError(message) {
    const errorElement = document.getElementById('errorMessage');
    document.getElementById('errorText').textContent = message;
    errorElement.style.display = 'flex';
    document.getElementById('attendanceDataContainer').style.display = 'none';
    document.getElementById('emptyState').style.display = 'none';
}

// Hiển thị thông báo thành công
function showSuccessToast(message) {
    // Xóa toast cũ nếu có
    const existingToast = document.querySelector('.success-toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    // Tạo toast mới
    const toast = document.createElement('div');
    toast.className = 'success-toast';
    toast.innerHTML = `
        <i class="fas fa-check-circle"></i>
        <span>${message}</span>
    `;
    
    document.body.appendChild(toast);
    
    // Tự động xóa sau 3 giây
    setTimeout(() => {
        toast.remove();
    }, 3000);
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