import User from "../utils/user.js";
import API from "../core/api.js";
import { showToast } from "../utils/toast.js";

const CARD_SELECTORS = {
    'tracking': 'a[href="/tracking"]',
    'approvals': 'a[href="/approvals"]',
    'export': 'a[href="/export"]',
    'users': 'a[href="/users"]',
    'feedbacks': 'a[href="/feedbacks"]',
    'settings': 'a[href="/settings"]'
};

// Hàm cập nhật lời chào với tên người dùng
function updateGreeting() {
    try {
        const userName = User.getName();
        const greetingElement = document.querySelector('h1.text-xl.sm\\:text-2xl.font-bold.text-white.mb-2');

        if (greetingElement && userName) {
            greetingElement.textContent = `Xin chào, ${userName}`;
        } else if (greetingElement) {
            // Fallback nếu không lấy được tên
            greetingElement.textContent = 'Xin chào';
        }
    } catch (error) {

        // Fallback khi có lỗi
        const greetingElement = document.querySelector('h1.text-xl.sm\\:text-2xl.font-bold.text-white.mb-2');
        if (greetingElement) {
            greetingElement.textContent = 'Xin chào';
        }
    }
}

function updateUserAvatar(avatarElement, userId) {
    if (!avatarElement || !userId) return;

    const avatarUrl = API.getAvatarUrl(userId);
 
    const testImg = new Image();
    testImg.onload = function () {
        avatarElement.innerHTML = '';
        avatarElement.className = 'w-10 h-10 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden shadow-sm';

        const imgElement = document.createElement('img');
        imgElement.src = avatarUrl;
        imgElement.alt = 'Avatar';
        imgElement.className = 'w-full h-full object-cover rounded-full';
        avatarElement.appendChild(imgElement);
    };

    testImg.src = avatarUrl;
}


/**
 * Cập nhật thông tin user trong header
 */
function updateUserHeader() {
    const userDisplay = User.getUserDisplay();

    // Lấy các elements
    const userAvatar = document.getElementById('userAvatar');
    const userName = document.getElementById('userName');
    const userRoleBadge = document.getElementById('userRoleBadge');


    // Cập nhật avatar
    updateUserAvatar(userAvatar, userDisplay.userId, userDisplay.displayName);

    // Cập nhật tên user
    if (userName) {
        userName.textContent = userDisplay.displayName;
    }

    // Cập nhật role badge
    if (userRoleBadge) {
        userRoleBadge.textContent = userDisplay.roleDisplay;
        userRoleBadge.className = `px-2 py-1 text-xs font-medium rounded-full ${User.getRoleBadgeColor(userDisplay.role)}`;
    }
}

async function handleLogout() {
    const logoutBtn = document.getElementById('logoutBtn');

    try {
        // Bắt đầu: vô hiệu hoá nút và gán icon loading
        if (logoutBtn) {
            logoutBtn.disabled = true;
            logoutBtn.innerHTML = `
                <svg class="animate-spin w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span class="hidden sm:block">Đăng xuất</span>
            `;
        }

        // Gọi API logout
        const response = await API.logout();

        if (response.status === 'success') {
            User.logout();

            showToast(
                "Đăng xuất thành công",
                "Bạn đã đăng xuất khỏi hệ thống",
                'success',
                2000
            );

            setTimeout(() => {
                window.location.href = '/';
            }, 1500);
        } else {
            throw new Error(response.message || 'Đăng xuất thất bại');
        }

    } catch (error) {
        showToast(
            "Lỗi đăng xuất",
            error.message || "Có lỗi xảy ra khi đăng xuất",
            'error',
            3000
        );

        const forceLogout = confirm("Có lỗi xảy ra. Bạn có muốn buộc đăng xuất không?");
        if (forceLogout) {
            User.logout();
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 500);
        }

    } finally {
        // Chỉ re-enable nếu user chưa logout (không redirect)
        if (logoutBtn && User.isLoggedIn()) {
            logoutBtn.disabled = false;
        }
    }
}


/**
 * Khởi tạo event listeners cho logout
 */
function initLogoutHandler() {
    const logoutBtn = document.getElementById('logoutBtn');
    logoutBtn.addEventListener('click', handleLogout);
}

/**
 * Kiểm tra session và tự động logout nếu cần
 */
function checkSessionValidity() {
    if (!User.isSessionValid()) {
        showToast(
            "Phiên đăng nhập hết hạn",
            "Bạn sẽ được chuyển về trang đăng nhập",
            'warning',
            3000
        );

        setTimeout(() => {
            User.logout();
            window.location.href = '/';
        }, 2000);
    }
}

