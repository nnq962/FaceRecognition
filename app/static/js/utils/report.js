// reports.js
import API from '../core/api.js';
import { showToast } from './toast.js';
import User from "../utils/user.js";

// Biến lưu trạng thái của trang báo cáo
let reportsState = {
    reportType: 'all',
    status: 'all',
    fromDate: null,
    toDate: null,
    currentPage: 1,
    totalPages: 1,
    isLoading: false,
    reports: []
};

// Hằng số: Số báo cáo hiển thị trên mỗi trang
const REPORTS_PER_PAGE = 10;

// Khởi tạo trang khi DOM đã sẵn sàng
function initReportsSection() {
    // Khởi tạo bộ lọc ngày từ đầu tháng hiện tại đến hôm nay
    initDateFilters();

    // Đăng ký các event listener
    registerEventListeners();

    // Tải báo cáo ban đầu
    loadReports();
}

// Khởi tạo bộ lọc ngày
function initDateFilters() {
    const today = new Date();

    // Đặt ngày bắt đầu là ngày 1 của tháng hiện tại
    const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
    reportsState.fromDate = formatDateForInput(firstDayOfMonth);

    // Đặt ngày kết thúc là ngày hiện tại
    reportsState.toDate = formatDateForInput(today);

    // Cập nhật input date
    const fromDateInput = document.getElementById('fromDate');
    const toDateInput = document.getElementById('toDate');

    if (fromDateInput) fromDateInput.value = reportsState.fromDate;
    if (toDateInput) toDateInput.value = reportsState.toDate;
}

// Định dạng ngày cho input type="date"
function formatDateForInput(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// Đăng ký các event listener
function registerEventListeners() {
    // Xử lý nút làm mới
    const refreshBtn = document.getElementById('refreshReports');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            loadReports(true);
        });
    }

    // Xử lý nút tab loại báo cáo
    const reportTypeButtons = document.querySelectorAll('[data-report-type]');
    reportTypeButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            const reportType = e.currentTarget.getAttribute('data-report-type');

            // Cập nhật UI - bỏ active tất cả các tab
            reportTypeButtons.forEach(btn => {
                btn.classList.remove('border-blue-500', 'text-blue-500');
                btn.classList.add('border-transparent');
            });

            // Đánh dấu tab hiện tại là active
            e.currentTarget.classList.remove('border-transparent');
            e.currentTarget.classList.add('border-blue-500', 'text-blue-500');

            // Cập nhật trạng thái và tải lại báo cáo
            reportsState.reportType = reportType;
            reportsState.currentPage = 1;
            loadReports();
        });
    });

    // Xử lý bộ lọc trạng thái
    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.addEventListener('change', () => {
            reportsState.status = statusFilter.value;
            reportsState.currentPage = 1;
            loadReports();
        });
    }

    // Xử lý bộ lọc ngày
    const fromDateInput = document.getElementById('fromDate');
    const toDateInput = document.getElementById('toDate');

    if (fromDateInput) {
        fromDateInput.addEventListener('change', () => {
            reportsState.fromDate = fromDateInput.value;
            reportsState.currentPage = 1;
            loadReports();
        });
    }

    if (toDateInput) {
        toDateInput.addEventListener('change', () => {
            reportsState.toDate = toDateInput.value;
            reportsState.currentPage = 1;
            loadReports();
        });
    }

    // Xử lý phân trang
    const prevPageBtn = document.getElementById('prevPage');
    const nextPageBtn = document.getElementById('nextPage');

    if (prevPageBtn) {
        prevPageBtn.addEventListener('click', () => {
            if (reportsState.currentPage > 1) {
                reportsState.currentPage--;
                loadReports();
            }
        });
    }

    if (nextPageBtn) {
        nextPageBtn.addEventListener('click', () => {
            if (reportsState.currentPage < reportsState.totalPages) {
                reportsState.currentPage++;
                loadReports();
            }
        });
    }
}

