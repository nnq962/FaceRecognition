import User from "../utils/user.js";
import API from "../core/api.js";
import { showToast } from "../utils/toast.js";


class SettingsPage {
    constructor() {
        this.currentUser = null;
        this.originalData = {};
        this.init();
    }

    async init() {
        try {
            await this.loadCurrentUser();
            this.setupEventListeners();
            this.populateForm();
        } catch (error) {
            console.error('Error initializing settings page:', error);
            showToast('Lỗi', 'Không thể tải thông tin tài khoản', 'error');
        }
    }

    async loadCurrentUser() {
        try {
            const response = await API.getUser(User.getUserId());
            this.currentUser = response.data;

            this.originalData = { ...this.currentUser };
        } catch (error) {
            console.error('Error loading current user:', error);
            throw error;
        }
    }

    populateForm() {
        if (!this.currentUser) return;

        // Populate display fields (read-only)
        document.getElementById('name-display').textContent = this.currentUser.name || 'Chưa cập nhật';
        document.getElementById('department-display').textContent = this.currentUser.room_id || 'Chưa cập nhật';

        // Populate editable fields
        document.getElementById('email').value = this.currentUser.email || '';
        document.getElementById('telegram_id').value = this.currentUser.telegram_id || '';

        // Update display elements
        document.getElementById('user-name-display').textContent = this.currentUser.name || 'Chưa cập nhật';
        const roleBadge = document.getElementById('role-badge');
        roleBadge.textContent = this.getRoleDisplayName(this.currentUser.role);
        roleBadge.className = 'inline-flex items-center px-3 py-1 rounded-full text-xs font-medium transition-colors duration-200 ' + User.getRoleBadgeColor(this.currentUser.role);

        // Update avatar
        this.updateAvatarDisplay();
    }

    getRoleDisplayName(role) {
        const roleMap = {
            'user': 'User',
            'admin': 'Admin',
            'super_admin': 'Super Admin'
        };
        return roleMap[role] || role;
    }
    
    updateAvatarDisplay() {
        const avatarImg = document.getElementById('current-avatar');
        const defaultAvatar = document.getElementById('default-avatar');
    
        // Luôn thử tải avatar từ API
        avatarImg.src = API.getAvatarUrl(User.getUserId());
    
        // Nếu không load được ảnh (404 chẳng hạn) → hiển thị ảnh mặc định
        avatarImg.onerror = () => {
            avatarImg.classList.add('hidden');
            defaultAvatar.classList.remove('hidden');
        };
    
        avatarImg.onload = () => {
            avatarImg.classList.remove('hidden');
            defaultAvatar.classList.add('hidden');
        };
    }
    

