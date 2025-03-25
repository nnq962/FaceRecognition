// Khai báo các biến và hằng số
const API_BASE_URL = 'http://27.72.62.241:6123/api';
const userGrid = document.getElementById('user-grid');
const searchInput = document.getElementById('search-user');
const lastUpdatedTime = document.getElementById('last-updated-time');
const loadingOverlay = document.querySelector('.loading-overlay');
const alertContainer = document.getElementById('alert-container');

// Modal thêm/sửa người dùng
const userModal = document.getElementById('user-modal');
const userForm = document.getElementById('user-form');
const userModalTitle = document.getElementById('user-modal-title');
const userIdInput = document.getElementById('user-id');
const fullNameInput = document.getElementById('full-name');
const departmentInput = document.getElementById('department');
const addUserBtn = document.getElementById('add-user-btn');
const saveUserBtn = document.getElementById('save-user-btn');
const cancelUserBtn = document.getElementById('cancel-user-btn');
const userModalCloseBtn = userModal.querySelector('.close');

// Modal quản lý ảnh
const photoModal = document.getElementById('photo-modal');
const photoModalTitle = document.getElementById('photo-modal-title');
const photoGallery = document.getElementById('photo-gallery');
const photoUpload = document.getElementById('photo-upload');
const uploadPhotoBtn = document.getElementById('upload-photo-btn');
const closePhotoBtn = document.getElementById('close-photo-btn');
const photoModalCloseBtn = photoModal.querySelector('.close');

let currentPhotoUserId = null;

// Hàm hiển thị loading overlay
function showLoading(show = true) {
    loadingOverlay.style.display = show ? 'flex' : 'none';
}

