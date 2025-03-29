// Constants and variables
const BASE_URL = 'http://localhost:6123';
const ATTENDANCE_API_URL = `${BASE_URL}/get_attendance`;
const ALL_USERS_API_URL = `${BASE_URL}/get_all_users?without_face_embeddings=1`;
let allEmployees = [];
let attendanceData = [];
let isLoading = false;

// Cooldown mechanism
let refreshCooldown = false;
let refreshTimeout = null;
const COOLDOWN_TIME = 1500; // 1.5 seconds

// Constants for work hours
const STANDARD_CHECK_IN_TIME = '08:00';
const STANDARD_CHECK_OUT_TIME = '17:30';

// DOM Elements
const refreshBtn = document.getElementById('refreshBtn');
const loadingElement = document.getElementById('loading');
const contentElement = document.getElementById('content');
const attendanceDataElement = document.getElementById('attendanceData');
const errorContainer = document.getElementById('errorContainer');
const errorMessage = document.getElementById('errorMessage');
const lastUpdatedElement = document.getElementById('lastUpdated');
const totalEmployeesElement = document.getElementById('totalEmployees');
const searchInput = document.getElementById('searchInput');
const emptyState = document.getElementById('emptyState');

// Helper functions
function formatTime(timeString) {
    return timeString || '---';
}

function handleRefreshClick(event) {
    if (event) event.preventDefault();
    
    if (refreshCooldown) return;
    
    if (refreshTimeout) {
        clearTimeout(refreshTimeout);
    }
    
    refreshCooldown = true;
    refreshBtn.style.transform = 'scale(0.95)';
    
    fetchAllData();
    
    refreshTimeout = setTimeout(() => {
        refreshCooldown = false;
        refreshBtn.style.transform = 'scale(1)';
    }, COOLDOWN_TIME);
}

function getAttendanceStatus(checkInTime, checkOutTime) {
    if (!checkInTime) {
        return '<span class="status status-absent">Chưa chấm công</span>';
    }
    
    const isLate = checkInTime > STANDARD_CHECK_IN_TIME;
    
    if (checkOutTime) {
        const isEarly = checkOutTime < STANDARD_CHECK_OUT_TIME;
        
        if (isLate && isEarly) {
            return '<span class="status status-late">Đi muộn & Về sớm</span>';
        } else if (isLate) {
            return '<span class="status status-late">Đi muộn</span>';
        } else if (isEarly) {
            return '<span class="status status-early">Về sớm</span>';
        } else {
            return '<span class="status status-present">Đúng giờ</span>';
        }
    } else {
        return isLate 
            ? '<span class="status status-late">Đi muộn</span>'
            : '<span class="status status-present">Đang làm việc</span>';
    }
}

function updateLastUpdated() {
    const now = new Date();
    const hours = now.getHours().toString().padStart(2, '0');
    const minutes = now.getMinutes().toString().padStart(2, '0');
    
    // Lấy tên thứ trong tuần
    const weekdayOptions = { weekday: 'long' };
    const weekday = now.toLocaleDateString('vi-VN', weekdayOptions);
    
    // Lấy ngày, tháng, năm
    const day = now.getDate();
    const month = now.getMonth() + 1; // getMonth() trả về 0-11
    const year = now.getFullYear();
    
    // Ghép chuỗi theo định dạng yêu cầu
    lastUpdatedElement.textContent = `Cập nhật lúc ${hours}:${minutes} ${weekday}, ${day} tháng ${month}, ${year}`;
}

function showLoading() {
    isLoading = true;
    loadingElement.style.display = 'block';
    contentElement.style.display = 'none';
    refreshBtn.disabled = true;
    refreshBtn.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i><span class="hide-on-mobile">Đang tải...</span>';
}

function hideLoading() {
    isLoading = false;
    loadingElement.style.display = 'none';
    contentElement.style.display = 'block';
    refreshBtn.disabled = false;
    refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i><span class="hide-on-mobile">Làm mới dữ liệu</span>';
}

