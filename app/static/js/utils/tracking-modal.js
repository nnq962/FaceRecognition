// tracking-modal.js
import API from '../core/api.js';
import { showToast } from './toast.js';
import User from "./user.js";
import {
    ATTENDANCE_STATUS,
    TIME_CONFIG,
    formatDate,
    formatDateDisplay,
    formatTimeDisplay,
    showNoPhoto,
    showPhotoLoading,
    showPhotoError,
    showPhoto
} from './attendance-constants.js';

// Biến lưu trữ file được chọn - chỉ dùng trong phạm vi module này
const selectedFiles = new Set();

/**
 * Hiển thị modal chi tiết chấm công
 * @param {string} date - Ngày cần hiển thị (YYYY-MM-DD)
 * @param {Array} records - Mảng dữ liệu chấm công của ngày đó
 */
function showAttendanceModal(date, records) {
    // Kiểm tra xem modal có tồn tại không
    let modal = document.getElementById('attendanceModal');

    // Nếu không có modal, tạo mới
    if (!modal) {
        // Tạo modal HTML đầy đủ chức năng với Tailwind CSS
        const modalHTML = `
        <div id="attendanceModal"
            class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30 backdrop-blur-md transition-opacity"
            style="overscroll-behavior: contain;">
            <div class="w-full max-w-3xl my-8 bg-white dark:bg-gray-800 rounded-xl shadow-xl transform transition-all flex flex-col max-h-[calc(100vh-2rem)]">
                <!-- Header -->
                <div class="flex justify-between items-center p-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
                        <h2 class="text-lg font-medium text-gray-800 dark:text-white">Chi tiết chấm công: <span id="modalDate">${formatDateDisplay(new Date(date))}</span></h2>                    <button type="button" id="closeModal" class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-white transition-colors">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>
                
                <!-- Body - scrollable content -->
                <div class="px-4 pt-4 pb-0 space-y-4 overflow-y-auto flex-1 min-h-0" style="overscroll-behavior: contain;">
                    <!-- Thông tin cơ bản -->
                    <div class="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 space-y-3">
                        <h3 class="text-lg font-medium text-gray-800 dark:text-white">Thông tin chấm công</h3>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div class="flex justify-between items-center">
                                <span class="text-gray-600 dark:text-gray-400">Giờ vào:</span>
                                <span class="font-medium text-gray-800 dark:text-gray-200" id="checkInTime">--:--:--</span>
                            </div>
                            <div class="flex justify-between items-center">
                                <span class="text-gray-600 dark:text-gray-400">Giờ ra:</span>
                                <span class="font-medium text-gray-800 dark:text-gray-200" id="checkOutTime">--:--:--</span>
                            </div>
                            <div class="flex justify-between items-center">
                                <span class="text-gray-600 dark:text-gray-400">Thời gian làm việc:</span>
                                <span class="font-medium text-gray-800 dark:text-gray-200" id="workHours">-- giờ -- phút</span>
                            </div>
                            <div class="flex justify-between items-center">
                                <span class="text-gray-600 dark:text-gray-400">Trạng thái:</span>
                                <div class="flex flex-wrap gap-2" id="statusTags">
                                    <!-- Sẽ được tạo động bằng JavaScript -->
                                </div>
                            </div>
                        </div>
                    </div>
        
                    <!-- Ảnh chấm công -->
                    <div class="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 space-y-3">
                        <h3 class="text-lg font-medium text-gray-800 dark:text-white">Ảnh chấm công</h3>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <!-- Check In photo -->
                            <div class="space-y-2">
                                <div class="flex justify-between items-center">
                                    <h4 class="font-medium text-gray-700 dark:text-gray-300">Check In</h4>
                                    <span class="text-sm text-gray-500 dark:text-gray-400" id="checkInTimeLabel">--:--:--</span>
                                </div>
                                <div class="relative h-48 sm:h-60 bg-gray-200 dark:bg-gray-700 rounded-lg overflow-hidden flex items-center justify-center" id="checkInPhoto">
                                    <div class="no-photo">Không có ảnh</div>
                                </div>
                                <div class="mt-2 flex justify-center">
                                    <button type="button" class="text-sm text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 transition-colors flex items-center report-btn" data-type="check_in">
                                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" viewBox="0 0 20 20" fill="currentColor">
                                            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                                        </svg>
                                        Báo ảnh không phải tôi
                                    </button>
                                </div>
                            </div>
                            
                            <!-- Check Out photo -->
                            <div class="space-y-2">
                                <div class="flex justify-between items-center">
                                    <h4 class="font-medium text-gray-700 dark:text-gray-300">Check Out</h4>
                                    <span class="text-sm text-gray-500 dark:text-gray-400" id="checkOutTimeLabel">--:--:--</span>
                                </div>
                                <div class="relative h-48 sm:h-60 bg-gray-200 dark:bg-gray-700 rounded-lg overflow-hidden flex items-center justify-center" id="checkOutPhoto">
                                    <div class="no-photo">Không có ảnh</div>
                                </div>
                                <div class="mt-2 flex justify-center">
                                    <button type="button" class="text-sm text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 transition-colors flex items-center report-btn" data-type="check_out">
                                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" viewBox="0 0 20 20" fill="currentColor">
                                            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                                        </svg>
                                        Báo ảnh không phải tôi
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
        
                    <!-- Các chức năng -->
                    <div class="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 space-y-3">
                        <h3 class="text-lg font-medium text-gray-800 dark:text-white">Các chức năng</h3>
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <button type="button" class="machine-error-btn flex items-center justify-center px-4 py-2 bg-amber-50 text-amber-700 border border-amber-200 rounded-lg hover:bg-amber-100 transition-colors dark:bg-amber-900 dark:text-amber-300 dark:border-amber-700 dark:hover:bg-amber-800">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                                    <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                                </svg>
                                <span class="truncate">Báo lỗi máy chấm công</span>
                            </button>
                            <button type="button" class="proof-btn flex items-center justify-center px-4 py-2 bg-blue-50 text-blue-700 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors dark:bg-blue-900 dark:text-blue-300 dark:border-blue-700 dark:hover:bg-blue-800">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                                    <path fill-rule="evenodd" d="M6 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V7.414A2 2 0 0015.414 6L12 2.586A2 2 0 0010.586 2H6zm5 6a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V8z" clip-rule="evenodd" />
                                </svg>
                                <span class="truncate">Gửi giấy tờ xin phép</span>
                            </button>
                        </div>
                    </div>
        
                    <!-- Form báo lỗi máy (đang ẩn) -->
                    <div id="machineErrorSection" class="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 space-y-4 hidden">
                        <h3 class="text-lg font-medium text-gray-800 dark:text-white">Báo lỗi máy chấm công</h3>
                        <form id="machineErrorForm" class="space-y-4">
                            <div class="space-y-2">
                                <label for="errorType" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Loại lỗi:</label>
                                <select id="errorType" name="errorType" class="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" required>
                                    <option value="">-- Chọn loại lỗi --</option>
                                    <option value="no_recognize">Máy không nhận diện</option>
                                    <option value="wrong_time">Máy ghi sai giờ</option>
                                    <option value="device_off">Máy không hoạt động</option>
                                    <option value="other">Lỗi khác</option>
                                </select>
                            </div>
                            <div class="space-y-2">
                                <label for="errorDescription" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Mô tả chi tiết:</label>
                                <textarea id="errorDescription" name="errorDescription" rows="3" class="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" placeholder="Mô tả chi tiết lỗi..."></textarea>
                            </div>
                            <div class="space-y-2">
                                <label for="errorTime" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Thời gian lỗi:</label>
                                <select id="errorTime" name="errorTime" class="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                    <option value="">-- Chọn thời gian --</option>
                                    <option value="morning">Buổi sáng</option>
                                    <option value="afternoon">Buổi chiều</option>
                                    <option value="allday">Cả ngày</option>
                                </select>
                            </div>
                            <div class="flex justify-end space-x-3 pt-2">
                                <button type="button" id="cancelMachineError" class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600">Hủy</button>
                                <button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">Gửi báo cáo</button>
                            </div>
                        </form>
                    </div>
        
                    <!-- Form gửi giấy tờ (đang ẩn) -->
                    <div id="proofUploadSection" class="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 space-y-4 hidden mb-4">
                        <h3 class="text-lg font-medium text-gray-800 dark:text-white">Gửi giấy tờ xin phép</h3>
                        <form id="proofUploadForm" class="space-y-4">
                            <div class="space-y-2">
                                <label for="proofType" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Loại giấy tờ:</label>
                                <select id="proofType" name="proofType" class="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" required>
                                    <option value="">-- Chọn loại giấy tờ --</option>
                                    <option value="late">Xin phép đi muộn</option>
                                    <option value="early_leave">Xin phép về sớm</option>
                                    <option value="absent">Xin phép nghỉ</option>
                                    <option value="other">Khác</option>
                                </select>
                            </div>
                            <div class="space-y-2">
                                <label for="proofDescription" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Mô tả:</label>
                                <textarea id="proofDescription" name="proofDescription" rows="3" class="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" placeholder="Mô tả lý do..."></textarea>
                            </div>
                            <div class="space-y-2">
                                <label for="proofFile" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Tài liệu đính kèm:</label>
                                <div class="flex items-center justify-center w-full">
                                    <label for="proofFile" class="flex flex-col items-center justify-center w-full h-32 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer bg-gray-50 dark:hover:bg-gray-700 dark:bg-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:hover:border-gray-500">
                                        <div class="flex flex-col items-center justify-center pt-5 pb-6">
                                            <svg class="w-8 h-8 mb-3 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                                            </svg>
                                            <p class="mb-1 text-sm text-gray-500 dark:text-gray-400"><span class="font-semibold">Nhấp để tải file</span> hoặc kéo và thả</p>
                                            <p class="text-xs text-gray-500 dark:text-gray-400">PDF, JPG, JPEG, PNG (Tối đa 5MB)</p>
                                        </div>
                                        <input id="proofFile" type="file" class="hidden" multiple accept=".pdf,.jpg,.jpeg,.png" />
                                    </label>
                                </div>
                                <div id="filePreviewContainer" class="file-preview-container flex flex-wrap gap-2 mt-2">
                                    <!-- File preview items will go here -->
                                </div>
                            </div>
                            <div class="flex justify-end space-x-3 pt-2">
                                <button type="button" id="cancelProofUpload" class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600">Hủy</button>
                                <button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">Gửi</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
        `;

        // Thêm modal vào body
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        // Lấy tham chiếu đến modal mới
        modal = document.getElementById('attendanceModal');

        // Khởi tạo các sự kiện cho modal
        initModalEvents();
    } else {
        // Cập nhật ngày cho modal đã tồn tại
        const modalDateElement = document.getElementById('modalDate');
        if (modalDateElement) {
            modalDateElement.textContent = formatDateDisplay(new Date(date));
        }
    }

    // Hiển thị modal - sử dụng cách mới với Tailwind
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden'; // Ngăn cuộn trang

    // Reset các form
    const machineErrorSection = document.getElementById('machineErrorSection');
    const proofUploadSection = document.getElementById('proofUploadSection');
    if (machineErrorSection) machineErrorSection.classList.add('hidden');
    if (proofUploadSection) proofUploadSection.classList.add('hidden');

    // Kiểm tra dữ liệu và hiển thị
    if (!records || records.length === 0) {
        displayEmptyAttendance();
        return;
    }

    // Lấy check-in và check-out từ dữ liệu
    const checkInRecord = records.find(r => r.check_in_time);
    const checkOutRecord = records.find(r => r.check_out_time);

    // Lấy tất cả các trạng thái
    const statuses = records.map(record => record.status);

    // Cập nhật thông tin chấm công
    updateAttendanceInfo(checkInRecord, checkOutRecord, statuses);

    // Cập nhật ảnh chấm công
    updateAttendancePhotos(checkInRecord, checkOutRecord);
}

