// Xu ly API calls cho tat ca trang 
import config from './config.js';

/**
 * Lớp API để xử lý các request tới server
 */
class API {
  /**
   * Lấy token xác thực từ localStorage
   * @returns {string|null} token xác thực
   */
  static getToken() {
    return localStorage.getItem('token');
  }

  /**
   * Tạo headers chuẩn cho API request
   * @param {boolean} includeAuth - Có kèm token xác thực không
   * @returns {Headers} headers cho request
   */
  static getHeaders(includeAuth = true) {
    const headers = new Headers({
      'Content-Type': 'application/json'
    });

    if (includeAuth) {
      const token = this.getToken();
      if (token) {
        headers.append('Authorization', `Bearer ${token}`);
      }
    }

    return headers;
  }

  /**
   * Gửi request API
   * @param {string} endpoint - Đường dẫn API
   * @param {string} method - Phương thức HTTP
   * @param {Object} data - Dữ liệu gửi kèm (cho POST, PUT)
   * @param {boolean} includeAuth - Có kèm token xác thực không
   * @param {boolean} redirectOn401 - Có chuyển hướng khi lỗi 401 không
   * @returns {Promise<any>} Kết quả từ API
   */
  static async request(endpoint, method = 'GET', data = null, includeAuth = true, redirectOn401 = true) {
    const url = `${config.apiBaseUrl}${endpoint}`;

    const options = {
      method,
      credentials: 'include'
    };

    // Xử lý headers và body dựa trên loại data
    if (data && ['POST', 'PUT', 'DELETE'].includes(method)) {
      if (data instanceof FormData) {
        // ✅ Cho FormData: không set Content-Type, để browser tự set với boundary
        options.headers = {};
        if (includeAuth && this.getToken()) {
          options.headers['Authorization'] = `Bearer ${this.getToken()}`;
        }
        options.body = data;
      } else {
        // ✅ Cho JSON data: sử dụng getHeaders() như cũ
        options.headers = this.getHeaders(includeAuth);
        options.body = JSON.stringify(data);
      }
    } else {
      // ✅ Cho GET requests: chỉ headers
      options.headers = this.getHeaders(includeAuth);
    }

    try {
      const response = await fetch(url, options);

      // Lấy dữ liệu từ response để xử lý
      let responseData;
      const contentType = response.headers.get('content-type');

      if (contentType && contentType.includes('application/json')) {
        responseData = await response.json();
      } else {
        responseData = await response.text();
      }

      // Kiểm tra lỗi xác thực (401)
      if (response.status === 401) {
        // Nếu đây là request login (redirectOn401 = false), 
        // không chuyển hướng mà trả về dữ liệu lỗi để xử lý
        if (!redirectOn401) {
          return {
            success: false,
            message: responseData.message || 'Tên đăng nhập hoặc mật khẩu không đúng',
            error: responseData.error || 'invalid_credentials'
          };
        }

        // Nếu là request khác và token hết hạn, xóa token và chuyển hướng
        localStorage.removeItem('token');
        window.location.href = '/login';
        return null;
      }

      // Xử lý các trường hợp response khác
      if (!response.ok) {
        if (typeof responseData === 'object' && responseData.message) {
          throw new Error(responseData.message);
        } else {
          throw new Error('Có lỗi xảy ra');
        }
      }

      return responseData;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Thực hiện đăng nhập
   * @param {string} username - Tên đăng nhập
   * @param {string} password - Mật khẩu
   * @param {boolean} remember - Nhớ mật khẩu
   * @returns {Promise<any>} Thông tin đăng nhập
   */
  static async login(username, password, remember = false) {
    // Tham số cuối cùng false: không tự động chuyển hướng khi status 401
    return this.request(config.endpoints.auth.login, 'POST', { username, password, remember }, false, false);
  }

  /** Thực hiện logout */
  static async logout() {
    return this.request(config.endpoints.auth.logout, 'POST');
  }

  /**
   * Lấy danh sách người dùng
   * @returns {Promise<any>} Danh sách người dùng
   */
  static async getUsers() {
    return this.request(config.endpoints.users.get_users, 'GET');
  }

  /**
   * Lấy thông tin người dùng hiện tại
   * @param {string} userId - ID của người dùng
   * @returns {Promise<any>} Thông tin người dùng
   */
  static async getUser(userId) {
    return this.request(`${config.endpoints.users.get_user}/${userId}`, 'GET');
  }

  /**
   * Thêm người dùng mới
   * @param {Object} userData - Thông tin người dùng mới
   * @param {string} userData.name - Tên người dùng
   * @param {string} userData.room_id - ID phòng
   * @param {string} userData.role - Vai trò (user, admin, super_admin)
   * @param {string} userData.telegram_id - Telegram ID (tùy chọn)
   * @param {string} userData.email - Email (tùy chọn)
   * @returns {Promise<Object>} Thông tin người dùng đã được tạo
   */
  static async addUser(userData) {
    // Validate dữ liệu bắt buộc
    const requiredFields = ['name', 'room_id', 'role'];
    const missingFields = requiredFields.filter(field => !userData[field]);

    if (missingFields.length > 0) {
      return Promise.reject(new Error(`Thiếu các trường bắt buộc: ${missingFields.join(', ')}`));
    }

    // Validate role
    const validRoles = ['user', 'admin', 'super_admin'];
    if (!validRoles.includes(userData.role)) {
      return Promise.reject(new Error('Vai trò không hợp lệ. Chỉ chấp nhận: user, admin, super_admin'));
    }

    return this.request(config.endpoints.users.add_user, 'POST', userData);
  }

  /**
 * Gửi yêu cầu xóa người dùng (không kèm token)
 * @param {string} userId - ID của người dùng cần xóa
 * @returns {Promise<Object>} Kết quả từ server
 */
  static async deleteUser(userId) {
    if (!userId || typeof userId !== 'string') {
      throw new Error('User ID là bắt buộc và phải là string');
    }

    const endpoint = `${config.endpoints.users.delete_user}/${userId}`;
    return this.request(endpoint, 'DELETE', null, false); // includeAuth = false
  }

  /**
   * Đổi mật khẩu
   * @param {string} currentPassword - Mật khẩu hiện tại
   * @param {string} newPassword - Mật khẩu mới
   * @returns {Promise<Object>} Kết quả từ server
   */
  static async changePassword(currentPassword, newPassword) {
    return this.request(config.endpoints.users.change_password, 'POST', { current_password: currentPassword, new_password: newPassword });
  }


  static async submitFeedback(formData) {
    console.log('submitFeedback called with:', formData);
    return this.request(config.endpoints.users.submit_feedback, 'POST', formData);
  }


  /**
   * Cập nhật thông tin người dùng
   * @param {string} userId - ID của người dùng cần cập nhật
   * @param {Object} userData - Dữ liệu cần cập nhật
   * @param {string} userData.name - Tên người dùng (tùy chọn)
   * @param {string} userData.room_id - ID phòng (tùy chọn)
   * @param {string} userData.role - Vai trò (tùy chọn)
   * @param {string} userData.email - Email (tùy chọn)
   * @param {string} userData.telegram_id - Telegram ID (tùy chọn)
   * @param {string} userData.avatar_file - File avatar (tùy chọn)
   * @param {boolean} userData.active - Trạng thái hoạt động (tùy chọn)
   * @returns {Promise<Object>} Thông tin cập nhật
   */
  static async updateUser(userId, userData) {
    // Validate userId
    if (!userId || typeof userId !== 'string') {
      return Promise.reject(new Error('User ID là bắt buộc và phải là string'));
    }

    // Validate userData
    if (!userData || typeof userData !== 'object' || Object.keys(userData).length === 0) {
      return Promise.reject(new Error('Dữ liệu cập nhật không được để trống'));
    }

    // Validate allowed fields
    const allowedFields = ['name', 'room_id', 'avatar_file', 'active', 'role', 'telegram_id', 'email'];
    const invalidFields = Object.keys(userData).filter(field => !allowedFields.includes(field));

    if (invalidFields.length > 0) {
      return Promise.reject(new Error(`Các trường không được phép cập nhật: ${invalidFields.join(', ')}`));
    }

    // Validate role if provided
    if (userData.role) {
      const validRoles = ['user', 'admin', 'super_admin'];
      if (!validRoles.includes(userData.role)) {
        return Promise.reject(new Error('Vai trò không hợp lệ. Chỉ chấp nhận: user, admin, super_admin'));
      }
    }

    // Validate email format if provided
    if (userData.email && userData.email.trim()) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(userData.email)) {
        return Promise.reject(new Error('Định dạng email không hợp lệ'));
      }
    }

    // Validate active field if provided
    if (userData.active !== undefined && typeof userData.active !== 'boolean') {
      return Promise.reject(new Error('Trường active phải là boolean (true/false)'));
    }

    // Clean data - remove empty strings and convert to appropriate types
    const cleanedData = {};
    Object.keys(userData).forEach(key => {
      const value = userData[key];
      if (value !== undefined && value !== null && value !== '') {
        if (key === 'active') {
          cleanedData[key] = Boolean(value);
        } else if (typeof value === 'string') {
          cleanedData[key] = value.trim();
        } else {
          cleanedData[key] = value;
        }
      }
    });

    const endpoint = `${config.endpoints.users.update_user}/${userId}`;
    return this.request(endpoint, 'PUT', cleanedData);
  }


