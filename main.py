'''
all dates are in year/month/day

'''

import concurrent.futures
import json
import os
import random
import re
import threading
import time
from collections import Counter
from datetime import date, datetime, timedelta
from pprint import pprint
from statistics import mean

import cloudinary.uploader
import matplotlib.pyplot as plt
import numpy as np
import pytz
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import Flask, request
from scipy import stats
from spotipy import Spotify, SpotifyOAuth
from werkzeug.serving import run_simple

load_dotenv()
app = Flask(__name__)
port = 5000
dpi = 500
cloudinary_cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
cloudinary_api_key = os.getenv("CLOUDINARY_API_KEY")
cloudinary_api_secret = os.getenv("CLOUDINARY_API_SECRET")
spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
openai_api_key = os.getenv("OPENAI_API_KEY")
telegram_api_key = os.getenv("TELEGRAM_API_KEY")
telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
suggestion_playlist_id = os.getenv("SUGGESTION_PLAYLIST_ID")
ngrok_url = os.getenv("NGROK_URL")
gpt_model = "gpt-3.5-turbo"
tz = pytz.timezone("America/New_York")
first_day_of_school = "2023/09/15"
last_day_of_school = "2024/06/15"
in_school = True
http_request_header = {
	"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36"
}
auth_manager = SpotifyOAuth(
	client_id=spotify_client_id,
	client_secret=spotify_client_secret,
	redirect_uri="http://www.evantoomey.com/",
	open_browser=True,
	scope=["user-library-read","playlist-modify-public"],
)
spotify_client = Spotify(oauth_manager=auth_manager)

cloudinary.config(
	cloud_name=cloudinary_cloud_name,
	api_key=cloudinary_api_key,
	api_secret=cloudinary_api_secret
)
gpt_header = {
	"Content-Type": "application/json",
	"Authorization": "Bearer " + str(openai_api_key),
	}
plot_attributes = {
	"weight": {
		"grid": "y",
		"title":"Weight Over Time",
		"x_label": "Year",
		"y_label": "Weight(lbs)",
		"filename": "weight.png",
		"show_points": False,
		"show_moving_avg": True,
		"show_regression_line": True,
		"window_size": 7,
		"bulk/cut_dates": {"2023/1/29": "bulk", "2023/8/22": "bulk", "2023/6/6": "cut"}
	}
}
bro_split = ["Legs", "Chest + Shoulders", "Arms", "Back + Abs"]
ppl = ["Legs", "Pull", "Push"]
workout_splits = {
	"bro_split": bro_split,
	"ppl": ppl
}
exercise_list = list(json.load(open("text_files/exercises.json")))


def set_webhook_url(url=ngrok_url):
	api_url = f"https://api.telegram.org/bot{telegram_api_key}/"
	method = "setWebhook"
	response = requests.get(api_url+method, params={"url": url})
	pprint(response.json())

def message_user(body, media_url=None):
	if not body:
		return
	try:
		log_message(body, "script", image=bool(media_url))
		api_url = f"https://api.telegram.org/bot{telegram_api_key}/"
		method = "sendMessage"
		requests.get(api_url+method, params={"chat_id": telegram_chat_id, "text":body})
		if media_url:
			method = "sendPhoto"
			time.sleep(.2)
			requests.get(api_url+method, params={"chat_id": telegram_chat_id, "photo":media_url})
	except:
		pass


@app.route("/", methods=["GET","POST"])
def hook():
	message = request.json["message"]["text"]
	pprint(request.json["message"])
	if in_conversation():
		pprint(message)
		log_response(message)
		return "200"
	log_message(message, "user")
	response = gpt_request(message, function_call=True)
	if not response:
		message_user("Error\nPlease try again.")
		return "200"
	response = response["choices"][0]
	if response["finish_reason"] == "stop":
		message_user(response["message"]["content"])
		return "200"
	response_text = response["message"]["function_call"]["name"]
	args = eval(response["message"]["function_call"]["arguments"])
	match response_text:
		case "kill":
			kill()
		case "temp":
			if not log_command("temp"):
				message_user(f'''{get_weather("temp")}°''')
		case "weather":
			if not log_command("weather"):
				message_user(formatted_weather())
		case "quote":
			if not log_command("quote"):
				message_user(get_quote())
		case "school":
			school()
		case "scan":
			scan(args["scan"])
		case "today":
			today()
		case "desc":
			desc()
		case "commands":
			commands()
		case "weight":
			log_weight(args["weight"], args["day_offset"])
		case "weight_graph":
			send_weight_graph(plot_attributes)
		case "hi":
			message_user("Hello!")
		case "spotify":
			spotify_data_description()
		case "artists":
			send_artist_graph()
		case "durations":
			send_song_duration_graph()
		case "genres":
			send_genre_graph()
		case "explicit":
			send_explicit_graph()
		case "covers":
			send_covers_graph()
		case "decades":
			send_decade_graph()
		case "episodes":
			send_episode_graph()
		case "run_times":
			send_podcast_runtime_graph()
		case "gym":
			start_workout(exercise_list)
		case "train":
			get_train_schedule(args)
		case "time":
			get_time(args)
		case "set_gym_day":
			set_gym_day()
		case "toggle_workout_split":
			toggle_workout_split()
		case "get_current_workout_split":
			respond_with_current_workout_split()
		case "get_gym_day":
			respond_with_gym_day()
		case _:
			message_user("That command does not exist.\nTo see a list of all commands, text \"commands\".")
	return "200"

def kill():
	try:
		log_command("kill")
	finally:
		os.abort()

def rn(target="%H:%M"):
	now = datetime.now(tz)
	if target == "date":
		return now
	return now.strftime(target)

def log_command(name):
	with open("text_files/command_list", "a") as command_file:
		command_file.write(f'''{rn("date").timestamp()}:{name}\n''')
	with open("text_files/cancel") as cancel_file:
		cancels = cancel_file.readlines()
	return name in cancels

def days_until(target, start=None, return_days=False):
	if log_command("days_until"):
		return "error"
	target = to_datetime(target)
	if not start:
		start = date.today()
	else:
		start = to_datetime(start)
	if not target or not start:
		return "error"
	difference = target - start
	if return_days:
		return int(difference.days)
	return difference

def school():
	if log_command("school"):
		return
	try:
		left = days_until(first_day_of_school, return_days=True)
		total = days_until(first_day_of_school, last_day_of_school, return_days=True)
		message = f"School completed - {round((1-(left/total))*100, 1)}%\n"
		message += f"School ends in {left} days"
		message_user(message)
	except:
		message_user("Error")

def scan(args):
	if log_command("scan"):
		return
	keyword = args
	message_user(get_quote(keyword))

def today():
	if log_command("today"):
		return
	day_num = int(rn("%d"))
	suffix = num_suffix(int(rn("%d")[1]))
	message = rn(f"Today is %A, %b {day_num}{suffix}\n")
	message += f"Today's word of the day is '{get_todays_word().capitalize()}'"
	message_user(message)

def log_weight(pounds, day_offset=0):
	if log_command("log_weight"):
		return
	now = datetime.now(tz) - timedelta(days=day_offset)
	with open("text_files/weight", "a") as weight_file:
		weight_file.write(f'''{now.strftime("%Y/%m/%d")}:{pounds}\n''')
	message_user("Weight logged")

