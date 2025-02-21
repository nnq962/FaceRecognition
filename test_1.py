import requests

url = "http://127.0.0.1:6123/api/get_user_data"
params = {
    "user_id": 1,
    "start_date": "2025-01-16 23:53:19",
    "end_date": "2025-01-16 23:53:24",
    "camera_name": "webcam_0"
}

response = requests.get(url, params=params)
print(response.json())