    setupEventListeners() {
        // Avatar change
        document.getElementById('change-avatar-btn').addEventListener('click', () => {
            document.getElementById('avatar-input').click();
        });

        document.getElementById('avatar-input').addEventListener('change', (e) => {
            this.handleAvatarChange(e);
        });

        // Profile form submission
        document.getElementById('profile-form').addEventListener('submit', (e) => {
            this.handleFormSubmit(e);
        });

        // Cancel button
        document.getElementById('cancel-btn').addEventListener('click', () => {
            this.resetForm();
        });

        // Change password modal
        document.getElementById('change-password-btn').addEventListener('click', () => {
            this.showPasswordModal();
        });

        document.getElementById('close-password-modal').addEventListener('click', () => {
            this.hidePasswordModal();
        });

        document.getElementById('cancel-password-btn').addEventListener('click', () => {
            this.hidePasswordModal();
        });

        document.getElementById('change-password-form').addEventListener('submit', (e) => {
            this.handlePasswordChange(e);
        });

        // Close modal on backdrop click
        document.getElementById('change-password-modal').addEventListener('click', (e) => {
            if (e.target.id === 'change-password-modal') {
                this.hidePasswordModal();
            }
        });

        // ESC key to close modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hidePasswordModal();
            }
        });

        // Real-time form validation
        const inputs = document.querySelectorAll('#profile-form input');
        inputs.forEach(input => {
            input.addEventListener('input', () => {
                this.checkFormChanges();
            });
        });
    }

    async handleAvatarChange(e) {
        const file = e.target.files[0];
        if (!file) return;
    
        // Validate file type
        if (!file.type.startsWith('image/')) {
            showToast('Lỗi', 'Vui lòng chọn file hình ảnh', 'error');
            return;
        }
    
        // Validate file size (max 10MB)
        if (file.size > 10 * 1024 * 1024) {
            showToast('Lỗi', 'Kích thước file không được vượt quá 10MB', 'error');
            return;
        }
    
        try {
            this.showLoading(true);
    
            const response = await API.uploadAvatar(User.getUserId(), file);
            console.log('Avatar upload response:', response);
    
            if (response.status === 'success') {
                showToast('Thành công', 'Đã cập nhật avatar', 'success');
                this.updateAvatarDisplay(); // Không cần truy cập avatar_file nữa
            } else {
                showToast('Lỗi', 'Có lỗi xảy ra khi cập nhật avatar', 'error');
            }
    
        } catch (error) {
            console.error('Error updating avatar:', error);
            showToast('Lỗi', 'Có lỗi xảy ra khi cập nhật avatar', 'error');
        } finally {
            this.showLoading(false);
            e.target.value = ''; // Reset input file
        }
    }


    async handleFormSubmit(e) {
        e.preventDefault();

        if (!this.validateForm()) {
            return;
        }

        try {
            this.showLoading(true);

            const formData = this.collectFormData();

            const response = await API.updateUser(User.getUserId(), formData);

            // Temporary success simulation
            if (Object.keys(formData).length > 0) {
                showToast('Thành công', 'Đã lưu thông tin tài khoản', 'success');
            } else {
                showToast('Thông báo', 'Không có thay đổi nào để lưu', 'info');
            }

        } catch (error) {
            console.error('Error updating profile:', error);
            showToast('Lỗi', 'Có lỗi xảy ra khi cập nhật thông tin', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    validateForm() {
        const email = document.getElementById('email').value.trim();

        if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            showToast('Lỗi', 'Email không hợp lệ', 'error');
            return false;
        }

        return true;
    }

    collectFormData() {
        const formData = {};

        const email = document.getElementById('email').value.trim();
        const telegramId = document.getElementById('telegram_id').value.trim();

        // Only include changed fields
        if (email !== (this.originalData.email || '')) {
            formData.email = email || null;
        }

        if (telegramId !== (this.originalData.telegram_id || '')) {
            formData.telegram_id = telegramId || null;
        }

        return formData;
    }

    resetForm() {
        this.populateForm();
        this.checkFormChanges();
    }

    checkFormChanges() {
        const currentData = {
            email: document.getElementById('email').value.trim(),
            telegram_id: document.getElementById('telegram_id').value.trim()
        };

        const originalData = {
            email: this.originalData.email || '',
            telegram_id: this.originalData.telegram_id || ''
        };

        const hasChanges = Object.keys(currentData).some(key =>
            currentData[key] !== originalData[key]
        );

        const saveBtn = document.getElementById('save-btn');
        const cancelBtn = document.getElementById('cancel-btn');

        saveBtn.disabled = !hasChanges;
        cancelBtn.disabled = !hasChanges;
    }

    showPasswordModal() {
        const modal = document.getElementById('change-password-modal');
        modal.classList.remove('pointer-events-none');

        requestAnimationFrame(() => {
            modal.classList.remove('opacity-0');
            modal.querySelector('div').classList.remove('scale-95');
            modal.querySelector('div').classList.add('scale-100');
        });

        // Focus first input
        setTimeout(() => {
            document.getElementById('current-password').focus();
        }, 150);

        // Prevent body scroll
        document.body.style.overflow = 'hidden';
    }

    hidePasswordModal() {
        const modal = document.getElementById('change-password-modal');
        modal.classList.add('opacity-0');
        modal.querySelector('div').classList.remove('scale-100');
        modal.querySelector('div').classList.add('scale-95');

        setTimeout(() => {
            modal.classList.add('pointer-events-none');
            // Reset form
            document.getElementById('change-password-form').reset();
        }, 150);

        // Restore body scroll
        document.body.style.overflow = '';
    }

    async handlePasswordChange(e) {
        e.preventDefault();

        const currentPassword = document.getElementById('current-password').value;
        const newPassword = document.getElementById('new-password').value;
        const confirmPassword = document.getElementById('confirm-password').value;

        // Validate passwords
        if (!currentPassword || !newPassword || !confirmPassword) {
            showToast('Lỗi', 'Vui lòng điền đầy đủ thông tin', 'error');
            return;
        }

        if (newPassword !== confirmPassword) {
            showToast('Lỗi', 'Mật khẩu mới và xác nhận mật khẩu không khớp', 'error');
            return;
        }

        if (newPassword.length < 6) {
            showToast('Lỗi', 'Mật khẩu mới phải có ít nhất 6 ký tự', 'error');
            return;
        }

        if (currentPassword === newPassword) {
            showToast('Lỗi', 'Mật khẩu mới phải khác mật khẩu hiện tại', 'error');
            return;
        }

        try {
            this.showLoading(true);

            const response = await API.changePassword(currentPassword, newPassword);

            if (response.status === 'success') {
                showToast('Thành công', 'Đã thay đổi mật khẩu', 'success');
                this.hidePasswordModal();
            } else {
                showToast('Lỗi', 'Có lỗi xảy ra khi thay đổi mật khẩu', 'error');
            }

        } catch (error) {
            console.error('Error changing password:', error);
            showToast('Lỗi', 'Có lỗi xảy ra khi thay đổi mật khẩu', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        if (show) {
            overlay.classList.remove('hidden');
        } else {
            overlay.classList.add('hidden');
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new SettingsPage();
});