  /**
   * Lấy danh sách ảnh của người dùng
   * @param {string} userId - ID của người dùng
   * @param {string} type - Loại ảnh ("face" hoặc "avatar")
   * @returns {Promise<Object>} Danh sách ảnh
   */
  static async getUserPhotos(userId, type) {
    // Validate userId
    if (!userId || typeof userId !== 'string') {
      return Promise.reject(new Error('User ID là bắt buộc và phải là string'));
    }

    // Validate type
    if (!type || !['face', 'avatar'].includes(type)) {
      return Promise.reject(new Error('Type phải là "face" hoặc "avatar"'));
    }

    const queryParams = new URLSearchParams({ type });
    const endpoint = `${config.endpoints.users.get_photos}/${userId}?${queryParams.toString()}`;

    return this.request(endpoint, 'GET');
  }

  /**
   * Lấy URL để xem ảnh khuôn mặt
   * @param {string} userId - ID của người dùng
   * @param {string} filename - Tên file ảnh
   * @returns {string} URL để xem ảnh
   */
  static getFacePhotoUrl(userId, filename) {
    // Validate parameters
    if (!userId || !filename) {
      return null;
    }

    return `${config.apiBaseUrl}${config.endpoints.users.view_face_photo}/${userId}/${filename}`;
  }