def send_weight_graph(plot_attributes):
	if log_command("send_weight_graph"):
		return
	with open("text_files/weight") as f:
		raw_weights = f.readlines()
	raw_weights = [i for i in raw_weights if i != "\n"]
	data = [weight_date_format(i).split(":") for i in raw_weights]
	data = sorted(data)
	x = [int(i[0]) for i in data]
	y = [float(i[1]) for i in data]
	create_graph(x, y, "weight", plot_attributes)
	graph_url = cloudinary.uploader.upload(
		"weight.png",
		public_id="weight_graph",
		overwrite=True)["secure_url"]
	message_user("Here is your weight graph", graph_url)
	delete_file("weight.png")

def update_spotify_data():
	if log_command("update_spotify_data"):
		return
	threading.Thread(target=get_genres, args=(spotify_client,)).start()
	threading.Thread(target=podcasts, args=(spotify_client,)).start()
	get_all_songs(spotify_client)
	clear_suggestions_playlist(spotify_client, suggestion_playlist_id)

def spotify_data_description():
	data = read_spotify_data()
	track_num = len(data)
	_, artist_num = get_artist_info(data)
	_, avg_track_len, longest, shortest = duration_graph_organization(data, 20)
	all_durations = sum([i["duration_ms"] for i in data])
	hours = float(round((all_durations/(60*1000))/60, 1))
	explicits = get_explicits(data)
	genre_num = genre_data_organization(genre_num_only=True)
	cover_num = covers(data)
	release_range = release_date_data(data, True)
	podcast_data = get_podcast_data()
	podcast_hours = get_podcast_duration(podcast_data)
	podcast_hours = float(round((podcast_hours/(60*1000))/60, 1))
	shows = get_show_frequency(podcast_data)
	message = [
		f"Your playlist is {track_num} songs long and it is {hours} hours long.",
		f"It spans {release_range} years of music.",
		f"Your playlist consisted of {artist_num} artists that represented {genre_num} different genres.",
		f"The songs were an average of {min_sec(avg_track_len)} long.",
		f"The longest song was {min_sec(longest)} long.",
		f"The shortest song was {min_sec(shortest)} long.",
		f"There were around {cover_num} cover songs.",
		f'''About {round((explicits["Explicit"]/track_num)*100, 1)}% of the songs were explicit.''',
		f"You have {len(podcast_data)} saved podcast episodes that are collectively {podcast_hours} hours long.",
		f"Those episodes are from {len(shows.keys())} different shows."
		]
	message_user("\n".join(message))
	update_spotify_data()

def send_artist_graph():
	if log_command("send_artist_graph"):
		return
	data = read_spotify_data()
	artist_dict, _ = get_artist_info(data)
	popular_artists, artist_uses = find_popular(artist_dict, 20)
	plt.figure(figsize=(10, 10), dpi=dpi, layout="tight")
	plt.yticks(fontsize=8)
	plt.title("Most Liked Songs")
	plt.xlabel("Number of Liked Songs")
	plt.barh(popular_artists[::-1], artist_uses[::-1])
	plt.savefig("artist_graph.png")
	graph_url = cloudinary.uploader.upload(
		"artist_graph.png",
		public_id="artist_graph",
		overwrite=True)["secure_url"]
	message_user("Here are your top artists.", graph_url)
	delete_file("artist_graph.png")

def send_song_duration_graph():
	if log_command("send_song_duration_graph"):
		return
	data = read_spotify_data()
	durations, *_ = duration_graph_organization(
		data, 20)
	duration_names = [list(i.values())[0] for i in durations][::-1]
	duration_values = [list(i.keys())[0]/(60*1000) for i in durations][::-1]
	plt.figure(figsize=(10, 10), dpi=dpi, layout="tight")
	plt.yticks(fontsize=8)
	plt.title("Longest Songs")
	plt.xlabel("Song Duration (minutes)")
	plt.barh(duration_names, duration_values)
	plt.savefig("song_duration_graph.png")
	graph_url = cloudinary.uploader.upload(
		"song_duration_graph.png",
		public_id="song_duration_graph",
		overwrite=True)["secure_url"]
	message_user("Here are your longest songs.", graph_url)
	delete_file("song_duration_graph.png")

def send_genre_graph():
	if log_command("send_genre_graph"):
		return
	popular_genres, genres_uses, _ = genre_data_organization(20)
	plt.figure(figsize=(10, 10), dpi=dpi, layout="tight")
	plt.yticks(fontsize=8)
	plt.title("Most Popular Genres")
	plt.xlabel("Number of Liked Genres")
	plt.barh(popular_genres[::-1], genres_uses[::-1])
	plt.savefig("genre_graph.png")
	graph_url = cloudinary.uploader.upload(
		"genre_graph.png",
		public_id="genre_graph",
		overwrite=True)["secure_url"]
	message_user("Here are your top genres.", graph_url)
	delete_file("genre_graph.png")

def send_explicit_graph():
	if log_command("send_explicit_graph"):
		return
	data = read_spotify_data()
	explicits = get_explicits(data)
	plt.figure(figsize=(10, 10), dpi=dpi)
	plt.title("Number of Explicit Songs(Approximate)", pad=40)
	plt.pie(x=explicits.values(), labels=list(explicits.keys()), radius=1.3,
					autopct=lambda pct: auto_pct(pct, list(explicits.values())),)
	plt.savefig("explicit_graph.png")
	graph_url = cloudinary.uploader.upload(
		"explicit_graph.png",
		public_id="explicit_graph",
		overwrite=True)["secure_url"]
	message_user("Here is the ratio of explicit songs in your library.", graph_url)
	delete_file("explicit_graph.png")

def send_covers_graph():
	if log_command("send_covers_graph"):
		return
	data = read_spotify_data()
	cover_num = covers(data)
	plt.figure(figsize=(10, 10), dpi=dpi, layout="tight")
	plt.title("Number of Covers (Approximate)")
	plt.pie(x=[len(data)-cover_num, cover_num], labels=["Original Songs", "Covers"], pctdistance=.85,
					autopct=lambda pct: auto_pct(pct, [len(data)-cover_num, cover_num]))
	plt.savefig("covers_graph.png")
	graph_url = cloudinary.uploader.upload(
		"covers_graph.png",
		public_id="covers_graph",
		overwrite=True)["secure_url"]
	message_user("Here is the ratio of covers in your library.", graph_url)
	delete_file("covers_graph.png")

def send_decade_graph():
	if log_command("send_decade_graph"):
		return
	data = read_spotify_data()
	release_decades, release_nums, _ = release_date_data(data)
	plt.figure(figsize=(10, 10), dpi=dpi)
	plt.title("Songs from Each Decade", pad=40, fontdict={'fontsize': 20})
	plt.pie(x=release_nums, labels=release_decades, autopct=lambda pct: auto_pct(pct, release_nums),
					pctdistance=.85, labeldistance=1.05)
	plt.savefig("decade_graph.png")
	graph_url = cloudinary.uploader.upload(
		"decade_graph.png",
		public_id="decade_graph",
		overwrite=True)["secure_url"]
	message_user("Here are the decades your songs were released in.", graph_url)
	delete_file("decade_graph.png")

def send_episode_graph():
	if log_command("send_episode_graph"):
		return
	podcast_data = get_podcast_data()
	shows = get_show_frequency(podcast_data)
	plt.figure(figsize=(10, 10), dpi=dpi)
	plt.title(f"Number of Episodes (total {sum(shows.values())})")
	plt.pie(x=shows.values(), labels=list(shows.keys()),
					autopct=lambda pct: auto_pct(pct, list(shows.values())))
	plt.savefig("episode_graph.png")
	graph_url = cloudinary.uploader.upload(
		"episode_graph.png",
		public_id="episode_graph",
		overwrite=True)["secure_url"]
	message_user("Here are the podcasts you listen to.", graph_url)
	delete_file("episode_graph.png")