function showError(message) {
    errorMessage.textContent = message;
    errorContainer.style.display = 'flex';
    setTimeout(() => {
        errorContainer.classList.add('pulse');
        setTimeout(() => {
            errorContainer.classList.remove('pulse');
        }, 2000);
    }, 100);
}

function hideError() {
    errorContainer.style.display = 'none';
}

function renderAttendanceData(data) {
    if (!data || data.length === 0) {
        attendanceDataElement.innerHTML = '';
        emptyState.style.display = 'flex';
        totalEmployeesElement.textContent = `Tổng số: 0 nhân viên`;
        return;
    }

    emptyState.style.display = 'none';
    
    // Apply fade effect
    attendanceDataElement.style.opacity = '0.3';
    
    // Render data
    attendanceDataElement.innerHTML = data.map(employee => {
        const checkInStyle = employee.check_in_time && employee.check_in_time > STANDARD_CHECK_IN_TIME
            ? 'background-color:rgba(255,149,0,0.1);color:var(--late)'
            : '';
            
        const checkInIcon = employee.check_in_time && employee.check_in_time > STANDARD_CHECK_IN_TIME
            ? ' <i class="fas fa-exclamation-circle"></i>'
            : '';
            
        const checkOutStyle = employee.check_out_time && employee.check_out_time < STANDARD_CHECK_OUT_TIME
            ? 'background-color:rgba(88,86,214,0.1);color:var(--early)'
            : '';
            
        const checkOutIcon = employee.check_out_time && employee.check_out_time < STANDARD_CHECK_OUT_TIME
            ? ' <i class="fas fa-exclamation-circle"></i>'
            : '';
            
        return `
            <tr>
                <td>${employee.name}</td>
                <td><span class="badge department-badge">${employee.department || 'N/A'}</span></td>
                <td>
                    ${employee.check_in_time
                        ? `<div class="time-badge" style="${checkInStyle}">
                            <i class="fas fa-sign-in-alt"></i> ${formatTime(employee.check_in_time)}${checkInIcon}
                           </div>`
                        : '---'}
                </td>
                <td>
                    ${employee.check_out_time
                        ? `<div class="time-badge" style="${checkOutStyle}">
                            <i class="fas fa-sign-out-alt"></i> ${formatTime(employee.check_out_time)}${checkOutIcon}
                           </div>`
                        : '---'}
                </td>
                <td>${getAttendanceStatus(employee.check_in_time, employee.check_out_time)}</td>
            </tr>
        `;
    }).join('');
    
    // Fade in after rendering
    setTimeout(() => {
        attendanceDataElement.style.opacity = '1';
    }, 50);
    
    totalEmployeesElement.textContent = `Tổng số: ${data.length} nhân viên`;
}

async function fetchAllData() {
    if (isLoading) return;
    
    showLoading();
    hideError();
    
    try {
        // Fetch both APIs in parallel
        const [usersResponse, attendanceResponse] = await Promise.all([
            fetch(ALL_USERS_API_URL),
            fetch(ATTENDANCE_API_URL)
        ]);
        
        if (!usersResponse.ok) {
            throw new Error(`Lỗi khi lấy dữ liệu nhân viên: ${usersResponse.status} ${usersResponse.statusText}`);
        }
        
        if (!attendanceResponse.ok) {
            throw new Error(`Lỗi khi lấy dữ liệu chấm công: ${attendanceResponse.status} ${attendanceResponse.statusText}`);
        }
        
        // Parse responses
        const users = await usersResponse.json();
        attendanceData = await attendanceResponse.json();
        
        // Create a map of attendance data for quick lookups
        const attendanceMap = Object.fromEntries(
            attendanceData.map(record => [record.name, record])
        );
        
        // Combine the data
        allEmployees = users.map(user => ({
            name: user.full_name,
            department: user.department_id,
            check_in_time: attendanceMap[user.full_name]?.check_in_time || null,
            check_out_time: attendanceMap[user.full_name]?.check_out_time || null
        }));
        
        // Sort data
        allEmployees.sort((a, b) => {
            if (a.check_in_time && b.check_in_time) {
                return a.check_in_time.localeCompare(b.check_in_time);
            }
            if (a.check_in_time) return -1;
            if (b.check_in_time) return 1;
            return a.name.localeCompare(b.name);
        });
        
        renderAttendanceData(allEmployees);
        updateLastUpdated();
        createFilters();
        
    } catch (error) {
        console.error('Lỗi khi lấy dữ liệu:', error);
        showError(`Không thể lấy dữ liệu: ${error.message}`);
        renderAttendanceData([]);
    } finally {
        hideLoading();
    }
}

