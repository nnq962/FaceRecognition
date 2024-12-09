from pytapo import Tapo
import tkinter as tk
from tkinter import ttk

class TapoCameraController:
    def __init__(self):
        self.user = "admin"
        self.password = "061223abc" 
        self.host = "27.72.62.241"
        
        # Khởi tạo kết nối camera
        self.tapo = Tapo(self.host, self.user, self.password, controlPort=8443)
        
        # Tạo cửa sổ GUI
        self.window = tk.Tk()
        self.window.title("Điều khiển Camera Tapo")
        
        # Tạo các nút điều khiển
        btn_up = ttk.Button(self.window, text="↑", command=self.move_up)
        btn_down = ttk.Button(self.window, text="↓", command=self.move_down)
        btn_left = ttk.Button(self.window, text="←", command=self.move_left)
        btn_right = ttk.Button(self.window, text="→", command=self.move_right)
        btn_reset = ttk.Button(self.window, text="Reset", command=self.calibrate_motor_position)
        
        # Sắp xếp các nút
        btn_up.grid(row=0, column=1, padx=5, pady=5)
        btn_left.grid(row=1, column=0, padx=5, pady=5)
        btn_right.grid(row=1, column=2, padx=5, pady=5)
        btn_down.grid(row=2, column=1, padx=5, pady=5)
        btn_reset.grid(row=1, column=1, padx=5, pady=5)

    def move_up(self):
        self.tapo.moveMotor(0, 10)  # Di chuyển lên 10 đơn vị
        
    def move_down(self):
        self.tapo.moveMotor(0, -10)  # Di chuyển xuống 10 đơn vị
        
    def move_left(self):
        self.tapo.moveMotor(-10, 0)  # Di chuyển trái 10 đơn vị
        
    def move_right(self):
        self.tapo.moveMotor(10, 0)  # Di chuyển phải 10 đơn vị
        
    def calibrate_motor_position(self):
        """Đưa camera về vị trí gốc"""
        self.tapo.calibrateMotor()  
        
    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = TapoCameraController()
    app.run()