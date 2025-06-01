/**
 * Cấu hình hệ thống chấm công
 * Tệp này chứa các thiết lập toàn cục cho ứng dụng
 */
const config = {
  // Cấu hình API
  apiBaseUrl: 'https://edulive.nnq962.pro',
  
  // Các thiết lập hệ thống
  system: {
    appName: 'Hệ thống chấm công',
    version: '1.0.0',
    maxLoginAttempts: 5,
    sessionTimeout: 30 // minutes
  },
  
  // Cấu hình người dùng
  user: {
    roles: {
      USER: 'user',
      ADMIN: 'admin',
      SUPER_ADMIN: 'super_admin'
    }
  },
  
  // Cấu hình chấm công
  attendance: {
    workHours: {
      start: '08:00',
      end: '17:30'
    },
    lateThreshold: 10, // minutes
    earlyLeaveThreshold: 0// minutes
  },
  
  // Định nghĩa các endpoint API
  endpoints: {
    auth: {
      login: '/api/auth/login',
      logout: '/api/auth/logout'
    },
    users: {
      view_avatar: '/api/view_avatar',
      get_users: '/api/get_users',
      get_user: '/api/get_user',
      add_user: '/api/add_user',
      update_user: '/api/update_user',
      delete_user: '/api/delete_user',
      get_photos: '/api/get_photos',
      view_face_photo: '/api/view_face_photo',
      upload_photo: '/api/upload_photo',
      delete_photo: '/api/delete_photo',
      change_password: '/api/change_password',
      submit_feedback: '/api/submit_feedback',
    },
    
    attendance: {
      get_attendance: '/api/get_attendance',
      view_attendance_photo: '/api/view_attendance_photo',
      create_report: '/api/create_report',
      get_user_reports: '/api/get_user_reports',
      download_report_file: '/api/download_report_file',
      get_pending_reports_summary: '/api/get_pending_reports_summary',
    },
    admin: {
      get_pending_reports_count: '/api/get_pending_reports_count',
      get_reports: '/api/get_reports',
      update_report_status: '/api/update_report_status'
    },
    export: {
      export_attendance: '/api/export_attendance',
      generate_excel: '/api/generate_excel',
      download_excel: '/api/download'
    }
  }
};

// Export config để sử dụng trong các module khác
export default config;