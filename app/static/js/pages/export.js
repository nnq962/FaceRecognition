import API from "../core/api.js";
import { showToast } from "../utils/toast.js";


class AttendanceReportManager {
    constructor() {
        this.attendanceData = [];
        this.filteredData = [];
        this.currentPage = 1;
        this.pageSize = 25;
        this.users = [];
        this.rooms = [];
        this.currentFilters = {
            month: '',
            user: '',
            room: ''
        };

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setDefaultMonth();
        this.loadData();
    }

    setupEventListeners() {
        // Month filter - tự động tải dữ liệu khi thay đổi
        const monthFilter = document.getElementById('monthFilter');
        if (monthFilter) {
            monthFilter.addEventListener('change', () => this.handleMonthChange());
        }

        // User filter - tự động áp dụng filter khi thay đổi
        const userFilter = document.getElementById('userFilter');
        if (userFilter) {
            userFilter.addEventListener('change', () => this.applyFilters());
        }

        // Room filter - tự động áp dụng filter khi thay đổi
        const roomFilter = document.getElementById('roomFilter');
        if (roomFilter) {
            roomFilter.addEventListener('change', () => this.applyFilters());
        }

        // Loại bỏ event listener cho apply button
        // const applyBtn = document.getElementById('applyFiltersBtn');

        const resetBtn = document.getElementById('resetFiltersBtn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetFilters());
        }

        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshData());
        }

        const exportBtn = document.getElementById('exportBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportToExcel());
        }

        // Pagination
        const pageSizeSelect = document.getElementById('pageSizeSelect');
        if (pageSizeSelect) {
            pageSizeSelect.addEventListener('change', () => this.handlePageSizeChange());
        }

        const prevBtn = document.getElementById('prevPageBtn');
        if (prevBtn) {
            prevBtn.addEventListener('click', () => this.goToPreviousPage());
        }

        const nextBtn = document.getElementById('nextPageBtn');
        if (nextBtn) {
            nextBtn.addEventListener('click', () => this.goToNextPage());
        }
    }

    setDefaultMonth() {
        const monthFilter = document.getElementById('monthFilter');
        if (monthFilter) {
            const now = new Date();
            const currentMonth = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0');
            monthFilter.value = currentMonth;
            this.currentFilters.month = currentMonth;
        }
    }

    handleMonthChange() {
        const monthFilter = document.getElementById('monthFilter');
        if (monthFilter) {
            this.currentFilters.month = monthFilter.value;
            if (monthFilter.value) {
                // Tự động tải dữ liệu khi thay đổi tháng
                this.loadData();
            } else {
                this.showEmptyState();
            }
        }
    }

    async loadData() {
        if (!this.currentFilters.month) {
            showToast('Cảnh báo', 'Vui lòng chọn tháng', 'warning');
            return;
        }

        try {
            this.showLoading();
            showToast('Đang tải dữ liệu...', 'Vui lòng chờ trong giây lát', 'info');

            const response = await API.exportAttendance(this.currentFilters.month);

            if (response.status === 'success') {
                this.attendanceData = response.data.attendance_records || [];
                this.updateSummaryStats(response.data);

                // Lấy danh sách phòng từ API response
                this.extractUsersAndRooms(response.data);

                this.populateFilterDropdowns();
                this.applyFilters();

                showToast('Thành công', 'Đã tải dữ liệu thành công', 'success');
            } else {
                throw new Error(response.message || 'Không thể tải dữ liệu');
            }

        } catch (error) {
            showToast('Lỗi', 'Không thể tải dữ liệu: ' + error.message, 'error');
            this.showEmptyState();
        }
    }

    extractUsersAndRooms(responseData) {
        const userSet = new Set();
        const roomSet = new Set();

        this.attendanceData.forEach(record => {
            // Extract users
            if (record.ID && record['Tên nhân viên']) {
                userSet.add(JSON.stringify({
                    id: record.ID,
                    name: record['Tên nhân viên'],
                    room: record['Phòng ban'] || null
                }));
            }

            // Extract rooms từ dữ liệu
            if (record['Phòng ban']) {
                roomSet.add(record['Phòng ban']);
            }
        });

        this.users = Array.from(userSet).map(userStr => JSON.parse(userStr));

        // Ưu tiên dùng danh sách phòng từ API response
        this.rooms = responseData.rooms || Array.from(roomSet);

        // Fallback nếu không có dữ liệu phòng
        if (this.rooms.length === 0) {
            showToast('Lỗi', 'Không có dữ liệu phòng ban', 'error');
        }
    }

    populateFilterDropdowns() {
        // User filter
        const userSelect = document.getElementById('userFilter');
        if (userSelect) {
            userSelect.innerHTML = '<option value="">Tất cả nhân viên</option>';

            this.users.forEach(user => {
                const option = document.createElement('option');
                option.value = user.id;
                option.textContent = `${user.id} - ${user.name}`;
                userSelect.appendChild(option);
            });
        }

        // Room filter
        const roomSelect = document.getElementById('roomFilter');
        if (roomSelect) {
            roomSelect.innerHTML = '<option value="">Tất cả phòng ban</option>';

            this.rooms.forEach(room => {
                const option = document.createElement('option');
                option.value = room;
                option.textContent = room;
                roomSelect.appendChild(option);
            });
        }
    }

    applyFilters() {
        const userFilter = document.getElementById('userFilter');
        const roomFilter = document.getElementById('roomFilter');

        const userValue = userFilter ? userFilter.value : '';
        const roomValue = roomFilter ? roomFilter.value : '';

        this.filteredData = this.attendanceData.filter(record => {
            const matchUser = !userValue || record.ID === userValue;
            const matchRoom = !roomValue || record['Phòng ban'] === roomValue;
            return matchUser && matchRoom;
        });

        this.currentPage = 1;
        this.renderTable();
        this.renderPagination();
    }

    resetFilters() {
        const userFilter = document.getElementById('userFilter');
        const roomFilter = document.getElementById('roomFilter');

        if (userFilter) userFilter.value = '';
        if (roomFilter) roomFilter.value = '';

        this.setDefaultMonth();
        // Tự động tải lại dữ liệu sau khi reset
        this.loadData();
        showToast('Thành công', 'Đã đặt lại bộ lọc', 'success');
    }

    refreshData() {
        if (this.currentFilters.month) {
            this.loadData();
        }
        showToast('Thành công', 'Đã làm mới dữ liệu', 'success');
    }

    updateSummaryStats(data) {
        const elements = {
            totalUsers: document.getElementById('totalUsers'),
            workingDays: document.getElementById('workingDays'),
            totalRecords: document.getElementById('totalRecords'),
            approvedReports: document.getElementById('approvedReports')
        };

        if (elements.totalUsers) elements.totalUsers.textContent = data.total_users || 0;
        if (elements.workingDays) elements.workingDays.textContent = data.working_days || 0;
        if (elements.totalRecords) elements.totalRecords.textContent = data.total_records || 0;
        if (elements.approvedReports) elements.approvedReports.textContent = data.approved_reports_integrated || 0;
    }

    showLoading() {
        const elements = {
            loading: document.getElementById('loadingState'),
            empty: document.getElementById('emptyState'),
            table: document.getElementById('tableContainer'),
            pagination: document.getElementById('paginationContainer')
        };

        if (elements.loading) elements.loading.classList.remove('hidden');
        if (elements.empty) elements.empty.classList.add('hidden');
        if (elements.table) elements.table.classList.add('hidden');
        if (elements.pagination) elements.pagination.classList.add('hidden');
    }

    showEmptyState() {
        const elements = {
            loading: document.getElementById('loadingState'),
            empty: document.getElementById('emptyState'),
            table: document.getElementById('tableContainer'),
            pagination: document.getElementById('paginationContainer')
        };

        if (elements.loading) elements.loading.classList.add('hidden');
        if (elements.empty) elements.empty.classList.remove('hidden');
        if (elements.table) elements.table.classList.add('hidden');
        if (elements.pagination) elements.pagination.classList.add('hidden');
    }

    renderTable() {
        const tableBody = document.getElementById('tableBody');
        if (!tableBody) return;

        const startIndex = (this.currentPage - 1) * this.pageSize;
        const endIndex = startIndex + this.pageSize;
        const pageData = this.filteredData.slice(startIndex, endIndex);

        if (pageData.length === 0) {
            this.showEmptyState();
            return;
        }

        // Show table
        const elements = {
            loading: document.getElementById('loadingState'),
            empty: document.getElementById('emptyState'),
            table: document.getElementById('tableContainer'),
            pagination: document.getElementById('paginationContainer')
        };

        if (elements.loading) elements.loading.classList.add('hidden');
        if (elements.empty) elements.empty.classList.add('hidden');
        if (elements.table) elements.table.classList.remove('hidden');
        if (elements.pagination) elements.pagination.classList.remove('hidden');

        // Clear and populate table
        tableBody.innerHTML = '';
        pageData.forEach(record => {
            const row = this.createTableRow(record);
            tableBody.appendChild(row);
        });

        // Update record count
        const recordCount = document.getElementById('recordCount');
        if (recordCount) {
            recordCount.textContent = `${this.filteredData.length} bản ghi`;
        }
    }

    createTableRow(record) {
        const row = document.createElement('tr');
        row.className = 'hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors';

        const noteClass = (record['Ghi chú'] && record['Ghi chú'] !== 'Nghỉ')
            ? 'text-yellow-600 dark:text-yellow-400' : 'text-gray-500 dark:text-gray-400';

        const fineClass = (record['Phạt tiền'] && record['Phạt tiền'] > 0)
            ? 'text-red-600 dark:text-red-400 font-medium' : 'text-gray-900 dark:text-white';

        row.innerHTML = `
            <td class="px-3 py-4 text-sm text-gray-900 dark:text-white truncate text-left">
                ${record.ID || '--'}
            </td>
            <td class="px-3 py-4 text-sm text-gray-900 dark:text-white truncate text-left" title="${record['Tên nhân viên'] || '--'}">
                ${record['Tên nhân viên'] || '--'}
            </td>
            <td class="px-3 py-4 text-sm text-gray-900 dark:text-white whitespace-nowrap text-left">
                ${this.formatDate(record['Ngày']) || '--'}
            </td>
            <td class="px-3 py-4 text-sm text-gray-900 dark:text-white whitespace-nowrap text-left">
                ${record['Thứ'] || '--'}
            </td>
            <td class="px-3 py-4 text-sm text-gray-900 dark:text-white whitespace-nowrap text-left">
                ${record['Thời gian vào'] || '--'}
            </td>
            <td class="px-3 py-4 text-sm text-gray-900 dark:text-white whitespace-nowrap text-left">
                ${record['Thời gian ra'] || '--'}
            </td>
            <td class="px-3 py-4 text-sm text-gray-900 dark:text-white whitespace-nowrap text-left">
                ${record['Tổng giờ công'] || '--'}
            </td>
            <td class="px-3 py-4 text-sm whitespace-nowrap text-left ${fineClass}">
                ${this.formatCurrency(record['Phạt tiền']) || '--'}
            </td>
            <td class="px-3 py-4 text-sm truncate text-left ${noteClass}" title="${record['Ghi chú'] || '--'}">
                ${record['Ghi chú'] || '--'}
            </td>
        `;
        return row;
    }

    formatDate(dateStr) {
        if (!dateStr) return '--';
        try {
            const date = new Date(dateStr);
            const day = String(date.getDate()).padStart(2, '0');
            const month = String(date.getMonth() + 1).padStart(2, '0'); // Lưu ý: tháng bắt đầu từ 0
            const year = date.getFullYear();
            return `${day}/${month}/${year}`;
        } catch {
            return dateStr;
        }
    }


    formatCurrency(amount) {
        if (!amount || amount === 0) return '0';
        return `${amount}K`;
    }


    renderPagination() {
        const totalPages = Math.ceil(this.filteredData.length / this.pageSize);

        // Update info
        const totalRecordsText = document.getElementById('totalRecordsText');
        if (totalRecordsText) {
            totalRecordsText.textContent = this.filteredData.length;
        }

        const pageSizeSelect = document.getElementById('pageSizeSelect');
        if (pageSizeSelect) {
            pageSizeSelect.value = this.pageSize;
        }

        // Update buttons
        const prevBtn = document.getElementById('prevPageBtn');
        const nextBtn = document.getElementById('nextPageBtn');

        if (prevBtn) prevBtn.disabled = this.currentPage <= 1;
        if (nextBtn) nextBtn.disabled = this.currentPage >= totalPages;

        this.renderPageNumbers(totalPages);
    }

    renderPageNumbers(totalPages) {
        const container = document.getElementById('pageNumbers');
        if (!container) return;

        container.innerHTML = '';

        const maxPages = 5;
        let start = Math.max(1, this.currentPage - Math.floor(maxPages / 2));
        let end = Math.min(totalPages, start + maxPages - 1);

        if (end - start + 1 < maxPages) {
            start = Math.max(1, end - maxPages + 1);
        }

        for (let i = start; i <= end; i++) {
            const btn = document.createElement('button');
            btn.textContent = i;
            btn.className = `px-3 py-2 rounded-lg text-sm font-medium transition-colors ${i === this.currentPage
                ? 'bg-blue-600 text-white'
                : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'
                }`;

            btn.addEventListener('click', () => this.goToPage(i));
            container.appendChild(btn);
        }
    }

    goToPage(page) {
        this.currentPage = page;
        this.renderTable();
        this.renderPagination();
    }

    goToPreviousPage() {
        if (this.currentPage > 1) {
            this.goToPage(this.currentPage - 1);
        }
    }

    goToNextPage() {
        const totalPages = Math.ceil(this.filteredData.length / this.pageSize);
        if (this.currentPage < totalPages) {
            this.goToPage(this.currentPage + 1);
        }
    }

    handlePageSizeChange() {
        const pageSizeSelect = document.getElementById('pageSizeSelect');
        if (pageSizeSelect) {
            this.pageSize = parseInt(pageSizeSelect.value);
            this.currentPage = 1;
            this.renderTable();
            this.renderPagination();
        }
    }

    async exportToExcel() {
        if (!this.currentFilters.month) {
            showToast('Cảnh báo', 'Vui lòng chọn tháng trước khi xuất', 'warning');
            return;
        }

        if (!this.filteredData || this.filteredData.length === 0) {
            showToast('Cảnh báo', 'Không có dữ liệu để xuất', 'warning');
            return;
        }

        const exportBtn = document.getElementById('exportBtn');
        if (!exportBtn) return;

        try {
            // Hiển thị trạng thái loading
            exportBtn.disabled = true;
            exportBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Đang tạo Excel...';

            // Sử dụng filteredData thay vì attendanceData để xuất đúng dữ liệu đã lọc
            const dataToExport = this.filteredData;

            // Gọi API để tạo và tải Excel
            await API.exportAndDownloadExcel(dataToExport, this.currentFilters.month);

            showToast('Thành công', 'Đã tải file Excel thành công', 'success');

        } catch (error) {
            showToast('Lỗi', 'Không thể xuất file Excel: ' + error.message, 'error');
        } finally {
            // Khôi phục trạng thái button
            exportBtn.disabled = false;
            exportBtn.innerHTML = '<i class="fas fa-download mr-2"></i>Xuất Excel';
        }
    }

    // Method backup để xuất CSV (giữ lại phòng trường hợp cần)
    downloadAsCSV() {
        const headers = ['ID', 'Tên nhân viên', 'Ngày', 'Thứ', 'Thời gian vào', 'Thời gian ra', 'Tổng giờ công', 'Phạt tiền', 'Ghi chú'];

        const rows = this.filteredData.map(record => [
            record.ID || '',
            `"${record['Tên nhân viên'] || ''}"`,
            record['Ngày'] || '',
            `"${record['Thứ'] || ''}"`,
            record['Thời gian vào'] || '',
            record['Thời gian ra'] || '',
            record['Tổng giờ công'] || '',
            record['Phạt tiền'] || '',
            `"${record['Ghi chú'] || ''}"`
        ].join(','));

        const csvContent = [headers.join(','), ...rows].join('\n');
        const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });

        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `attendance_${this.currentFilters.month}.csv`;
        link.style.display = 'none';

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);
    }

    // Method xuất Excel với tất cả dữ liệu (không lọc)
    async exportAllToExcel() {
        if (!this.currentFilters.month) {
            showToast('Cảnh báo', 'Vui lòng chọn tháng trước khi xuất', 'warning');
            return;
        }

        if (!this.attendanceData || this.attendanceData.length === 0) {
            showToast('Cảnh báo', 'Không có dữ liệu để xuất', 'warning');
            return;
        }

        try {
            // Sử dụng attendanceData để xuất tất cả dữ liệu
            await API.exportAndDownloadExcel(this.attendanceData, this.currentFilters.month);
            showToast('Thành công', 'Đã tải file Excel với tất cả dữ liệu', 'success');
        } catch (error) {
            showToast('Lỗi', 'Không thể xuất file Excel: ' + error.message, 'error');
        }
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    new AttendanceReportManager();
});