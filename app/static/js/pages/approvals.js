// approvals.js - JavaScript cho trang phê duyệt báo cáo
import API from "../core/api.js";
import { showToast } from "../utils/toast.js";
import User from "../utils/user.js";

class ReportsApproval {
    constructor() {
        this.reports = [];
        this.currentFilters = {
            report_type: 'all',
            status: 'all',
            from_date: '',
            to_date: ''
        };
        this.init();
    }

    /**
     * Khởi tạo ứng dụng
     */
    init() {
        this.toggleDateFilter();
        this.bindEvents();
        this.loadReports();
    }

    /**
     * Gắn các event listeners
     */
    bindEvents() {
        // Report type tabs
        document.querySelectorAll('[data-report-type]').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchReportType(e.target.dataset.reportType);
            });
        });

        // Status filter
        const statusFilter = document.getElementById('statusFilter');
        if (statusFilter) {
            statusFilter.addEventListener('change', () => {
                this.currentFilters.status = statusFilter.value;
                this.loadReports();
            });
        }

        // Date filters
        const fromDateInput = document.getElementById('fromDate');
        if (fromDateInput) {
            fromDateInput.addEventListener('change', () => {
                this.currentFilters.from_date = fromDateInput.value;
                this.loadReports();
            });
        }

        const toDateInput = document.getElementById('toDate');
        if (toDateInput) {
            toDateInput.addEventListener('change', () => {
                this.currentFilters.to_date = toDateInput.value;
                this.loadReports();
            });
        }


        // Refresh button
        const refreshBtn = document.getElementById('refreshReports');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadReports(true);
            });
        }
    }

    /**
     * Chuyển đổi loại báo cáo
     */
    switchReportType(reportType) {
        // Update active tab
        document.querySelectorAll('[data-report-type]').forEach(tab => {
            const isActive = tab.dataset.reportType === reportType;

            if (isActive) {
                tab.classList.add('border-blue-500', 'text-blue-500', 'font-medium');
                tab.classList.remove('border-transparent', 'text-gray-600', 'dark:text-gray-300');
            } else {
                tab.classList.remove('border-blue-500', 'text-blue-500', 'font-medium');
                tab.classList.add('border-transparent', 'text-gray-600', 'dark:text-gray-300');
            }
        });

        // Update filter
        this.currentFilters.report_type = reportType;
        this.loadReports();
    }

    toggleDateFilter() {
        const role = User.getRole();
        const isSuperAdmin = role === 'super_admin';

        const dateFilter = document.getElementById('dateFilter');
        const statusWrapper = document.getElementById('statusFilterWrapper');

        if (isSuperAdmin) {
            dateFilter.classList.remove('hidden');
            statusWrapper.classList.remove('sm:col-span-2');
            statusWrapper.classList.add('sm:col-span-1');
        } else {
            dateFilter.classList.add('hidden');
            statusWrapper.classList.remove('sm:col-span-1');
            statusWrapper.classList.add('sm:col-span-2');
        }
    }

    formatErrorTime(time) {
        switch (time) {
            case 'morning':
                return 'Buổi sáng';
            case 'afternoon':
                return 'Buổi chiều';
            case 'full_day':
                return 'Cả ngày';
            default:
                return time; // fallback nếu không match
        }
    }

    /**
     * Tải danh sách báo cáo từ API
     */
    async loadReports(forceRefresh = false) {
        try {
            this.showLoading();

            // Chuẩn bị params cho API
            const params = {};
            if (this.currentFilters.report_type !== 'all') {
                params.report_type = this.currentFilters.report_type;
            }
            if (this.currentFilters.status !== 'all') {
                params.status = this.currentFilters.status;
            }
            if (this.currentFilters.from_date) {
                params.from_date = this.currentFilters.from_date;
            }
            if (this.currentFilters.to_date) {
                params.to_date = this.currentFilters.to_date;
            }

            const response = await API.getReports(params);
            console.log(response);

            if (response.status === 'success') {
                this.reports = response.data.reports;
                this.updateSummaryStats(response.data.summary);
                this.renderReports();

                if (forceRefresh) {
                    showToast('Đã cập nhật', 'Danh sách báo cáo đã được cập nhật', 'success');
                }
            } else {
                throw new Error(response.message || 'Không thể tải danh sách báo cáo');
            }

        } catch (error) {
            console.error('Error loading reports:', error);
            showToast('Lỗi', 'Không thể tải danh sách báo cáo: ' + error.message, 'error');
            this.showError();
        }
    }

    /**
     * Cập nhật thống kê tổng quan
     */
    updateSummaryStats(summary) {
        // Cập nhật số liệu trong stats cards
        const statsCards = document.querySelectorAll('.bg-white.dark\\:bg-gray-800.rounded-xl.p-6');

        if (statsCards.length >= 3) {
            // Card "Chờ phê duyệt"
            const pendingCount = statsCards[0].querySelector('.text-2xl');
            if (pendingCount) pendingCount.textContent = summary.pending || 0;

            // Card "Đã phê duyệt" 
            const approvedCount = statsCards[1].querySelector('.text-2xl');
            if (approvedCount) approvedCount.textContent = summary.approved || 0;

            // Card "Đã từ chối"
            const rejectedCount = statsCards[2].querySelector('.text-2xl');
            if (rejectedCount) rejectedCount.textContent = summary.rejected || 0;
        }
    }

    /**
     * Hiển thị trạng thái loading
     */
    showLoading() {
        const container = document.getElementById('reportsList');
        if (!container) return;

        container.innerHTML = `
            <div class="bg-gray-50 dark:bg-gray-800 p-8 rounded-lg text-center min-h-[300px] flex flex-col items-center justify-center text-gray-500 dark:text-gray-400">
                <i class="fas fa-spinner fa-spin text-xl mb-2"></i>
                <p class="text-sm">Đang tải dữ liệu...</p>
            </div>
        `;
    }

    /**
     * Hiển thị trạng thái lỗi
     */
    showError() {
        const container = document.getElementById('reportsList');
        if (!container) return;

        container.innerHTML = `
            <div class="bg-red-50 dark:bg-red-900/20 p-8 rounded-lg text-center min-h-[300px] flex flex-col justify-center">
                <svg class="mx-auto h-12 w-12 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <h3 class="mt-2 text-sm font-medium text-red-800 dark:text-red-200">Không thể tải dữ liệu</h3>
                <p class="mt-1 text-sm text-red-700 dark:text-red-300">Đã xảy ra lỗi khi tải danh sách báo cáo. Vui lòng thử lại sau.</p>
                <div class="mt-4">
                    <button type="button" id="retryLoadReports" class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500">
                        <i class="fas fa-redo mr-2"></i>
                        Thử lại
                    </button>
                </div>
            </div>
        `;

        // Thêm event listener cho nút thử lại
        const retryBtn = document.getElementById('retryLoadReports');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => this.loadReports());
        }
    }

    /**
     * Render danh sách báo cáo
     */
    renderReports() {
        const container = document.getElementById('reportsList');
        if (!container) return;

        if (!this.reports || this.reports.length === 0) {
            container.innerHTML = `
                <div class="bg-gray-50 dark:bg-gray-800 p-8 rounded-lg text-center min-h-[300px] flex flex-col justify-center">
                    <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">Không tìm thấy báo cáo nào</h3>
                    <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">Không có báo cáo nào phù hợp với bộ lọc hiện tại.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.reports.map(report => this.createReportCard(report)).join('');
        this.bindReportActions();
    }

    /**
     * Tạo HTML cho một báo cáo
     */
    createReportCard(report) {
        // Xác định thông tin loại báo cáo
        const reportTypeInfo = this.getReportTypeInfo(report.report_type, report);

        // Xác định trạng thái
        const statusInfo = this.getStatusInfo(report.status);

        // Format ngày
        const createdDate = this.formatDate(report.created_at);

        // Định dạng ngày báo cáo
        let reportDateStr = '';
        if (report.date) {
            if (report.end_date && report.end_date !== report.date) {
                reportDateStr = `${this.formatShortDate(report.date)} - ${this.formatShortDate(report.end_date)}`;
            } else {
                reportDateStr = this.formatShortDate(report.date);
            }
        }

        // Tạo HTML cho tệp đính kèm
        let attachmentsHTML = '';
        if (report.attached_files && report.attached_files.length > 0) {
            const fileLinks = report.attached_files.map(file => {
                const fileName = file.original_filename || file.saved_filename;
                const fileUrl = API.getReportFileUrl(report.user_id, file.saved_filename);
                return `
                    <a href="${fileUrl}" target="_blank" 
                       class="inline-flex items-center px-3 py-1 rounded-md text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 dark:bg-gray-700 dark:text-blue-200 dark:hover:bg-gray-600 transition-colors max-w-xs truncate">
                        <svg class="flex-shrink-0 mr-1.5 h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"></path>
                        </svg>
                        <span class="truncate">${fileName}</span>
                    </a>`;
            }).join('');

            attachmentsHTML = `
                <div class="mt-3 mb-3">
                    <span class="text-xs font-medium text-gray-500 dark:text-gray-300 block mb-2">Tệp đính kèm:</span>
                    <div class="flex flex-wrap gap-2">
                        ${fileLinks}
                    </div>
                </div>
            `;
        }

        // Tạo HTML cho phần phản hồi từ quản lý
        const adminNoteHTML = `
            <div class="mt-3">
                <span class="text-xs font-medium text-gray-500 dark:text-gray-300 block mb-2">Phản hồi từ quản lý:</span>
                <div class="bg-gray-50 dark:bg-gray-700 rounded-md p-3">
                    <textarea 
                        class="admin-note w-full text-xs text-gray-700 dark:text-gray-300 bg-transparent border-none resize-none focus:outline-none focus:ring-0"
                        rows="3"
                        placeholder="Nhập phản hồi của bạn..."
                    >${report.admin_note || ''}</textarea>
                </div>
            </div>
        `;

        // Tạo HTML cho buttons (chỉ hiển thị nếu status là pending)
        let actionButtonsHTML = '';
        if (report.status === 'pending') {
            actionButtonsHTML = `
                <div class="flex flex-col sm:flex-row gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                    <button class="approve-btn flex-1 bg-green-600 hover:bg-green-700 text-white px-4 py-2.5 rounded-lg font-medium transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800">
                        <div class="flex items-center justify-center">
                            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                            </svg>
                            Phê duyệt
                        </div>
                    </button>
                    <button class="reject-btn flex-1 bg-red-600 hover:bg-red-700 text-white px-4 py-2.5 rounded-lg font-medium transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800">
                        <div class="flex items-center justify-center">
                            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                            </svg>
                            Từ chối
                        </div>
                    </button>
                </div>
            `;
        }

        return `
            <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow mb-4" data-report-id="${report.report_id}">
                <div class="flex justify-between items-start mb-3">
                    <h3 class="text-sm font-medium text-gray-800 dark:text-white">
                        ${reportTypeInfo.title}
                    </h3>
                    <span class="bg-${statusInfo.bgColor} text-${statusInfo.textColor} text-xs font-semibold px-2 py-0.5 rounded-full dark:bg-${statusInfo.darkBgColor} dark:text-${statusInfo.darkTextColor}">
                        ${statusInfo.label}
                    </span>
                </div>
                
                <div class="grid grid-cols-1 gap-3 mb-3">
                    <div class="flex items-center">
                        <span class="text-xs font-medium text-gray-500 dark:text-gray-300 mr-1.5">Nhân viên:</span>
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300">
                            ${report.user_name}
                        </span>
                    </div>
                    <div class="flex items-center">
                        <span class="text-xs font-medium text-gray-500 dark:text-gray-300 mr-1.5">Loại báo cáo:</span>
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300">
                            ${reportTypeInfo.tagLabel}
                        </span>
                    </div>
                    ${reportDateStr ? `
                    <div class="flex items-center">
                        <span class="text-xs font-medium text-gray-500 dark:text-gray-300 mr-1.5">Thời gian:</span>
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300">
                            ${reportDateStr}
                        </span>
                    </div>
                    ` : ''}
                    <div class="flex items-center">
                        <span class="text-xs font-medium text-gray-500 dark:text-gray-300 mr-1.5">Ngày tạo:</span>
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300">${createdDate}</span>
                    </div>
                    ${report.error_time ? `
                    <div class="flex items-center">
                        <span class="text-xs font-medium text-gray-500 dark:text-gray-300 mr-1.5">Thời gian lỗi:</span>
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300">
                            ${this.formatErrorTime(report.error_time)}
                        </span>
                    </div>
                    ` : ''}
                    ${report.updated_by ? `
                    <div class="flex items-center">
                        <span class="text-xs font-medium text-gray-500 dark:text-gray-300 mr-1.5">Phê duyệt bởi:</span>
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300">
                            ${report.updated_by}
                        </span>
                    </div>
                    ` : ''}
                </div>
                
                <div class="mb-3">
                    <span class="text-xs font-medium text-gray-500 dark:text-gray-300 block mb-2">Mô tả:</span>
                    <div class="bg-gray-50 dark:bg-gray-700 rounded-md p-3">
                        <p class="text-xs text-gray-600 dark:text-gray-300">${report.description || 'Không có mô tả'}</p>
                    </div>
                </div>
                
                ${attachmentsHTML}
                ${adminNoteHTML}
                ${actionButtonsHTML}
            </div>
        `;
    }

    /**
     * Gắn event cho các nút hành động
     */
    bindReportActions() {
        // Approve buttons
        document.querySelectorAll('.approve-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const reportCard = e.target.closest('[data-report-id]');
                const reportId = reportCard.dataset.reportId;
                const adminNote = reportCard.querySelector('.admin-note').value.trim();
                this.updateReportStatus(reportId, 'approved', adminNote);
            });
        });

        // Reject buttons
        document.querySelectorAll('.reject-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const reportCard = e.target.closest('[data-report-id]');
                const reportId = reportCard.dataset.reportId;
                const adminNote = reportCard.querySelector('.admin-note').value.trim();
                this.updateReportStatus(reportId, 'rejected', adminNote);
            });
        });
    }

    /**
     * Cập nhật trạng thái báo cáo
     */
    async updateReportStatus(reportId, status, adminNote) {
        try {
            const reportCard = document.querySelector(`[data-report-id="${reportId}"]`);
            const buttons = reportCard.querySelectorAll('button');

            // Disable buttons và hiển thị loading
            buttons.forEach(btn => {
                btn.disabled = true;
                btn.classList.add('opacity-50');
            });

            const response = await API.updateReportStatus(reportId, status, adminNote);

            if (response.status === 'success') {
                const statusText = status === 'approved' ? 'phê duyệt' : 'từ chối';
                showToast(
                    'Thành công',
                    `Đã ${statusText} báo cáo thành công`,
                    'success'
                );

                // Reload reports để cập nhật UI
                this.loadReports();
            } else {
                throw new Error(response.message || 'Không thể cập nhật trạng thái báo cáo');
            }

        } catch (error) {
            console.error('Error updating report status:', error);
            showToast('Lỗi', 'Không thể cập nhật báo cáo: ' + error.message, 'error');

            // Re-enable buttons
            const reportCard = document.querySelector(`[data-report-id="${reportId}"]`);
            const buttons = reportCard.querySelectorAll('button');
            buttons.forEach(btn => {
                btn.disabled = false;
                btn.classList.remove('opacity-50');
            });
        }
    }

    /**
     * Lấy thông tin loại báo cáo
     */
    getReportTypeInfo(reportType, report) {
        switch (reportType) {
            case 'incorrect_photo':
                let photoTypeLabel = 'Ảnh không đúng';
                if (report.photo_type === 'check_in') {
                    photoTypeLabel = 'Ảnh check-in không đúng';
                } else if (report.photo_type === 'check_out') {
                    photoTypeLabel = 'Ảnh check-out không đúng';
                }

                return {
                    title: 'Báo cáo ảnh không đúng',
                    tagLabel: photoTypeLabel
                };

            case 'machine_error':
                let errorTypeLabel = 'Lỗi máy';
                switch (report.error_type) {
                    case 'no_recognize':
                        errorTypeLabel = 'Máy không nhận diện';
                        break;
                    case 'wrong_time':
                        errorTypeLabel = 'Máy ghi sai giờ';
                        break;
                    case 'device_off':
                        errorTypeLabel = 'Máy không hoạt động';
                        break;
                    case 'other':
                        errorTypeLabel = 'Lỗi máy khác';
                        break;
                }

                return {
                    title: 'Báo cáo lỗi máy chấm công',
                    tagLabel: errorTypeLabel
                };

            case 'leave_request':
                let requestTypeLabel = 'Giấy phép';
                switch (report.request_type) {
                    case 'late':
                        requestTypeLabel = 'Xin phép đi muộn';
                        break;
                    case 'early_leave':
                        requestTypeLabel = 'Xin phép về sớm';
                        break;
                    case 'absent':
                        requestTypeLabel = 'Xin phép nghỉ';
                        break;
                    case 'other':
                        requestTypeLabel = 'Giấy phép khác';
                        break;
                }

                return {
                    title: 'Giấy phép nghỉ',
                    tagLabel: requestTypeLabel
                };

            default:
                return {
                    title: 'Báo cáo khác',
                    tagLabel: 'Khác'
                };
        }
    }

    /**
     * Lấy thông tin trạng thái
     */
    getStatusInfo(status) {
        const statuses = {
            'pending': {
                label: 'Chờ phê duyệt',
                bgColor: 'yellow-100',
                textColor: 'yellow-800',
                darkBgColor: 'yellow-900',
                darkTextColor: 'yellow-300'
            },
            'approved': {
                label: 'Đã phê duyệt',
                bgColor: 'green-100',
                textColor: 'green-800',
                darkBgColor: 'green-900',
                darkTextColor: 'green-300'
            },
            'rejected': {
                label: 'Đã từ chối',
                bgColor: 'red-100',
                textColor: 'red-800',
                darkBgColor: 'red-900',
                darkTextColor: 'red-300'
            }
        };

        return statuses[status] || statuses['pending'];
    }

    /**
     * Format ngày tháng đầy đủ
     */
    formatDate(dateString) {
        if (!dateString) return '';

        const date = new Date(dateString);
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');

        return `${day}/${month}/${year} ${hours}:${minutes}`;
    }

    /**
     * Format ngày ngắn
     */
    formatShortDate(dateString) {
        if (!dateString) return '';

        const date = new Date(dateString);
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();

        return `${day}/${month}/${year}`;
    }
}

// Khởi tạo ứng dụng khi DOM loaded
document.addEventListener('DOMContentLoaded', () => {
    new ReportsApproval();
});