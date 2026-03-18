import requests
import json

url = "http://127.0.0.1:8000/api/extra_points/"

payload = {
  "Team_A": {
    "late_entry": [2, 4],
    "out_of_field": [9],
    "warning": [15],
    "dream_run": [8]
  },
  "Team_B": {
    "late_entry": [2, 4],
    "out_of_field": [9],
    "warning": [15],
    "dream_run": [8]
  }
}

print("POSTing data...")
response = requests.post(url, json=payload)
print(f"Status Code: {response.status_code}")
print("Response JSON:")
print(json.dumps(response.json(), indent=2))

if response.status_code == 201:
    print("\n\nGETting data back...")
    list_resp = requests.get(url)
    print(json.dumps(list_resp.json()[-1], indent=2))
