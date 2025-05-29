import API from "../core/api.js";
import { showToast } from "../utils/toast.js";

class AddUserModal {
    constructor() {
        this.modal = null;
        this.isModalOpen = false;
        this.departments = []; // Will be populated from existing users
        this.roles = []; // Will be populated from existing users
    }

    // Create modal HTML
    createModalHTML() {
        return `
            <!-- Add User Modal -->
            <div id="addUserModal"
                class="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/50 backdrop-blur-sm transition-opacity opacity-0 pointer-events-none">
                <div
                    class="w-full max-w-lg max-h-[90vh] bg-white dark:bg-gray-800 rounded-xl shadow-xl transform transition-all scale-95 mx-4">
                    <!-- Header -->
                    <div class="flex justify-between items-center p-4 border-b border-gray-200 dark:border-gray-700">
                        <h2 class="text-lg font-semibold text-gray-800 dark:text-white">Thêm người dùng mới</h2>
                        <button type="button" id="closeAddUserModal"
                            class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-white transition-colors">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24"
                                stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                    d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>

                    <!-- Body -->
                    <div class="p-4 space-y-4 overflow-y-auto max-h-[calc(90vh-128px)]">
                        <form id="addUserForm" class="space-y-4">
                            <!-- Họ và tên -->
                            <div class="space-y-2">
                                <label for="name" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Họ và
                                    tên <span class="text-red-500">*</span></label>
                                <input type="text" id="name" name="name" placeholder="Nhập họ và tên đầy đủ" required
                                    class="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                            </div>

                            <!-- Email (tùy chọn) -->
                            <div class="space-y-2">
                                <div class="flex items-center justify-between">
                                    <label for="email"
                                        class="block text-sm font-medium text-gray-700 dark:text-gray-300">Email</label>
                                    <span class="text-xs text-gray-500 dark:text-gray-400">Tùy chọn</span>
                                </div>
                                <input type="email" id="email" name="email" placeholder="example@company.com"
                                    class="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                            </div>

                            <!-- ID Telegram (tùy chọn) -->
                            <div class="space-y-2">
                                <div class="flex items-center justify-between">
                                    <label for="telegramId"
                                        class="block text-sm font-medium text-gray-700 dark:text-gray-300">ID Telegram</label>
                                    <span class="text-xs text-gray-500 dark:text-gray-400">Tùy chọn</span>
                                </div>
                                <input type="text" id="telegramId" name="telegramId" placeholder="@username hoặc ID số"
                                    class="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                            </div>

                            <!-- Phòng ban -->
                            <div class="space-y-2">
                                <label for="department" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Phòng
                                    ban <span class="text-red-500">*</span></label>
                                <select id="department" name="department" required
                                    class="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                    <option value="">-- Chọn phòng ban --</option>
                                </select>
                            </div>

                            <!-- Vai trò -->
                            <div class="space-y-2">
                                <label for="role" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Vai trò
                                    <span class="text-red-500">*</span></label>
                                <select id="role" name="role" required
                                    class="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                    <option value="">-- Chọn vai trò --</option>
                                </select>
                            </div>
                        </form>
                    </div>

                    <!-- Footer -->
                    <div class="flex justify-end items-center gap-3 p-4 border-t border-gray-200 dark:border-gray-700">
                        <button type="button" id="cancelAddUser"
                            class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600">
                            Hủy
                        </button>
                        <button type="submit" form="addUserForm" id="submitAddUser"
                            class="flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                            Thêm người dùng
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    // Render modal to DOM
    render() {
        // Remove existing modal if any
        const existingModal = document.getElementById('addUserModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', this.createModalHTML());
        this.modal = document.getElementById('addUserModal');

        // Setup event listeners
        this.setupEventListeners();

        // Populate dropdowns
        this.populateDropdowns();
    }

    // Populate department and role dropdowns
    populateDropdowns() {
        this.populateDepartmentDropdown();
        this.populateRoleDropdown();
    }

    // Populate department dropdown
    populateDepartmentDropdown() {
        const departmentSelect = document.getElementById('department');
        if (!departmentSelect) return;

        // Clear existing options except the first one
        departmentSelect.innerHTML = '<option value="">-- Chọn phòng ban --</option>';

        // Add departments from existing users data
        this.departments.forEach(dept => {
            const option = document.createElement('option');
            option.value = dept;
            option.textContent = dept;
            departmentSelect.appendChild(option);
        });

        // Add some default departments if none exist
        if (this.departments.length === 0) {
            const defaultDepartments = ['Công nghệ', 'Marketing', 'Nhân sự', 'Tài chính', 'Kinh doanh'];
            defaultDepartments.forEach(dept => {
                const option = document.createElement('option');
                option.value = dept;
                option.textContent = dept;
                departmentSelect.appendChild(option);
            });
        }
    }

    // Populate role dropdown
    populateRoleDropdown() {
        const roleSelect = document.getElementById('role');
        if (!roleSelect) return;

        // Clear existing options except the first one
        roleSelect.innerHTML = '<option value="">-- Chọn vai trò --</option>';

        // Define available roles
        const availableRoles = [
            { value: 'user', label: 'User' },
            { value: 'admin', label: 'Admin' },
            { value: 'super_admin', label: 'Super admin' }
        ];

        availableRoles.forEach(role => {
            const option = document.createElement('option');
            option.value = role.value;
            option.textContent = role.label;
            roleSelect.appendChild(option);
        });
    }

    // Setup event listeners
    setupEventListeners() {
        // Close modal buttons
        document.getElementById('closeAddUserModal').addEventListener('click', () => this.hide());
        document.getElementById('cancelAddUser').addEventListener('click', () => this.hide());

        // Close modal on backdrop click
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.hide();
            }
        });

        // Close modal on ESC key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isModalOpen) {
                this.hide();
            }
        });

        // Form submission
        document.getElementById('addUserForm').addEventListener('submit', (e) => this.handleSubmit(e));
    }

    // Basic form validation (only check required fields)
    validateForm() {
        const form = document.getElementById('addUserForm');
        const requiredFields = form.querySelectorAll('[required]');
        
        for (let field of requiredFields) {
            if (!field.value.trim()) {
                return false;
            }
        }
        
        // Basic email validation if email is provided
        const emailField = document.getElementById('email');
        if (emailField.value.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailField.value.trim())) {
            return false;
        }
        
        return true;
    }

    // Handle form submission
    async handleSubmit(e) {
        e.preventDefault();

        if (!this.validateForm()) {
            showToast('Lỗi', 'Vui lòng điền đầy đủ thông tin bắt buộc', 'error');
            return;
        }

        const submitButton = document.getElementById('submitAddUser');
        const originalText = submitButton.textContent;

        try {
            // Disable submit button
            submitButton.disabled = true;
            submitButton.innerHTML = `
                <svg class="animate-spin w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                Đang thêm...
            `;

            // Collect form data
            const formData = this.collectFormData();

            // Call API to add user
            const response = await API.addUser(formData);

            if (response.status === 'success') {
                showToast('Thành công', 'Đã thêm người dùng mới', 'success');
                this.hide();

                // Trigger refresh of users list
                if (window.loadUsers && typeof window.loadUsers === 'function') {
                    window.loadUsers();
                }
            } else {
                throw new Error(response.message || 'Không thể thêm người dùng');
            }

        } catch (error) {
            console.error('Error adding user:', error);
            showToast('Lỗi', error.message || 'Có lỗi xảy ra khi thêm người dùng', 'error');
        } finally {
            // Re-enable submit button
            submitButton.disabled = false;
            submitButton.textContent = originalText;
        }
    }

    // Collect form data
    collectFormData() {
        const form = document.getElementById('addUserForm');
        const formData = new FormData(form);

        // Get values and trim whitespace
        const name = formData.get('name')?.trim();
        const email = formData.get('email')?.trim();
        const telegramId = formData.get('telegramId')?.trim();
        const department = formData.get('department')?.trim();
        const role = formData.get('role')?.trim();

        // Validate required fields
        if (!name || !department || !role) {
            throw new Error('Thiếu thông tin bắt buộc');
        }

        return {
            name: name,
            room_id: department, // Map department to room_id for backend
            role: role,
            email: email || undefined, // Undefined sẽ không được gửi đi
            telegram_id: telegramId || undefined // Undefined sẽ không được gửi đi
        };
    }

    // Set departments data (from users list)
    setDepartments(departments) {
        this.departments = [...new Set(departments.filter(Boolean))];
    }

    // Set roles data (from users list)
    setRoles(roles) {
        this.roles = [...new Set(roles.filter(Boolean))];
    }

    // Show modal
    show() {
        if (!this.modal) {
            this.render();
        }

        this.isModalOpen = true;
        this.modal.classList.remove('pointer-events-none');

        // Trigger animations
        requestAnimationFrame(() => {
            this.modal.classList.remove('opacity-0');
            this.modal.querySelector('div').classList.remove('scale-95');
            this.modal.querySelector('div').classList.add('scale-100');
        });

        // Focus first input
        setTimeout(() => {
            const firstInput = this.modal.querySelector('input');
            if (firstInput) firstInput.focus();
        }, 150);

        // Prevent body scroll
        document.body.style.overflow = 'hidden';
    }

    // Hide modal
    hide() {
        if (!this.modal) return;

        this.isModalOpen = false;
        this.modal.classList.add('opacity-0');
        this.modal.querySelector('div').classList.remove('scale-100');
        this.modal.querySelector('div').classList.add('scale-95');

        // Remove modal after animation
        setTimeout(() => {
            this.modal.classList.add('pointer-events-none');
            // Reset form
            const form = document.getElementById('addUserForm');
            if (form) {
                form.reset();
            }
        }, 150);

        // Restore body scroll
        document.body.style.overflow = '';
    }

    // Destroy modal
    destroy() {
        if (this.modal) {
            this.modal.remove();
            this.modal = null;
        }
        this.isModalOpen = false;
        document.body.style.overflow = '';
    }
}

// Export singleton instance
const addUserModal = new AddUserModal();
export default addUserModal;