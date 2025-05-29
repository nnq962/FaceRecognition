import API from "../core/api.js";
import { showToast } from "../utils/toast.js";
import addUserModal from "../utils/add_user_modal.js";
import editUserModal from "../utils/edit_user_modal.js";

// Global variables
let allUsers = []; // Store all users data
let filteredUsers = []; // Store filtered users

// Function to get user initials from name
function getUserInitials(name) {
    return name.split(' ').map(word => word.charAt(0)).join('').substring(0, 2).toUpperCase();
}

// Function to format date
function formatDate(dateString) {
    const date = new Date(dateString);
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0'); // getMonth() returns 0-11
    const year = date.getFullYear();
    return `${day}/${month}/${year}`;
}

// Function to get avatar colors based on user ID
function getAvatarColor(userId) {
    const colors = [
        { bg: 'bg-blue-100 dark:bg-blue-900', text: 'text-blue-600 dark:text-blue-300' },
        { bg: 'bg-purple-100 dark:bg-purple-900', text: 'text-purple-600 dark:text-purple-300' },
        { bg: 'bg-yellow-100 dark:bg-yellow-900', text: 'text-yellow-600 dark:text-yellow-300' },
        { bg: 'bg-green-100 dark:bg-green-900', text: 'text-green-600 dark:text-green-300' },
        { bg: 'bg-red-100 dark:bg-red-900', text: 'text-red-600 dark:text-red-300' },
        { bg: 'bg-indigo-100 dark:bg-indigo-900', text: 'text-indigo-600 dark:text-indigo-300' },
        { bg: 'bg-pink-100 dark:bg-pink-900', text: 'text-pink-600 dark:text-pink-300' },
        { bg: 'bg-orange-100 dark:bg-orange-900', text: 'text-orange-600 dark:text-orange-300' }
    ];
    
    // Ensure userId is valid number
    const validUserId = userId && !isNaN(userId) ? parseInt(userId) : 0;
    return colors[validUserId % colors.length];
}

// Function to update avatar after render
function updateUserAvatar(avatarElement, userId, userName) {
    if (!avatarElement || !userId) return;

    const avatarUrl = API.getAvatarUrl(userId);

    const testImg = new Image();
    testImg.onload = function () {
        avatarElement.innerHTML = '';
        avatarElement.className = avatarElement.className.replace(/bg-\w+-\d+/, '').replace(/dark:bg-\w+-\d+/, '');
        avatarElement.classList.add('overflow-hidden');

        const imgElement = document.createElement('img');
        imgElement.src = avatarUrl;
        imgElement.alt = userName || 'Avatar';
        imgElement.className = 'w-full h-full object-cover';
        avatarElement.appendChild(imgElement);
    };

    testImg.onerror = function () {
        // Giữ nguyên avatar initials nếu load ảnh thất bại
    };

    testImg.src = avatarUrl;
}

// Function to get role badge color
function getRoleBadgeColor(role) {
    const colorMap = {
        'super_admin': 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
        'admin': 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
        'user': 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
    };
    return colorMap[role] || 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400';
}

// Function to format role name
function formatRole(role) {
    if (role === 'super_admin') {
        return 'Super admin';
    }
    // Capitalize first letter for other roles
    return role ? role.charAt(0).toUpperCase() + role.slice(1) : 'User';
}

// Function to populate filter options
function populateFilterOptions(users) {
    // Get unique roles
    const roles = [...new Set(users.map(user => user.role).filter(Boolean))];
    const roleFilter = document.getElementById('roleFilter');
    
    // Clear existing options except "Tất cả vai trò"
    roleFilter.innerHTML = '<option value="">Tất cả vai trò</option>';
    
    roles.forEach(role => {
        const option = document.createElement('option');
        option.value = role;
        option.textContent = formatRole(role);
        roleFilter.appendChild(option);
    });

    // Get unique departments
    const departments = [...new Set(users.map(user => user.room_id).filter(Boolean))];
    const departmentFilter = document.getElementById('departmentFilter');
    
    // Clear existing options except "Tất cả phòng ban"
    departmentFilter.innerHTML = '<option value="">Tất cả phòng ban</option>';
    
    departments.forEach(department => {
        const option = document.createElement('option');
        option.value = department;
        option.textContent = department;
        departmentFilter.appendChild(option);
    });
}