// Tải danh sách báo cáo
async function loadReports(forceRefresh = false) {
    // Nếu đang tải, bỏ qua
    if (reportsState.isLoading) return;

    // Hiển thị trạng thái đang tải
    reportsState.isLoading = true;
    showLoadingState();

    try {
        // Lấy ID người dùng
        const userId = User.getUserId();

        if (!userId) {
            showToast('Lỗi xác thực', 'Vui lòng đăng nhập lại', 'error');
            return;
        }

        // Chuẩn bị tham số cho API
        const params = {
            report_type: reportsState.reportType !== 'all' ? reportsState.reportType : undefined,
            status: reportsState.status !== 'all' ? reportsState.status : undefined,
            from_date: reportsState.fromDate,
            to_date: reportsState.toDate,
            page: reportsState.currentPage,
            limit: REPORTS_PER_PAGE
        };

        // Gọi API lấy danh sách báo cáo
        const response = await API.getUserReports(userId, params);

        if (response && response.status === 'success') {
            // SỬA: Truy xuất data từ response.data
            reportsState.reports = response.data?.reports || [];
            reportsState.totalPages = response.data?.total_pages || 1;

            // Cập nhật UI
            updateReportsList();
            updatePagination();

            // Nếu tải thành công và là do refresh, hiển thị thông báo
            if (forceRefresh) {
                showToast('Đã cập nhật', 'Danh sách báo cáo đã được cập nhật', 'success');
            }
        } else {
            showToast('Lỗi tải dữ liệu', response?.message || 'Không thể tải danh sách báo cáo', 'error');
            showErrorState();
        }
    } catch (error) {
        showToast('Lỗi kết nối', 'Không thể kết nối đến máy chủ. Vui lòng thử lại sau.', 'error');
        showErrorState();
    } finally {
        reportsState.isLoading = false;
    }
}

// Hiển thị trạng thái đang tải
function showLoadingState() {
    const reportsListEl = document.getElementById('reportsList');
    if (!reportsListEl) return;

    reportsListEl.innerHTML = `
        <div class="bg-gray-50 dark:bg-gray-800 p-8 rounded-lg text-center min-h-[300px] flex flex-col items-center justify-center text-gray-500 dark:text-gray-400">
        <i class="fas fa-spinner fa-spin text-xl mb-2"></i>
        <p class="text-sm">Đang tải dữ liệu...</p>
        </div>
    `;
  

    // Cập nhật UI của nút phân trang
    const prevPageBtn = document.getElementById('prevPage');
    const nextPageBtn = document.getElementById('nextPage');

    if (prevPageBtn) prevPageBtn.disabled = true;
    if (nextPageBtn) nextPageBtn.disabled = true;
}

// Hiển thị trạng thái lỗi
function showErrorState() {
    const reportsListEl = document.getElementById('reportsList');
    if (!reportsListEl) return;

    reportsListEl.innerHTML = `
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
        retryBtn.addEventListener('click', () => loadReports());
    }
}

// Cập nhật phân trang
function updatePagination() {
    const currentPageEl = document.getElementById('currentPage');
    const totalPagesEl = document.getElementById('totalPages');
    const prevPageBtn = document.getElementById('prevPage');
    const nextPageBtn = document.getElementById('nextPage');

    if (currentPageEl) {
        currentPageEl.textContent = reportsState.currentPage;
    }

    if (totalPagesEl) {
        totalPagesEl.textContent = reportsState.totalPages;
    }

    if (prevPageBtn) {
        prevPageBtn.disabled = reportsState.currentPage <= 1;
    }

    if (nextPageBtn) {
        nextPageBtn.disabled = reportsState.currentPage >= reportsState.totalPages;
    }
}



// Xử lý xem chi tiết báo cáo
function viewReportDetail(reportId) {
    // Tìm báo cáo theo ID
    const report = reportsState.reports.find(r => r.id === reportId);

    if (!report) {
        showToast('Không tìm thấy', 'Không tìm thấy thông tin báo cáo', 'error');
        return;
    }

    // Tùy chỉnh hiển thị chi tiết dựa vào loại báo cáo
    switch (report.report_type) {
        case 'incorrect_photo':
            showIncorrectPhotoReportDetail(report);
            break;
        case 'machine_error':
            showMachineErrorReportDetail(report);
            break;
        case 'leave_request':
            showLeaveRequestReportDetail(report);
            break;
        default:
            showGenericReportDetail(report);
    }
}

// Định dạng ngày giờ dễ đọc
function formatDate(dateStr) {
    if (!dateStr) return '';

    const date = new Date(dateStr);
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');

    return `${day}/${month}/${year} ${hours}:${minutes}`;
}

// Định dạng ngày ngắn gọn
function formatShortDate(dateStr) {
    if (!dateStr) return '';

    const date = new Date(dateStr);
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();

    return `${day}/${month}/${year}`;
}


// Cập nhật danh sách báo cáo
function updateReportsList() {
    const reportsListEl = document.getElementById('reportsList');
    if (!reportsListEl) return;

    // Nếu không có báo cáo nào, hiển thị thông báo trống
    if (!reportsState.reports || reportsState.reports.length === 0) {
        reportsListEl.innerHTML = `
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

    // Tạo HTML cho danh sách báo cáo
    const reportsHTML = reportsState.reports.map(report => {
        return createReportCard(report);
    }).join('');

    reportsListEl.innerHTML = reportsHTML;

    // Đã bỏ phần thêm event listener cho nút "Xem chi tiết"
}