def send_podcast_runtime_graph():
	if log_command("send_podcast_runtime_graph"):
		return
	podcast_data = get_podcast_data()
	show_duration_dict = get_show_durations(podcast_data)
	plt.figure(figsize=(10, 10), dpi=dpi)
	plt.title("Runtime (minutes)")
	plt.pie(x=show_duration_dict.values(), labels=list(show_duration_dict.keys()),
					autopct=lambda pct: auto_pct(pct, list(show_duration_dict.values())))
	plt.savefig("podcast_runtime_graph.png")
	graph_url = cloudinary.uploader.upload(
		"podcast_runtime_graph.png",
		public_id="podcast_runtime_graph",
		overwrite=True)["secure_url"]
	message_user("Here are the podcasts you listen to.", graph_url)
	delete_file("podcast_runtime_graph.png")

# TODO: need to use threading or something because it takes too long and telegram times out
def start_workout(all_exercises):
	if log_command("start_workout"):
		return
	day_type = workout_splits[get_current_workout_split()][get_gym_day_num()]
	wait_between_sets = 60 * 2.5
	workout_dict = {
		"exercises": {}, "start": time.time(), "end": None,"day_type": day_type,
		"split": get_current_workout_split()
	}
	with open("text_files/current_workout", "w") as workout_file:
		json.dump(workout_dict, workout_file, indent=2)
	quit_workout = False
	while not quit_workout:
		raw_todays_exercises = get_day_exercises(all_exercises)
		todays_exercises = []
		for i in raw_todays_exercises:
			todays_exercises.append(f'''{i["num"]}: {i["name"]}''')
		todays_exercises ="\n".join(todays_exercises)
		exercise_list = "Pick an exercise(0 to end the workout)\n\n"+todays_exercises
		exercise_num = get_response(exercise_list, wait_time=900)
		if not exercise_num:
			clear_file("text_files/current_workout")
			return
		exercise_num = int(exercise_num)
		if not exercise_num:
			quit_workout = True
		else:
			message_user("Good choice")
			time.sleep(wait_between_sets)
			log_set(exercise_num, is_first_set(exercise_num))
			another_set = get_response("Another set?", 900)
			while another_set == "yes":
				time.sleep(wait_between_sets)
				log_set(exercise_num)
				another_set = get_response("Another set?", 900)
	end_workout()

def get_train_schedule(station_json):
	station1 = station_json["starting station"].replace("Jefferson", "Market East")
	station2 = station_json["destination station"].replace("Jefferson", "Market East")
	with open("text_files/station_inputs.json") as f:
		station_inputs = list(json.load(f).keys())
	prompt = f'''Here is a list of train stations:\n
	{station_inputs}\n
	Which stations are these "{station1}" and "{station2}"?\n
	Your answer will be in this format ["first station", "second station"].
	Only return that list format, nothing else.
	Make sure to include the quotation marks.
	'''
	gpt_response = gpt_request(prompt)["choices"][0]
	try:
		stations = eval(gpt_response["message"]["content"])
	except:
		pprint(gpt_response["message"]["content"])
		return
	station1 = stations[0]
	station2 = stations[1]
	septa_headers = {'Accept': 'application/json'}
	parameters = {'req1': station1, 'req2': station2}
	septa_response = requests.get(
		"https://www3.septa.org/api/NextToArrive/index.php",
		params=parameters, headers=septa_headers).json()
	price = get_train_price(station1, station2, septa_response[0])
	if not septa_response:
		message_user("There are no upcoming trains between those stations.")
		message_user(f"A ride between those stations will cost about ${'{:.2f}'.format(price)} depending on the time of day.")
		return
	try:
		departure_time = septa_response[0]["orig_departure_time"][:-2]
		arrival_time = septa_response[0]["orig_arrival_time"][:-2]
		delay = septa_response[0]["orig_delay"]
	except:
		message_user("There are no upcoming trains between those stations.")
		pprint(septa_response)
		return
	price = get_train_price(station1, station2, septa_response[0])
	station1 = station1.replace("Market East", "Jefferson")
	station2 = station2.replace("Market East", "Jefferson")
	message = f'''The next train from {station1} to {station2} leaves at {departure_time} and arrives at {arrival_time}.'''
	if delay != "On time":
		message += f"\nIt is currently delayed {delay}"
	if price is not None:
		message += f'''\nIt will cost ${"{:.2f}".format(price)}.'''
	message_user(message)

def set_gym_day():
	if log_command("set_gym_day"):
		return
	current_split = workout_splits[get_current_workout_split()]
	current_day = current_split[get_gym_day_num()]
	message = f'''
		Current gym day is {current_day}
		What day would you like to set it to?(respond with a number)'''
	for i in range(len(current_split)):
		message += f"\n{i}: {current_split[i]}"
	day_num = get_response(message)
	if not day_num:
		return
	with open("text_files/gym_day", "w") as gym_day_file:
		gym_day_file.write(str(day_num))

def respond_with_current_workout_split():
	if log_command("respond_with_current_workout_split"):
		return
	message_user(f"Current workout split is {get_current_workout_split()}")

def toggle_workout_split():
	if log_command("toggle_workout_split"):
		return
	current_split = get_current_workout_split()
	if current_split == "bro_split":
		set_workout_split("ppl")
		message_user("Workout split set to PPL")
	else:
		set_workout_split("bro_split")
		message_user("Workout split set to Bro Split")

def respond_with_gym_day():
	if log_command("respond_with_gym_day"):
		return
	day = workout_splits[get_current_workout_split()][get_gym_day_num()]
	message_user(f"Current gym day: {day}")

def desc():
	if log_command("desc"):
		return
	message = '''
	I am a chat bot created by Evan Toomey.
	I am still in development, so please be patient with me.
	If I am going crazy and you need to terminate me, text "kill".
	If you would like to see my commands, text "commands".\n
	Have an amazing day :)
	'''
	message_user(message)

def commands():
	if log_command("commands"):
		return
	command_lst = [
		"get the current temperature in Philadelphia"
		, "get the current weather conditions in Philadelphia"
		, "get a random quote"
		, "gets how much school is left for the year"
		, "searches through all the unused quotes that contain that word/phrase"
		, "sends the day of the month and the weekday"
		, "logs your weight"
		, "sends a graph of your weight over time"
		, "sends some data about your spotify account"
		, "sends a graph of your top artists"
		, "sends a graph of your longest songs"
		, "sends a graph of your top genres"
		, "sends a graph of the ratio of explicit songs in your library"
		, "sends a graph of the ratio of covers in your library"
		, "sends a graph of the decades your songs were released in"
		, "sends a graph of the podcasts you listen to"
		, "sends a graph of the run times of the podcasts you listen to"
		, "starts a workout"
		, "sends the next train between two stations"
		, "sends the current time in a city of your choice"
		, "sends a description of this bot"
		, "sends this"]
	message = "\n".join(command_lst)
	message += "\nI also have a few other surprises ;)"
	message_user(message)

