/**
 * User Utility Functions
 * Quản lý thông tin người dùng trong localStorage
 */

class UserManager {
    constructor() {
        this.storageKey = 'user_info';
    }

    /**
     * Lưu thông tin user vào localStorage
     * @param {Object} userInfo - Thông tin user
     */
    setUser(userInfo) {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(userInfo));
            return true;
        } catch (error) {
            console.error('Lỗi khi lưu thông tin user:', error);
            return false;
        }
    }

    /**
     * Lấy thông tin user từ localStorage
     * @returns {Object|null} - Thông tin user hoặc null nếu không có
     */
    getUser() {
        try {
            const userInfo = localStorage.getItem(this.storageKey);
            return userInfo ? JSON.parse(userInfo) : null;
        } catch (error) {
            console.error('Lỗi khi đọc thông tin user:', error);
            return null;
        }
    }

    /**
     * Kiểm tra user đã đăng nhập chưa
     * @returns {boolean}
     */
    isLoggedIn() {
        const user = this.getUser();
        return user !== null && user.user_id;
    }

    /**
     * Lấy ID của user
     * @returns {string|null}
     */
    getUserId() {
        const user = this.getUser();
        return user ? user.user_id : null;
    }

    /**
     * Lấy username
     * @returns {string|null}
     */
    getUsername() {
        const user = this.getUser();
        return user ? user.username : null;
    }

    /**
     * Lấy tên hiển thị của user
     * @returns {string|null}
     */
    getName() {
        const user = this.getUser();
        return user ? (user.name || user.username) : null;
    }

    /**
     * Lấy vai trò của user
     * @returns {string|null}
     */
    getRole() {
        const user = this.getUser();
        return user ? user.role : null;
    }

    /**
     * Lấy URL avatar
     * @returns {string|null}
     */
    getAvatarUrl() {
        const user = this.getUser();
        return user ? user.avatar_url : null;
    }

    /**
     * Lấy quyền hạn của user
     * @returns {Object}
     */
    getPermissions() {
        const user = this.getUser();
        return user ? (user.permissions || {}) : {};
    }

    /**
     * Kiểm tra user có quyền cụ thể không
     * @param {string} permission - Tên quyền cần kiểm tra
     * @returns {boolean}
     */
    hasPermission(permission) {
        const permissions = this.getPermissions();
        return permissions[permission] === true;
    }

    /**
     * Kiểm tra user có vai trò admin không
     * @returns {boolean}
     */
    isAdmin() {
        const role = this.getRole();
        return role === 'admin' || role === 'administrator';
    }

    /**
     * Kiểm tra user có vai trò manager không
     * @returns {boolean}
     */
    isManager() {
        const role = this.getRole();
        return role === 'manager' || this.isAdmin();
    }

    /**
     * Cập nhật thông tin user (merge với dữ liệu hiện tại)
     * @param {Object} updateData - Dữ liệu cần cập nhật
     * @returns {boolean}
     */
    updateUser(updateData) {
        const currentUser = this.getUser();
        if (!currentUser) {
            return false;
        }

        const updatedUser = { ...currentUser, ...updateData };
        return this.setUser(updatedUser);
    }

    /**
     * Cập nhật avatar URL
     * @param {string} avatarUrl - URL avatar mới
     * @returns {boolean}
     */
    updateAvatar(avatarUrl) {
        return this.updateUser({ avatar_url: avatarUrl });
    }

    /**
     * Cập nhật tên hiển thị
     * @param {string} name - Tên mới
     * @returns {boolean}
     */
    updateName(name) {
        return this.updateUser({ name: name });
    }

    /**
     * Xóa thông tin user (đăng xuất)
     */
    logout() {
        try {
            localStorage.removeItem(this.storageKey);
            return true;
        } catch (error) {
            console.error('Lỗi khi đăng xuất:', error);
            return false;
        }
    }

    /**
     * Lấy thông tin user để hiển thị (formatted)
     * @returns {Object}
     */
    getUserDisplay() {
        const user = this.getUser();
        if (!user) {
            return {
                isLoggedIn: false,
                displayName: 'Khách',
                avatar: '/default-avatar.png'
            };
        }

        return {
            isLoggedIn: true,
            displayName: user.name || user.username,
            username: user.username,
            role: user.role,
            userId: user.user_id,
            avatar: user.avatar_url || '/default-avatar.png',
            roleDisplay: this.getRoleDisplay(user.role)
        };
    }

    getRoleBadgeColor(role) {
        const colorMap = {
            'super_admin': 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
            'admin': 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
            'user': 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
        };
        return colorMap[role] || 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400';
    }

    /**
     * Chuyển đổi role thành text hiển thị
     * @param {string} role - Vai trò
     * @returns {string}
     */
    getRoleDisplay(role) {
        const roleMap = {
            'super_admin': 'Super Admin',
            'admin': 'Admin',
            'user': 'User'
        };
        return roleMap[role] || 'Người dùng';
    }

    /**
     * Kiểm tra phiên đăng nhập có hợp lệ không (có thể thêm logic kiểm tra token expire)
     * @returns {boolean}
     */
    isSessionValid() {
        // Có thể mở rộng để kiểm tra token expiry, etc.
        return this.isLoggedIn();
    }

    /**
     * Lấy thông tin tóm tắt để log
     * @returns {string}
     */
    getUserSummary() {
        const user = this.getUser();
        if (!user) return 'Chưa đăng nhập';
        
        return `${user.name || user.username} (${this.getRoleDisplay(user.role)})`;
    }
}

// Tạo instance duy nhất
const User = new UserManager();

// Export default instance
export default User;

// Export class nếu cần tạo instance riêng
export { UserManager };