function updateDateTime() {
    const now = new Date();

    // Mảng các thứ trong tuần
    const dayNames = [
        'Chủ nhật', 'Thứ hai', 'Thứ ba', 'Thứ tư',
        'Thứ năm', 'Thứ sáu', 'Thứ bảy'
    ];

    // Lấy thông tin ngày
    const dayOfWeek = dayNames[now.getDay()];
    const day = String(now.getDate()).padStart(2, '0');
    const month = String(now.getMonth() + 1).padStart(2, '0'); // getMonth() trả về 0-11
    const year = now.getFullYear();

    // Lấy thông tin giờ
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');

    // Định dạng ngày: Thứ, dd/mm/yyyy
    const formattedDate = `${dayOfWeek}, ${day}/${month}/${year}`;

    // Định dạng giờ: hh:mm
    const formattedTime = `${hours}:${minutes}`;

    // Cập nhật DOM
    const dateElement = document.getElementById('currentDate');
    const timeElement = document.getElementById('currentTime');

    if (dateElement) {
        dateElement.textContent = formattedDate;
    }

    if (timeElement) {
        timeElement.textContent = formattedTime;
    }
}

// Hàm cập nhật badge phê duyệt
async function updateApprovalBadge() {
    try {
        // Gọi API với tham số mặc định (ngày hôm nay, tất cả loại báo cáo)
        const response = await API.getPendingReportsCount();

        // Lấy các elements cần thiết
        const badgeElement = document.querySelector('.absolute.-top-2.-right-2');
        const pendingCountElement = document.getElementById('pendingApprovals');

        // Kiểm tra response có thành công và có data không
        if (response && response.status === 'success' && response.data) {
            const totalPending = response.data.total_pending;

            if (totalPending > 0) {
                // Có phê duyệt pending - hiển thị badge
                if (badgeElement) {
                    badgeElement.classList.remove('hidden');
                }

                if (pendingCountElement) {
                    pendingCountElement.textContent = totalPending;
                }

            } else {
                // Không có phê duyệt pending - ẩn badge
                if (badgeElement) {
                    badgeElement.classList.add('hidden');
                }
            }
        } else {
            // Lỗi API hoặc không có data - ẩn badge
            if (badgeElement) {
                badgeElement.classList.add('hidden');
            }
        }

    } catch (error) {
        // Ẩn badge khi có lỗi
        const badgeElement = document.querySelector('.absolute.-top-2.-right-2');

        if (badgeElement) {
            badgeElement.classList.add('hidden');
        }
    }
}


/**
 * Kiểm tra user có quyền truy cập trang không
 * @param {string} page - Tên trang cần kiểm tra
 * @param {Object} userPermissions - Object quyền của user từ backend (key: value)
 * @returns {boolean} - True nếu có quyền, false nếu không
 */
function hasPermission(page, userPermissions) {
    // Kiểm tra xem user có quyền cho trang này không
    // userPermissions là object: {approve: true, export: false, ...}
    return userPermissions && userPermissions[page] === true;
}


/**
 * Hiển thị card với animation mượt mà
 */
function showCard(cardName, delay = 0) {
    const cardElement = document.querySelector(CARD_SELECTORS[cardName]);
    if (!cardElement) return;

    setTimeout(() => {
        // Bỏ hidden và thêm animation classes
        cardElement.classList.remove('hidden');
        cardElement.classList.add(
            'opacity-0',           // Bắt đầu trong suốt
            'translate-y-4',       // Bắt đầu ở dưới
            'transition-all',      // Smooth transition
            'duration-500',        // 500ms animation
            'ease-out'            // Easing
        );

        // Trigger animation sau 1 frame
        requestAnimationFrame(() => {
            cardElement.classList.remove('opacity-0', 'translate-y-4');
            cardElement.classList.add('opacity-100', 'translate-y-0');
        });
    }, delay);
}

function applyPermissions() {
    try {
        const userPermissions = User.getPermissions();
        if (!userPermissions) {
            return;
        }
        let hasApprovalAccess = false; // Track xem có quyền approvals không

        // Chỉ hiển thị cards được phép
        Object.keys(CARD_SELECTORS).forEach((page, index) => {
            const hasAccess = hasPermission(page, userPermissions);

            if (hasAccess) {
                showCard(page, index * 100);

                // Kiểm tra nếu là card approvals
                if (page === 'approvals') {
                    hasApprovalAccess = true;
                }
            } else {
            }
        });

        // Chỉ gọi updateApprovalBadge nếu có quyền approvals
        if (hasApprovalAccess) {
            updateApprovalBadge();
        } else {
        }

    } catch (error) {
    }
}


function userHasApprovalAccess() {
    try {
        const userPermissions = User.getPermissions();
        return hasPermission('approve', userPermissions);
    } catch (error) {
        return false;
    }
}

// Gọi hàm ngay lập tức để hiển thị thời gian hiện tại
updateDateTime();

// Cập nhật mỗi giây (60000ms)
setInterval(updateDateTime, 60000);

// THAY BẰNG
setInterval(() => {
    if (userHasApprovalAccess()) {
        updateApprovalBadge();
    }
}, 30000);


// Tùy chọn: Cập nhật khi user focus vào tab
document.addEventListener('visibilitychange', function () {
    if (!document.hidden && userHasApprovalAccess()) {
        updateApprovalBadge();
    }
});

document.addEventListener('DOMContentLoaded', () => {
    updateUserHeader();
    initLogoutHandler();
    checkSessionValidity();
    updateGreeting();
    applyPermissions();
});