/**
 * Khởi tạo các sự kiện cho modal
 */
function initModalEvents() {
    // DOM Elements
    const modal = document.getElementById('attendanceModal');
    const closeModalBtn = document.getElementById('closeModal');
    const machineErrorBtn = document.querySelector('.machine-error-btn');
    const proofBtn = document.querySelector('.proof-btn');
    const machineErrorSection = document.getElementById('machineErrorSection');
    const proofUploadSection = document.getElementById('proofUploadSection');
    const cancelMachineErrorBtn = document.getElementById('cancelMachineError');
    const cancelProofUploadBtn = document.getElementById('cancelProofUpload');

    // Đăng ký sự kiện đóng modal
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeModal);
    }

    // Đóng modal khi click bên ngoài nội dung
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal();
            }
        });
    }

    // Đóng modal khi nhấn phím Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal && !modal.classList.contains('hidden')) {
            closeModal();
        }
    });

    // Sự kiện nút báo lỗi máy
    if (machineErrorBtn) {
        machineErrorBtn.addEventListener('click', () => {
            if (proofUploadSection) proofUploadSection.classList.add('hidden');
            if (machineErrorSection) {
                machineErrorSection.classList.toggle('hidden');
            }
        });
    }

    // Sự kiện nút gửi giấy tờ
    if (proofBtn) {
        proofBtn.addEventListener('click', () => {
            if (machineErrorSection) machineErrorSection.classList.add('hidden');
            if (proofUploadSection) {
                proofUploadSection.classList.toggle('hidden');
            }
        });
    }

    // Sự kiện nút hủy form báo lỗi máy
    if (cancelMachineErrorBtn) {
        cancelMachineErrorBtn.addEventListener('click', () => {
            if (machineErrorSection) machineErrorSection.classList.add('hidden');
        });
    }

    // Sự kiện nút hủy form gửi giấy tờ
    if (cancelProofUploadBtn) {
        cancelProofUploadBtn.addEventListener('click', () => {
            if (proofUploadSection) proofUploadSection.classList.add('hidden');
        });
    }

    // Xử lý form báo lỗi máy
    const machineErrorForm = document.getElementById('machineErrorForm');
    if (machineErrorForm) {
        machineErrorForm.addEventListener('submit', (e) => {
            e.preventDefault();

            // Lấy dữ liệu form
            const formData = {
                errorType: document.getElementById('errorType').value,
                errorDescription: document.getElementById('errorDescription').value,
                errorTime: document.getElementById('errorTime').value
            };

            // Kiểm tra dữ liệu bắt buộc
            if (!formData.errorType) {
                showToast("Thiếu thông tin", "Vui lòng chọn loại lỗi", "warning");
                return;
            }

            // Lấy thông tin date từ modal
            const modalDateEl = document.getElementById('modalDate');
            if (!modalDateEl) return;

            // Lấy ngày và chuyển về format YYYY-MM-DD
            const dateText = modalDateEl.textContent;
            const dateParts = dateText.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/);

            if (!dateParts) return;

            const day = dateParts[1].padStart(2, '0');
            const month = dateParts[2].padStart(2, '0');
            const year = dateParts[3];
            const formattedDate = `${year}-${month}-${day}`;

            // Lấy user ID
            const userId = User.getUserId();

            // Xử lý báo cáo lỗi máy
            handleReportMachineError(userId, formattedDate, formData);
        });
    }

    // Xử lý form gửi giấy tờ
    const proofUploadForm = document.getElementById('proofUploadForm');
    if (proofUploadForm) {
        proofUploadForm.addEventListener('submit', (e) => {
            e.preventDefault();

            // Lấy dữ liệu form
            const formData = {
                proofType: document.getElementById('proofType').value,
                proofDescription: document.getElementById('proofDescription').value
            };

            // Kiểm tra dữ liệu bắt buộc
            if (!formData.proofType) {
                showToast("Thiếu thông tin", "Vui lòng chọn loại giấy tờ", "warning");
                return;
            }

            // Lấy files
            const proofFile = document.getElementById('proofFile');
            const files = proofFile ? proofFile.files : null;

            // Kiểm tra file
            if (files && files.length > 0) {
                for (let i = 0; i < files.length; i++) {
                    const file = files[i];
                    if (file.size > 5 * 1024 * 1024) {
                        showToast("Lỗi upload", `File "${file.name}" vượt quá kích thước tối đa 5MB`, "error");
                        return;
                    }
                }
            }

            // Lấy thông tin date từ modal
            const modalDateEl = document.getElementById('modalDate');
            if (!modalDateEl) return;

            // Lấy ngày và chuyển về format YYYY-MM-DD
            const dateText = modalDateEl.textContent;
            const dateParts = dateText.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/);

            if (!dateParts) return;

            const day = dateParts[1].padStart(2, '0');
            const month = dateParts[2].padStart(2, '0');
            const year = dateParts[3];
            const formattedDate = `${year}-${month}-${day}`;

            // Lấy user ID
            const userId = User.getUserId();

            // Xử lý gửi giấy tờ xin phép
            handleSubmitLeaveRequest(userId, formattedDate, formData, files);
        });
    }

    // Xử lý nút báo ảnh không phải tôi
    document.addEventListener('click', async (e) => {
        // Kiểm tra xem có phải click vào nút báo cáo không
        if (e.target.closest('.report-btn')) {
            const reportBtn = e.target.closest('.report-btn');
            // Lấy loại ảnh từ data attribute
            const type = reportBtn.getAttribute('data-type') || 'check_in';

            // Lấy ngày hiện tại từ modal title
            const modalDateEl = document.getElementById('modalDate');
            if (!modalDateEl) return;

            // Lấy ngày và chuyển về format YYYY-MM-DD
            const dateText = modalDateEl.textContent;
            const dateParts = dateText.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/);

            if (!dateParts) return;

            const day = dateParts[1].padStart(2, '0');
            const month = dateParts[2].padStart(2, '0');
            const year = dateParts[3];
            const formattedDate = `${year}-${month}-${day}`;

            // Lấy user ID
            const userId = User.getUserId();

            // Xử lý báo cáo ảnh
            await handleReportIncorrectPhoto(userId, formattedDate, type);
        }
    });

    // Khởi tạo chức năng upload nhiều file
    initMultiFileUpload();
}