// Hàm hiển thị thông báo dạng popup
function showAlert(message, type = 'success') {
    const toastContainer = document.getElementById('toast-container');
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-icon">
            <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
        </div>
        <div class="toast-message">${message}</div>
        <div class="toast-close">&times;</div>
    `;
    
    // Thêm vào container
    toastContainer.appendChild(toast);
    
    // Xử lý sự kiện đóng thông báo
    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', () => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    });
    
    // Tự động xóa thông báo sau 5 giây
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 5000);
}

// Hàm cập nhật thời gian cập nhật gần nhất
function updateLastUpdatedTime() {
    const now = new Date();
    const formattedDate = `${now.getDate().toString().padStart(2, '0')}/${(now.getMonth() + 1).toString().padStart(2, '0')}/${now.getFullYear()} ${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
    lastUpdatedTime.textContent = formattedDate;
}

// Hàm lấy dữ liệu người dùng từ API
async function fetchUsers() {
    try {
        const response = await fetch(`${API_BASE_URL}/get_all_users?without_face_embeddings=1`);
        if (!response.ok) {
            throw new Error('Không thể lấy dữ liệu người dùng');
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Lỗi khi lấy dữ liệu người dùng:', error);
        showAlert('Lỗi khi lấy dữ liệu người dùng: ' + error.message, 'error');
        return [];
    }
}

// Hàm tạo card hiển thị thông tin người dùng
async function createUserCard(user) {
    const card = document.createElement('div');
    card.className = 'user-card';
    card.dataset.userId = user._id;
    
    // Kiểm tra xem người dùng có ảnh không
    let hasPhoto = false;
    let firstPhotoName = '';
    
    try {
        const photos = await fetchUserPhotos(user._id);
        hasPhoto = photos && photos.length > 0;
        if (hasPhoto) {
            firstPhotoName = photos[0];
        }
    } catch (error) {
        console.error('Không thể lấy ảnh đại diện:', error);
    }
    
    card.innerHTML = `
        <div class="user-header">
            <div class="user-avatar">
                ${hasPhoto 
                    ? `<img src="${API_BASE_URL}/view_photo/${user._id}/${firstPhotoName}" alt="${user.full_name}">`
                    : `<i class="fas fa-user no-photo"></i>`
                }
            </div>
        </div>
        <div class="user-info">
            <h3 class="user-name">${user.full_name}</h3>
            <div class="user-dept">${user.department_id}</div>
            <div class="user-created">Tạo ngày: ${formatDate(user.created_at)}</div>
            <div class="user-actions">
                <button class="btn-circle btn-edit edit-user" title="Chỉnh sửa">
                    <i class="fas fa-pencil-alt"></i>
                </button>
                <button class="btn-circle btn-photo manage-photos" title="Quản lý ảnh">
                    <i class="fas fa-images"></i>
                </button>
                <button class="btn-circle btn-delete delete-user" title="Xóa">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `;
    
    // Thêm các sự kiện cho các nút
    card.querySelector('.edit-user').addEventListener('click', () => openEditUserModal(user));
    card.querySelector('.delete-user').addEventListener('click', () => confirmDeleteUser(user._id));
    card.querySelector('.manage-photos').addEventListener('click', () => openPhotoManager(user._id, user.full_name));
    
    return card;
}

// Hàm định dạng ngày tháng
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    
    try {
        const date = new Date(dateString);
        return `${date.getDate().toString().padStart(2, '0')}/${(date.getMonth() + 1).toString().padStart(2, '0')}/${date.getFullYear()}`;
    } catch (e) {
        return dateString;
    }
}

// Hàm hiển thị danh sách người dùng
async function renderUsers() {
    userGrid.innerHTML = '<div class="loading"><div class="spinner"></div><p>Đang tải dữ liệu người dùng...</p></div>';
    
    try {
        const users = await fetchUsers();
        
        userGrid.innerHTML = '';
        
        if (!users || users.length === 0) {
            userGrid.innerHTML = `
                <div class="empty-user-state">
                    <i class="fas fa-users" style="font-size: 40px; margin-bottom: 15px; color: rgba(0, 0, 0, 0.2);"></i>
                    <p>Chưa có người dùng nào trong hệ thống</p>
                </div>
            `;
            return;
        }
        
        // Sử dụng Promise.all để đợi tất cả các card được tạo
        const cardPromises = users.map(user => createUserCard(user));
        const cards = await Promise.all(cardPromises);
        
        cards.forEach(card => userGrid.appendChild(card));
        
        updateLastUpdatedTime();
    } catch (error) {
        userGrid.innerHTML = `
            <div class="empty-user-state">
                <i class="fas fa-exclamation-circle" style="font-size: 40px; margin-bottom: 15px; color: var(--error);"></i>
                <p>Lỗi khi tải dữ liệu: ${error.message}</p>
            </div>
        `;
    }
}

// Hàm tìm kiếm người dùng
function searchUsers() {
    const searchTerm = searchInput.value.toLowerCase();
    const userCards = userGrid.querySelectorAll('.user-card');
    
    userCards.forEach(card => {
        const userName = card.querySelector('.user-name').textContent.toLowerCase();
        const userDept = card.querySelector('.user-dept').textContent.toLowerCase();
        
        if (userName.includes(searchTerm) || userDept.includes(searchTerm)) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}

// Hàm mở modal thêm người dùng mới
function openAddUserModal() {
    userModalTitle.textContent = 'Thêm người dùng mới';
    userIdInput.value = '';
    userForm.reset();
    userModal.style.display = 'block';
}

// Hàm mở modal chỉnh sửa người dùng
function openEditUserModal(user) {
    userModalTitle.textContent = 'Chỉnh sửa thông tin người dùng';
    userIdInput.value = user._id;
    fullNameInput.value = user.full_name;
    departmentInput.value = user.department_id;
    userModal.style.display = 'block';
}

// Hàm đóng modal người dùng
function closeUserModal() {
    userModal.style.display = 'none';
}

// Hàm lưu thông tin người dùng (thêm/sửa)
async function saveUser() {
    const userId = userIdInput.value;
    const fullName = fullNameInput.value.trim();
    const department = departmentInput.value.trim();
    
    // Kiểm tra dữ liệu
    if (!fullName || !department) {
        showAlert('Vui lòng nhập đầy đủ thông tin người dùng', 'error');
        return;
    }
    
    showLoading();
    
    try {
        // API hiện tại chưa có endpoint cập nhật người dùng, 
        // nên tạm thời chỉ xử lý thêm mới
        if (!userId) {
            // Thêm người dùng mới
            const response = await fetch(`${API_BASE_URL}/add_user`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    full_name: fullName,
                    department_id: department
                })
            });
            
            if (!response.ok) {
                throw new Error('Lỗi khi thêm người dùng');
            }
            
            showAlert('Thêm người dùng thành công!');
        } else {
            // Cập nhật thông tin người dùng
            const response = await fetch(`${API_BASE_URL}/update_user/${userId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    full_name: fullName,
                    department_id: department
                })
            });
            
            if (!response.ok) {
                throw new Error('Lỗi khi cập nhật thông tin người dùng');
            }
            
            const result = await response.json();
            showAlert(result.message || 'Cập nhật thông tin người dùng thành công!');
        }
        
        closeUserModal();
        renderUsers();
    } catch (error) {
        showAlert('Lỗi: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Hàm xác nhận xóa người dùng
function confirmDeleteUser(userId) {
    if (confirm('Bạn có chắc chắn muốn xóa người dùng này?')) {
        deleteUser(userId);
    }
}

// Hàm xóa người dùng
async function deleteUser(userId) {
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE_URL}/delete_user/${userId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error('Lỗi khi xóa người dùng');
        }
        
        showAlert('Xóa người dùng thành công!');
        renderUsers();
    } catch (error) {
        showAlert('Lỗi: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Hàm mở trình quản lý ảnh
async function openPhotoManager(userId, userName) {
    currentPhotoUserId = userId;
    photoModalTitle.textContent = `Quản lý ảnh: ${userName}`;
    photoModal.style.display = 'block';
    
    // Tải danh sách ảnh
    photoGallery.innerHTML = '<div class="loading"><div class="spinner"></div><p>Đang tải ảnh...</p></div>';
    
    try {
        const photos = await fetchUserPhotos(userId);
        renderPhotoGallery(photos, userId);
    } catch (error) {
        photoGallery.innerHTML = `
            <div class="empty-user-state">
                <i class="fas fa-exclamation-circle" style="font-size: 30px; margin-bottom: 10px; color: var(--error);"></i>
                <p>Lỗi khi tải ảnh: ${error.message}</p>
            </div>
        `;
    }
}

// Hàm đóng trình quản lý ảnh
function closePhotoModal() {
    photoModal.style.display = 'none';
    currentPhotoUserId = null;
}

// Hàm lấy danh sách ảnh của người dùng
async function fetchUserPhotos(userId) {
    try {
        const response = await fetch(`${API_BASE_URL}/get_photos/${userId}`);
        if (!response.ok) {
            throw new Error('Không thể lấy danh sách ảnh');
        }
        const data = await response.json();
        // Trả về mảng photos từ đối tượng data
        return data.photos || [];
    } catch (error) {
        console.error('Lỗi khi lấy danh sách ảnh:', error);
        throw error;
    }
}

// Hàm hiển thị danh sách ảnh
function renderPhotoGallery(photos, userId) {
    photoGallery.innerHTML = '';
    
    if (!photos || photos.length === 0) {
        photoGallery.innerHTML = `
            <div class="empty-user-state">
                <i class="fas fa-images" style="font-size: 30px; margin-bottom: 10px; color: rgba(0, 0, 0, 0.2);"></i>
                <p>Chưa có ảnh nào được tải lên</p>
            </div>
        `;
        return;
    }
    
    photos.forEach(fileName => {
        const photoItem = document.createElement('div');
        photoItem.className = 'photo-item';
        photoItem.innerHTML = `
            <img src="${API_BASE_URL}/view_photo/${userId}/${fileName}" alt="${fileName}">
            <div class="delete-photo" data-filename="${fileName}">
                <i class="fas fa-times"></i>
            </div>
        `;
        
        // Thêm sự kiện xóa ảnh
        photoItem.querySelector('.delete-photo').addEventListener('click', () => {
            confirmDeletePhoto(userId, fileName);
        });
        
        photoGallery.appendChild(photoItem);
    });
}

// Hàm xác nhận xóa ảnh
function confirmDeletePhoto(userId, fileName) {
    if (confirm(`Bạn có chắc chắn muốn xóa ảnh "${fileName}"?`)) {
        deletePhoto(userId, fileName);
    }
}

// Hàm xóa ảnh
async function deletePhoto(userId, fileName) {
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE_URL}/delete_photo/${userId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file_name: fileName
            })
        });
        
        if (!response.ok) {
            throw new Error('Lỗi khi xóa ảnh');
        }
        
        showAlert('Xóa ảnh thành công!');
        
        // Cập nhật lại danh sách ảnh
        const photos = await fetchUserPhotos(userId);
        renderPhotoGallery(photos, userId);
    } catch (error) {
        showAlert('Lỗi: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Hàm tải lên ảnh mới
async function uploadPhoto() {
    const fileInput = photoUpload;
    
    if (!fileInput.files || fileInput.files.length === 0) {
        showAlert('Vui lòng chọn ảnh để tải lên', 'error');
        return;
    }
    
    const file = fileInput.files[0];
    
    if (!file.type.startsWith('image/')) {
        showAlert('Vui lòng chọn tệp ảnh hợp lệ', 'error');
        return;
    }
    
    showLoading();
    
    try {
        const formData = new FormData();
        formData.append('photo', file);
        
        const response = await fetch(`${API_BASE_URL}/upload_photo/${currentPhotoUserId}`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Lỗi khi tải ảnh lên');
        }
        
        showAlert('Tải ảnh lên thành công!');
        
        // Đặt lại input file
        fileInput.value = '';
        
        // Cập nhật lại danh sách ảnh
        const photos = await fetchUserPhotos(currentPhotoUserId);
        renderPhotoGallery(photos, currentPhotoUserId);
    } catch (error) {
        showAlert('Lỗi: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Thiết lập các sự kiện
function setupEventListeners() {
    // Sự kiện tìm kiếm
    searchInput.addEventListener('input', searchUsers);
    
    // Sự kiện cho modal người dùng
    addUserBtn.addEventListener('click', openAddUserModal);
    saveUserBtn.addEventListener('click', saveUser);
    cancelUserBtn.addEventListener('click', closeUserModal);
    userModalCloseBtn.addEventListener('click', closeUserModal);
    
    // Sự kiện cho modal ảnh
    closePhotoBtn.addEventListener('click', closePhotoModal);
    photoModalCloseBtn.addEventListener('click', closePhotoModal);
    uploadPhotoBtn.addEventListener('click', uploadPhoto);
    
    // Đóng modal khi click ra ngoài
    window.addEventListener('click', (event) => {
        if (event.target === userModal) {
            closeUserModal();
        }
        if (event.target === photoModal) {
            closePhotoModal();
        }
    });
}

// Khởi tạo ứng dụng
function initApp() {
    setupEventListeners();
    renderUsers();
}

// Chạy ứng dụng khi trang đã tải xong
document.addEventListener('DOMContentLoaded', initApp);