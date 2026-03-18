import requests
import json

url = "http://127.0.0.1:8000/api/running_batch/"

payload = {
  "Team_A": {
    "turn_I": [
      [7, 9, 3],
      [5, 6],
      [2]
    ],
    "turn_II": [
      [2, 4],
      [8, 10, 1],
      [3],
      [6]
    ],
    "turn_III": [
      [6, 7],
      [9],
      [11, 12],
      [4]
    ],
    "turn_IV": [
      [3],
      [5, 8]
    ]
  },
  "Team_B": {
    "turn_I": [
      [7, 9, 3],
      [5, 6],
      [2]
    ],
    "turn_II": [
      [2, 4],
      [8, 10, 1],
      [3],
      [6]
    ],
    "turn_III": [
      [6, 7],
      [9],
      [11, 12],
      [4]
    ],
    "turn_IV": [
      [3],
      [5, 8]
    ]
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
