import User from "../utils/user.js";
import { showToast } from "../utils/toast.js";
import API from "../core/api.js";

class FeedbackPage {
    constructor() {
        this.selectedImages = [];
        this.maxFileSize = 5 * 1024 * 1024; // 5MB
        this.maxImages = 5;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.populateUserInfo();
    }

    populateUserInfo() {
        try {
            const userName = User.getName();
            const userRole = User.getRole();

        } catch (error) {
            console.error('Error getting user info:', error);
        }
    }

    setupEventListeners() {
        // Form submission
        document.getElementById('feedback-form').addEventListener('submit', (e) => {
            this.handleFormSubmit(e);
        });

        // Cancel button
        document.getElementById('cancel-btn').addEventListener('click', () => {
            this.resetForm();
        });

        // Image upload
        const uploadArea = document.getElementById('upload-area');
        const imageInput = document.getElementById('image-input');

        uploadArea.addEventListener('click', () => {
            imageInput.click();
        });

        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('border-blue-400', 'bg-blue-50', 'dark:bg-blue-900/20');
        });

        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('border-blue-400', 'bg-blue-50', 'dark:bg-blue-900/20');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('border-blue-400', 'bg-blue-50', 'dark:bg-blue-900/20');

            const files = Array.from(e.dataTransfer.files);
            this.handleImageSelection(files);
        });

        imageInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files);
            this.handleImageSelection(files);
        });

        // Real-time validation
        document.getElementById('description').addEventListener('input', (e) => {
            this.validateDescription(e.target);
        });

        document.getElementById('subject').addEventListener('input', (e) => {
            this.validateSubject(e.target);
        });
    }

    handleImageSelection(files) {
        const validFiles = [];

        for (const file of files) {
            // Check if we've reached max images
            if (this.selectedImages.length + validFiles.length >= this.maxImages) {
                showToast('Cảnh báo', `Chỉ được tải tối đa ${this.maxImages} hình ảnh`, 'warning');
                break;
            }

            // Validate file type
            if (!file.type.startsWith('image/')) {
                showToast('Lỗi', `File "${file.name}" không phải là hình ảnh`, 'error');
                continue;
            }

            // Validate file size
            if (file.size > this.maxFileSize) {
                showToast('Lỗi', `File "${file.name}" vượt quá 5MB`, 'error');
                continue;
            }

            validFiles.push(file);
        }

        if (validFiles.length > 0) {
            this.addImages(validFiles);
        }

        // Reset input
        document.getElementById('image-input').value = '';
    }

    addImages(files) {
        files.forEach(file => {
            const imageId = Date.now() + Math.random();
            const imageObject = {
                id: imageId,
                file: file,
                url: URL.createObjectURL(file)
            };

            this.selectedImages.push(imageObject);
            this.createImagePreview(imageObject);
        });

        this.updateImagePreviewVisibility();
    }

    createImagePreview(imageObject) {
        const previewContainer = document.getElementById('image-preview');

        const imageDiv = document.createElement('div');
        imageDiv.className = 'relative group';
        imageDiv.dataset.imageId = imageObject.id;

        imageDiv.innerHTML = `
            <div class="aspect-square bg-gray-100 dark:bg-gray-700 rounded-xl overflow-hidden">
                <img src="${imageObject.url}" alt="Preview" class="w-full h-full object-cover">
            </div>
            <button type="button" class="absolute -top-2 -right-2 w-6 h-6 bg-red-500 hover:bg-red-600 text-white rounded-full flex items-center justify-center text-xs opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
            </button>
            <div class="absolute bottom-0 left-0 right-0 bg-black bg-opacity-50 text-white text-xs p-2 rounded-b-xl truncate">
                ${imageObject.file.name}
            </div>
        `;

        // Add remove event listener
        const removeBtn = imageDiv.querySelector('button');
        removeBtn.addEventListener('click', () => {
            this.removeImage(imageObject.id);
        });

        previewContainer.appendChild(imageDiv);
    }

    removeImage(imageId) {
        // Remove from array
        const index = this.selectedImages.findIndex(img => img.id === imageId);
        if (index > -1) {
            URL.revokeObjectURL(this.selectedImages[index].url);
            this.selectedImages.splice(index, 1);
        }

        // Remove from DOM
        const imageDiv = document.querySelector(`[data-image-id="${imageId}"]`);
        if (imageDiv) {
            imageDiv.remove();
        }

        this.updateImagePreviewVisibility();
    }

    updateImagePreviewVisibility() {
        const previewContainer = document.getElementById('image-preview');
        if (this.selectedImages.length > 0) {
            previewContainer.classList.remove('hidden');
        } else {
            previewContainer.classList.add('hidden');
        }
    }

    validateSubject(input) {
        const value = input.value.trim();
        if (value.length > 0 && value.length < 5) {
            input.classList.add('border-red-500');
            return false;
        } else {
            input.classList.remove('border-red-500');
            return true;
        }
    }

    validateDescription(input) {
        const value = input.value.trim();
        if (value.length > 0 && value.length < 20) {
            input.classList.add('border-red-500');
            return false;
        } else {
            input.classList.remove('border-red-500');
            return true;
        }
    }

    validateForm() {
        const feedbackType = document.querySelector('input[name="feedback_type"]:checked');
        const subject = document.getElementById('subject').value.trim();
        const priority = document.getElementById('priority').value;
        const description = document.getElementById('description').value.trim();
        const contactEmail = document.getElementById('contact-email').value.trim();

        // Required fields
        if (!feedbackType) {
            showToast('Lỗi', 'Vui lòng chọn loại phản hồi', 'error');
            return false;
        }

        if (!subject || subject.length < 5) {
            showToast('Lỗi', 'Tiêu đề phải có ít nhất 5 ký tự', 'error');
            document.getElementById('subject').focus();
            return false;
        }

        if (!priority) {
            showToast('Lỗi', 'Vui lòng chọn mức độ ưu tiên', 'error');
            return false;
        }

        if (!description || description.length < 20) {
            showToast('Lỗi', 'Mô tả chi tiết phải có ít nhất 20 ký tự', 'error');
            document.getElementById('description').focus();
            return false;
        }

        // Email validation if provided
        if (contactEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contactEmail)) {
            showToast('Lỗi', 'Email liên hệ không hợp lệ', 'error');
            document.getElementById('contact-email').focus();
            return false;
        }

        return true;
    }

    async handleFormSubmit(e) {
        e.preventDefault();
        console.log('=== FORM SUBMIT STARTED ===');

        // Debug validation trước
        const feedbackTypeCheck = document.querySelector('input[name="feedback_type"]:checked');
        console.log('Pre-validation feedback type check:', feedbackTypeCheck);

        if (!this.validateForm()) {
            console.log('❌ Form validation failed');
            return;
        }
        console.log('✅ Form validation passed');

        try {
            this.showLoading(true);

            const formData = this.collectFormData();

            console.log('About to call API.submitFeedback...');
            const response = await API.submitFeedback(formData);

            if (response.status === 'success') {
                showToast('Thành công', 'Đã gửi phản hồi thành công. Cảm ơn bạn!', 'success');
                this.resetForm();
            } else {
                showToast('Lỗi', response.message || 'Có lỗi xảy ra khi gửi phản hồi. Vui lòng thử lại.', 'error');
            }

        } catch (error) {
            console.error('Error submitting feedback:', error);
            showToast('Lỗi', error.message || 'Có lỗi xảy ra khi gửi phản hồi. Vui lòng thử lại.', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    collectFormData() {
        console.log('=== DEBUG COLLECT FORM DATA ===');

        // Debug feedback type selection
        const allFeedbackInputs = document.querySelectorAll('input[name="feedback_type"]');
        console.log('All feedback type inputs:', allFeedbackInputs);
        console.log('Number of feedback inputs found:', allFeedbackInputs.length);

        allFeedbackInputs.forEach((input, index) => {
            console.log(`Input ${index}:`, {
                value: input.value,
                checked: input.checked,
                name: input.name,
                type: input.type
            });
        });

        const feedbackTypeElement = document.querySelector('input[name="feedback_type"]:checked');
        console.log('Selected feedback type element:', feedbackTypeElement);
        console.log('Selected feedback type value:', feedbackTypeElement ? feedbackTypeElement.value : 'NULL');

        // Get other form values
        const subject = document.getElementById('subject').value.trim();
        const priority = document.getElementById('priority').value;
        const description = document.getElementById('description').value.trim();
        const contactEmail = document.getElementById('contact-email').value.trim();
        const contactPhone = document.getElementById('contact-phone').value.trim();

        console.log('Form values:', {
            subject: subject,
            priority: priority,
            description: description.substring(0, 50) + '...',
            contactEmail: contactEmail,
            contactPhone: contactPhone
        });

        // Create FormData for file upload
        const formData = new FormData();

        // Add feedback_type - CRITICAL FIELD
        if (feedbackTypeElement && feedbackTypeElement.value) {
            formData.append('feedback_type', feedbackTypeElement.value);
            console.log('✅ Added feedback_type:', feedbackTypeElement.value);
        } else {
            console.error('❌ NO FEEDBACK TYPE SELECTED!');
            console.log('This will cause server error');
        }

        // Add other form fields
        formData.append('subject', subject);
        formData.append('priority', priority);
        formData.append('description', description);

        if (contactEmail) {
            formData.append('contact_email', contactEmail);
        }

        if (contactPhone) {
            formData.append('contact_phone', contactPhone);
        }

        // Add user info
        try {
            const userName = User.getName();
            const userRole = User.getRole();
            formData.append('reporter_name', userName);
            formData.append('reporter_role', userRole);
            console.log('User info added:', { userName, userRole });
        } catch (error) {
            console.error('Error getting user info:', error);
        }

        // Add images
        console.log('Selected images count:', this.selectedImages.length);
        this.selectedImages.forEach((imageObj, index) => {
            formData.append('images', imageObj.file);
            console.log(`Added image ${index}:`, imageObj.file.name);
        });

        // Add browser and system info
        formData.append('browser_info', navigator.userAgent);
        formData.append('screen_resolution', `${screen.width}x${screen.height}`);
        formData.append('timestamp', new Date().toISOString());

        // Debug: Show all FormData entries
        console.log('=== FINAL FORMDATA CONTENTS ===');
        for (let [key, value] of formData.entries()) {
            if (value instanceof File) {
                console.log(`${key}: [File] ${value.name} (${value.size} bytes)`);
            } else {
                console.log(`${key}: ${value}`);
            }
        }
        console.log('=== END DEBUG ===');

        return formData;
    }

    resetForm() {
        // Reset form
        document.getElementById('feedback-form').reset();

        // Clear images
        this.selectedImages.forEach(imageObj => {
            URL.revokeObjectURL(imageObj.url);
        });
        this.selectedImages = [];

        // Clear image preview
        document.getElementById('image-preview').innerHTML = '';
        this.updateImagePreviewVisibility();

        // Remove validation classes
        document.querySelectorAll('.border-red-500').forEach(el => {
            el.classList.remove('border-red-500');
        });

        showToast('Thông báo', 'Đã xóa toàn bộ nội dung form', 'info');
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
    new FeedbackPage();
});