/**
* Đóng modal
*/
function closeModal() {
    const modal = document.getElementById('attendanceModal');
    if (!modal) return;

    modal.classList.add('hidden');
    document.body.style.overflow = ''; // Khôi phục cuộn trang
}

/**
* Hiển thị trạng thái khi không có dữ liệu chấm công
*/
function displayEmptyAttendance() {
    // Cập nhật các phần tử hiển thị
    const checkInTimeEl = document.getElementById('checkInTime');
    const checkOutTimeEl = document.getElementById('checkOutTime');
    const workHoursEl = document.getElementById('workHours');
    const statusTagsEl = document.getElementById('statusTags');

    if (checkInTimeEl) checkInTimeEl.textContent = '--:--:--';
    if (checkOutTimeEl) checkOutTimeEl.textContent = '--:--:--';
    if (workHoursEl) workHoursEl.textContent = '-- giờ -- phút';

    if (statusTagsEl) {
        statusTagsEl.innerHTML = `
            <span class="px-2 py-1 bg-red-100 text-red-800 text-xs font-medium rounded-md dark:bg-red-900 dark:text-red-200">Không có dữ liệu chấm công</span>
        `;
    }

    // Reset ảnh chấm công
    const checkInPhotoEl = document.getElementById('checkInPhoto');
    const checkOutPhotoEl = document.getElementById('checkOutPhoto');

    if (checkInPhotoEl) {
        showNoPhoto(checkInPhotoEl, "Không có ảnh");
    }

    if (checkOutPhotoEl) {
        showNoPhoto(checkOutPhotoEl, "Không có ảnh");
    }
}

