import requests
import json

url = "http://127.0.0.1:8000/api/chase/"

payload = {
  "Team_A": {
    "I": [7, 9, 3, 5],
    "II": [2, 4, 6, 8, 10],
    "III": [1, 11, 12],
    "IV": [3, 5, 7, 9]
  },
  "Team_B": {
    "I": [7, 9, 3, 5],
    "II": [2, 4, 6, 8, 10],
    "III": [1, 11, 12],
    "IV": [3, 5, 7, 9]
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