# end of commands, start of helper functions
def to_datetime(date):
	if isinstance(date, datetime):
		return date
	try:
		date = float(date)
		return datetime.fromtimestamp(date)
	except:
		pass
	if isinstance(date, str):
		match date.count("/"):
			case 3:
				return datetime.strptime(date, "%Y/%m/%d")
			case 4:
				return datetime.strptime(date, "%Y/%m/%d/%H")
			case 5:
				return datetime.strptime(date, "%Y/%m/%d/%H/%M")
			case 6:
				return datetime.strptime(date, "%Y/%m/%d/%H/%M/%S")
			case _:
				return

def set_workout_split(split):
	if log_command("set_workout_split"):
		return
	with open("text_files/workout_split", "w") as workout_split_file:
		workout_split_file.write(split)

def get_current_workout_split():
	if log_command("get_current_workout_split"):
		return
	with open("text_files/current_workout_split") as workout_split_file:
		split = workout_split_file.readline()
	return split.strip()

def get_train_price(station1, station2, response=None):
	if log_command("get_train_price"):
		return
	city_weekday = {
		0: 3.75,
		1: 3.75,
		2: 4.75,
		3: 5.75,
		4: 6.50,
		5: 8.25,
	}
	city_weekend = {
		0: 3.75,
		1: 3.75,
		2: 4.25,
		3: 5.25,
		4: 5.25,
		5: 8.25,
	}
	local_price = 3.75
	extended_price = 6.5
	airport_price = 6.5
	airport_to_eastwick = 3.75
	zone1 = get_station_zone(station1)
	zone2 = get_station_zone(station2)
	if "Terminal" in station1:
		if station2 == "Eastwick Station":
			return airport_to_eastwick
		return airport_price
	if "Terminal" in station2:
		if station1 == "Eastwick Station":
			return airport_to_eastwick
		return airport_price
	if response and zone1 != 0 and zone2 != 0:
		if response["isdirect"] == "false" and get_station_zone(response["Connection"]) == 0:
			return extended_price
	if zone1>0 and zone2<0:
		return extended_price
	if zone1<0 and zone2>0:
		return extended_price
	if zone1<0 and zone2<0:
		return local_price
	if zone1>0 and zone2>0:
		return local_price
	now = datetime.now(tz)
	if not response:
		departure = now.strftime("%I:%M %p")
	else:
		departure = response["orig_departure_time"]
	if now.weekday() < 5 and not is_septa_holiday():
		if not ("PM" in departure and int(departure.split(":")[0]) >= 7):
			if zone1 == 0:
				return city_weekday[zone2]
			return city_weekday[zone1]
	if zone1 == 0:
		return city_weekend[zone2]
	return city_weekend[zone1]

def get_station_zone(station):
	with open("text_files/station_inputs.json") as f:
		station_inputs = dict(json.load(f))
	return int(station_inputs[station])

def is_septa_holiday():
	if log_command("is_septa_holiday"):
		return
	now = datetime.now(tz)
	if rn("%m/%d") == "01/01": #New Year's Day
		return True
	if rn("%m/%d") == "07/04": #Independence Day
		return True
	if rn("%m/%d") == "12/25": #Christmas
		return True
	if now.weekday() == 0 and now.month == 5 and now.day >= 25: #Memorial Day
		return True
	if now.weekday() == 0 and now.month == 9 and now.day <= 7: #Labor Day
		return True
	if now.month == 11: #Thanksgiving
		first = date(now.year, 11, 1)
		thurs = 1 + (7 - (first.weekday() - 3))
		if thurs > 7:
			thurs -= 7
		thurs += 21
		if now.day == thurs:
			return True
	return False

def set_max(set):
	if log_command("set_max"):
		return
	reps = mean(set["reps"])
	weight = mean(set["weight"])
	return one_rep_max(reps, weight)

def exercise_maxes():
	if log_command("exercise_maxes"):
		return
	try:
		with open("text_files/workout_log") as f:
			workouts = list(json.load(f))
	except:
		return None
	exercise_maxes = {}
	for workout in workouts:
		for name in workout["exercises"].keys():
			if name in exercise_maxes.keys():
				exercise_maxes[name][workout["start"]] = set_max(workout["exercises"][name])
			else:
				exercise_maxes[name] = {workout["start"]: set_max(workout["exercises"][name])}
	return exercise_maxes

def get_exercise_log():
	if log_command("get_exercise_log"):
		return
	with open("text_files/workout_log") as workout_file:
		workout_log = list(json.load(workout_file))
	return workout_log

def search_tracks(id):
	if log_command("search_tracks"):
		return
	data = read_spotify_data()
	for track in data:
		try:
			if track["linked_from"]["id"] == id:
				return track
		except KeyError:
			pass
		if track["id"] == id:
			return track
	return False

def clear_suggestions_playlist(sp, playlist_id):
	limit = 100
	playlist = dict(sp.playlist(playlist_id))["tracks"]
	if not int(playlist["total"]):
		return
	playlist = playlist["items"]
	liked_tracks = [i["track"]["id"] for i in playlist if search_tracks(i["track"]["id"])]
	if len(playlist) > limit:
		for i in range(iterations(len(playlist)-limit, limit)):
			track_batch = dict(sp.playlist_items(playlist_id, offset=i*limit, limit=limit))
			liked_tracks.extend([i["track"]["id"] for i in track_batch if search_tracks(i["track"]["id"])])
	for i in liked_tracks:
		sp.playlist_remove_all_occurrences_of_items(playlist_id, [i])

def check_file_timestamps(filename, strf_format="%Y/%m/%d/%H/%M", remove_past=False):
	if log_command("check_file_timestamps"):
		return
	with open("text_files/"+filename) as f:
		lines = f.readlines()
	now = datetime.now(tz)
	for i in range(len(lines)):
		try:
			timestamp = lines[i].strip().split(":")[0]
			date_obj = datetime.strptime(timestamp, strf_format)
			date_obj = date_obj.replace(tzinfo=tz)
			if not remove_past:
				continue
			if (now-date_obj).total_seconds() > 0:
				lines[i] = False
		except:
			lines[i] = False
	lines = [i for i in lines if i]
	return lines

def check_brentford_file():
	if log_command("check_brentford_file"):
		return
	games = check_file_timestamps("brentford", remove_past=True)
	for i in range(len(games)):
		games[i] = games[i].strip().split(":")
		games[i][1] = games[i][1].title()
		games[i] = ":".join(games[i])+"\n"
	with open("text_files/brentford", "w") as brentford_file:
		brentford_file.writelines(sorted(games))

def check_weight_file():
	if log_command("check_weight_file"):
		return
	weights = check_file_timestamps("weight", strf_format="%Y/%m/%d")
	for i in range(len(weights)):
		try:
			weights[i] = weights[i].strip().split(":")
			weights[i][1] = str(float(weights[i][1]))
			weights[i] = ":".join(weights[i])+"\n"
		except:
			weights[i] = False
	weights = [i for i in weights if i]
	with open("text_files/weight", "w") as weight_file:
		weight_file.writelines(sorted(weights))

def check_error_file():
	if log_command("check_error_file"):
		return
	errors = check_file_timestamps("errors", "%Y/%m/%d/%H/%M/%S")
	if not errors:
		return
	with open("text_files/errors", "w") as error_file:
		error_file.writelines(sorted(errors))

