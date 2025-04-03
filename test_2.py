import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

# Dữ liệu
x = np.array([41, 54, 63, 63, 46, 48, 50, 61, 64, 71]).reshape(-1, 1)
y = np.array([1250, 1380, 1425, 1425, 1450, 1300, 1400, 1510, 1575, 1650])

# Mô hình hồi quy
model = LinearRegression()
model.fit(x, y)

# Dự đoán
y_pred = model.predict(x)

# Hệ số hồi quy
a = model.intercept_
b = model.coef_[0]
print(f"Hàm hồi quy: y = {a:.2f} + {b:.2f} * x")

# Tính MSE
mse = mean_squared_error(y, y_pred)
print(f"MSE: {mse:.2f}")

# Vẽ đồ thị
plt.scatter(x, y, color='blue', label='Dữ liệu thực tế')
plt.plot(x, y_pred, color='red', label='Đường hồi quy')
plt.xlabel('Chi tiêu quảng cáo (x)')
plt.ylabel('Doanh thu (y)')
plt.title('Hồi quy tuyến tính: Chi tiêu quảng cáo vs Doanh thu')
plt.legend()
plt.grid(True)
plt.show()