function applyFilters() {
    const searchTerm = searchInput.value.toLowerCase().trim();
    const departmentFilter = document.getElementById('departmentFilter');
    const statusFilter = document.getElementById('statusFilter');
    
    if (!departmentFilter || !statusFilter) return;
    
    const selectedDepartment = departmentFilter.value;
    const selectedStatus = statusFilter.value;
    
    const filteredData = allEmployees.filter(employee => {
        // Apply search filter
        const matchesSearch = !searchTerm || employee.name.toLowerCase().includes(searchTerm);
        
        // Apply department filter
        const matchesDepartment = !selectedDepartment || employee.department === selectedDepartment;
        
        // Apply status filter
        let matchesStatus = true;
        if (selectedStatus) {
            const hasCheckIn = !!employee.check_in_time;
            const hasCheckOut = !!employee.check_out_time;
            const isLate = hasCheckIn && employee.check_in_time > STANDARD_CHECK_IN_TIME;
            const isEarly = hasCheckOut && employee.check_out_time < STANDARD_CHECK_OUT_TIME;
            
            switch (selectedStatus) {
                case 'present':
                    matchesStatus = hasCheckIn && !isLate && (!hasCheckOut || !isEarly);
                    break;
                case 'late':
                    matchesStatus = isLate;
                    break;
                case 'early':
                    matchesStatus = isEarly;
                    break;
                case 'absent':
                    matchesStatus = !hasCheckIn;
                    break;
            }
        }
        
        return matchesSearch && matchesDepartment && matchesStatus;
    });
    
    renderAttendanceData(filteredData);
}

function createFilters() {
    // Remove existing filters if any
    const existingFilters = document.querySelector('.filters-container');
    if (existingFilters) {
        existingFilters.remove();
    }
    
    // Create department filter
    const departmentFilter = document.createElement('select');
    departmentFilter.id = 'departmentFilter';
    departmentFilter.className = 'filter-select';
    
    // Create a set of unique departments
    const departments = new Set(
        allEmployees
            .filter(emp => emp.department)
            .map(emp => emp.department)
    );
    
    // Add options
    let deptOptions = '<option value="">Tất cả phòng ban</option>';
    departments.forEach(dept => {
        deptOptions += `<option value="${dept}">${dept}</option>`;
    });
    departmentFilter.innerHTML = deptOptions;
    
    const statusFilter = document.createElement('select');
    statusFilter.id = 'statusFilter';
    statusFilter.className = 'filter-select';
    statusFilter.innerHTML = `
        <option value="">Tất cả trạng thái</option>
        <option value="present">Đúng giờ</option>
        <option value="late">Đi muộn</option>
        <option value="early">Về sớm</option>
        <option value="absent">Chưa chấm công</option>
    `;
    
    // Filters container
    const filtersContainer = document.createElement('div');
    filtersContainer.className = 'filters-container';
    filtersContainer.appendChild(document.createTextNode('Lọc theo: '));
    filtersContainer.appendChild(departmentFilter);
    filtersContainer.appendChild(statusFilter);
    
    document.querySelector('.search-container').appendChild(filtersContainer);
    
    // Event listeners for filters
    departmentFilter.addEventListener('change', applyFilters);
    statusFilter.addEventListener('change', applyFilters);
}

// Event Listeners
refreshBtn.addEventListener('click', handleRefreshClick);
searchInput.addEventListener('input', applyFilters); // Direct use of applyFilters

// Initial data fetch
fetchAllData();

// Update time every minute
setInterval(updateLastUpdated, 60000);