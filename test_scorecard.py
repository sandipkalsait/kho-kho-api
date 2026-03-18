import requests
import json

url = "http://127.0.0.1:8000/api/score_card/"

payload = {
    "Team_A": {
        "I": {
            "defender": [1, 2, 3],
            "attacker": [4, 5, 6],
            "run_time": ["0:30", "0:45"],
            "per_time": ["1:00"],
            "symbol": "+"
        },
        "II": {
            "defender": [7, 8, 9],
            "attacker": [10, 11],
            "run_time": ["0:20", "0:40"],
            "per_time": ["0:50"],
            "symbol": "-"
        }
    },
    "Team_B": {
        "I": {
            "defender": [1, 2, 3],
            "attacker": [4, 5, 6],
            "run_time": ["0:30", "0:45"],
            "per_time": ["1:00"],
            "symbol": "+"
        },
        "II": {
            "defender": [7, 8, 9],
            "attacker": [10, 11],
            "run_time": ["0:20", "0:40"],
            "per_time": ["0:50"],
            "symbol": "-"
        }
    }
}

print("POSTing data...")
response = requests.post(url, json=payload)
print(f"Status Code: {response.status_code}")
print("Response JSON:")
print(json.dumps(response.json(), indent=2))

if response.status_code == 201:
    print("\n\nGETting data back...")
    get_url = f"{url}{response.json()['id']}/" if 'id' in response.json() else url
    # Wait, the POST response might not have ID since ID was removed from to_representation wrapper?
    # Ah, the view list returns array, let's just do GET list.
    list_resp = requests.get(url)
    print(json.dumps(list_resp.json()[-1], indent=2))