/**
* Cập nhật thông tin chấm công trong modal
*/
function updateAttendanceInfo(checkInRecord, checkOutRecord, statuses) {
    // Cập nhật các phần tử hiển thị
    const checkInTimeEl = document.getElementById('checkInTime');
    const checkOutTimeEl = document.getElementById('checkOutTime');
    const workHoursEl = document.getElementById('workHours');
    const statusTagsEl = document.getElementById('statusTags');

    // Cập nhật giờ vào
    if (checkInTimeEl) {
        checkInTimeEl.textContent = checkInRecord && checkInRecord.check_in_time ?
            checkInRecord.check_in_time : '--:--:--';
    }

    // Cập nhật giờ ra
    if (checkOutTimeEl) {
        checkOutTimeEl.textContent = checkOutRecord && checkOutRecord.check_out_time ?
            checkOutRecord.check_out_time : '--:--:--';
    }

    // Tính và hiển thị thời gian làm việc
    if (workHoursEl && checkInRecord && checkOutRecord &&
        checkInRecord.check_in_time && checkOutRecord.check_out_time) {

        const checkInTime = new Date(`2000-01-01T${checkInRecord.check_in_time}`);
        const checkOutTime = new Date(`2000-01-01T${checkOutRecord.check_out_time}`);

        // Tính thời gian làm việc (giờ)
        let hoursWorked = (checkOutTime - checkInTime) / (1000 * 60 * 60);

        // Kiểm tra xem có trải qua giờ nghỉ trưa không
        const afternoonStart = new Date(`2000-01-01T${TIME_CONFIG.AFTERNOON_START}`);
        if (checkInTime < afternoonStart && checkOutTime > afternoonStart) {
            hoursWorked -= TIME_CONFIG.LUNCH_BREAK_HOURS;
        }

        // Chuyển đổi sang giờ và phút
        const hours = Math.floor(hoursWorked);
        const minutes = Math.floor((hoursWorked - hours) * 60);

        workHoursEl.textContent = `${hours} giờ ${minutes} phút`;
    } else if (workHoursEl) {
        workHoursEl.textContent = '-- giờ -- phút';
    }

    // Cập nhật các trạng thái
    updateStatusTags(statuses);
}

