import os
import json
import getpass
import shutil

# Dictionary to store user information
users = {}
departments = {
    1: "HR",
    2: "AI",
    3: "Kỹ thuật",
    4: "Kế toán"
}
user_id_counter = 0  # Global counter for user IDs
data_file = "users.json"  # File to save and load user data
database_folder = "dataset"  # Folder to store user images

def load_data():
    """Load user data from a JSON file."""
    global users, user_id_counter
    if os.path.exists(data_file):
        with open(data_file, "r") as file:
            data = json.load(file)
            users = data.get("users", {})
            user_id_counter = data.get("user_id_counter", 0)
            print("✅ Data loaded successfully.")
    else:
        print("ℹ️ No existing data found. Starting fresh.")

def save_data():
    """Save user data to a JSON file."""
    with open(data_file, "w") as file:
        json.dump({"users": users, "user_id_counter": user_id_counter}, file, indent=4)
    print("✅ Data saved successfully.")

def add_user():
    """Add a new user."""
    global user_id_counter
    username = input("Enter username: ")
    if username in users:
        print("❌ Username already exists!")
        return
    user_id = user_id_counter  # Auto-increment user ID
    password = getpass.getpass("Enter password: ")
    
    # Show department options
    print("\nAvailable Departments:")
    for dept_id, dept_name in departments.items():
        print(f"{dept_id}: {dept_name}")
    
    while True:
        try:
            department_id = int(input("Choose a department by entering its ID: "))
            if department_id in departments:
                break
            else:
                print("❌ Invalid department ID. Please try again.")
        except ValueError:
            print("❌ Please enter a valid number.")
    
    users[username] = {
        "userid": user_id,
        "password": password,
        "departmentid": department_id
    }
    user_id_counter += 1
    print(f"✅ User '{username}' added successfully with UserID: {user_id}.")
    save_data()

def view_users():
    """View all users."""
    if not users:
        print("No users found.")
        return
    print(f"\n{'Username':<15}{'UserID':<10}{'Department':<15}")
    print("-" * 40)
    for username, info in users.items():
        dept_name = departments.get(info['departmentid'], "Unknown")
        print(f"{username:<15}{info['userid']:<10}{dept_name:<15}")

def add_face_image():
    """Add a face image for a user."""
    username = input("Enter your username: ")
    if username not in users:
        print("❌ User not found!")
        return
    
    # Authenticate the user
    password = getpass.getpass("Enter your password: ")
    if password != users[username]['password']:
        print("❌ Incorrect password!")
        return
    
    user_id = users[username]['userid']
    print(f"✅ Logged in as '{username}' (UserID: {user_id}).")
    
    while True:
        # Prompt to select an image file
        image_path = input("Enter the path to the image file: ")
        if not os.path.isfile(image_path):
            print("❌ Invalid file path or file does not exist! Please try again.")
            continue

        # Extract the original file name
        file_name = os.path.basename(image_path)
        
        # Create user folder in database if not exists
        user_folder = os.path.join(database_folder, str(user_id))
        os.makedirs(user_folder, exist_ok=True)

        # Set the destination path with the original file name
        destination = os.path.join(user_folder, file_name)
        
        # Check if the image already exists
        if os.path.exists(destination):
            print(f"⚠️ Image '{file_name}' already exists for user '{username}'.")
            overwrite = input("Do you want to overwrite it? (yes/no): ").strip().lower()
            if overwrite != "yes":
                print("⚠️ Skipping overwrite. Please provide another image.")
                continue

        # Copy the image to the user's folder
        shutil.copy(image_path, destination)
        print(f"✅ Image saved to '{destination}'.")
        break

def update_user():
    """Update user information."""
    username = input("Enter username to update: ")
    if username not in users:
        print("❌ User not found!")
        return
    print(f"Editing user '{username}'. Leave fields empty to keep current values.")
    
    password = getpass.getpass("Enter new password (leave empty to keep current): ") or users[username]['password']
    
    # Show department options
    print("\nAvailable Departments:")
    for dept_id, dept_name in departments.items():
        print(f"{dept_id}: {dept_name}")
    
    while True:
        try:
            department_id = input(f"Enter new department ID (current: {departments[users[username]['departmentid']]}): ")
            if department_id == "":
                department_id = users[username]['departmentid']
                break
            department_id = int(department_id)
            if department_id in departments:
                break
            else:
                print("❌ Invalid department ID. Please try again.")
        except ValueError:
            print("❌ Please enter a valid number.")
    
    users[username].update({
        "password": password,
        "departmentid": department_id
    })
    print(f"✅ User '{username}' updated successfully.")
    save_data()

def delete_user():
    """Delete a user."""
    username = input("Enter username to delete: ")
    if username not in users:
        print("❌ User not found!")
        return
    password = getpass.getpass("Enter password to confirm: ")
    if password == users[username]['password']:
        user_id = users[username]['userid']
        del users[username]
        
        # Remove user's folder from database if exists
        user_folder = os.path.join(database_folder, str(user_id))
        if os.path.exists(user_folder):
            shutil.rmtree(user_folder)
            print(f"✅ User folder '{user_folder}' deleted.")
        
        print(f"✅ User '{username}' deleted successfully.")
        save_data()
    else:
        print("❌ Incorrect password. User not deleted.")

def main():
    """Main function to display the menu and handle user input."""
    load_data()
    while True:
        print("\nUser Management System")
        print("1. Add User")
        print("2. View Users")
        print("3. Update User")
        print("4. Delete User")
        print("5. Add Face Image")
        print("6. Exit")
        choice = input("Enter your choice: ")
        if choice == "1":
            add_user()
        elif choice == "2":
            view_users()
        elif choice == "3":
            update_user()
        elif choice == "4":
            delete_user()
        elif choice == "5":
            add_face_image()
        elif choice == "6":
            print("Exiting User Management System. Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == "__main__":
    main()