  /**
   * Kiểm tra xem ảnh khuôn mặt có tồn tại không
   * @param {string} userId - ID của người dùng
   * @param {string} filename - Tên file ảnh
   * @returns {Promise<boolean>} true nếu ảnh tồn tại, false nếu không
   */
  static async checkFacePhotoExists(userId, filename) {
    try {
      if (!userId || !filename) {
        return false;
      }

      const url = this.getFacePhotoUrl(userId, filename);

      // Sử dụng HEAD request để kiểm tra sự tồn tại của ảnh
      const response = await fetch(url, {
        method: 'HEAD',
        headers: this.getHeaders(true),
        credentials: 'include'
      });

      return response.ok;
    } catch (error) {
      return false;
    }
  }

  /**
   * Tải ảnh khuôn mặt về dưới dạng blob để hiển thị
   * @param {string} userId - ID của người dùng
   * @param {string} filename - Tên file ảnh
   * @returns {Promise<Blob>} Blob của ảnh
   */
  static async getFacePhotoBlob(userId, filename) {
    try {
      if (!userId || !filename) {
        throw new Error('User ID và filename là bắt buộc');
      }

      const url = this.getFacePhotoUrl(userId, filename);

      const response = await fetch(url, {
        method: 'GET',
        headers: this.getHeaders(true),
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Không thể tải ảnh');
      }

      return await response.blob();
    } catch (error) {
      throw new Error(`Lỗi tải ảnh: ${error.message}`);
    }
  }


  /**
   * Lấy URL avatar
   * @param {string} user_id - ID người dùng
   * @returns {string} URL avatar
   */
  static getAvatarUrl(user_id) {
    // Tạo URL trực tiếp đến ảnh, khớp với route của backend
    return `${config.apiBaseUrl}${config.endpoints.users.view_avatar}/${user_id}`;
  }

  /**
   * Lấy lịch sử chấm công của người dùng
   * @param {string} user_id - ID người dùng
   * @param {string} startDate - Ngày bắt đầu (YYYY-MM-DD)
   * @param {string} endDate - Ngày kết thúc (YYYY-MM-DD)
   * @returns {Promise<any>} Lịch sử chấm công
   */
  static async getAttendance(user_id, startDate, endDate) {
    const queryParams = new URLSearchParams({
      user_id,
      start_date: startDate,
      end_date: endDate
    }).toString();

    return this.request(`${config.endpoints.attendance.get_attendance}?${queryParams}`);
  }


  /**
   * Lấy URL ảnh chấm công
   * @param {string} user_id - ID người dùng
   * @param {string} date - Ngày chấm công (YYYY-MM-DD)
   * @param {string} type - Loại ảnh (check_in hoặc check_out)
   * @returns {string} URL ảnh chấm công
   */
  static getAttendancePhotoUrl(user_id, date, type) {
    // Chuyển đổi format ngày từ YYYY-MM-DD sang YYYY_MM_DD
    const formattedDate = date.replace(/-/g, '_');

    // Tạo URL trực tiếp đến ảnh, khớp với route của backend
    return `${config.apiBaseUrl}${config.endpoints.attendance.view_attendance_photo}/${user_id}?date=${formattedDate}&type=${type}`;
  }

  // Thêm các methods sau vào class API trong file api.js

  /**
   * Upload ảnh cho người dùng (face hoặc avatar)
   * @param {string} userId - ID của người dùng
   * @param {File} photoFile - File ảnh cần upload
   * @param {string} type - Loại ảnh ("face" hoặc "avatar")
   * @returns {Promise<Object>} Kết quả upload
   */
  static async uploadPhoto(userId, photoFile, type) {
    // Validate parameters
    if (!userId || typeof userId !== 'string') {
      return Promise.reject(new Error('User ID là bắt buộc và phải là string'));
    }

    if (!photoFile || !(photoFile instanceof File)) {
      return Promise.reject(new Error('Photo file là bắt buộc và phải là File object'));
    }

    if (!type || !['face', 'avatar'].includes(type)) {
      return Promise.reject(new Error('Type phải là "face" hoặc "avatar"'));
    }

    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/heic', 'image/heif'];
    if (!allowedTypes.includes(photoFile.type)) {
      return Promise.reject(new Error('Chỉ chấp nhận file JPG, JPEG, PNG, HEIC, HEIF'));
    }

    // Validate file size (10MB)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (photoFile.size > maxSize) {
      return Promise.reject(new Error('File không được vượt quá 10MB'));
    }

    try {
      // Tạo FormData
      const formData = new FormData();
      formData.append('photo', photoFile);
      formData.append('type', type);

      // Tạo URL
      const endpoint = `${config.endpoints.users.upload_photo}/${userId}`;
      const url = `${config.apiBaseUrl}${endpoint}`;

      // Gửi request
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.getToken()}` // Không set Content-Type để browser tự set với boundary
        },
        body: formData,
        credentials: 'include'
      });

      // Xử lý response
      const contentType = response.headers.get('content-type');
      let responseData;

      if (contentType && contentType.includes('application/json')) {
        responseData = await response.json();
      } else {
        responseData = await response.text();
      }

      // Kiểm tra lỗi xác thực (401)
      if (response.status === 401) {
        localStorage.removeItem('token');
        window.location.href = '/login';
        return null;
      }

      // Xử lý lỗi khác
      if (!response.ok) {
        if (typeof responseData === 'object' && responseData.message) {
          throw new Error(responseData.message);
        } else {
          throw new Error('Có lỗi xảy ra khi upload ảnh');
        }
      }

      return responseData;
    } catch (error) {
      throw new Error(`Lỗi upload ảnh: ${error.message}`);
    }
  }

  /**
   * Upload nhiều ảnh khuôn mặt cùng lúc
   * @param {string} userId - ID của người dùng
   * @param {FileList|Array} photoFiles - Danh sách file ảnh
   * @returns {Promise<Array>} Mảng kết quả upload cho từng ảnh
   */
  static async uploadMultipleFacePhotos(userId, photoFiles) {
    if (!userId || typeof userId !== 'string') {
      return Promise.reject(new Error('User ID là bắt buộc và phải là string'));
    }

    if (!photoFiles || photoFiles.length === 0) {
      return Promise.reject(new Error('Danh sách ảnh không được rỗng'));
    }

    const results = [];
    const errors = [];

    // Upload từng ảnh một cách tuần tự để tránh quá tải server
    for (let i = 0; i < photoFiles.length; i++) {
      const file = photoFiles[i];
      try {
        const result = await this.uploadPhoto(userId, file, 'face');
        results.push({
          file: file.name,
          success: true,
          data: result
        });
      } catch (error) {
        errors.push({
          file: file.name,
          success: false,
          error: error.message
        });
      }
    }

    return {
      results,
      errors,
      total: photoFiles.length,
      successful: results.length,
      failed: errors.length
    };
  }

  /**
   * Xóa ảnh của người dùng
   * @param {string} userId - ID của người dùng
   * @param {string} filename - Tên file ảnh cần xóa
   * @param {string} type - Loại ảnh ("face" hoặc "avatar")
   * @returns {Promise<Object>} Kết quả xóa
   */
  static async deletePhoto(userId, filename, type) {
    // Validate parameters
    if (!userId || typeof userId !== 'string') {
      return Promise.reject(new Error('User ID là bắt buộc và phải là string'));
    }

    if (!filename || typeof filename !== 'string') {
      return Promise.reject(new Error('Filename là bắt buộc và phải là string'));
    }

    if (!type || !['face', 'avatar'].includes(type)) {
      return Promise.reject(new Error('Type phải là "face" hoặc "avatar"'));
    }

    const data = {
      file_name: filename,
      type: type
    };

    const endpoint = `${config.endpoints.users.delete_photo}/${userId}`;
    return this.request(endpoint, 'DELETE', data);
  }

  /**
   * Upload ảnh avatar (convenience method)
   * @param {string} userId - ID của người dùng
   * @param {File} photoFile - File ảnh avatar
   * @returns {Promise<Object>} Kết quả upload
   */
  static async uploadAvatar(userId, photoFile) {
    return this.uploadPhoto(userId, photoFile, 'avatar');
  }

  /**
   * Upload ảnh khuôn mặt (convenience method)
   * @param {string} userId - ID của người dùng
   * @param {File} photoFile - File ảnh khuôn mặt
   * @returns {Promise<Object>} Kết quả upload
   */
  static async uploadFacePhoto(userId, photoFile) {
    return this.uploadPhoto(userId, photoFile, 'face');
  }

  /**
   * Kiểm tra xem ảnh chấm công có tồn tại không
   * @param {string} user_id - ID người dùng
   * @param {string} date - Ngày chấm công (YYYY-MM-DD)
   * @param {string} type - Loại ảnh (check_in hoặc check_out)
   * @returns {Promise<boolean>} true nếu ảnh tồn tại, false nếu không
   */
  static async checkAttendancePhotoExists(user_id, date, type) {
    try {
      const url = this.getAttendancePhotoUrl(user_id, date, type);

      // Sử dụng HEAD request để kiểm tra sự tồn tại của ảnh
      const response = await fetch(url, {
        method: 'HEAD',
        headers: this.getHeaders(true),
        credentials: 'include'
      });

      return response.ok;
    } catch (error) {
      return false;
    }
  }

  /**
 * Gửi báo cáo (chung cho tất cả các loại báo cáo)
 * @param {string} userId - ID của người dùng tạo báo cáo
 * @param {Object} reportData - Dữ liệu báo cáo 
 * @param {FileList|null} files - Danh sách file đính kèm (nếu có)
 * @returns {Promise<any>} Kết quả báo cáo
 */
  static async createReport(userId, reportData, files = null) {
    const endpoint = `${config.endpoints.attendance.create_report}/${userId}`;

    // Không cần gửi user_id trong reportData vì đã nằm trong URL
    // Loại bỏ user_id khỏi reportData nếu có
    const { user_id, ...dataWithoutUserId } = reportData;

    // Nếu không có file, sử dụng JSON request
    if (!files || files.length === 0) {
      return this.request(endpoint, 'POST', dataWithoutUserId);
    }

    // Nếu có file, sử dụng FormData
    const formData = new FormData();

    // Thêm dữ liệu báo cáo vào FormData
    Object.keys(dataWithoutUserId).forEach(key => {
      formData.append(key, dataWithoutUserId[key]);
    });

    // Thêm các file vào FormData
    if (files) {
      for (let i = 0; i < files.length; i++) {
        formData.append('files[]', files[i]);
      }
    }

    // Gửi request với FormData
    const url = `${config.apiBaseUrl}${endpoint}`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.getToken()}`
        },
        body: formData,
        credentials: 'include'
      });

      const contentType = response.headers.get('content-type');
      let responseData;

      if (contentType && contentType.includes('application/json')) {
        responseData = await response.json();
      } else {
        responseData = await response.text();
      }

      if (!response.ok) {
        if (typeof responseData === 'object' && responseData.message) {
          throw new Error(responseData.message);
        } else {
          throw new Error('Có lỗi xảy ra');
        }
      }

      return responseData;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Lấy danh sách báo cáo của người dùng
   * @param {string} userId - ID người dùng (bắt buộc)
   * @param {Object} params - Tham số truy vấn (report_type, status, from_date, to_date, page, limit)
   * @returns {Promise<Object>} Danh sách báo cáo
   */
  static getUserReports(userId, params = {}) {
    if (!userId) {
      return Promise.reject(new Error('Thiếu tham số user_id'));
    }

    // Làm sạch params trước khi tạo URLSearchParams
    const cleanParams = { ...params };
    Object.keys(cleanParams).forEach(key => {
      if (cleanParams[key] === undefined ||
        cleanParams[key] === null ||
        cleanParams[key] === 'undefined' ||
        cleanParams[key] === 'null') {
        delete cleanParams[key];
      }
    });

    // Không cần thêm userId vào query params nữa vì đã có trong URL
    const queryParams = new URLSearchParams(cleanParams);

    const queryString = queryParams.toString() ? `?${queryParams.toString()}` : '';
    const endpoint = `${config.endpoints.attendance.get_user_reports}/${userId}${queryString}`;
    return this.request(endpoint, 'GET');
  }

  /**
   * Lấy URL tải file đính kèm của báo cáo
   * @param {string} userId - ID của người dùng (bắt buộc)
   * @param {string} filename - Tên file đã lưu
   * @returns {string} URL tải file
   */
  static getReportFileUrl(userId, filename) {
    if (!userId) {
      return null;
    }

    return `${config.apiBaseUrl}${config.endpoints.attendance.download_report_file}/${userId}/${filename}`;
  }


  /**
   * Lấy số lượng báo cáo cần phê duyệt
   * @param {string} date - Ngày cần kiểm tra (YYYY-MM-DD), mặc định là hôm nay
   * @param {string} reportType - Loại báo cáo (all, incorrect_photo, machine_error, leave_request)
   * @returns {Promise<Object>} Số lượng báo cáo cần phê duyệt
   */
  static async getPendingReportsCount(date = null, reportType = 'all') {
    const params = {};

    if (date) {
      params.date = date;
    }

    if (reportType && reportType !== 'all') {
      params.report_type = reportType;
    }

    const queryString = Object.keys(params).length > 0
      ? `?${new URLSearchParams(params).toString()}`
      : '';

    return this.request(`${config.endpoints.admin.get_pending_reports_count}${queryString}`);
  }


  /**
   * Lấy danh sách báo cáo để phê duyệt (dành cho admin/super_admin)
   * @param {Object} params - Tham số lọc
   * @param {string} params.status - Trạng thái báo cáo (all, pending, approved, rejected)
   * @param {string} params.from_date - Từ ngày (YYYY-MM-DD)
   * @param {string} params.to_date - Đến ngày (YYYY-MM-DD)
   * @returns {Promise<Object>} Danh sách báo cáo với thông tin user
   */
  static async getReports(params = {}) {
    // Làm sạch params trước khi tạo URLSearchParams
    const cleanParams = { ...params };
    Object.keys(cleanParams).forEach(key => {
      if (cleanParams[key] === undefined ||
        cleanParams[key] === null ||
        cleanParams[key] === 'undefined' ||
        cleanParams[key] === 'null' ||
        cleanParams[key] === '') {
        delete cleanParams[key];
      }
    });

    const queryString = Object.keys(cleanParams).length > 0
      ? `?${new URLSearchParams(cleanParams).toString()}`
      : '';

    return this.request(`${config.endpoints.admin.get_reports}${queryString}`, 'GET');
  }

  /**
   * Cập nhật trạng thái báo cáo (phê duyệt/từ chối)
   * @param {string} reportId - ID của báo cáo
   * @param {string} status - Trạng thái mới ("approved" hoặc "rejected")
   * @param {string} adminNote - Phản hồi từ quản lý (optional)
   * @returns {Promise<Object>} Kết quả cập nhật
   */
  static async updateReportStatus(reportId, status, adminNote = '') {
    if (!reportId) {
      return Promise.reject(new Error('Thiếu tham số report ID'));
    }

    if (!['approved', 'rejected'].includes(status)) {
      return Promise.reject(new Error('Trạng thái không hợp lệ. Chỉ chấp nhận "approved" hoặc "rejected"'));
    }

    const endpoint = `${config.endpoints.admin.update_report_status}/${reportId}`;
    const data = {
      status: status,
      admin_note: adminNote
    };

    return this.request(endpoint, 'POST', data);
  }


  /**
   * Xuất dữ liệu chấm công theo tháng
   * @param {string} month - Tháng cần xuất (YYYY-MM)
   * @returns {Promise<Object>} Dữ liệu chấm công đã được tích hợp thông tin từ reports
   */
  static async exportAttendance(month) {
    if (!month) {
      return Promise.reject(new Error('Thiếu tham số month (format: YYYY-MM)'));
    }

    // Validate month format
    const monthRegex = /^\d{4}-\d{2}$/;
    if (!monthRegex.test(month)) {
      return Promise.reject(new Error('Format tháng không hợp lệ. Sử dụng YYYY-MM'));
    }

    const data = { month: month };
    return this.request(config.endpoints.export.export_attendance, 'POST', data);
  }


  /**
   * Tạo file Excel từ dữ liệu chấm công
   * @param {Array} data - Mảng dữ liệu chấm công đã được chỉnh sửa
   * @param {string} month - Tháng xuất (YYYY-MM)
   * @returns {Promise<Object>} Thông tin file Excel được tạo
   */
  static async generateExcel(data, month) {
    if (!data || !Array.isArray(data) || data.length === 0) {
      return Promise.reject(new Error('Dữ liệu không hợp lệ hoặc rỗng'));
    }

    if (!month) {
      return Promise.reject(new Error('Thiếu tham số month (format: YYYY-MM)'));
    }

    // Validate month format
    const monthRegex = /^\d{4}-\d{2}$/;
    if (!monthRegex.test(month)) {
      return Promise.reject(new Error('Format tháng không hợp lệ. Sử dụng YYYY-MM'));
    }

    const requestData = {
      data: data,
      month: month
    };

    return this.request(config.endpoints.export.generate_excel, 'POST', requestData);
  }

  /**
   * Tải file Excel đã được tạo
   * @param {string} filePath - Đường dẫn file từ server
   * @param {string} filename - Tên file tải về (tùy chọn)
   * @returns {Promise<void>} Tải file về máy
   */
  static async downloadExcelFile(filePath, filename = null) {
    try {
      // Tạo URL với query parameter
      const downloadUrl = `${config.apiBaseUrl}${config.endpoints.export.download_excel}?file=${encodeURIComponent(filePath)}`;

      const response = await fetch(downloadUrl, {
        method: 'GET',
        headers: this.getHeaders(true),
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Không thể tải file');
      }

      // Tạo blob từ response
      const blob = await response.blob();

      // Tạo URL tạm thời cho blob
      const url = window.URL.createObjectURL(blob);

      // Tạo thẻ a ẩn để tải file
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;

      // Đặt tên file
      if (filename) {
        a.download = filename;
      } else {
        // Lấy tên file từ response header hoặc tạo tên mặc định
        const contentDisposition = response.headers.get('content-disposition');
        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename="(.+)"/);
          a.download = filenameMatch ? filenameMatch[1] : `bao_cao_cham_cong_${new Date().getTime()}.xlsx`;
        } else {
          a.download = `bao_cao_cham_cong_${new Date().getTime()}.xlsx`;
        }
      }

      // Thêm vào DOM, click và xóa
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

    } catch (error) {
      throw new Error(`Lỗi tải file: ${error.message}`);
    }
  }

  /**
   * Tạo và tải Excel trong một bước (convenience method)
   * @param {Array} data - Mảng dữ liệu chấm công
   * @param {string} month - Tháng xuất (YYYY-MM)
   * @param {string} filename - Tên file tùy chọn
   * @returns {Promise<void>} Hoàn thành quá trình xuất và tải
   */
  static async exportAndDownloadExcel(data, month, filename = null) {
    try {
      // Bước 1: Tạo file Excel
      const result = await this.generateExcel(data, month);

      if (!result.file) {
        throw new Error('Không nhận được đường dẫn file từ server');
      }

      // Bước 2: Tải file
      const defaultFilename = `bao_cao_cham_cong_${month.replace('-', '_')}.xlsx`;
      await this.downloadExcelFile(result.file, filename || defaultFilename);

      return result;
    } catch (error) {
      throw new Error(`Lỗi xuất Excel: ${error.message}`);
    }
  }


}

// Export API class
export default API;