// Import API và showToast
import API from '../core/api.js';
import { showToast } from '../utils/toast.js';

// Đợi DOM đã tải hoàn tất
document.addEventListener('DOMContentLoaded', function () {
    // Các phần tử DOM
    const loginForm = document.getElementById('loginForm');
    const usernameInput = document.getElementById('email'); // ID là 'email' nhưng thực tế là username
    const passwordInput = document.getElementById('password');
    const rememberCheckbox = document.getElementById('remember');
    const togglePasswordBtn = document.getElementById('togglePassword');
    const eyeIcon = document.getElementById('eyeIcon');

    // Xử lý sự kiện toggle hiển thị mật khẩu
    togglePasswordBtn.addEventListener('click', function () {
        const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
        passwordInput.setAttribute('type', type);

        // Thay đổi icon tùy thuộc vào trạng thái mật khẩu
        if (type === 'text') {
            // Icon "mắt bị gạch" khi đang hiển thị mật khẩu
            eyeIcon.innerHTML = `
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
            `;
        } else {
            // Icon "mắt thường" khi đang ẩn mật khẩu
            eyeIcon.innerHTML = `
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            `;
        }
    });

    // Xử lý sự kiện submit form đăng nhập
    loginForm.addEventListener('submit', async function (e) {
        e.preventDefault();

        // Lấy giá trị từ form
        const username = usernameInput.value.trim();
        const password = passwordInput.value;
        const remember = rememberCheckbox.checked;

        // Kiểm tra trường dữ liệu trước khi gửi
        if (!username || !password) {
            showToast('Thiếu thông tin', 'Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu', 'error', 3000);
            return;
        }

        // Thay đổi nút submit để hiển thị trạng thái đang xử lý
        const submitButton = loginForm.querySelector('button[type="submit"]');
        const originalButtonText = submitButton.innerHTML;
        submitButton.disabled = true;
        submitButton.innerHTML = `
            <svg class="animate-spin mr-0.1 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span class="w-24 inline-block">Đang xử lý...</span>
        `;

        try {
            // Gọi API đăng nhập
            const response = await API.login(username, password, remember);

            if (response.status === 'success') {
                const user = response.data.user;

                const userInfo = {
                    user_id: user.user_id,
                    username: user.username,
                    name: user.name || user.username,
                    role: user.role,
                    avatar_file: user.avatar_file,
                    permissions: user.permissions || {}
                };

                localStorage.setItem('user_info', JSON.stringify(userInfo));

                // Hiển thị toast chào mừng và điều hướng sau khi toast hiển thị xong
                showToast('Đăng nhập thành công', `Chào mừng ${userInfo.name} đã quay trở lại!`, 'success', 3000);

                // Đợi toast hiển thị xong rồi chuyển hướng đến dashboard
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 2000);
            } else {
                // Hiển thị thông báo lỗi bằng toast
                showToast('Đăng nhập thất bại', response.message || 'Tên đăng nhập hoặc mật khẩu không chính xác', 'error', 3000);

                // Khôi phục nút submit
                submitButton.disabled = false;
                submitButton.innerHTML = originalButtonText;
            }
        } catch (error) {

            // Hiển thị thông báo lỗi bằng toast
            showToast('Lỗi kết nối', 'Có lỗi xảy ra khi kết nối đến máy chủ. Vui lòng thử lại sau.', 'error', 3000);

            // Khôi phục nút submit
            submitButton.disabled = false;
            submitButton.innerHTML = originalButtonText;
        }
    });

    // Tự động focus vào ô tên đăng nhập khi trang tải
    usernameInput.focus();

    const forgotPasswordLink = document.getElementById('forgotPasswordLink');
    if (forgotPasswordLink) {
        forgotPasswordLink.addEventListener('click', (e) => {
            e.preventDefault(); // Ngăn link chuyển trang
            showToast(
                'Quên thì chịu thui', 
                'Chức năng này chưa được phát triển ^^', 
                'info'
            );
        });
    }
});