/**
* Cập nhật tags trạng thái
*/
function updateStatusTags(statuses) {
    const statusTagsEl = document.getElementById('statusTags');
    if (!statusTagsEl) return;

    statusTagsEl.innerHTML = '';

    if (!statuses || statuses.length === 0) {
        statusTagsEl.innerHTML = `<span class="px-2 py-1 bg-red-100 text-red-800 text-xs font-medium rounded-md dark:bg-red-900 dark:text-red-200">Không có dữ liệu</span>`;
        return;
    }

    // Thêm các tag trạng thái theo thiết kế Tailwind
    if (statuses.includes(ATTENDANCE_STATUS.PRESENT)) {
        statusTagsEl.innerHTML += `<span class="px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-md dark:bg-green-900 dark:text-green-200">Đúng giờ</span>`;
    }
    if (statuses.includes(ATTENDANCE_STATUS.LATE)) {
        statusTagsEl.innerHTML += `<span class="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs font-medium rounded-md dark:bg-yellow-900 dark:text-yellow-200">Đi muộn (8:10-8:30) phạt 30K</span>`;
    }
    if (statuses.includes(ATTENDANCE_STATUS.VERY_LATE)) {
        statusTagsEl.innerHTML += `<span class="px-2 py-1 bg-amber-100 text-amber-800 text-xs font-medium rounded-md dark:bg-amber-900 dark:text-amber-200">Đi muộn (sau 8:30) phạt 50K</span>`;
    }
    if (statuses.includes(ATTENDANCE_STATUS.EARLY_LEAVE)) {
        statusTagsEl.innerHTML += `<span class="px-2 py-1 bg-orange-100 text-orange-800 text-xs font-medium rounded-md dark:bg-orange-900 dark:text-orange-200">Về sớm</span>`;
    }
    if (statuses.includes(ATTENDANCE_STATUS.HALF_DAY_MORNING)) {
        statusTagsEl.innerHTML += `<span class="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded-md dark:bg-blue-900 dark:text-blue-200">Vắng buổi sáng</span>`;
    }
    if (statuses.includes(ATTENDANCE_STATUS.HALF_DAY_AFTERNOON)) {
        statusTagsEl.innerHTML += `<span class="px-2 py-1 bg-purple-100 text-purple-800 text-xs font-medium rounded-md dark:bg-purple-900 dark:text-purple-200">Vắng buổi chiều</span>`;
    }
    if (statuses.includes(ATTENDANCE_STATUS.ABSENT)) {
        statusTagsEl.innerHTML += `<span class="px-2 py-1 bg-red-100 text-red-800 text-xs font-medium rounded-md dark:bg-red-900 dark:text-red-200">Vắng cả ngày</span>`;
    }
}