// Function to normalize text for search (handle Unicode)
function normalizeText(text) {
    if (!text) return '';
    return text
        .toLowerCase()
        .normalize('NFD') // Decompose Unicode characters
        .replace(/[\u0300-\u036f]/g, '') // Remove diacritics/accents
        .trim();
}

// Function to filter users
function filterUsers() {
    const searchTerm = normalizeText(document.getElementById('searchInput').value);
    const selectedRole = document.getElementById('roleFilter').value;
    const selectedDepartment = document.getElementById('departmentFilter').value;

    filteredUsers = allUsers.filter(user => {
        // Search by name with Unicode normalization
        const nameMatch = !searchTerm || normalizeText(user.name).includes(searchTerm);
        
        // Filter by role
        const roleMatch = !selectedRole || user.role === selectedRole;
        
        // Filter by department
        const departmentMatch = !selectedDepartment || user.room_id === selectedDepartment;
        
        return nameMatch && roleMatch && departmentMatch;
    });

    renderUsers(filteredUsers);
    updateResultsCount();
}

// Function to update results count
function updateResultsCount() {
    const totalCount = allUsers.length;
    const filteredCount = filteredUsers.length;
    
    // You can add a results counter element if needed
    console.log(`Hiển thị ${filteredCount} / ${totalCount} người dùng`);
}

// Function to setup add user button
function setupAddUserButton() {
    const addUserBtn = document.getElementById('addUserBtn');
    if (addUserBtn) {
        addUserBtn.addEventListener('click', () => {
            // Set departments data from current users
            const departments = [...new Set(allUsers.map(user => user.room_id).filter(Boolean))];
            addUserModal.setDepartments(departments);
            
            // Show modal
            addUserModal.show();
        });
    }
}

// Function to setup filter event listeners
function setupFilterListeners() {
    const searchInput = document.getElementById('searchInput');
    const roleFilter = document.getElementById('roleFilter');
    const departmentFilter = document.getElementById('departmentFilter');

    // Search input with debounce
    let searchTimeout;
    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(filterUsers, 300); // 300ms debounce
    });

    // Role filter
    roleFilter.addEventListener('change', filterUsers);

    // Department filter
    departmentFilter.addEventListener('change', filterUsers);
}

