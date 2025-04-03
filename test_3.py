import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

# Dữ liệu từ bảng
data = {
    "y": [1250, 1380, 1425, 1425, 1450, 1300, 1400, 1510, 1575, 1650],
    "quang_cao": [41, 54, 63, 54, 48, 46, 62, 61, 64, 71],
    "vi_tri": [21, 30, 63, 54, 25, 46, 26, 61, 45, 17],
    "mat_hang": [4, 9, 36, 5, 6, 23, 62, 16, 43, 12]
}

df = pd.DataFrame(data)

# Tách biến độc lập và phụ thuộc
X = df[["quang_cao", "vi_tri", "mat_hang"]]
y = df["y"]

# Huấn luyện mô hình
model = LinearRegression()
model.fit(X, y)

# Hệ số
intercept = model.intercept_
coefs = model.coef_
print("Phương trình hồi quy:")
print(f"y = {intercept:.2f} + {coefs[0]:.2f}*quang_cao + {coefs[1]:.2f}*vi_tri + {coefs[2]:.2f}*mat_hang")

# Dự đoán và tính SSE
y_pred = model.predict(X)
sse = np.sum((y - y_pred) ** 2)
print(f"SSE = {sse:.2f}")

# Vẽ biểu đồ từng biến vs y (thực tế và dự đoán)
variables = ["quang_cao", "vi_tri", "mat_hang"]
for var in variables:
    plt.figure(figsize=(6, 4))
    plt.scatter(df[var], y, color='blue', label='Thực tế')
    plt.scatter(df[var], y_pred, color='red', label='Dự đoán', marker='x')
    plt.xlabel(var)
    plt.ylabel('Doanh số (y)')
    plt.title(f'{var} vs Doanh số')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()