/**
* Cập nhật ảnh chấm công
*/
async function updateAttendancePhotos(checkInRecord, checkOutRecord) {
    const checkInPhotoEl = document.getElementById('checkInPhoto');
    const checkOutPhotoEl = document.getElementById('checkOutPhoto');
    const checkInTimeLabel = document.getElementById('checkInTimeLabel');
    const checkOutTimeLabel = document.getElementById('checkOutTimeLabel');

    // Cập nhật thời gian trên header
    if (checkInTimeLabel && checkInRecord && checkInRecord.check_in_time) {
        checkInTimeLabel.textContent = checkInRecord.check_in_time;
    } else if (checkInTimeLabel) {
        checkInTimeLabel.textContent = '--:--:--';
    }

    if (checkOutTimeLabel && checkOutRecord && checkOutRecord.check_out_time) {
        checkOutTimeLabel.textContent = checkOutRecord.check_out_time;
    } else if (checkOutTimeLabel) {
        checkOutTimeLabel.textContent = '--:--:--';
    }

    // Xử lý ảnh check-in
    if (checkInPhotoEl) {
        if (checkInRecord && checkInRecord.check_in_time) {
            const userId = User.getUserId();
            const date = checkInRecord.date;

            // Hiển thị trạng thái loading
            showPhotoLoading(checkInPhotoEl);

            try {
                // Kiểm tra xem ảnh có tồn tại không
                const photoExists = await API.checkAttendancePhotoExists(userId, date, 'check_in');

                if (photoExists) {
                    // Lấy URL ảnh và hiển thị
                    const imageUrl = API.getAttendancePhotoUrl(userId, date, 'check_in');
                    showPhoto(checkInPhotoEl, imageUrl);
                } else {
                    // Không có ảnh
                    showNoPhoto(checkInPhotoEl, "Không có ảnh check-in");
                }
            } catch (error) {
                showPhotoError(checkInPhotoEl);
            }
        } else {
            // Không có dữ liệu check-in
            showNoPhoto(checkInPhotoEl);
        }
    }

    // Xử lý ảnh check-out
    if (checkOutPhotoEl) {
        if (checkOutRecord && checkOutRecord.check_out_time) {
            const userId = User.getUserId();
            const date = checkOutRecord.date;

            // Hiển thị trạng thái loading
            showPhotoLoading(checkOutPhotoEl);

            try {
                // Kiểm tra xem ảnh có tồn tại không
                const photoExists = await API.checkAttendancePhotoExists(userId, date, 'check_out');

                if (photoExists) {
                    // Lấy URL ảnh và hiển thị
                    const imageUrl = API.getAttendancePhotoUrl(userId, date, 'check_out');
                    showPhoto(checkOutPhotoEl, imageUrl);
                } else {
                    // Không có ảnh
                    showNoPhoto(checkOutPhotoEl, "Không có ảnh check-out");
                }
            } catch (error) {
                showPhotoError(checkOutPhotoEl);
            }
        } else {
            // Không có dữ liệu check-out
            showNoPhoto(checkOutPhotoEl);
        }
    }
}