function generateUserHTML(user, index) {
    const initials = getUserInitials(user.name);
    const userId = user.user_id || user.id || index;
    const avatarColor = getAvatarColor(userId);
    const formattedDate = formatDate(user.created_at);
    const role = user.role || 'user'; // Default to user if no role
    const department = user.room_id || 'Chưa phân bổ'; // Use room_id as department
    const email = user.email || 'Chưa có email'; // Show default text instead of null
    const formattedRole = formatRole(role);
    const roleBadgeColor = getRoleBadgeColor(role);
    
    return `
        <div class="border-b border-gray-100 dark:border-gray-700/50 hover:bg-gray-50/50 dark:hover:bg-gray-800/50 transition-all duration-300 last:border-b-0 backdrop-blur-sm">
            <!-- Mobile Card Layout -->
            <div class="md:hidden p-5">
                <div class="flex flex-col space-y-4">
                    <!-- Top row: Avatar + Name + Actions -->
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-3 flex-1 min-w-0">
                            <div class="w-12 h-12 ${avatarColor.bg} rounded-full flex items-center justify-center flex-shrink-0 shadow-sm ring-1 ring-black/5 dark:ring-white/10" data-user-id="${userId}" data-user-name="${user.name}">
                                <span class="${avatarColor.text} font-semibold text-sm">${initials}</span>
                            </div>
                            <div class="flex-1 min-w-0">
                                <h3 class="font-semibold text-gray-900 dark:text-gray-100 truncate">${user.name}</h3>
                                <p class="text-sm text-gray-500 dark:text-gray-400 truncate mt-0.5" title="${email}">${email}</p>
                            </div>
                        </div>
                        
                        <!-- Action buttons - Always visible and properly spaced -->
                        <div class="flex items-center space-x-2 flex-shrink-0 ml-3">
                            <button onclick="editUser('${userId}')" 
                                class="w-9 h-9 bg-blue-500/90 hover:bg-blue-500 active:bg-blue-600 text-white rounded-lg transition-all duration-200 flex items-center justify-center shadow-sm hover:shadow-md active:scale-95">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                                </svg>
                            </button>
                            <button onclick="deleteUser('${userId}')" 
                                class="w-9 h-9 bg-red-500/90 hover:bg-red-500 active:bg-red-600 text-white rounded-lg transition-all duration-200 flex items-center justify-center shadow-sm hover:shadow-md active:scale-95">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                </svg>
                            </button>
                        </div>
                    </div>
                    
                    <!-- Bottom row: Info badges -->
                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
                        <div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 border border-gray-200/50 dark:border-gray-700/50">
                            <div class="text-xs text-gray-500 dark:text-gray-400 mb-1 font-medium">Vai trò</div>
                            <span class="inline-flex items-center px-2.5 py-1 ${roleBadgeColor} rounded-full text-xs font-medium">${formattedRole}</span>
                        </div>
                        <div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 border border-gray-200/50 dark:border-gray-700/50">
                            <div class="text-xs text-gray-500 dark:text-gray-400 mb-1 font-medium">Phòng ban</div>
                            <div class="text-gray-900 dark:text-gray-100 font-medium truncate" title="${department}">${department}</div>
                        </div>
                        <div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 border border-gray-200/50 dark:border-gray-700/50 sm:col-span-1">
                            <div class="text-xs text-gray-500 dark:text-gray-400 mb-1 font-medium">Tham gia</div>
                            <div class="text-gray-900 dark:text-gray-100 font-medium">${formattedDate}</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Desktop Table Layout -->
            <div class="hidden md:block px-6 py-5">
                <div class="grid grid-cols-6 gap-6 items-center">
                    <div class="flex items-center col-span-2 min-w-0">
                        <div class="w-11 h-11 ${avatarColor.bg} rounded-full flex items-center justify-center flex-shrink-0 shadow-sm ring-1 ring-black/5 dark:ring-white/10" data-user-id="${userId}" data-user-name="${user.name}">
                            <span class="${avatarColor.text} font-semibold text-sm">${initials}</span>
                        </div>
                        <div class="min-w-0 ml-4 flex-1">
                            <div class="font-semibold text-gray-900 dark:text-gray-100 truncate">${user.name}</div>
                            <div class="text-sm text-gray-500 dark:text-gray-400 truncate mt-0.5" title="${email}">${email}</div>
                        </div>
                    </div>
                    <div class="flex justify-start">
                        <span class="inline-flex items-center px-3 py-1.5 ${roleBadgeColor} rounded-full text-xs font-medium">${formattedRole}</span>
                    </div>
                    <div class="text-gray-900 dark:text-gray-100 font-medium truncate" title="${department}">${department}</div>
                    <div class="text-gray-900 dark:text-gray-100 font-medium">${formattedDate}</div>
                    <div class="flex justify-center space-x-2">
                        <button onclick="editUser('${userId}')" 
                            class="inline-flex items-center px-3 py-2 bg-blue-500/90 hover:bg-blue-500 active:bg-blue-600 text-white text-sm font-medium rounded-lg transition-all duration-200 shadow-sm hover:shadow-md active:scale-95">
                            <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                            </svg>
                            Sửa
                        </button>
                        <button onclick="deleteUser('${userId}')" 
                            class="inline-flex items-center px-3 py-2 bg-red-500/90 hover:bg-red-500 active:bg-red-600 text-white text-sm font-medium rounded-lg transition-all duration-200 shadow-sm hover:shadow-md active:scale-95">
                            <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                            </svg>
                            Xóa
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
}


// Function to render all users
function renderUsers(usersData) {
    const usersList = document.getElementById('users-list');
    
    if (!usersData || usersData.length === 0) {
        usersList.innerHTML = `
            <div class="px-6 py-12 text-center">
                <div class="text-gray-500 dark:text-gray-400">
                    <svg class="mx-auto h-12 w-12 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
                    </svg>
                    <p class="text-lg font-medium">Không có người dùng nào</p>
                    <p class="text-sm">Hãy thêm người dùng đầu tiên!</p>
                </div>
            </div>
        `;
        return;
    }

    const usersHTML = usersData.map((user, index) => generateUserHTML(user, index)).join('');
    usersList.innerHTML = usersHTML;
    
    // Update avatars after rendering
    setTimeout(() => {
        usersData.forEach((user, index) => {
            const userId = user.user_id || user.id || index;
            const avatarElements = document.querySelectorAll(`[data-user-id="${userId}"]`);
            
            avatarElements.forEach(avatarElement => {
                updateUserAvatar(avatarElement, userId, user.name);
            });
        });
    }, 100);
    
    // Update avatars after rendering
    setTimeout(() => {
        usersData.forEach((user, index) => {
            const userId = user.user_id || user.id || index;
            const avatarElements = document.querySelectorAll(`[data-user-id="${userId}"]`);
            
            avatarElements.forEach(avatarElement => {
                updateUserAvatar(avatarElement, userId, user.name);
            });
        });
    }, 100);
}

// Action functions (you'll need to implement these)
window.editUser = function(userId) {
    // Find user data
    const user = allUsers.find(u => (u.user_id || u.id) == userId);
    
    if (!user) {
        showToast('Lỗi', 'Không tìm thấy thông tin người dùng', 'error');
        return;
    }

    // Set departments data from current users
    const departments = [...new Set(allUsers.map(user => user.room_id).filter(Boolean))];
    editUserModal.setDepartments(departments);
    
    // Show edit modal with user data
    editUserModal.show(userId, user);
};

window.deleteUser = function(userId) {
    // Find user info
    const user = allUsers.find(u => (u.user_id || u.id) == userId);
    const userName = user ? user.name : 'người dùng này';
    
    // Create custom confirm modal
    showDeleteConfirmModal(userId, userName);
};

// Function to create and show delete confirmation modal
function showDeleteConfirmModal(userId, userName) {
    // Remove existing modal if any
    const existingModal = document.getElementById('deleteConfirmModal');
    if (existingModal) {
        existingModal.remove();
    }

    // Create modal HTML
    const modalHTML = `
        <div id="deleteConfirmModal" class="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/50 backdrop-blur-sm transition-opacity">
            <div class="w-full max-w-md bg-white dark:bg-gray-800 rounded-xl shadow-xl transform transition-all mx-4">
                <!-- Header -->
                <div class="flex items-center p-6 pb-2">
                    <div class="w-12 h-12 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mr-4">
                        <svg class="w-6 h-6 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.232 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
                        </svg>
                    </div>
                    <div>
                        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Xác nhận xóa</h3>
                        <p class="text-sm text-gray-500 dark:text-gray-400">Hành động này không thể hoàn tác</p>
                    </div>
                </div>

                <!-- Body -->
                <div class="px-6 py-4">
                    <p class="text-gray-700 dark:text-gray-300">
                        Bạn có chắc chắn muốn xóa người dùng <strong class="text-gray-900 dark:text-white">${userName}</strong> không?
                    </p>
                    <div class="mt-3 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                        <p class="text-sm text-red-700 dark:text-red-400">
                            ⚠️ Tất cả dữ liệu liên quan đến người dùng này sẽ bị xóa vĩnh viễn.
                        </p>
                    </div>
                </div>

                <!-- Footer -->
                <div class="flex justify-end items-center gap-3 p-6 pt-2 border-t border-gray-200 dark:border-gray-700">
                    <button type="button" id="cancelDelete"
                        class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600">
                        Hủy
                    </button>
                    <button type="button" id="confirmDelete"
                        class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2">
                        <i class="fas fa-trash-alt"></i>
                        Xoá người dùng
                    </button>
                </div>
            </div>
        </div>
    `;

    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    const modal = document.getElementById('deleteConfirmModal');

    // Setup event listeners
    document.getElementById('cancelDelete').addEventListener('click', () => {
        hideDeleteConfirmModal();
    });

    document.getElementById('confirmDelete').addEventListener('click', async () => {
        await handleDeleteUser(userId);
    });

    // Close on backdrop click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            hideDeleteConfirmModal();
        }
    });

    // Close on ESC key
    const handleEsc = (e) => {
        if (e.key === 'Escape') {
            hideDeleteConfirmModal();
            document.removeEventListener('keydown', handleEsc);
        }
    };
    document.addEventListener('keydown', handleEsc);

    // Prevent body scroll
    document.body.style.overflow = 'hidden';

    // Focus cancel button
    setTimeout(() => {
        document.getElementById('cancelDelete').focus();
    }, 150);
}

// Function to hide delete confirmation modal
function hideDeleteConfirmModal() {
    const modal = document.getElementById('deleteConfirmModal');
    if (modal) {
        modal.remove();
    }
    document.body.style.overflow = '';
}

// Function to handle actual user deletion
async function handleDeleteUser(userId) {
    const confirmButton = document.getElementById('confirmDelete');
    const originalText = confirmButton.textContent;

    try {
        // Show loading state
        confirmButton.disabled = true;
        confirmButton.innerHTML = `
            <svg class="animate-spin w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
            Đang xóa...
        `;

        // Call API to delete user
        const response = await API.deleteUser(userId);

        if (response.status === 'success') {
            showToast('Thành công', 'Đã xóa người dùng', 'success');
            hideDeleteConfirmModal();
            
            // Refresh users list
            loadUsers();
        } else {
            throw new Error(response.message || 'Không thể xóa người dùng');
        }

    } catch (error) {
        console.error('Error deleting user:', error);
        showToast('Lỗi', error.message || 'Có lỗi xảy ra khi xóa người dùng', 'error');
        
        // Reset button
        confirmButton.disabled = false;
        confirmButton.textContent = originalText;
    }
}

// Load and render users
async function loadUsers() {
    try {
        const response = await API.getUsers();
        
        if (response.status === 'success') {
            allUsers = response.data; // Store all users
            filteredUsers = [...allUsers]; // Initialize filtered users
            
            populateFilterOptions(allUsers); // Populate filter dropdowns
            setupFilterListeners(); // Setup event listeners
            setupAddUserButton(); // Setup add user button
            renderUsers(filteredUsers); // Render users
            
            showToast('Thành công', `Đã tải ${allUsers.length} người dùng`, 'success');
        } else {
            throw new Error(response.message || 'Không thể tải danh sách người dùng');
        }
    } catch (error) {
        console.error('Error loading users:', error);
        showToast('Lỗi', 'Không thể tải danh sách người dùng', 'error');
        
        // Show error state
        const usersList = document.getElementById('users-list');
        usersList.innerHTML = `
            <div class="px-6 py-12 text-center">
                <div class="text-red-500 dark:text-red-400">
                    <svg class="mx-auto h-12 w-12 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.232 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
                    </svg>
                    <p class="text-lg font-medium">Có lỗi xảy ra</p>
                    <p class="text-sm">Không thể tải danh sách người dùng</p>
                    <button onclick="loadUsers()" class="mt-4 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors">
                        Thử lại
                    </button>
                </div>
            </div>
        `;
    }
}

// Make loadUsers global so modal can refresh the list
window.loadUsers = loadUsers;

// Initialize
loadUsers();