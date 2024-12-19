import getpass
import os
import json

# Danh sách các camera có sẵn
available_cameras = {
    1: "rtsp://local:8554/stream1",
    2: "rtsp://local:8554/stream2",
    3: "rtsp://local:8554/stream3"
}

# Dictionary lưu trữ thông tin người quản lý camera
camera_managers = {}
data_file = "camera_managers.json"  # File để lưu và tải dữ liệu

def load_data():
    """Load camera manager data from a JSON file."""
    global camera_managers
    if os.path.exists(data_file):
        with open(data_file, "r") as file:
            camera_managers = json.load(file)
            print("✅ Camera manager data loaded successfully.")
    else:
        print("ℹ️ No existing camera manager data found. Starting fresh.")

def save_data():
    """Save camera manager data to a JSON file."""
    with open(data_file, "w") as file:
        json.dump(camera_managers, file, indent=4)
    print("✅ Camera manager data saved successfully.")

# Thêm user_id_counter để tự động tạo ID cho người quản lý camera
camera_user_id_counter = 0  # Global counter for camera manager IDs

def add_camera_manager():
    """Add a new camera manager."""
    global camera_user_id_counter
    username = input("Enter username: ")
    if username in camera_managers:
        print("❌ Username already exists!")
        return
    password = getpass.getpass("Enter password: ")

    # Hiển thị danh sách camera có sẵn
    print("\nAvailable Cameras (Enter the number corresponding to the camera):")
    for cam_id, cam_url in available_cameras.items():
        print(f"{cam_id}: {cam_url}")

    while True:
        try:
            camera_id = int(input("Choose a camera by entering its ID: "))
            if camera_id in available_cameras:
                break
            else:
                print("❌ Invalid camera ID. Please try again.")
        except ValueError:
            print("❌ Please enter a valid number.")

    # Tạo ID tự động cho người quản lý camera
    camera_manager_id = camera_user_id_counter
    camera_user_id_counter += 1

    camera_managers[username] = {
        "id": camera_manager_id,
        "password": password,
        "camera_id": camera_id,
        "camera_url": available_cameras[camera_id]
    }
    print(f"✅ Camera manager '{username}' added successfully with ID: {camera_manager_id}.")
    save_data()

def view_camera_managers():
    """View all camera managers."""
    if not camera_managers:
        print("No camera managers found.")
        return
    print(f"\n{'ID':<5}{'Username':<15}{'Camera ID':<20}{'Camera URL':<30}")
    print("-" * 70)
    for username, info in camera_managers.items():
        print(f"{info['id']:<5}{username:<15}{info['camera_id']:<20}{info['camera_url']:<30}")

def update_camera_manager():
    """Update camera manager information."""
    username = input("Enter username to update: ")
    if username not in camera_managers:
        print("❌ Camera manager not found!")
        return
    print(f"Editing camera manager '{username}'. Leave fields empty to keep current values.")
    
    password = getpass.getpass("Enter new password (leave empty to keep current): ") or camera_managers[username]['password']
    
    # Hiển thị danh sách camera có sẵn
    print("\nAvailable Cameras:")
    for cam_id, cam_url in available_cameras.items():
        print(f"Camera {cam_id}: {cam_url}")

    while True:
        try:
            camera_id = input(f"Enter new camera ID (current: {camera_managers[username]['camera_id']}): ")
            if camera_id == "":
                camera_id = camera_managers[username]['camera_id']
                break
            camera_id = int(camera_id)
            if camera_id in available_cameras:
                break
            else:
                print("❌ Invalid camera ID. Please try again.")
        except ValueError:
            print("❌ Please enter a valid number.")

    camera_managers[username].update({
        "password": password,
        "camera_id": camera_id,
        "camera_url": available_cameras[camera_id]
    })
    print(f"✅ Camera manager '{username}' updated successfully.")
    save_data()

def delete_camera_manager():
    """Delete a camera manager."""
    username = input("Enter username to delete: ")
    if username not in camera_managers:
        print("❌ Camera manager not found!")
        return
    password = getpass.getpass("Enter password to confirm: ")
    if password == camera_managers[username]['password']:
        del camera_managers[username]
        print(f"✅ Camera manager '{username}' deleted successfully.")
        save_data()
    else:
        print("❌ Incorrect password. Camera manager not deleted.")

def main():
    """Main function to display the menu and handle user input."""
    load_data()
    while True:
        print("\nCamera Manager System")
        print("1. Add Camera Manager")
        print("2. View Camera Managers")
        print("3. Update Camera Manager")
        print("4. Delete Camera Manager")
        print("5. Exit")
        choice = input("Enter your choice: ")
        if choice == "1":
            add_camera_manager()
        elif choice == "2":
            view_camera_managers()
        elif choice == "3":
            update_camera_manager()
        elif choice == "4":
            delete_camera_manager()
        elif choice == "5":
            print("Exiting Camera Manager System. Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == "__main__":
    main()