from flask import Blueprint, request, jsonify
import cv2
from database_config import config
from app.auth import login_required, role_required
import utils.onvif_camera_tools as onvif_camera_tools

# Khởi tạo Blueprint
camera_bp = Blueprint('camera_routes', __name__)

# Kết nối MongoDB
camera_collection = config.camera_collection


# ------------------------------------------------------------
@camera_bp.route('/get_cameras', methods=['GET'])
@login_required
@role_required('get_cameras')
def get_cameras():
    try:
        cameras = list(camera_collection.find({}, {"_id": 0}))

        return jsonify({
            "status": "success",
            "message": "Cameras retrieved successfully",
            "data": cameras
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve cameras: {str(e)}"
        }), 500


# ------------------------------------------------------------
@camera_bp.route('/get_camera', methods=['GET'])
@login_required
@role_required('get_camera')
def get_camera():
    _id = request.args.get('_id')
    location = request.args.get('camera_location')

    if _id and location:
        return jsonify({"error": "Only filtering by _id or camera_location is allowed, not both."}), 400
    
    if _id:
        try:
            _id = int(_id)
        except ValueError:
            return jsonify({"error": "_id must be a number."}), 400
        camera = camera_collection.find_one({'_id': _id})
        if camera:
            return jsonify(camera)
        else:
            return jsonify({"error": "No camera found with the given _id."}), 404

    elif location:
        cameras = list(camera_collection.find({'camera_location': location}))
        if cameras:
            return jsonify(cameras)
        else:
            return jsonify({"error": "No cameras found with the given camera_location."}), 404
    
    else:
        return jsonify({"error": "Please provide either _id or camera_location for filtering."}), 400


# ------------------------------------------------------------
@camera_bp.route('/add_camera', methods=['POST'])
@login_required
@role_required('add_camera')
def add_camera():
    data = request.get_json()

    # Lấy auto_discover từ query string (?auto_discover=0)
    auto_discover = request.args.get('auto_discover', '1') == '1'  # mặc định True

    # Các trường bắt buộc
    required_fields = ["camera_id", "name", "room_id"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields: camera_id, name, room_id"}), 400

    camera_id = data["camera_id"]
    name = data["name"]
    room_id = data["room_id"]

    # Kiểm tra trùng camera_id
    if camera_collection.find_one({"camera_id": camera_id}):
        return jsonify({"error": "Camera code already exists."}), 400

    account = data.get("account")
    password = data.get("password")
    if not account or not password:
        return jsonify({"error": "Account and password are required."}), 400

    if auto_discover:
        # Không cho phép nhập IP và RTSP nếu auto_discover là True
        mac_address = data.get("MAC_address")
        if not mac_address:
            return jsonify({"error": "MAC_address is required when auto_discover is enabled."}), 400
        if "IP" in data or "RTSP" in data:
            return jsonify({"error": "Do not provide IP and RTSP when auto_discover is enabled."}), 400

        result = onvif_camera_tools.find_ip_and_rtsp_by_mac(mac_address, account, password)
        if not result:
            return jsonify({"error": f"Could not find device with MAC address {mac_address}."}), 404
        ip_address = result["IP"]
        rtsp_url = result["RTSP"]
    else:
        # Cho phép nhập đầy đủ IP/RTSP
        mac_address = data.get("MAC_address")
        ip_address = data.get("IP")
        rtsp_url = data.get("RTSP")

        if not all([mac_address, ip_address, rtsp_url]):
            return jsonify({"error": "MAC_address, IP, and RTSP are required when auto_discover is disabled."}), 400

    camera = {
        "camera_id": camera_id,
        "name": name,
        "room_id": room_id,
        "account": account,
        "password": password,
        "MAC_address": mac_address,
        "IP": ip_address,
        "RTSP": rtsp_url,
        "created_at": config.get_vietnam_time()
    }

    camera_collection.insert_one(camera)

    return jsonify({
        "message": "Camera added successfully."
    }), 201

# ------------------------------------------------------------
@camera_bp.route('/delete_camera', methods=['DELETE'])
@login_required
@role_required('delete_camera')
def delete_camera():
    camera_id = request.args.get('camera_id')

    if not camera_id:
        return jsonify({"error": "camera_id is required for deletion."}), 400

    result = camera_collection.delete_one({'camera_id': camera_id})

    if result.deleted_count == 0:
        return jsonify({"error": "No camera found with the given camera_id."}), 404

    return jsonify({"message": "Camera deleted successfully."}), 200

# ------------------------------------------------------------
@camera_bp.route('/update_camera', methods=['PUT'])
@login_required
@role_required('update_camera')
def update_camera():
    camera_id = request.args.get('camera_id')
    data = request.get_json()

    if not camera_id:
        return jsonify({"error": "camera_id is required for updating."}), 400

    if not data or not isinstance(data, dict):
        return jsonify({"error": "Invalid request body."}), 400

    # Loại bỏ trường không cho phép cập nhật
    update_fields = {key: data[key] for key in data if key != 'created_at'}

    if not update_fields:
        return jsonify({"error": "No valid fields provided for update."}), 400

    result = camera_collection.update_one(
        {'camera_id': camera_id},
        {'$set': update_fields}
    )

    if result.matched_count == 0:
        return jsonify({"error": "No camera found with the given camera_id."}), 404

    return jsonify({"message": "Camera updated successfully."}), 200

# ------------------------------------------------------------
@camera_bp.route('/get_qr_code', methods=['GET'])
@login_required
@role_required('get_qr_code')
def get_qr_code():
    from flask import send_file
    from qr_code.generate_aruco_tags import generate_aruco_marker
    import io
    import cv2
    
    try:
        marker_id = int(request.args.get("id", 0))
        size = int(request.args.get("size", 400))
        dictionary_name = request.args.get("marker", "DICT_5X5_100")

        marker_image = generate_aruco_marker(dictionary_name, marker_id, size)

        # Encode ảnh thành PNG và đưa vào bộ nhớ RAM
        success, encoded_image = cv2.imencode(".png", marker_image)
        if not success:
            raise RuntimeError("Failed to encode marker image.")
        
        # Dùng BytesIO giả lập file
        image_io = io.BytesIO(encoded_image.tobytes())
        image_io.seek(0)

        return send_file(image_io, mimetype="image/png", as_attachment=False)

    except Exception as e:
        return jsonify({"error": str(e)}), 400 