function formatErrorTime(time) {
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


// Tạo HTML cho thẻ báo cáo
function createReportCard(report) {
    // Xác định màu sắc dựa trên loại báo cáo
    const reportTypeInfo = getReportTypeInfo(report.report_type, report);

    // Xác định trạng thái
    const statusInfo = getStatusInfo(report.status);

    // Định dạng ngày tạo
    const createdDate = formatDate(report.created_at);

    // Định dạng ngày báo cáo
    let reportDateStr = '';
    if (report.date) {
        if (report.end_date && report.end_date !== report.date) {
            reportDateStr = `${formatShortDate(report.date)} - ${formatShortDate(report.end_date)}`;
        } else {
            reportDateStr = formatShortDate(report.date);
        }
    }

    // Tạo HTML cho tệp đính kèm (nếu có)
    let attachmentsHTML = '';
    if (report.attached_files && report.attached_files.length > 0) {
        const fileLinks = report.attached_files.map(file => {
            const fileName = file.original_filename || file.saved_filename;
            // Sử dụng API.getReportFileUrl để lấy URL đúng
            const fileUrl = API.getReportFileUrl(report.user_id, file.saved_filename);
            return `
                <a href="${fileUrl}" target="_blank" 
                   class="inline-flex items-center px-3 py-1 rounded-md text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 dark:bg-gray-700 dark:text-blue-200 dark:hover:bg-gray-600 transition-colors max-w-xs truncate">
                    <svg class="flex-shrink-0 mr-1.5 h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
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

    // Tạo HTML cho phần phản hồi từ quản lý (luôn hiển thị dù có hay không)
    let adminNoteHTML = `
        <div class="mt-3">
            <span class="text-xs font-medium text-gray-500 dark:text-gray-300 block mb-2">Phản hồi từ quản lý:</span>
            <div class="bg-gray-50 dark:bg-gray-700 rounded-md p-3">
                <p class="text-xs text-gray-700 dark:text-gray-300">${report.admin_note && report.admin_note.trim() !== '' ? report.admin_note : 'Không có phản hồi'}</p>
            </div>
        </div>
    `;

    // Tạo HTML cho thẻ báo cáo
    return `
    <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow mb-4">
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
                <span class="text-xs font-medium text-gray-500 dark:text-gray-300 mr-1.5">Thời gian lỗi: </span>
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300">
                    ${formatErrorTime(report.error_time)}
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
    </div>
`;
}


// Lấy thông tin loại báo cáo - đã cập nhật để hiển thị chi tiết hơn dựa trên các trường con
function getReportTypeInfo(reportType, report) {
    switch (reportType) {
        case 'incorrect_photo':
            // Hiển thị chi tiết theo photo_type
            let photoTypeLabel = 'Ảnh không đúng';
            if (report.photo_type === 'check_in') {
                photoTypeLabel = 'Ảnh check-in không đúng';
            } else if (report.photo_type === 'check_out') {
                photoTypeLabel = 'Ảnh check-out không đúng';
            }

            return {
                title: 'Báo cáo ảnh không đúng',
                tagLabel: photoTypeLabel,
                dotColor: 'bg-yellow-500',
                bgColor: 'yellow-100',
                textColor: 'yellow-800',
                darkBgColor: 'yellow-900',
                darkTextColor: 'yellow-300',
                iconColor: 'yellow-600',
                darkIconColor: 'yellow-300'
            };

        case 'machine_error':
            // Hiển thị chi tiết theo error_type
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
                tagLabel: errorTypeLabel,
                dotColor: 'bg-amber-500',
                bgColor: 'amber-100',
                textColor: 'amber-800',
                darkBgColor: 'amber-900',
                darkTextColor: 'amber-300',
                iconColor: 'amber-600',
                darkIconColor: 'amber-300'
            };

        case 'leave_request':
            // Hiển thị chi tiết theo request_type
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
                tagLabel: requestTypeLabel,
                dotColor: 'bg-blue-500',
                bgColor: 'blue-100',
                textColor: 'blue-800',
                darkBgColor: 'blue-900',
                darkTextColor: 'blue-300',
                iconColor: 'blue-600',
                darkIconColor: 'blue-300'
            };

        default:
            return {
                title: 'Báo cáo khác',
                tagLabel: 'Khác',
                dotColor: 'bg-gray-500',
                bgColor: 'gray-100',
                textColor: 'gray-800',
                darkBgColor: 'gray-700',
                darkTextColor: 'gray-300',
                iconColor: 'gray-600',
                darkIconColor: 'gray-300'
            };
    }
}

// Lấy thông tin trạng thái báo cáo
function getStatusInfo(status) {
    switch (status) {
        case 'pending':
            return {
                label: 'Đang chờ xử lý',
                bgColor: 'blue-100',
                textColor: 'blue-800',
                darkBgColor: 'blue-900',
                darkTextColor: 'blue-300'
            };
        case 'reviewed':
            return {
                label: 'Đang xem xét',
                bgColor: 'purple-100',
                textColor: 'purple-800',
                darkBgColor: 'purple-900',
                darkTextColor: 'purple-300'
            };
        case 'approved':
            return {
                label: 'Đã phê duyệt',
                bgColor: 'green-100',
                textColor: 'green-800',
                darkBgColor: 'green-900',
                darkTextColor: 'green-300'
            };
        case 'rejected':
            return {
                label: 'Đã từ chối',
                bgColor: 'red-100',
                textColor: 'red-800',
                darkBgColor: 'red-900',
                darkTextColor: 'red-300'
            };
        default:
            return {
                label: 'Không xác định',
                bgColor: 'gray-100',
                textColor: 'gray-800',
                darkBgColor: 'gray-700',
                darkTextColor: 'gray-300'
            };
    }
}

// Hiển thị chi tiết báo cáo ảnh không đúng
function showIncorrectPhotoReportDetail(report) {
    // Tạo modal hiển thị chi tiết
    // Code hiển thị modal với thông tin báo cáo ảnh không đúng
    showToast('Chi tiết báo cáo', 'Đang phát triển tính năng xem chi tiết báo cáo ảnh không đúng', 'info');
}

// Hiển thị chi tiết báo cáo lỗi máy
function showMachineErrorReportDetail(report) {
    // Code hiển thị modal với thông tin báo cáo lỗi máy
    showToast('Chi tiết báo cáo', 'Đang phát triển tính năng xem chi tiết báo cáo lỗi máy', 'info');
}

// Hiển thị chi tiết giấy phép nghỉ
function showLeaveRequestReportDetail(report) {
    // Code hiển thị modal với thông tin giấy phép
    showToast('Chi tiết báo cáo', 'Đang phát triển tính năng xem chi tiết giấy phép', 'info');
}

// Hiển thị chi tiết loại báo cáo khác
function showGenericReportDetail(report) {
    // Code hiển thị modal với thông tin báo cáo chung
    showToast('Chi tiết báo cáo', 'Đang phát triển tính năng xem chi tiết báo cáo', 'info');
}

// Lắng nghe sự kiện DOMContentLoaded
document.addEventListener('DOMContentLoaded', initReportsSection);

// Export các hàm cần thiết
export { initReportsSection, loadReports };