/**
* Khởi tạo tính năng upload nhiều file
*/
function initMultiFileUpload() {
    const fileInput = document.getElementById('proofFile');
    const filePreviewContainer = document.getElementById('filePreviewContainer');

    // Xóa Set cũ và tạo mới
    selectedFiles.clear();

    if (!fileInput || !filePreviewContainer) return;

    // Sự kiện khi chọn file
    fileInput.addEventListener('change', () => {
        handleFiles(fileInput.files);
    });

    // Drag and drop events
    const dropArea = fileInput.closest('label');
    if (dropArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => {
                dropArea.classList.add('border-blue-500', 'bg-blue-50', 'dark:bg-blue-900/20');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => {
                dropArea.classList.remove('border-blue-500', 'bg-blue-50', 'dark:bg-blue-900/20');
            }, false);
        });

        dropArea.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            handleFiles(dt.files);
        }, false);
    }

    // Prevent default drag behaviors
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Xử lý các file được chọn
    function handleFiles(fileList) {
        // Chuyển FileList thành mảng để dễ xử lý
        const filesArray = Array.from(fileList);

        // Kiểm tra từng file
        filesArray.forEach(file => {
            // Kiểm tra định dạng file
            const validTypes = ['.pdf', '.jpg', '.jpeg', '.png'];
            const fileExt = '.' + file.name.split('.').pop().toLowerCase();

            if (!validTypes.includes(fileExt)) {
                showToast("Lỗi tải lên", `File "${file.name}" không đúng định dạng. Chỉ chấp nhận PDF, JPG, JPEG, PNG.`, "error");
                return;
            }

            // Kiểm tra kích thước file (max 5MB)
            if (file.size > 5 * 1024 * 1024) {
                showToast("Lỗi tải lên", `File "${file.name}" quá lớn. Kích thước tối đa là 5MB.`, "error");
                return;
            }

            // Thêm file vào danh sách đã chọn
            selectedFiles.add(file);

            // Tạo preview
            createFilePreview(file);
        });
    }
}

/**
* Tạo preview cho file
*/
function createFilePreview(file) {
    const fileId = 'file-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    const filePreviewContainer = document.getElementById('filePreviewContainer');

    if (!filePreviewContainer) return;

    const fileDiv = document.createElement('div');
    fileDiv.className = 'bg-white dark:bg-gray-700 rounded-lg shadow p-2 max-w-[200px]';
    fileDiv.setAttribute('data-file-id', fileId);

    // Định dạng kích thước file
    const fileSize = formatFileSize(file.size);

    // Xác định loại file và icon tương ứng
    const fileExt = file.name.split('.').pop().toLowerCase();
    let fileIconHTML = '';

    if (['jpg', 'jpeg', 'png'].includes(fileExt)) {
        // Tạo preview cho ảnh
        const reader = new FileReader();
        reader.onload = (e) => {
            const imgPreview = fileDiv.querySelector('.file-icon');
            if (imgPreview) {
                imgPreview.innerHTML = `<img src="${e.target.result}" alt="${file.name}" class="w-full h-20 object-cover rounded">`;
            }
        };
        reader.readAsDataURL(file);
        fileIconHTML = `<div class="file-icon h-20 flex items-center justify-center bg-gray-100 dark:bg-gray-800 rounded mb-2"><i class="fas fa-spinner fa-spin text-blue-500"></i></div>`;
    } else if (fileExt === 'pdf') {
        fileIconHTML = `<div class="file-icon h-20 flex items-center justify-center bg-gray-100 dark:bg-gray-800 rounded mb-2"><i class="fas fa-file-pdf text-red-500 text-2xl"></i></div>`;
    } else {
        fileIconHTML = `<div class="file-icon h-20 flex items-center justify-center bg-gray-100 dark:bg-gray-800 rounded mb-2"><i class="fas fa-file text-gray-500 text-2xl"></i></div>`;
    }

    fileDiv.innerHTML = `
        <div class="flex justify-between items-start mb-1">
            <div class="text-sm font-medium truncate max-w-[140px]" title="${file.name}">${file.name}</div>
            <button type="button" class="file-remove text-gray-400 hover:text-red-500 dark:text-gray-500 dark:hover:text-red-400 transition-colors" data-file-id="${fileId}">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                </svg>
            </button>
        </div>
        ${fileIconHTML}
        <div class="text-xs text-gray-500 dark:text-gray-400">${fileSize}</div>
    `;

    // Thêm vào container
    filePreviewContainer.appendChild(fileDiv);

    // Xử lý sự kiện xóa file
    const removeBtn = fileDiv.querySelector('.file-remove');
    if (removeBtn) {
        removeBtn.addEventListener('click', () => {
            // Tìm và xóa file khỏi danh sách đã chọn
            selectedFiles.forEach(selectedFile => {
                if (fileDiv.getAttribute('data-file-id') === fileId) {
                    selectedFiles.delete(selectedFile);
                }
            });

            // Xóa preview
            fileDiv.remove();
        });
    }
}

