// Các biến và hằng số toàn cục
const attendanceTable = document.getElementById('attendance-data');
const lastUpdatedTime = document.getElementById('last-updated-time');
const refreshButton = document.querySelector('.refresh-btn');
const searchInput = document.querySelector('.search-input');
const loadingElement = document.querySelector('.loading');

// Hàm mẫu để lấy dữ liệu chấm công (trong trường hợp thực tế sẽ thay thế bằng API)
async function fetchAttendanceData() {
    // Hiển thị trạng thái đang tải
    showLoading(true);
    
    try {
        // Mô phỏng việc gọi API với setTimeout
        return new Promise((resolve) => {
            setTimeout(() => {
                // Dữ liệu mẫu
                const sampleData = [
                    {
                        id: 'NV001',
                        name: 'Nguyễn Văn A',
                        department: 'Kỹ thuật',
                        timeIn: '08:00',
                        timeOut: '17:30',
                        status: 'present'
                    },
                    {
                        id: 'NV002',
                        name: 'Trần Thị B',
                        department: 'Nhân sự',
                        timeIn: '08:45',
                        timeOut: '17:30',
                        status: 'late'
                    },
                    {
                        id: 'NV003',
                        name: 'Lê Văn C',
                        department: 'Kế toán',
                        timeIn: '08:10',
                        timeOut: '16:30',
                        status: 'early'
                    },
                    {
                        id: 'NV004',
                        name: 'Phạm Thị D',
                        department: 'Marketing',
                        timeIn: null,
                        timeOut: null,
                        status: 'absent'
                    }
                ];
                resolve(sampleData);
            }, 1000); // Giả lập độ trễ mạng 1 giây
        });
    } catch (error) {
        console.error('Lỗi khi tải dữ liệu:', error);
        return [];
    } finally {
        showLoading(false);
    }
}

// Hiển thị hoặc ẩn trạng thái đang tải
function showLoading(isLoading) {
    if (isLoading) {
        loadingElement.style.display = 'block';
        if (attendanceTable) {
            attendanceTable.style.display = 'none';
        }
    } else {
        loadingElement.style.display = 'none';
        if (attendanceTable) {
            attendanceTable.style.display = 'table-row-group';
        }
    }
}

// Cập nhật thời gian cập nhật gần nhất
function updateLastUpdatedTime() {
    const now = new Date();
    const formattedDate = `${now.getDate().toString().padStart(2, '0')}/${(now.getMonth() + 1).toString().padStart(2, '0')}/${now.getFullYear()} ${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
    lastUpdatedTime.textContent = formattedDate;
}

// Tạo HTML cho từng dòng dữ liệu
function createAttendanceRow(employee) {
    const tr = document.createElement('tr');
    
    // Tạo chuỗi HTML cho dòng
    tr.innerHTML = `
        <td>${employee.id}</td>
        <td>${employee.name}</td>
        <td><span class="badge department-badge">${employee.department}</span></td>
        <td>${employee.timeIn ? `<span class="time-badge"><i class="fas fa-sign-in-alt"></i> ${employee.timeIn}</span>` : '-'}</td>
        <td>${employee.timeOut ? `<span class="time-badge"><i class="fas fa-sign-out-alt"></i> ${employee.timeOut}</span>` : '-'}</td>
        <td>
            <span class="status status-${employee.status}">
                ${getStatusText(employee.status)}
            </span>
        </td>
    `;
    
    return tr;
}

// Chuyển đổi mã trạng thái thành văn bản hiển thị
function getStatusText(status) {
    switch (status) {
        case 'present':
            return 'Có mặt';
        case 'absent':
            return 'Vắng mặt';
        case 'late':
            return 'Đi muộn';
        case 'early':
            return 'Về sớm';
        default:
            return 'Không xác định';
    }
}

// Cập nhật các số liệu thống kê
function updateStatistics(data) {
    const presentCount = data.filter(emp => emp.status === 'present').length;
    const absentCount = data.filter(emp => emp.status === 'absent').length;
    const lateCount = data.filter(emp => emp.status === 'late').length;
    const earlyCount = data.filter(emp => emp.status === 'early').length;
    
    document.querySelector('.status-present').textContent = `Có mặt: ${presentCount}`;
    document.querySelector('.status-absent').textContent = `Vắng mặt: ${absentCount}`;
    document.querySelector('.status-late').textContent = `Đi muộn: ${lateCount}`;
    document.querySelector('.status-early').textContent = `Về sớm: ${earlyCount}`;
}

// Tạo bảng dữ liệu
async function renderAttendanceTable() {
    const data = await fetchAttendanceData();
    
    if (!data || data.length === 0) {
        attendanceTable.innerHTML = `
            <tr>
                <td colspan="6">
                    <div class="empty-state">
                        <i class="fas fa-clipboard-list empty-icon"></i>
                        <p>Không có dữ liệu chấm công</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    // Xóa tất cả dữ liệu hiện tại
    attendanceTable.innerHTML = '';
    
    // Thêm từng dòng dữ liệu mới
    data.forEach(employee => {
        const row = createAttendanceRow(employee);
        attendanceTable.appendChild(row);
    });
    
    // Cập nhật thống kê
    updateStatistics(data);
    
    // Cập nhật thời gian
    updateLastUpdatedTime();
}

// Xử lý tìm kiếm
function handleSearch() {
    const searchTerm = searchInput.value.toLowerCase();
    const rows = attendanceTable.querySelectorAll('tr');
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        if (text.includes(searchTerm)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

// Khởi tạo các sự kiện
function initEvents() {
    // Sự kiện nút làm mới
    refreshButton.addEventListener('click', renderAttendanceTable);
    
    // Sự kiện tìm kiếm
    searchInput.addEventListener('input', handleSearch);
}

// Khởi tạo ứng dụng
function initApp() {
    renderAttendanceTable();
    initEvents();
}

// Chạy khi trang đã tải xong
document.addEventListener('DOMContentLoaded', initApp);