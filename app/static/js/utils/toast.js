/**
 * Toast Notification System - Phiên bản hiện đại
 * 
 * Hệ thống hiển thị thông báo Toast tự động hỗ trợ dark mode
 * Cách sử dụng:
 * 1. Import file này: <script src="toast.js"></script>
 * 2. Gọi hàm showToast:
 *    - showToast('Tiêu đề', 'Mô tả (tùy chọn)', 'success') - thành công (màu xanh lá)
 *    - showToast('Tiêu đề', 'Mô tả (tùy chọn)', 'error') - lỗi (màu đỏ)
 *    - showToast('Tiêu đề', 'Mô tả (tùy chọn)', 'warning') - cảnh báo (màu vàng)
 *    - showToast('Tiêu đề', 'Mô tả (tùy chọn)', 'info') - thông tin (màu xanh dương)
 * 
 * Tùy chọn thêm:
 *    - showToast('Tiêu đề', 'Mô tả', 'success', 5000) - hiển thị trong 5 giây
 */

// Khởi tạo container cho toast nếu chưa tồn tại
function initToastContainer() {
  if (!document.getElementById('toast-container')) {
    const toastContainer = document.createElement('div');
    toastContainer.id = 'toast-container';
    toastContainer.className = 'toast-container';
    document.body.appendChild(toastContainer);
  }
  return document.getElementById('toast-container');
}

/**
 * Hiển thị toast notification
 * @param {string} title - Tiêu đề thông báo
 * @param {string} description - Mô tả chi tiết (tùy chọn)
 * @param {string} type - Loại thông báo: 'success', 'error', 'warning', 'info'
 * @param {number} duration - Thời gian hiển thị (ms), mặc định là 3000ms
 */
function showToast(title, description = '', type = 'info', duration = 3000) {
  const container = initToastContainer();
  
  // Kiểm tra dark mode
  const isDarkMode = document.documentElement.classList.contains('dark');
  
  // Tạo toast element
  const toast = document.createElement('div');
  
  // Base classes cho tất cả loại toast
  toast.className = 'toast toast-' + type;
  
  // Thêm style inline cho viền trái
  let borderColor = '';
  switch(type) {
    case 'success':
      borderColor = '#28c840';
      break;
    case 'error':
      borderColor = '#ff5f57';
      break;
    case 'warning':
      borderColor = '#ffcc00';
      break;
    case 'info':
    default:
      borderColor = '#0071e3';
      break;
  }
  
  // Đảm bảo viền trái có màu đúng
  toast.style.borderLeft = '4px solid ' + borderColor;
  
  // Thêm icon tùy theo loại
  let icon = '';
  switch(type) {
    case 'success':
      icon = `
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-green-500">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
          <polyline points="22 4 12 14.01 9 11.01"></polyline>
        </svg>
      `;
      break;
    case 'error':
      icon = `
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-red-500">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="15" y1="9" x2="9" y2="15"></line>
          <line x1="9" y1="9" x2="15" y2="15"></line>
        </svg>
      `;
      break;
    case 'warning':
      icon = `
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-yellow-500">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
          <line x1="12" y1="9" x2="12" y2="13"></line>
          <line x1="12" y1="17" x2="12.01" y2="17"></line>
        </svg>
      `;
      break;
    case 'info':
    default:
      icon = `
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-blue-500">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="16" x2="12" y2="12"></line>
          <line x1="12" y1="8" x2="12.01" y2="8"></line>
        </svg>
      `;
      break;
  }
  
  // Nội dung toast
  toast.innerHTML = `
    <div class="toast-icon">
      ${icon}
    </div>
    <div class="toast-content">
      <div class="toast-message">${title}</div>
      ${description ? `<div class="toast-description">${description}</div>` : ''}
    </div>
    <button type="button" class="toast-close" aria-label="Đóng">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="18" y1="6" x2="6" y2="18"></line>
        <line x1="6" y1="6" x2="18" y2="18"></line>
      </svg>
    </button>
    <div class="toast-progress-container">
      <div class="toast-progress-bar"></div>
    </div>
  `;
  
  // Thêm toast vào container
  container.appendChild(toast);
  
  // Lấy reference tới progress bar
  const progressBar = toast.querySelector('.toast-progress-bar');
  
  // Hiệu ứng hiển thị toast
  setTimeout(() => {
    toast.classList.add('show');
  }, 10);
  
  // Thiết lập progress bar
  let width = 100;
  const interval = 10;
  const decrement = interval * (100 / duration);
  const progressInterval = setInterval(() => {
    width -= decrement;
    progressBar.style.width = `${width}%`;
    
    if (width <= 0) {
      clearInterval(progressInterval);
    }
  }, interval);
  
  // Tự động xóa toast sau thời gian duration
  const timeoutId = setTimeout(() => {
    removeToast(toast);
  }, duration);
  
  // Thêm sự kiện cho nút đóng
  const closeButton = toast.querySelector('.toast-close');
  closeButton.addEventListener('click', () => {
    clearTimeout(timeoutId);
    clearInterval(progressInterval);
    removeToast(toast);
  });
  
  // Trả về toast element để có thể tùy chỉnh thêm nếu cần
  return toast;
}

/**
 * Xóa toast
 * @param {HTMLElement} toast - Element toast cần xóa
 */
function removeToast(toast) {
  toast.classList.remove('show');
  
  // Xóa DOM sau khi hoàn tất animation
  setTimeout(() => {
    toast.remove();
  }, 300);
}

// Các hàm tiện ích
function successToast(title, description = '', duration) {
  return showToast(title, description, 'success', duration);
}

function errorToast(title, description = '', duration) {
  return showToast(title, description, 'error', duration);
}

function warningToast(title, description = '', duration) {
  return showToast(title, description, 'warning', duration);
}

function infoToast(title, description = '', duration) {
  return showToast(title, description, 'info', duration);
}

// Export các hàm để sử dụng
// if (typeof module !== 'undefined' && module.exports) {
//   module.exports = {
//     showToast,
//     successToast,
//     errorToast,
//     warningToast,
//     infoToast
//   };
// }


export {
  showToast,
  successToast,
  errorToast,
  warningToast,
  infoToast
};


// Đảm bảo các hàm có sẵn trong global scope
window.showToast = showToast;
window.successToast = successToast;
window.errorToast = errorToast;
window.warningToast = warningToast;
window.infoToast = infoToast;

// Lắng nghe thay đổi dark mode
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
  if (e.matches) {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
});

// Khởi tạo dark mode dựa trên preference
if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
  document.documentElement.classList.add('dark');
} else {
  document.documentElement.classList.remove('dark');
}