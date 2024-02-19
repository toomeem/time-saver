import json
import os
from pprint import pprint

import requests
from dotenv import load_dotenv

load_dotenv()
url = "https://streaming-availability.p.rapidapi.com/search/title"
api_key = os.getenv("STREAMING_AVAILABILITY_API_KEY")


headers = {
	"X-RapidAPI-Key": api_key,
	"X-RapidAPI-Host": "streaming-availability.p.rapidapi.com",
}
with open("text_files/media_list.json") as f:
	movie_list = json.load(f)["movies"]

movie_data = {}

for i in movie_list:
	querystring = {
		"title": i,
		"country": "us",
		"show_type": "all",
		"output_language": "en",
	}
	response = requests.get(url, headers=headers, params=querystring).json()
	response = response["result"][0]
	movie_data[i] = response

with open("text_files/media_data.json", "w") as f:
	json.dump(movie_data, f, indent=2)
