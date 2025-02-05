from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import requests
from functools import wraps
import os


app = Flask(__name__)
app.secret_key = "your_secret_key"  # Khóa bí mật để mã hóa session (đặt giá trị an toàn hơn)
API_SERVER_URL = "http://127.0.0.1:6123"

# ----------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))  # Chuyển hướng đến trang login nếu chưa đăng nhập
        return f(*args, **kwargs)
    return decorated_function

# ----------------------------------------------------------------
@app.route('/login', methods=['POST'])
def handle_login():
    username = request.form['username']
    password = request.form['password']

    try:
        response = requests.post(f"{API_SERVER_URL}/api/login", json={
            "username": username,
            "password": password
        })

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                session['username'] = username
                return redirect(url_for('dashboard'))  # Chuyển hướng đến Dashboard

        elif response.status_code == 404:
            session['error'] = "Username not found. Please try again."
        elif response.status_code == 401:
            session['error'] = "Incorrect password. Please try again."
        else:
            session['error'] = f"Unexpected error: {response.status_code}"

    except requests.exceptions.RequestException as e:
        session['error'] = f"Failed to connect to API server: {e}"

    # Redirect để áp dụng PRG, tránh lặp lại POST khi reload
    return redirect(url_for('login'))

# ----------------------------------------------------------------
@app.route('/')
def login():
    error = session.pop('error', None)  # Lấy lỗi từ session (nếu có)
    return render_template('login.html', error=error)

# ----------------------------------------------------------------
@app.route('/dashboard')
@login_required
def dashboard():
    # Gửi yêu cầu đến API để lấy dữ liệu
    response = requests.get(f"{API_SERVER_URL}/api/get_attendance")
    employees = response.json() if response.status_code == 200 else []

    return render_template('dashboard.html', employees=employees)

# ----------------------------------------------------------------
@app.route('/manage_employees', methods=['GET', 'POST'])
@login_required
def manage_employees():
    if request.method == 'POST':
        full_name = request.form['full_name']
        department_id = request.form['department_id']

        response = requests.post(f"{API_SERVER_URL}/api/add_user", json={
            "full_name": full_name,
            "department_id": department_id
        })

        if response.status_code == 201:
            session['message'] = "Employee added successfully!"
        else:
            session['message'] = response.json().get("error", "Failed to add employee.")

        # Redirect để tránh POST khi reload
        return redirect(url_for('manage_employees'))

    # Xử lý GET
    response = requests.get(f"{API_SERVER_URL}/api/get_all_users")
    employees = response.json() if response.status_code == 200 else []
    message = session.pop('message', None)  # Lấy thông báo từ session (nếu có)

    return render_template('manage_employees.html', employees=employees, message=message)

# ----------------------------------------------------------------
@app.route('/delete_employee', methods=['POST'])
@login_required
def delete_employee():
    employee_id = request.form['employee_id']

    # Gửi yêu cầu DELETE tới API backend
    response = requests.delete(f"{API_SERVER_URL}/api/delete_user/{employee_id}")
    if response.status_code == 200:
        message = "Employee deleted successfully!"
    elif response.status_code == 404:
        message = "User not found."
    else:
        message = "Failed to delete user."

    # Lưu thông báo vào session để hiển thị sau redirect
    session['message'] = message
    return redirect(url_for('manage_employees'))

# ----------------------------------------------------------------
@app.route('/upload_photo', methods=['POST'])
@login_required
def upload_photo():
    employee_id = request.form['employee_id']
    photo = request.files['photo']

    # Gửi file ảnh tới API backend
    files = {'photo': (photo.filename, photo.read(), photo.content_type)}
    response = requests.post(f"{API_SERVER_URL}/api/upload_photo/{employee_id}", files=files)

    if response.status_code == 200:
        session['message'] = "Photo uploaded successfully!"
    else:
        session['message'] = response.json().get("error", "Failed to upload photo.")

    return redirect(url_for('manage_employees'))

# ----------------------------------------------------------------
@app.route('/manage_managers', methods=['GET', 'POST'])
@login_required
def manage_managers():
    if request.method == 'POST':
        # Xử lý thêm manager từ form
        fullname = request.form['fullname']
        department_id = request.form['department_id']
        username = request.form['username']
        password = request.form['password']

        # Gửi yêu cầu tới API backend
        response = requests.post(f"{API_SERVER_URL}/api/add_manager", json={
            "fullname": fullname,
            "department_id": department_id,
            "username": username,
            "password": password
        })

        if response.status_code == 201:
            session['message'] = "Manager added successfully!"
        else:
            session['message'] = response.json().get("error", "Failed to add manager.")

        return redirect(url_for('manage_managers'))

    # Lấy danh sách managers từ API
    response = requests.get(f"{API_SERVER_URL}/api/get_all_managers")
    managers = response.json() if response.status_code == 200 else []

    # Hiển thị thông báo
    message = session.pop('message', None)
    return render_template('manage_managers.html', managers=managers, message=message)

# ----------------------------------------------------------------
@app.route('/delete_manager', methods=['POST'])
@login_required
def delete_manager():
    manager_id = request.form['manager_id']

    # Gửi yêu cầu DELETE tới API backend
    response = requests.delete(f"{API_SERVER_URL}/api/delete_manager/{manager_id}")

    if response.status_code == 200:
        session['message'] = "Manager deleted successfully!"
    else:
        session['message'] = response.json().get("error", "Failed to delete manager.")

    return redirect(url_for('manage_managers'))

# ----------------------------------------------------------------
@app.route('/webrtc')
@login_required
def webrtc():
    return render_template('webrtc_client.html')

# ----------------------------------------------------------------
@app.route('/logout')
def logout():
    # Xóa session (xóa username) để đăng xuất người dùng
    session.pop('username', None)
    # Chuyển hướng về trang login
    return redirect(url_for('login'))

# ----------------------------------------------------------------
@app.route('/export_attendance', methods=['GET', 'POST'])
@login_required
def export_attendance():
    if request.method == 'GET':
        # Hiển thị form nhập liệu
        return render_template('export_attendance.html')

    if request.method == 'POST':
        # Lấy dữ liệu từ form
        year = request.form.get("year")
        month = request.form.get("month")
        camera_name = request.form.get("camera_name")

        if not year or not month or not camera_name:
            return jsonify({"error": "Vui lòng nhập đầy đủ năm, tháng và tên camera"}), 400

        try:
            # Tạo định dạng tháng
            month_str = f"{year}-{month.zfill(2)}"

            # Gửi yêu cầu tới API backend
            response = requests.post(
                f"{API_SERVER_URL}/api/export_attendance",
                json={"month": month_str, "camera_name": camera_name}
            )

            # Kiểm tra phản hồi từ backend
            if response.status_code != 200:
                return jsonify({"error": f"Lỗi từ backend: {response.text}"}), response.status_code

            # Lấy đường dẫn tệp từ phản hồi JSON
            result = response.json()
            file_path = result.get("file")

            if not file_path or not os.path.exists(file_path):
                return jsonify({"error": "Không tìm thấy tệp xuất"}), 500

            # Gửi tệp Excel về trình duyệt
            return send_file(file_path, as_attachment=True)

        except Exception as e:
            return jsonify({"error": f"Lỗi xảy ra: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5555)