def check_quote_file():
	if log_command("check_quote_file"):
		return
	with open("text_files/quotes") as quotes_file:
		quotes = list(set(quotes_file.readlines()))
	with open("text_files/used_quotes") as used_quotes_file:
		used_quotes = list(set(used_quotes_file.readlines()))
	for i in quotes:
		if i in used_quotes:
			quotes.remove(i)
			used_quotes.append(i)
	quote_fix = False
	used_fix = False
	with open("text_files/quotes") as quotes_file:
		if quotes != quotes_file.readlines():
			quote_fix = True
	with open("text_files/used_quotes") as used_quotes_file:
		if used_quotes != used_quotes_file.readlines():
			used_fix = True
	if quote_fix:
		with open("text_files/quotes", "w") as quotes_file:
			quotes_file.writelines(quotes)
	if used_fix:
		with open("text_files/used_quotes", "w") as used_quotes_file:
			used_quotes_file.writelines(used_quotes)

def clean(updates=True):
	if log_command("clean"):
		return
	if updates:
		threading.Thread(target=update_spotify_data).start()
	clear_file("text_files/cancel")
	check_quote_file()
	check_brentford_file()
	check_weight_file()
	check_error_file()

def get_time(args):
	if log_command("get_time"):
		return
	tz_str = args["tz_info"]
	place = args["place"]
	tz_obj = pytz.timezone(tz_str)
	now = datetime.now(tz_obj)
	message_user(f'''It is currently {now.strftime("%I:%M %p")} in {place}.''')

def get_todays_word():
	if log_command("get_todays_word"):
		return
	url = "https://www.dictionary.com/"
	page = requests.get(url, headers=http_request_header)
	soup = BeautifulSoup(page.content, "html.parser")
	element = soup.find_all("a", class_="hJCqtPGYwMx5z04f6y2o")
	word = element[0].text
	return word

def delete_file(file_name):
	if log_command("delete_file"):
		return
	try:
		os.remove(file_name)
	except:
		pass

def error_count_notify():
	if log_command("error_count_notify"):
		return
	now = datetime.now(tz)
	with open("text_files/errors") as errors:
		error_list = list(errors.readlines())
	if not error_list:
		return 0
	error_count = []
	error_list = error_list[::-1]
	for i in range(len(error_list)):
		timestamp = error_list[i].strip().split(":")[1]
		name = error_list[i].strip().split(":")[0]
		timestamp = [int(i) for i in timestamp.split("/")]
		timestamp = datetime(timestamp[0], timestamp[1], timestamp[2], timestamp[3], timestamp[4], tzinfo=tz)
		if (now-timestamp).total_seconds() < 86400:
			error_count.append(name)
	return(Counter(error_count))

def morning_message():
	if log_command("morning_message"):
		return
	message = "Good Morning!\n"
	day_num = int(rn("%d"))
	suffix = num_suffix(int(rn("%d")[1]))
	brentford_game = brentford_plays_today()
	message += f'''Today is {rn(f"%A, %B {day_num}{suffix}")}\n'''
	if brentford_game:
		message += f"Brentford plays at {brentford_game} today!\n"
	message += "Here's today's weather:\n\t"
	message += formatted_weather().replace("\n", "\n\t")
	return(message)

def gpt_request(prompt, function_call=False):
	if log_command("gpt_request"):
		return
	messages = [{"role": "user", "content": prompt}]
	json_data = {"model": gpt_model, "messages": messages}
	if function_call:
		json_data = {"model": gpt_model, "messages": messages, "functions": functions()}
	response = requests.post(
		"https://api.openai.com/v1/chat/completions",
		headers=gpt_header,
		json=json_data,
	)
	return response.json()

def functions():
	with open("text_files/functions.json") as f:
		functions = json.load(f)
	return functions

def brentford_plays_today():
	if log_command("brentford_plays_today"):
		return False
	with open("text_files/brentford") as brentford_file:
		games = brentford_file.readlines()
	today = rn("%Y/%m/%d")
	for i in games:
		if today in i:
			return i.strip().split(":")[1]
	return False

def one_rep_max(reps, weight):
	if log_command("one_rep_max"):
		return
	return round(weight/(1.0278-(0.0278*reps)))

def is_first_set(num):
	with open("text_files/current_workout") as workout_file:
		exercises = dict(json.load(workout_file))["exercises"]
	return search_exercises(num) not in list(exercises.keys())

