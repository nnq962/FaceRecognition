// darkmode.js
function setupDarkMode() {
    // Hàm thiết lập darkmode dựa trên trạng thái hệ thống
    function applyDarkMode() {
      if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
    }
  
    // Áp dụng ngay khi trang tải
    applyDarkMode();
  
    // Lắng nghe thay đổi của hệ thống
    const darkModeMediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    // Sử dụng addEventListener nếu được hỗ trợ (mới)
    if (darkModeMediaQuery.addEventListener) {
      darkModeMediaQuery.addEventListener('change', (e) => {
        applyDarkMode();
      });
    } else if (darkModeMediaQuery.addListener) {
      // Fallback cho trình duyệt cũ
      darkModeMediaQuery.addListener((e) => {
        applyDarkMode();
      });
    }
  }
  
  // Gọi hàm setup khi trang đã tải xong
  document.addEventListener('DOMContentLoaded', setupDarkMode);