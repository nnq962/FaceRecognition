import API from "../core/api.js";
import { showToast } from "../utils/toast.js";

class EditUserModal {
    constructor() {
        this.modal = null;
        this.isModalOpen = false;
        this.currentUserId = null;
        this.currentUserData = null;
        this.departments = [];
        this.selectedFiles = [];
        this.existingImages = [];
    }

    // Create modal HTML
    createModalHTML() {
        return `
            <!-- Edit User Modal -->
            <div id="editUserModal"
                class="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/50 backdrop-blur-sm transition-opacity opacity-0 pointer-events-none">
                <div
                    class="w-full max-w-2xl max-h-[90vh] bg-white dark:bg-gray-800 rounded-xl shadow-xl transform transition-all scale-95 mx-4">
                    <!-- Header -->
                    <div class="flex justify-between items-center p-4 border-b border-gray-200 dark:border-gray-700">
                        <h2 class="text-xl font-semibold text-gray-800 dark:text-white">Chỉnh sửa thông tin người dùng</h2>
                        <button type="button" id="closeEditUserModal"
                            class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-white transition-colors">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24"
                                stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                    d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>

                    <!-- Body -->
                    <div class="p-4 space-y-6 overflow-y-auto max-h-[calc(90vh-128px)]">
                        <form id="editUserForm" class="space-y-6">
                            <!-- Thông tin cơ bản -->
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <!-- Họ và tên -->
                                <div class="space-y-2">
                                    <label for="editname"
                                        class="block text-sm font-medium text-gray-700 dark:text-gray-300">Họ và tên <span class="text-red-500">*</span></label>
                                    <input type="text" id="editname" name="name" placeholder="Nhập họ và tên đầy đủ"
                                        required
                                        class="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                    <div id="editnameError" class="text-red-500 text-xs hidden"></div>
                                </div>

                                <!-- Email -->
                                <div class="space-y-2">
                                    <label for="editEmail"
                                        class="block text-sm font-medium text-gray-700 dark:text-gray-300">Email</label>
                                    <input type="email" id="editEmail" name="email" placeholder="example@company.com"
                                        class="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                    <div id="editEmailError" class="text-red-500 text-xs hidden"></div>
                                </div>

                                <!-- ID Telegram -->
                                <div class="space-y-2">
                                    <label for="editTelegramId"
                                        class="block text-sm font-medium text-gray-700 dark:text-gray-300">ID Telegram</label>
                                    <input type="text" id="editTelegramId" name="telegramId" placeholder="@username hoặc ID số"
                                        class="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                    <div id="editTelegramIdError" class="text-red-500 text-xs hidden"></div>
                                </div>

                                <!-- Trạng thái -->
                                <div class="space-y-2">
                                    <label for="editStatus"
                                        class="block text-sm font-medium text-gray-700 dark:text-gray-300">Trạng thái <span class="text-red-500">*</span></label>
                                    <select id="editStatus" name="status" required
                                        class="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                        <option value="active">Hoạt động</option>
                                        <option value="inactive">Không hoạt động</option>
                                    </select>
                                    <div id="editStatusError" class="text-red-500 text-xs hidden"></div>
                                </div>

                                <!-- Phòng ban -->
                                <div class="space-y-2">
                                    <label for="editDepartment"
                                        class="block text-sm font-medium text-gray-700 dark:text-gray-300">Phòng ban <span class="text-red-500">*</span></label>
                                    <select id="editDepartment" name="department" required
                                        class="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                        <option value="">-- Chọn phòng ban --</option>
                                    </select>
                                    <div id="editDepartmentError" class="text-red-500 text-xs hidden"></div>
                                </div>

                                <!-- Vai trò -->
                                <div class="space-y-2">
                                    <label for="editRole" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Vai trò <span class="text-red-500">*</span></label>
                                    <select id="editRole" name="role" required
                                        class="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                        <option value="">-- Chọn vai trò --</option>
                                    </select>
                                    <div id="editRoleError" class="text-red-500 text-xs hidden"></div>
                                </div>
                            </div>

                            <!-- Ảnh khuôn mặt -->
                            <div class="space-y-4">
                                <h3
                                    class="text-lg font-medium text-gray-800 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-2">
                                    Ảnh khuôn mặt</h3>

                                <!-- Ảnh hiện có -->
                                <div class="space-y-3">
                                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Ảnh hiện có</label>
                                    <div id="existingImages" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                                        <!-- Existing images will be loaded here -->
                                    </div>
                                </div>

                                <!-- Upload ảnh mới -->
                                <div class="space-y-3">
                                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Thêm ảnh mới</label>
                                    <div class="flex items-center justify-center w-full">
                                        <label for="dropzone-file"
                                            class="flex flex-col items-center justify-center w-full h-32 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer bg-gray-50 dark:hover:bg-gray-700 dark:bg-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:hover:border-gray-500">
                                            <div class="flex flex-col items-center justify-center pt-5 pb-6">
                                                <svg class="w-8 h-8 mb-3 text-gray-500 dark:text-gray-400" fill="none"
                                                    stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12">
                                                    </path>
                                                </svg>
                                                <p class="mb-1 text-sm text-gray-500 dark:text-gray-400"><span
                                                        class="font-semibold">Nhấp để tải ảnh</span> hoặc kéo và thả</p>
                                                <p class="text-xs text-gray-500 dark:text-gray-400">JPG, JPEG, PNG, HEIC (Tối đa 10MB)</p>
                                            </div>
                                            <input id="dropzone-file" type="file" class="hidden" multiple accept=".jpg,.jpeg,.png,.heic" />
                                        </label>
                                    </div>

                                    <!-- Preview ảnh đã chọn để upload -->
                                    <div id="image-preview" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 mt-3">
                                        <!-- New image previews will be added here -->
                                    </div>
                                </div>

                                <!-- Ghi chú thêm -->
                                <div class="text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900 p-3 rounded-lg">
                                    <p class="flex items-start">
                                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2 flex-shrink-0 text-blue-500"
                                            viewBox="0 0 20 20" fill="currentColor">
                                            <path fill-rule="evenodd"
                                                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                                                clip-rule="evenodd" />
                                        </svg>
                                        Thêm nhiều ảnh khuôn mặt khác nhau sẽ giúp hệ thống nhận diện chính xác hơn. Nên chụp ở
                                        các góc và điều kiện ánh sáng khác nhau.
                                    </p>
                                </div>
                            </div>
                        </form>
                    </div>

                    <!-- Footer -->
                    <div class="flex justify-end items-center gap-3 p-4 border-t border-gray-200 dark:border-gray-700">
                        <button type="button" id="cancelEditUser"
                            class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600">
                            Hủy
                        </button>
                        <button type="submit" form="editUserForm" id="submitEditUser"
                            class="flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                            Lưu thay đổi
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    // Render modal to DOM
    render() {
        // Remove existing modal if any
        const existingModal = document.getElementById('editUserModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', this.createModalHTML());
        this.modal = document.getElementById('editUserModal');

        // Setup event listeners
        this.setupEventListeners();
    }

    // Setup event listeners
    setupEventListeners() {
        // Close modal buttons
        document.getElementById('closeEditUserModal').addEventListener('click', () => this.hide());
        document.getElementById('cancelEditUser').addEventListener('click', () => this.hide());

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
        document.getElementById('editUserForm').addEventListener('submit', (e) => this.handleSubmit(e));

        // File upload handling
        this.setupFileUpload();

        // Real-time validation
        this.setupFormValidation();
    }

    // Setup file upload
    setupFileUpload() {
        const fileInput = document.getElementById('dropzone-file');
        const dropZone = fileInput.parentElement;

        // File input change
        fileInput.addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files);
        });

        // Drag and drop
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('border-blue-500', 'bg-blue-50', 'dark:bg-blue-900/20');
        });

        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dropZone.classList.remove('border-blue-500', 'bg-blue-50', 'dark:bg-blue-900/20');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('border-blue-500', 'bg-blue-50', 'dark:bg-blue-900/20');
            this.handleFileSelect(e.dataTransfer.files);
        });
    }

    // Handle file selection
    handleFileSelect(files) {
        Array.from(files).forEach(file => {
            // Validate file
            if (!this.validateFile(file)) return;

            // Add to selected files
            this.selectedFiles.push(file);

            // Create preview
            this.createFilePreview(file);
        });
    }

    // Validate file
    validateFile(file) {
        // Check file type
        if (!['image/jpeg', 'image/jpg', 'image/png', 'image/heic'].includes(file.type)) {
            showToast('Lỗi', 'Chỉ chấp nhận file JPG, JPEG, PNG, HEIC', 'error');
            return false;
        }

        // Check file size (10MB)
        if (file.size > 10 * 1024 * 1024) {
            showToast('Lỗi', 'File không được vượt quá 10MB', 'error');
            return false;
        }

        return true;
    }

    // Create file preview
    createFilePreview(file) {
        const previewContainer = document.getElementById('image-preview');
        const fileId = Date.now() + Math.random();

        const reader = new FileReader();
        reader.onload = (e) => {
            const previewHTML = `
                <div class="relative group" data-file-id="${fileId}">
                    <div class="aspect-square rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-700 border border-blue-300 dark:border-blue-700">
                        <img src="${e.target.result}" alt="Ảnh đã chọn" class="w-full h-full object-cover">
                    </div>
                    <button type="button" onclick="editUserModal.removeFilePreview('${fileId}')"
                        class="absolute top-1 right-1 p-1 bg-red-500 text-white rounded-full hover:bg-red-600 transition-colors shadow-lg"
                        title="Xóa ảnh">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                        </svg>
                    </button>
                    <div class="absolute bottom-0 left-0 right-0 bg-blue-500 text-white text-xs text-center py-1 rounded-b-lg">
                        Đã chọn
                    </div>
                </div>
            `;
            previewContainer.insertAdjacentHTML('beforeend', previewHTML);
        };
        reader.readAsDataURL(file);

        // Store file with ID for removal
        file.previewId = fileId;
    }

    // Remove file preview
    removeFilePreview(fileId) {
        // Remove from selected files
        this.selectedFiles = this.selectedFiles.filter(file => file.previewId !== fileId);

        // Remove preview element
        const previewElement = document.querySelector(`[data-file-id="${fileId}"]`);
        if (previewElement) {
            previewElement.remove();
        }
    }

    // Delete existing image
    async deleteExistingImage(filename) {
        if (!confirm(`Bạn có chắc muốn xóa ảnh "${filename}"?`)) {
            return;
        }

        try {
            await API.deletePhoto(this.currentUserId, filename, 'face');

            // Xóa khỏi giao diện
            const imageElement = document.querySelector(`[data-photo-filename="${filename}"]`);
            if (imageElement) {
                imageElement.remove();
            }

            // Xóa khỏi danh sách ảnh hiện tại
            this.existingImages = this.existingImages.filter(img => img !== filename);

            // Hiển thị thông báo
            showToast('Thành công', `Đã xóa ảnh "${filename}"`, 'success');

        } catch (error) {
            console.error('Error deleting image:', error);
            showToast('Lỗi', `Không thể xóa ảnh: ${error.message}`, 'error');
        }
    }

    // Refresh existing images (useful after upload)
    async refreshExistingImages() {
        if (this.currentUserId) {
            await this.loadExistingImages(this.currentUserId);
        }
    }

    // Load existing images - Clean Tailwind version
    async loadExistingImages(userId) {
        const existingContainer = document.getElementById('existingImages');

        try {
            // Show loading state
            existingContainer.innerHTML = `
                <div class="col-span-full flex flex-col items-center justify-center py-8 text-gray-500 dark:text-gray-400">
                    <svg class="animate-spin w-8 h-8 mb-2" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                    </svg>
                    <p class="text-sm">Đang tải ảnh...</p>
                </div>
            `;

            // Call API to get user's face photos
            const response = await API.getUserPhotos(userId, 'face');

            if (response.status === 'success' && response.data.photos && response.data.photos.length > 0) {
                // Clear loading state
                existingContainer.innerHTML = '';

                // Store existing images for reference
                this.existingImages = response.data.photos;

                // Create image elements with Tailwind classes
                response.data.photos.forEach((filename) => {
                    const photoUrl = API.getFacePhotoUrl(userId, filename);

                    // Create image container with Tailwind
                    const imageContainer = document.createElement('div');
                    imageContainer.setAttribute('data-photo-filename', filename);
                    imageContainer.className = 'relative group aspect-square rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-700 border-2 border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500 transition-colors';

                    // Create loading placeholder
                    const placeholder = document.createElement('div');
                    placeholder.className = 'absolute inset-0 flex items-center justify-center text-xs text-gray-500 bg-gray-50 dark:bg-gray-800';
                    placeholder.textContent = 'Đang tải...';

                    // Create delete button (always visible on mobile, hover on desktop)
                    const deleteButton = document.createElement('button');
                    deleteButton.type = 'button';
                    deleteButton.className = 'absolute top-2 right-2 p-1.5 bg-red-500 text-white rounded-full hover:bg-red-600 focus:bg-red-600 transition-colors shadow-lg opacity-100 sm:opacity-0 group-hover:opacity-100 focus:opacity-100 z-10';
                    deleteButton.title = 'Xóa ảnh';
                    deleteButton.innerHTML = `
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" clip-rule="evenodd" />
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                        </svg>
                    `;

                    deleteButton.addEventListener('click', (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        this.deleteExistingImage(filename);
                    });

                    // Assemble components
                    imageContainer.appendChild(placeholder);
                    imageContainer.appendChild(deleteButton);
                    existingContainer.appendChild(imageContainer);

                    // Load image
                    const img = new Image();
                    img.onload = function () {
                        // Remove placeholder
                        placeholder.remove();

                        // Create and add image element
                        const imgElement = document.createElement('img');
                        imgElement.src = photoUrl;
                        imgElement.alt = `Ảnh khuôn mặt - ${filename}`;
                        imgElement.className = 'absolute inset-0 w-full h-full object-cover transition-transform group-hover:scale-105';

                        imageContainer.insertBefore(imgElement, deleteButton);
                    };

                    img.onerror = function () {
                        // Show error state
                        placeholder.textContent = 'Lỗi tải ảnh';
                        placeholder.className = 'absolute inset-0 flex items-center justify-center text-xs text-red-500 bg-red-50 dark:bg-red-900/20';
                        imageContainer.className = imageContainer.className.replace('border-gray-200 dark:border-gray-600', 'border-red-300 dark:border-red-700');
                    };

                    // Start loading
                    img.src = photoUrl;
                });

            } else {
                // No photos found
                existingContainer.innerHTML = `
                    <div class="col-span-full flex flex-col items-center justify-center py-8 text-gray-500 dark:text-gray-400">
                        <svg class="w-12 h-12 mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                        </svg>
                        <p class="text-sm">Chưa có ảnh khuôn mặt nào</p>
                        <p class="text-xs mt-1 text-gray-400">Thêm ảnh mới ở phần bên dưới</p>
                    </div>
                `;
            }

        } catch (error) {
            console.error('Error loading existing images:', error);

            // Show error state
            existingContainer.innerHTML = `
                <div class="col-span-full flex flex-col items-center justify-center py-8 text-red-500 dark:text-red-400">
                    <svg class="w-12 h-12 mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    <p class="text-sm">Không thể tải ảnh</p>
                    <p class="text-xs mt-1">${error.message}</p>
                    <button onclick="editUserModal.loadExistingImages('${userId}')" 
                            class="mt-2 text-xs text-blue-500 hover:text-blue-600 underline">
                        Thử lại
                    </button>
                </div>
            `;
        }
    }

    // Populate dropdowns
    populateDropdowns() {
        this.populateDepartmentDropdown();
        this.populateRoleDropdown();
    }

    // Populate department dropdown
    populateDepartmentDropdown() {
        const departmentSelect = document.getElementById('editDepartment');
        if (!departmentSelect) return;

        departmentSelect.innerHTML = '<option value="">-- Chọn phòng ban --</option>';

        this.departments.forEach(dept => {
            const option = document.createElement('option');
            option.value = dept;
            option.textContent = dept;
            departmentSelect.appendChild(option);
        });

        // Add default departments if none exist
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
        const roleSelect = document.getElementById('editRole');
        if (!roleSelect) return;

        roleSelect.innerHTML = '<option value="">-- Chọn vai trò --</option>';

        // Define all available roles - role permissions will be handled by backend
        const availableRoles = [
            { value: 'user', label: 'User' },
            { value: 'admin', label: 'Admin' },
            { value: 'super_admin', label: 'Super Admin' }
        ];

        availableRoles.forEach(role => {
            const option = document.createElement('option');
            option.value = role.value;
            option.textContent = role.label;
            roleSelect.appendChild(option);
        });
    }

    // Setup form validation
    setupFormValidation() {
        const form = document.getElementById('editUserForm');
        const inputs = form.querySelectorAll('input, select');

        inputs.forEach(input => {
            input.addEventListener('blur', () => this.validateField(input));
            input.addEventListener('input', () => this.clearFieldError(input));
        });
    }

    // Validate field
    validateField(field) {
        const value = field.value.trim();
        const fieldName = field.name;
        let isValid = true;
        let errorMessage = '';

        switch (fieldName) {
            case 'name':
                if (!value) {
                    isValid = false;
                    errorMessage = 'Họ và tên là bắt buộc';
                } else if (value.length < 2) {
                    isValid = false;
                    errorMessage = 'Họ và tên phải có ít nhất 2 ký tự';
                }
                break;

            case 'email':
                if (value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
                    isValid = false;
                    errorMessage = 'Email không hợp lệ';
                }
                break;

            case 'department':
                if (!value) {
                    isValid = false;
                    errorMessage = 'Vui lòng chọn phòng ban';
                }
                break;

            case 'role':
                if (!value) {
                    isValid = false;
                    errorMessage = 'Vui lòng chọn vai trò';
                }
                break;

            case 'status':
                if (!value) {
                    isValid = false;
                    errorMessage = 'Vui lòng chọn trạng thái';
                }
                break;
        }

        this.showFieldError(field, isValid ? '' : errorMessage);
        return isValid;
    }

    // Show/clear field errors
    showFieldError(field, message) {
        const errorElement = document.getElementById('edit' + field.name.charAt(0).toUpperCase() + field.name.slice(1) + 'Error');
        if (errorElement) {
            if (message) {
                errorElement.textContent = message;
                errorElement.classList.remove('hidden');
                field.classList.add('border-red-500');
            } else {
                errorElement.classList.add('hidden');
                field.classList.remove('border-red-500');
            }
        }
    }

    clearFieldError(field) {
        const errorElement = document.getElementById('edit' + field.name.charAt(0).toUpperCase() + field.name.slice(1) + 'Error');
        if (errorElement) {
            errorElement.classList.add('hidden');
            field.classList.remove('border-red-500');
        }
    }

    // Load user data into form
    loadUserData(userData) {
        this.currentUserData = userData;

        // Fill form fields
        document.getElementById('editname').value = userData.name || '';
        document.getElementById('editEmail').value = userData.email || '';
        document.getElementById('editTelegramId').value = userData.telegram_id || '';

        // Fix status mapping: API active field (boolean) to form status field (string)
        let statusValue = 'active'; // default
        if (userData.active === false) {
            statusValue = 'inactive';
        } else if (userData.active === true || userData.active === undefined) {
            statusValue = 'active'; // Treat undefined as active (default behavior)
        }
        document.getElementById('editStatus').value = statusValue;

        document.getElementById('editDepartment').value = userData.room_id || '';
        document.getElementById('editRole').value = userData.role || '';
    }

    // Handle form submission
    async handleSubmit(e) {
        e.preventDefault();

        if (!this.validateForm()) {
            showToast('Lỗi', 'Vui lòng kiểm tra lại thông tin đã nhập', 'error');
            return;
        }

        const submitButton = document.getElementById('submitEditUser');
        const originalText = submitButton.textContent;

        try {
            submitButton.disabled = true;
            submitButton.innerHTML = `
                <svg class="animate-spin w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                Đang lưu...
            `;

            // Collect form data
            const formData = this.collectFormData();

            // Call API to update user
            const response = await API.updateUser(this.currentUserId, formData);

            if (response.status === 'success') {
                // Upload new images if any
                if (this.selectedFiles.length > 0) {
                    await this.uploadImages();
                }

                showToast('Thành công', 'Đã cập nhật thông tin người dùng', 'success');
                this.hide();

                // Trigger refresh of users list
                if (window.loadUsers && typeof window.loadUsers === 'function') {
                    window.loadUsers();
                }
            } else {
                throw new Error(response.message || 'Không thể cập nhật thông tin người dùng');
            }

        } catch (error) {
            console.error('Error updating user:', error);
            showToast('Lỗi', error.message || 'Có lỗi xảy ra khi cập nhật thông tin', 'error');
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = originalText;
        }
    }

    // Collect form data
    collectFormData() {
        const form = document.getElementById('editUserForm');
        const formData = new FormData(form);

        // Get values and trim
        const name = formData.get('name')?.trim();
        const email = formData.get('email')?.trim();
        const telegramId = formData.get('telegramId')?.trim();
        const department = formData.get('department')?.trim();
        const role = formData.get('role')?.trim();
        const status = formData.get('status')?.trim();

        // Validate required fields
        if (!name || !department || !role || !status) {
            throw new Error('Thiếu thông tin bắt buộc');
        }

        // Build data object - only include fields that have values
        const data = {
            name: name,
            room_id: department, // Map department to room_id for backend
            role: role,
            active: status === 'active' // Map status to active boolean
        };

        // Only include optional fields if they have values
        if (email) {
            data.email = email;
        }

        if (telegramId) {
            data.telegram_id = telegramId;
        }

        return data;
    }

    // Upload images
    async uploadImages() {
        try {
            console.log('Uploading images:', this.selectedFiles);

            // Upload từng ảnh sử dụng API.uploadFacePhoto
            for (const file of this.selectedFiles) {
                await API.uploadFacePhoto(this.currentUserId, file);
            }

            // Upload xong thì refresh ảnh hiển thị lại
            await this.refreshExistingImages();

            // Xóa ảnh đã chọn và preview
            this.selectedFiles = [];
            const previewContainer = document.getElementById('image-preview');
            if (previewContainer) {
                previewContainer.innerHTML = '';
            }

            // Optional: show success toast
            showToast('Thành công', 'Tải ảnh lên thành công', 'success');

        } catch (error) {
            console.error('Error uploading images:', error);
            showToast('Cảnh báo', 'Cập nhật thông tin thành công nhưng không thể tải ảnh lên', 'warning');
        }
    }


    // Validate entire form
    validateForm() {
        const form = document.getElementById('editUserForm');
        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;

        requiredFields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });

        // Validate optional email field if filled
        const emailField = document.getElementById('editEmail');
        if (emailField.value.trim()) {
            if (!this.validateField(emailField)) {
                isValid = false;
            }
        }

        return isValid;
    }

    // Set departments data
    setDepartments(departments) {
        this.departments = [...new Set(departments.filter(Boolean))];
    }

    // Show modal with user data
    async show(userId, userData) {
        this.currentUserId = userId;

        if (!this.modal) {
            this.render();
        }

        // Populate dropdowns first
        this.populateDropdowns();

        // Load user data into form
        this.loadUserData(userData);

        // Load existing images
        await this.loadExistingImages(userId);

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
            // Reset form and clear data
            this.resetModal();
        }, 150);

        // Restore body scroll
        document.body.style.overflow = '';
    }

    // Reset modal data
    resetModal() {
        this.currentUserId = null;
        this.currentUserData = null;
        this.selectedFiles = [];
        this.existingImages = [];

        // Reset form
        const form = document.getElementById('editUserForm');
        if (form) {
            form.reset();
            // Clear all errors
            form.querySelectorAll('.text-red-500').forEach(error => error.classList.add('hidden'));
            form.querySelectorAll('.border-red-500').forEach(field => field.classList.remove('border-red-500'));
        }

        // Clear image previews
        const previewContainer = document.getElementById('image-preview');
        if (previewContainer) {
            previewContainer.innerHTML = '';
        }

        const existingContainer = document.getElementById('existingImages');
        if (existingContainer) {
            existingContainer.innerHTML = '';
        }
    }

    // Destroy modal
    destroy() {
        if (this.modal) {
            this.modal.remove();
            this.modal = null;
        }
        this.isModalOpen = false;
        this.resetModal();
        document.body.style.overflow = '';
    }
}

// Export singleton instance
const editUserModal = new EditUserModal();

// Make removeFilePreview globally accessible
window.editUserModal = editUserModal;

export default editUserModal;