/**
* Định dạng kích thước file
*/
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}

/**
* Xử lý báo cáo ảnh không đúng
*/
async function handleReportIncorrectPhoto(userId, date, type) {
    try {
        // Hiển thị dialog xác nhận
        if (!confirm(`Bạn muốn báo cáo ảnh ${type === 'check_in' ? 'check-in' : 'check-out'} này không đúng?`)) {
            return;
        }

        // Lấy lý do báo cáo
        const description = prompt('Vui lòng nhập lý do báo cáo:', 'Đây không phải ảnh của tôi');
        if (!description) {
            // Người dùng đã hủy
            return;
        }

        // Hiển thị loading
        showToast("Đang xử lý", "Đang gửi báo cáo, vui lòng đợi...", "info");

        // Chuẩn bị dữ liệu báo cáo
        const reportData = {
            report_type: 'incorrect_photo',
            user_id: userId,
            date: date,
            photo_type: type,
            description: description
        };

        // Gửi báo cáo
        const result = await API.createReport(userId, reportData);

        if (result && result.status === 'success') {
            showToast("Thành công", "Báo cáo của bạn đã được gửi thành công!", "success");
        } else {
            // Hiển thị message từ API nếu có
            const errorMessage = result?.message || "Không thể gửi báo cáo. Vui lòng thử lại!";
            showToast("Lỗi", errorMessage, "error");
        }
    } catch (error) {
        showToast("Lỗi", "Đã xảy ra lỗi khi gửi báo cáo. Vui lòng thử lại sau.", "error");
    }
}

/**
* Xử lý báo cáo lỗi máy chấm công
*/
async function handleReportMachineError(userId, date, formData) {
    try {
        // Hiển thị loading
        showToast("Đang xử lý", "Đang gửi báo cáo, vui lòng đợi...", "info");

        // Chuẩn bị dữ liệu báo cáo
        const reportData = {
            report_type: 'machine_error',
            user_id: userId,
            date: date,
            error_type: formData.errorType,
            description: formData.errorDescription || '',
            error_time: formData.errorTime || ''
        };

        // Gửi báo cáo
        const result = await API.createReport(userId, reportData);

        if (result && result.status === 'success') {
            showToast("Thành công", "Báo cáo lỗi máy chấm công đã được gửi thành công!", "success");

            // Đóng form sau khi gửi thành công
            const machineErrorSection = document.getElementById('machineErrorSection');
            if (machineErrorSection) {
                machineErrorSection.classList.add('hidden');
            }

            // Reset form
            const machineErrorForm = document.getElementById('machineErrorForm');
            if (machineErrorForm) {
                machineErrorForm.reset();
            }
        } else {
            showToast("Lỗi", result?.message || "Không thể gửi báo cáo. Vui lòng thử lại sau.", "error");
        }
    } catch (error) {
        showToast("Lỗi", "Đã xảy ra lỗi khi gửi báo cáo. Vui lòng thử lại sau.", "error");
    }
}

/**
* Xử lý gửi giấy tờ xin phép
*/
async function handleSubmitLeaveRequest(userId, date, formData, files) {
    try {
        // Hiển thị loading
        showToast("Đang xử lý", "Đang gửi giấy tờ, vui lòng đợi...", "info");

        // Chuẩn bị dữ liệu báo cáo
        const reportData = {
            report_type: 'leave_request',
            user_id: userId,
            date: date,
            request_type: formData.proofType,
            description: formData.proofDescription || ''
        };

        // Gửi báo cáo kèm file
        const result = await API.createReport(userId, reportData, files);

        if (result && result.status === 'success') {
            showToast("Thành công", "Giấy tờ xin phép đã được gửi thành công!", "success");

            // Đóng form sau khi gửi thành công
            const proofUploadSection = document.getElementById('proofUploadSection');
            if (proofUploadSection) {
                proofUploadSection.classList.add('hidden');
            }

            // Reset form
            const proofUploadForm = document.getElementById('proofUploadForm');
            if (proofUploadForm) {
                proofUploadForm.reset();
            }

            // Xóa tất cả các preview file
            const filePreviewContainer = document.getElementById('filePreviewContainer');
            if (filePreviewContainer) {
                filePreviewContainer.innerHTML = '';
            }

            // Xóa tất cả file đã chọn
            selectedFiles.clear();
        } else {
            showToast("Lỗi", result?.message || "Không thể gửi giấy tờ. Vui lòng thử lại sau.", "error");
        }
    } catch (error) {
        showToast("Lỗi", "Đã xảy ra lỗi khi gửi giấy tờ. Vui lòng thử lại sau.", "error");
    }
}

// Export hàm showAttendanceModal để sử dụng trong tracking.js
export { showAttendanceModal };