def min_sec(total_seconds):
	minutes = int(total_seconds//60)
	seconds = int(round(total_seconds % 60))
	min_string = "minutes"
	sec_string = "seconds"
	if minutes == 1:
		min_string = "minute"
	if seconds == 1:
		sec_string = "second"
	if not minutes:
		return f"{seconds} {sec_string}"
	return f"{minutes} {min_string} and {seconds} {sec_string}"

def get_day_exercises(all_exercises):
	if log_command("get_day_exercises"):
		return
	current_split = get_current_workout_split()
	gym_day = workout_splits[current_split][get_gym_day_num()]
	todays_exercises = [i for i in all_exercises if gym_day in i["exercise_day"][current_split]]
	return todays_exercises

def search_exercises(num):
	if log_command("search_exercises"):
		return
	with open("text_files/exercises.json") as exercise_file:
		exercise_list = list(json.load(exercise_file))
	for i in exercise_list:
		if int(i["num"]) == num:
			return i["name"]

def log_set(exercise_num, first=False):
	if log_command("log_set"):
		return
	reps, weight = None, None
	while not isinstance(reps, int):
		try:
			reps = int(get_response("How many reps did you do?", 600))
		except:
			pass
	while not isinstance(weight, float):
		try:
			weight = float(get_response("How much weight did you use?", 600))
		except:
			pass
	name = search_exercises(exercise_num)
	if not (name and reps and weight):
		end_workout()
		return
	with open("text_files/current_workout") as workout_file:
		workout_dict = dict(json.load(workout_file))
	if first:
		workout_dict["exercises"][name] = {"sets": 1, "reps": [reps], "weight": [weight]}
	else:
		workout_dict["exercises"][name]["sets"] += 1
		workout_dict["exercises"][name]["reps"].append(reps)
		workout_dict["exercises"][name]["weight"].append(weight)
	with open("text_files/current_workout", "w") as workout_file:
		json.dump(workout_dict, workout_file, indent=2)

def end_workout(start=False):
	if log_command("end_workout"):
		return
	try:
		with open("text_files/current_workout") as workout_file:
			workout_dict = dict(json.load(workout_file))
		if not workout_dict["end"]:
			workout_dict["end"] = time.time()
			workout_dict["DNF"] = not start
		with open("text_files/workout_log") as workout_file:
			try:
				workouts = list(json.load(workout_file))
			except:
				workouts = []
		workouts.append(workout_dict)
		with open("text_files/workout_log", "w") as workout_file:
			json.dump(workouts, workout_file, indent=2)
		if not start:
			message_user("Workout Logged")
		increment_gym_day()
	except:
		pass
	clear_file("text_files/current_workout")

def get_gym_day_num():
	if log_command("get_gym_day"):
		return 0
	with open("text_files/gym_day") as gym_file:
		gym_day = gym_file.readline().strip()
	if not gym_day:
		return 0
	return int(gym_day)

def increment_gym_day(increment=1):
	if log_command("increment_gym_day"):
		return
	gym_day = get_gym_day_num()
	gym_day += increment
	if gym_day >= len(gym_schedule):
		gym_day = 0
	set_gym_day(gym_day)

def clear_file(file_name):
	file = open(file_name, "w")
	file.close()

def log_response(response):
	log_message(response, "user")
	if log_command("log_response"):
		return
	with open("text_files/response", "w") as message_file:
		message_file.write(response)

def clear_response():
	if log_command("clear_response"):
		return
	clear_file("text_files/response")

def get_response(question=None, wait_time=300, confirmation=None):
	if log_command("get_response"):
		return
	if question:
		message_user(question)
	set_in_conversation(True)
	start = time.time()
	time_left = start + wait_time - time.time()
	while time_left > 0:
		with open("text_files/response") as message_file:
			response = message_file.read().strip()
		if not response:
			time.sleep(.5)
			continue
		set_in_conversation(False)
		if not confirmation:
			message_user(confirmation)
		if response.lower() == "pass":
			return
		return response
	message_user("nvm")
	set_in_conversation(False)

def get_weight():
	if log_command("get_weight"):
		return
	response = get_response("What's your weight?", 600, "thanks")
	if (not response) or response.lower() == "error":
		return
	log_weight(response)

def set_in_conversation(is_in_conversation):
	if log_command("set_in_conversation"):
		return
	if not is_in_conversation:
		clear_response()
	with open("text_files/in_conversation", "w") as message_file:
		message_file.write(str(is_in_conversation))

def in_conversation():
	if log_command("in_conversation"):
		return
	with open("text_files/in_conversation") as message_file:
		conversation_bool = message_file.read().strip()
	return conversation_bool == "True"

def log_message(message, sender, image=False):
	if log_command("log_message"):
		return
	with open("text_files/conversation_log.json") as message_file:
		log = list(json.load(message_file))
	clear_file("text_files/conversation_log.json")
	with open("text_files/conversation_log.json", "a") as message_file:
		json.dump(
			log + [{"message": message, "sender": sender, "sent_at":str(time.time()), "image": image}],
			message_file, indent=2
		)

def error_report(name):
	time_stamp = rn("%y/%m/%d/%H/%M/%S")
	with open("text_files/errors", "a") as error_list:
		error_list.write(f"{name}:{time_stamp}\n")
	with open("text_files/errors") as error_file:
		errors = error_file.readlines()
	if len(errors) >=40:
		errors = errors[30:]
	elif len(errors)>=10:
		errors=errors[10:]
	elif len(errors)>=5:
		errors = errors[5:]
	if len(errors) >5 and errors.count(errors[0])==len(errors):
		with open("text_files/cancel") as cancel_file:
			cancels = cancel_file.readlines()
		cancels.append(name+"\n")
		cancels = list(set(cancels))
		with open("text_files/cancel", "w") as cancel_file:
			cancel_file.writelines(cancels)

def num_suffix(num):
	num = str(int(num))
	if len(num) > 2:
		num = num[len(num)-2:]
	if num in ["1", "21","31"]:
		return "st"
	if num in ["2","22","32"]:
		return "nd"
	if num in ["3","23","33"]:
		return "rd"
	return "th"

def get_weather(data="full"):
	try:
		weather_page = requests.get(
			"https://forecast.weather.gov/MapClick.php?lat=39.95222000000007&lon=-75.16217999999998")
		weather_soup = BeautifulSoup(weather_page.content, "html.parser")
		if "Not a current observation" in str(weather_soup):
			error_report("weather")
			return "error"
		full = data == "full"
		if data == "conditions" or full:
			weather_conditions = re.search("\">.+</p", str(weather_soup)).group()[2:-3]
		weather_soup = str(weather_soup.get_text())
		if data == "temp" or full:
			try:
				temp = int(re.search(r"Wind Chill*\d+°F", weather_soup).group()[10:-2])
			except:
				temp = int(np.round(float(re.search(r"\d+°F", weather_soup).group()[:-2]),0))
		if data == "humidity" or full:
			humidity = int(re.search(r"\d+%", weather_soup).group()[:-1])
		if data == "wind_speed" or full:
			wind_speed = int(re.search(r"\d+\smph", weather_soup).group()[:-4])
			if ("Calm" in weather_soup) and (" Calm" not in weather_soup):
				wind_speed = 0
		if data == "dewpoint" or full:
			dewpoint = int(re.search(r"Dewpoint\s\d+°F", weather_soup).group()[9:-2])
		if data == "vis" or full:
			vis = re.search("Visibility\n.+", weather_soup).group().replace("Visibility\n","")
		if data == "conditions":
			return weather_conditions
		elif data == "temp":
			return temp
		elif data == "humidity":
			return humidity
		elif data == "wind_speed":
			return wind_speed
		elif data == "dewpoint":
			return dewpoint
		elif data == "vis":
			return vis
		weather_data = {
			"conditions":weather_conditions,"temp":temp,"humidity":humidity,
			"wind_speed": wind_speed, "dewpoint":dewpoint,"vis":vis
			}
		return weather_data
	except:
		error_report("get_weather")
		return "error"

def formatted_weather():
	weather = get_weather()
	try:
		conditions = weather["conditions"]
		temp = weather["temp"]
		humidity = weather["humidity"]
		wind_speed = weather["wind_speed"]
		dewpoint = weather["dewpoint"]
	except:
		error_report("formatted_weather")
		return "error"
	message = f"Temperature - {temp}°\nConditions - {conditions}\n"
	if 62 <dewpoint<69:
		message += "Humidity - Above Average\n"
	elif 69<=dewpoint:
		message += "Humidity - High\n"
	elif humidity<=30:
		message += "Humidity - Very Low\n"
	elif humidity<=45:
		message += "Humidity - Low\n"
	else:
		message += "Humidity - Average\n"
	if wind_speed>=25:
		message += "Wind Speed - Extremely High\n"
	elif 17<=wind_speed<25:
		message += "Wind Speed - Very High\n"
	elif 10<=wind_speed<17:
		message += "Wind Speed - Windy\n"
	elif 5<=wind_speed<10:
		message += "Wind Speed - Light Breeze\n"
	else:
		message += "Wind Speed - Negligible\n"
	message += f'''Visibility - {weather["vis"].replace("10.00", "10")}'''
	return message.replace("Fog/Mist", "Foggy")

def uncancel(name):
	with open("text_files/cancel") as cancel_file:
		cancels = cancel_file.readlines()
	name += "\n"
	if name not in cancels:
		return
	cancels.remove(name)
	with open("text_files/cancel", "w") as cancel_file:
		cancel_file.writelines(cancels)

def get_quote(scan=None):
	with open("text_files/used_quotes") as used_quotes_file:
		used_quotes = (used_quotes_file.readlines())
	with open("text_files/quotes") as quotes_file:
		quote_list = list(set(quotes_file.readlines()))
	if "" in quote_list:
		quote_list.remove("")
	message = ""
	if not scan:
		quote = quote_list[0]
	else:
		keyword_quotes = [i for i in quote_list if scan in i]
		message += f"Total Number of Quotes: {len(quote_list)}\n"
		message += f"Number of Matching Quotes: {len(keyword_quotes)}\n"
		if not keyword_quotes:
			return "No matching quotes"
		random.shuffle(keyword_quotes)
		while keyword_quotes[0] in used_quotes:
			keyword_quotes.remove(keyword_quotes[0])
		quote = keyword_quotes[0]
		message += f"One of the Matching Quotes: {quote}"
	for i in used_quotes:
		if i in quote_list:
			quote_list.remove(i)
	random.shuffle(quote_list)
	with open("text_files/quotes", "w") as quotes_file:
		quotes_file.writelines(quote_list)
	with open("text_files/used_quotes", "a") as used_quotes_file:
		used_quotes_file.write(quote)
	if scan:
		return message
	return quote

def weight_date_format(line):
	line = line.split(":")
	return f"{date_to_num(line[0])}:{line[1]}"

def date_to_num(date):
	date = date.split("/")
	date = str(int(date[1])*30 + int(date[2]) + int(date[0])*365)
	return date

def moving_avg(data, window):
	avg = []
	for i in range(window, len(data)):
		avg.append(np.mean(data[i-window:i]))
	for i in range(window):
		avg.insert(0, avg[0])
	return avg

def closest_num(num, lst):
	closest = 0
	num = int(num)
	for i in range(len(lst)):
		if abs(lst[i]-num) < abs(lst[closest]-num):
			closest = i
	return closest

def slope(m , x, b):
	return m*x+b

def create_graph(x, y, data_type, plot_attributes):
	plot_attributes = plot_attributes[data_type]
	show_points = plot_attributes["show_points"]
	show_regression_line = plot_attributes["show_regression_line"]
	show_moving_avg = plot_attributes["show_moving_avg"]
	window = plot_attributes["window_size"]
	plt.clf()
	if show_points:
		plt.scatter(x, y)
	if show_moving_avg and data_type == "weight":
		avg = moving_avg(y, window)
		bulk_cut_dates = [date_to_num(i) for i in plot_attributes["bulk/cut_dates"].keys()]
		bulk_cut_dates.sort()
		gym_start = closest_num(bulk_cut_dates[0], x)
		plt.plot(x[:gym_start], avg[:gym_start], color="#4063c2")
		for i in range(len(bulk_cut_dates)):
			start = closest_num(bulk_cut_dates[i], x)
			color = "#b81414"
			if i%2==0:
				color = "#109410"
			if i == len(bulk_cut_dates)-1:
				plt.plot(x[start:], avg[start:], color=color)
				continue
			end = closest_num(bulk_cut_dates[i+1], x)
			plt.plot(x[start:end], avg[start:end], color=color)
	elif show_moving_avg:
		avg = moving_avg(y, window)
		plt.plot(x, avg)
	if show_regression_line:
		slope, intercept, r, p, std_err = stats.linregress(x, y)
		slope_func = lambda x: slope * x + intercept
		regression_line = list(map(slope_func, x))
		plt.plot(x, regression_line, color="#3b3b3b")
	year_position, year = [], []
	for i in range(int(rn("%y"))-21+1):
		year_position.append((i+2021)*365)
		year.append(str(i+21))
	while min(x) > year_position[1]:
		year_position.pop(0)
		year.pop(0)
	while max(x) < year_position[-1]:
		year_position.pop(-1)
		year.pop(-1)
	plt.grid(axis=plot_attributes["grid"])
	plt.xticks(year_position, year)
	plt.title(plot_attributes["title"])
	plt.xlabel(plot_attributes["x_label"])
	plt.ylabel(plot_attributes["y_label"])
	plt.legend(["Not Dieting", "Bulking", "Cutting"])
	plt.savefig(plot_attributes["filename"], dpi=dpi)

# start of spotify functions

def iterations(length, max_request=50):
	if length % max_request == 0:
		return int((length/max_request)-1)
	return int(str(length/max_request).split(".")[0])

def format_song_name(song_name):
	song_name = song_name.split(" (")[0]
	song_name = song_name.split(" - ")[0]
	song_name = song_name.split(" / ")[0]
	song_name = song_name.split(" Remastered")[0]
	while song_name[-1] in [" ", "/", "\\"]:
		song_name = song_name[:-1]
	return song_name

def format_artist(artist_dict):
	del artist_dict["external_urls"]
	del artist_dict["href"]
	del artist_dict["uri"]
	return artist_dict

def format_track(song, track_num):
	added = None
	if "added_at" in song.keys():
		added = song["added_at"]
		song = dict(song["track"])
	song["added_at"] = added
	song["formatted_name"] = format_song_name(song["name"])
	try:
		del song["album"]["available_markets"]
	except:
		pass
	del song["album"]["external_urls"]
	del song["album"]["href"]
	del song["album"]["images"]
	del song["album"]["uri"]
	song["album"]["artists"] = [
		format_artist(i) for i in song["album"]["artists"]]
	song["artists"] = [format_artist(i) for i in song["artists"]]
	del song["external_ids"]
	del song["external_urls"]
	del song["href"]
	del song["preview_url"]
	del song["uri"]
	song["artist_num"] = len(song["artists"])
	song["album_track_number"] = song["track_number"]
	song["track_number"] = int(track_num)
	for i in song["artists"]:
		if i["name"] == "Andr\u00e9 Benjamin":
			i["name"] = "Andr\u00e9 3000"
		elif i["name"] in [
			"King Geedorah", "MF Doom", "Viktor Vaughn", "Zev Love X", "Doom", "DOOM",
			"Metal Fingers", "KMD", "JJ DOOM", "Danger Doom", "Madvillain",
			]:
			i["name"] = "MF DOOM"
		elif i["name"] == "Passengers":
			i["name"] = "U2"
		elif i["name"] == "The Network":
			i["name"] = "Green Day"
		elif i["name"] == "Larry Lurex":
			i["name"] = "Queen"
		elif i["name"] == "Los Unidades":
			i["name"] = "Coldplay"
		elif i["name"] == "The Desert Sessions":
			i["name"] = "Queens of the Stone Age"
		elif i["name"] == "Chris Gaines":
			i["name"] = "Garth Brooks"
	return song

def format_podcast(podcast):
	added = None
	if "added_at" in podcast.keys():
		added = podcast["added_at"]
		podcast = dict(podcast["episode"])
	podcast["added_at"] = added
	del podcast["audio_preview_url"]
	del podcast["external_urls"]
	del podcast["href"]
	del podcast["html_description"]
	del podcast["images"]
	del podcast["is_externally_hosted"]
	del podcast["language"]
	del podcast["languages"]
	del podcast["uri"]
	podcast["show"] = format_podcast_show(podcast["show"])
	return podcast

def format_podcast_show(show):
	del show["available_markets"]
	del show["copyrights"]
	del show["external_urls"]
	del show["href"]
	del show["html_description"]
	del show["images"]
	del show["is_externally_hosted"]
	del show["languages"]
	del show["uri"]
	return show

def requests_per_thread_func(thread_count, playlist_len, max_request):
	total_requests = (playlist_len//max_request)-1
	if playlist_len % max_request != 0:
		total_requests += 1
	requests_per_thread = []
	for i in range(thread_count):
		requests_per_thread.append(total_requests//thread_count)
	for i in range(total_requests % thread_count):
		requests_per_thread[i] += 1
	return requests_per_thread[::-1]

def get_song_data(sp,thread_num, requests_per_thread, max_request, playlist_len):
	data_list = []
	wait_time = 0
	i = 0
	while i < requests_per_thread[thread_num]:
		try:
			time.sleep(wait_time)
			offset = (sum(requests_per_thread[:thread_num])+i+1)*max_request+1
			raw_data = dict(sp.current_user_saved_tracks(
				limit=50, market="US", offset=offset))["items"]
			data_list.extend([format_track(raw_data[i], playlist_len-(offset+i)-1) for i in range(len(raw_data))])
			i += 1
		except:
			error_report("get_song_data")
			wait_time += 1
	return data_list

def get_all_songs(sp):
	if log_command("get_all_songs"):
		return
	try:
		max_request = 50
		raw_data = dict(sp.current_user_saved_tracks(
			limit=max_request, market="US", offset=0))
		playlist_len = int(raw_data["total"])
		raw_data = raw_data["items"]
		data_list = [format_track(raw_data[i], playlist_len-i-1) for i in range(len(raw_data))]
		thread_count = 10
		requests_per_thread = requests_per_thread_func(thread_count, playlist_len, max_request)
		with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
			futures = [
				executor.submit(get_song_data,sp, thread_num, requests_per_thread, max_request, playlist_len)
				for thread_num in range(len(requests_per_thread))]
			results = [futures.result() for futures in concurrent.futures.as_completed(futures)]
		for i in results:
			data_list.extend(i)
		data_list.sort(key=lambda x: x["track_number"], reverse=True)
		with open("text_files/tracks.json", "w") as data_file:
			json.dump({"data": data_list}, data_file, indent=2)
	except:
		error_report("get_all_songs")
def get_genres(spotify_client):
	with open("text_files/tracks.json") as data_file:
		data = dict(json.load(data_file))["data"]
	max_request = 50
	genre_list = []
	artist_ids = []
	for song in data:
		for artist in song["artists"]:
			artist_ids.append(artist["id"])
	artist_ids = list(set(artist_ids))
	for i in range(iterations(len(artist_ids))):
		batch_genres = dict(spotify_client.artists(artist_ids[i*max_request:(i+1)*max_request]))
		for artist in batch_genres["artists"]:
			genre_list.extend(artist["genres"])
	genre_dict = dict(Counter(genre_list))
	with open("text_files/genres.json", "w") as data_file:
		json.dump(genre_dict, data_file, indent=2)

def podcasts(sp):
	max_podcast_request = True
	podcasts = []
	n = 0
	while max_podcast_request:
		new_podcast_request = dict(sp.current_user_saved_episodes(offset=n))["items"]
		podcasts.extend([format_podcast(i) for i in new_podcast_request])
		if len(new_podcast_request) < 20:
			max_podcast_request = False
		n += 20
	with open("text_files/podcasts.json", "w") as podcast_file:
		json.dump(podcasts, podcast_file)

def read_spotify_data():
	with open("text_files/tracks.json") as data_file:
		data = list(json.load(data_file)["data"])
	return data

def duration_graph_organization(data, bars_per_graph):
	if log_command("duration_graph_organization"):
		return
	maxes, durations = [], []
	shortest = {data[0]["duration_ms"]: data[0]["formatted_name"]}
	for i in data:
		duration = i["duration_ms"]
		durations.append(duration)
		if len(maxes) < bars_per_graph:
			maxes.append({duration: i["formatted_name"]})
		maxes_min = min([list(i.keys())[0] for i in maxes])
		if duration >= list(shortest.keys())[0] and duration <= maxes_min:
			continue
		if duration < list(shortest.keys())[0]:
			shortest = {duration: i["formatted_name"]}
			continue
		for j in range(len(maxes)):
			if list(maxes[j].keys())[0] == maxes_min:
				maxes[j] = {duration: i["formatted_name"]}
				break
	avg_track = round(np.mean(a=durations)/1000)
	maxes.sort(key=lambda x: list(x.keys())[0], reverse=True)
	longest = round(int(list(maxes[0].keys())[0])/1000)
	shortest = round(int(list(shortest.keys())[0])/1000)
	return maxes, avg_track, longest, shortest

def get_artist_info(data):
	artist_dict = {}
	for i in data:
		for artist in i["artists"]:
			if artist["name"] in artist_dict.keys():
				artist_dict[artist["name"]] += 1
			else:
				artist_dict.update({artist["name"]: 1})
	return artist_dict, len(artist_dict)

def find_popular(artist_dict, artists_per_graph):
	values_list = list(artist_dict.values())
	popularity = {}
	most_popular = []
	uses = []
	for i in values_list:
		if i not in popularity.keys():
			popularity.update({i: 1})
		else:
			popularity[i] += 1
	use_nums = sorted(popularity.keys(), reverse=True)
	done = False
	for key in use_nums:
		if done:
			break
		for artist in artist_dict:
			if artist_dict[artist] == key:
				most_popular.append(artist)
				uses.append(key)
			if len(most_popular) == artists_per_graph:
				done = True
	return most_popular, uses

def get_explicits(data):
	explicits = {"Explicit": 0, "Clean": 0, "Unknown": 0}
	for item in data:
		if str(item["explicit"]) == "True":
			explicits["Explicit"] += 1
		elif str(item["explicit"]) == "False":
			explicits["Clean"] += 1
		else:
			explicits["Unknown"] += 1
	if not explicits["Unknown"]:
		del explicits["Unknown"]
	return explicits

def genre_data_organization(genres_per_graph=20, genre_num_only=False):
	with open("text_files/genres.json") as data_file:
		data = json.load(data_file)
	if genre_num_only:
		return len(data)
	values_list = list(data.values())
	popularity = {}
	most_popular = []
	uses = []
	for i in values_list:
		if i not in popularity.keys():
			popularity.update({i: 1})
		else:
			popularity[i] += 1
	use_nums = sorted(popularity.keys(), reverse=True)
	for key in use_nums:
		for artist in data:
			if data[artist] == key:
				most_popular.append(artist.capitalize())
				uses.append(key)
		if len(most_popular) >= genres_per_graph:
			break
	return most_popular, uses, len(data)

def covers(data):
	names = [i["formatted_name"] for i in data]
	copies = list(set([i for i in names if list(names).count(i) > 1]))
	return len(copies)

def release_date_data(data, range_only=False):
	yrs = [int(i["album"]["release_date"][:4]) for i in data]
	first = min(yrs)
	last = max(yrs)
	if range_only:
		return last-first
	def to_decade(i): return int(str(i)[:-1]+"0")
	yrs = sorted(list(map(to_decade, yrs)))
	popularity = {}
	for i in yrs:
		if i not in popularity.keys():
			popularity.update({i: 1})
		else:
			popularity[i] += 1
	popularity = dict(sorted(popularity.items(), key=lambda item: item[0]))
	return list(popularity.keys()), list(popularity.values()), last-first

def auto_pct(pct, all_values):
	absolute = int(pct / 100.*np.sum(all_values))
	return "{:.1f}%\n({:d})".format(pct, absolute)

def get_podcast_data():
	with open("text_files/podcasts.json") as data_file:
		data = json.load(data_file)
	return data

def get_podcast_duration(data):
	total = 0
	for i in data:
		total += i["duration_ms"]
	return total

def get_show_frequency(data):
	shows = []
	show_dict = {}
	for i in data:
		shows.append(i["show"]["name"])
	for i in shows:
		show_dict.update({i: shows.count(i)})
	return show_dict

def get_show_durations(data):
	show_dict = {}
	for i in data:
		show_name = i["show"]["name"]
		duration = int(i["duration_ms"]/(60*1000))
		if show_name in show_dict.keys():
			show_dict[show_name] = show_dict[show_name] + duration
		else:
			show_dict.update({show_name: duration})
	return show_dict

# end of spotify functions

def on_start():
	if log_command("on_start"):
		return
	clear_file("text_files/response")
	clear_file("text_files/cancel")
	clear_file("text_files/current_workout")
	set_in_conversation(False)


if __name__ == '__main__':
	on_start()
	app.run(host="0.0.0.0", port=port, debug=True)
	# run_simple('localhost', 5000, app)
