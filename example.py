import httpx

BASE_URL = "http://localhost:8000"

response = httpx.post(f"{BASE_URL}/token", data={"username": "alvin_admin", "password": "password123"})
token = response.json()["access_token"]
print("POST /token", response.json(), "\n", sep = "\n")

response = httpx.get(f"{BASE_URL}/sensorList", timeout = 30)
print("GET /sensorList", response.json(), "\n", sep = "\n")

response = httpx.get(f"{BASE_URL}/sensorMinMax", params={"target_date": "2019-07-28"}, headers={"Authorization": f"Bearer {token}"}, timeout = 30)
print("GET /sensorMinMax", response.json(), "\n", sep = "\n")

response = httpx.get(f"{BASE_URL}/measureFilter", params={"target_sensor_id_list": [22, 34], "target_metric_id_list": 1, "time_from": "2019-07-01 01:00:00", "time_to": "2019-07-01 05:00:00", "value_from": 25, "value_to": 26.5}, headers={"Authorization": f"Bearer {token}"}, timeout = 30)
print("GET /measureFilter", response.json(), "\n", sep = "\n")