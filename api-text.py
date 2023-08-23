import requests
import time
from pprint import pprint
import json


api_url = 'https://api.api-ninjas.com/v1/exercises'

exercise_types = ["stretching", "strongman"]

def increment_api_requests():
	with open("text_files/api_requests") as f:
		api_requests = int(f.read())
	with open("text_files/api_requests", "w") as f:
		f.write(str(api_requests + 1))

def log_exercises(new_exercises):
	with open("text_files/exercise-data") as f:
		exercises = json.load(f)
	exercises.update({i["name"]:i for i in new_exercises})
	with open("text_files/exercise-data", "w") as f:
		json.dump(exercises, f)


for i in exercise_types:
	offset = 0
	if i == "strength":
		offset = 200
	done = False
	error = False
	while not done:
		params = {'type': i, "offset":offset}
		response = requests.get(url=api_url, headers={'X-Api-Key': 'eq7LSDik6CIO0QrT9zzrIA==DeMvmsLTMOTkbgK3'}, params=params)
		increment_api_requests()
		if response.status_code == requests.codes.ok:
			data = response.json()
			log_exercises(data)
			if len(data) < 10:
				done = True
		else:
			print(response.status_code)
			done = True
		offset += 1
	if error:
		break
