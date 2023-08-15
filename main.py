'''
all dates are in month/day/year

'''

from flask import Flask, request
from pprint import pprint
import json
import requests
import time
from datetime import datetime, date
import pytz
import random
import os
import numpy as np
from bs4 import BeautifulSoup
import re
from twilio.rest import Client
from dotenv import load_dotenv
import pandas as pd
import matplotlib.pyplot as plt
import cloudinary.uploader
from scipy import stats
import threading
import openai
import spotipy
from spotipy import SpotifyOAuth
from collections import Counter


load_dotenv()

app = Flask(__name__)
port = 5000
dpi =500
twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
client = Client(twilio_account_sid, twilio_auth_token)
bot_num = os.getenv("TWILIO_PHONE_NUMBER")
my_num = os.getenv("MY_PHONE_NUMBER")
cloudinary_cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
cloudinary_api_key = os.getenv("CLOUDINARY_API_KEY")
cloudinary_api_secret = os.getenv("CLOUDINARY_API_SECRET")
spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
tz = pytz.timezone("America/New_York")
request_header = {
	"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36"
}
auth_manager = SpotifyOAuth(
	client_id=spotify_client_id,
	client_secret=spotify_client_secret,
	redirect_uri="http://www.evantoomey.com/",
	open_browser=True,
	scope="user-library-read",
)
spotify_client = spotipy.Spotify(oauth_manager=auth_manager)
cloudinary.config(
	cloud_name=cloudinary_cloud_name,
	api_key=cloudinary_api_key,
	api_secret=cloudinary_api_secret
)


plot_attributes = {
	"weight": {
		"grid": "y",
		"title":"Weight Over Time",
		"xlabel": "Year",
		"ylabel": "Weight(lbs)",
		"filename": "weight.png",
		"show_points": False,
		"show_moving_avg": True,
		"show_regression_line": True,
		"window_size": 7,
		"bulk_dates":["01/29/2023"],
		"cut_dates":["06/06/2023"]
	}
}

def text_me(body, media_url=None):
	try:
		message = client.messages.create(body=body, from_=bot_num, to=my_num, media_url=media_url)
		log_message(body, "script")
	except:
		pass


@app.route("/", methods=["POST"])
def hook():
	message = dict(request.values)["Body"]
	if message.lower().strip() == "kill":
		kill()
	if in_conversation():
		log_response(message)
		return "200"
	if " " in message:
		message = message.split(" ")
		args = message[1:]
		message = message[0].lower()
	else:
		args = []
		message = message.lower()
	log_message(message, "evan")
	match message:
		case "kill":
			kill()
		case "alarm":
			text_me(alarm())
		case "temp":
			if not log_command("temp"):
				text_me(f'''{get_weather("temp")}°''')
		case "spam":
			spam(args)
		case "weather":
			if not log_command("weather"):
				text_me(formatted_weather())
		case "quote":
			if not log_command("quote"):
				text_me(get_quote())
		case "school":
			school()
		case "scan":
			if not log_command("scan"):
				text_me(get_quote(args[0]))
		case "bday":
			text_me(bday())
		case "today":
			today()
		case "desc":
			desc()
		case "commands":
			commands()
		case "clean":
			clean()
		case "weight":
			log_weight(args[0])
			text_me("Logged")
		case "calories":
			text_me(log_calories(args))
		case "weight_graph":
			send_weight_graph(plot_attributes)
		case "hi":
			text_me("Hello!")
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
		case "runtimes":
			send_podcast_runtime_graph()
		case _:
			text_me("That command does not exist.\nTo see a list of all commands, text \"commands\".")
	return "200"

def kill():
	log = log_command("kill")
	os.abort()

def rn(target="%H:%M"):
	now = datetime.now(tz)
	return now.strftime(target)


def log_command(name):
	with open("text_files/command_list", "a") as command_file:
		command_file.write(f"{name}\n")
	with open("text_files/cancel") as cancel_file:
		cancels = cancel_file.readlines()
	return(name in cancels)


def days_until(target, start=None, return_days=False):
	if log_command("days_until"):
		return "error"
	target = target.split("/")
	target = date(year=int(target[2]), month=int(target[0]), day=int(target[1]))
	if start == None:
		start = date.today()
	else:
		start = start.split("/")
		start = date(year=int(start[2]), month=int(start[0]), day=int(start[1]))
	difference = target - start
	if return_days:
		return int(difference.days)
	return difference


def alarm():
	if log_command("alarm"):
		return
	with open("text_files/alarm") as alarm_file:
		alarm_on = bool(int(alarm_file.readline()))
	with open("text_files/alarm", "w") as alarm_file:
		if alarm_on:
			alarm_file.write("0")
		else:
			alarm_file.write("1")
		alarm_state = "off" if alarm_on else "on"
		return(f"Your alarm is now {alarm_state}")


def spam(message):
	if log_command("spam"):
		return
	for i in range(5):
		text_me(message)
		time.sleep(2)


def school():
	if log_command("school"):
		return
	try:
		left = days_until("09/15/2023", return_days=True)
		total = days_until("09/15/2023", "06/15/2023", return_days=True)
		message = f"Summer completed - {round((1-(left/total))*100, 1)}%\n" # type: ignore
		message += f"Days until I move out - {left}"
		text_me(message)
	except:
		text_me("Error")


def bday_famousbirthdays():
	if log_command("bday_famousbirthdays"):
		return
	month = rn("%B").lower()
	day = str(int(rn("%d")))
	url = f"https://www.famousbirthdays.com/{month}{day}.html"
	bday_page = requests.get(url, headers=request_header)
	bday_soup = BeautifulSoup(bday_page.content, "html.parser")
	raw_bday_list = list(
		filter(lambda x: x != "", bday_soup.text.split("\n")))[7:-9]
	for i in range(len(raw_bday_list)):
		try:
			not_used = int(raw_bday_list[i])
			raw_bday_list.remove(raw_bday_list[i])
		except:
			pass
	fake_famous = [
		"TikTok Star", "Reality Star", "Gospel Singer",
		"YouTube Star", "Cricket Player", "Instagram Star", "Snapchat Star",
		"Family Member", "Dubsmash Star", "Twitch Star", "Stylist",
		"eSports Player", "Cat", "Dog", "Rugby Player", "Soap Opera Actress",
		"World Music Singer"
	]
	bday_list = []
	name = None
	birth = None
	death = None
	job = None
	for i in range(len(raw_bday_list)):
		if i % 2 == 0:
			if raw_bday_list[i].count(",") > 1:
				name = ",".join(raw_bday_list[i].split(",")[:-1])
				birth = int(rn("%Y")) - int(raw_bday_list[i].split(",")[-1].strip())
				death = "?"
				if int(rn("%Y")) - birth < 18:
					continue
			elif raw_bday_list[i].count(",") == 1:
				name = raw_bday_list[i].split(",")[0]
				birth = int(rn("%Y")) - int(raw_bday_list[i].split(",")[-1].strip())
				death = "?"
				if int(rn("%Y")) - birth < 18:
					continue
			else:
				name = raw_bday_list[i].split("(")[0]
				birth = int(raw_bday_list[i].split("(")[-1].split("-")[0])
				death = int(raw_bday_list[i].split("(")[-1].replace(")", "").split("-")[-1])
			job = raw_bday_list[i+1]
			bday_list.append({"name":name.strip().replace("Í", "i"), "birth":birth,"death":death, "job":job, "source":"famousbirthdays"})
	final_bday_list = []
	for i in range(len(bday_list)):
		makes_list = False
		if bday_list[i]["death"] != "?":
			makes_list = True
		if not bday_list[i]["job"] in fake_famous:
			makes_list = True
		if makes_list:
			final_bday_list.append(bday_list[i])
	return final_bday_list


def bday_ducksters():
	month = rn("%B").lower()
	day = str(int(rn("%d")))
	url = f"https://www.ducksters.com/history/{month}birthdays.php?day={day}"
	bday_page = requests.get(url, headers=request_header)
	bday_soup = BeautifulSoup(bday_page.content, "html.parser")
	bday_text = ("".join(bday_soup.get_text().split("Birthdays: \n")[1])).split("Archive:\n")[0].split("\xa0")
	for i in range(bday_text.count("")):
		bday_text.remove("")
	for i in range(len(bday_text)):
		bday_text[i] = bday_text[i].replace("\n", "")
	bday_list = []
	name = bday_text[1].split("(")[0].strip()
	birth = int(bday_text[0].strip())
	death = "?"
	job = bday_text[1].split("(")[-1].split(")")[0].strip()
	bday_list.append({"name":name.replace("Í", "i"), "birth":birth,"death":death, "job":job, "source":"ducksters"})
	for i in range(2, len(bday_text)):
		name = bday_text[i].split("(")[0].strip()
		birth = int(bday_text[i-1].split(")")[-1].strip())
		death = "?"
		job = bday_text[i].split("(")[-1].split(")")[0].strip()
		bday_list.append({"name":name.replace("Í", "i"), "birth":birth,"death":death, "job":job, "source":"ducksters"})
	return(bday_list)


def bday():
	if log_command("bday"):
		return "error"
	try:
		big_list = bday_famousbirthdays() + bday_ducksters()
		merged_list = []
		for i in big_list:
			if merged_list == []:
				merged_list.append(i)
				continue
			in_list = False
			for k in merged_list:
				if i["name"] == k["name"]:
					in_list = True
					if i["death"] != "?" and k["death"] == "?":
						k["death"] = i["death"]
					if k["source"] == "famousbirthdays":
						k["source"] = "both"
						k["job"] = i["job"]
			if not in_list:
				merged_list.append(i)
		top_ten = []
		for i in merged_list:
			if i["source"] == "both":
				top_ten.append(i)
		if len(top_ten) < 10:
			for i in merged_list:
				if i["source"] == "ducksters":
					top_ten.append(i)
		births = []
		if len(top_ten) < 10:
			for i in merged_list:
				if i["source"] == "famousbirthdays":
					births.append(i["birth"])
		births.sort()
		births = births[:10-len(top_ten)]
		for i in births:
			for k in merged_list:
				if k["birth"] == i:
					top_ten.append(k)
		message = ["Famous Birthdays Today:"]
		for i in top_ten:
			message.append(f'''{i["name"]}({i["birth"]}-{i["death"]}): {i["job"]}''')
		return "\n".join(message)
	except:
		error_report("bday")
		return "error"

def today():
	if log_command("today"):
		return
	day_num = int(rn("%d"))
	suffix = num_suffix(int(rn("%d")[1]))
	message = rn(f"Today is %A, %b {day_num}{suffix}") + "\n"
	text_me(message)

def clean():
	if log_command("clean"):
		return
	daily_funcs()
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
	with open("text_files/alarm") as alarm_file:
		alarm_bool = alarm_file.readline()
		try:
			x = int(alarm_bool)
		except:
			text_me("error in alarm file")
			error_report("alarm_file")
	update_spotify_data()
	text_me("All Clean!")

def log_weight(pounds):
	if log_command("log_weight"):
		return
	with open("text_files/weight", "a") as weight_file:
		weight_file.write(f'''{rn("%m/%d/%Y")}:{pounds}\n''')

def send_weight_graph(plot_attributes):
	if log_command("send_weight_graph"):
		return
	with open("text_files/weight") as f:
		raw_weights = f.readlines()
	data = [date_to_num(i).split(":") for i in raw_weights]
	data = sorted(data)
	x = [int(i[0]) for i in data]
	y = [float(i[1]) for i in data]
	create_graph(x, y, "weight", plot_attributes)
	graph_url = cloudinary.uploader.upload(
		"weight.png",
		public_id="weight_graph",
		overwrite=True)["secure_url"]
	text_me("Here is your weight graph", graph_url)
	os.remove("weight.png")


def log_calories(cals):
	if log_command("log_calories"):
		return
	with open("text_files/calories", "a") as calories_file:
		calories_file.write(f'''{rn("%m/%d/%Y")}:{cals[0]}\n''')
	return "Logged"


def update_spotify_data():
	if log_command("update_spotify_data"):
		return
	threading.Thread(target=podcasts, args=(spotify_client,)).start()
	threading.Thread(target=get_genres, args=(spotify_client,)).start()
	get_all_songs(spotify_client)


def spotify_data_description():
	data, track_num = read_spotify_data()
	artist_dict, artist_num = get_artist_info(data)
	durations, avg_track_len, longest, shortest = duration_graph_organization(
		data, 20)
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
		f"The songs were an average of "+str(int(avg_track_len//60)) + " minutes and "+str(int(avg_track_len % 60))+" seconds long.",
		f"The longest song was "+str(longest//60) + " minutes and "+str(longest % 60)+" seconds long.",
		f"The shortest song was "+str(shortest//60) + " minute and "+str(shortest % 60)+" seconds long.",
		f"There were around {cover_num} cover songs.",
		f'''About {round((explicits["Explicit"]/track_num)*100, 1)}% of the songs were explicit.''',
		f"You have {len(podcast_data)} saved podcast episodes that are collectively {podcast_hours} hours long.",
		f"Those episodes are from {len(shows.keys())} different shows."
		]
	text_me("\n".join(message))
	update_spotify_data()

def send_artist_graph():
	if log_command("send_artist_graph"):
		return
	data, track_num = read_spotify_data()
	artist_dict, artist_num = get_artist_info(data)
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
	text_me("Here are your top artists.", graph_url)
	os.remove("artist_graph.png")

def send_song_duration_graph():
	if log_command("send_song_duration_graph"):
		return
	data, track_num = read_spotify_data()
	durations, avg_track_len, longest, shortest = duration_graph_organization(
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
	text_me("Here are your longest songs.", graph_url)
	os.remove("song_duration_graph.png")

def send_genre_graph():
	if log_command("send_genre_graph"):
		return
	data, track_num = read_spotify_data()
	popular_genres, genres_uses, genre_num = genre_data_organization(20)
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
	text_me("Here are your top genres.", graph_url)
	os.remove("genre_graph.png")

def send_explicit_graph():
	if log_command("send_explicit_graph"):
		return
	data, track_num = read_spotify_data()
	explicits = get_explicits(data)
	plt.figure(figsize=(10, 10), dpi=dpi)
	plt.title("Number of Explicit Songs(Aproximate)", pad=40)
	plt.pie(x=explicits.values(), labels=list(explicits.keys()), radius=1.3,
					autopct=lambda pct: auto_pct(pct, list(explicits.values())),)
	plt.savefig("explicit_graph.png")
	graph_url = cloudinary.uploader.upload(
		"explicit_graph.png",
		public_id="explicit_graph",
		overwrite=True)["secure_url"]
	text_me("Here is the ratio of explicit songs in your library.", graph_url)
	os.remove("explicit_graph.png")

def send_covers_graph():
	if log_command("send_covers_graph"):
		return
	data, track_num = read_spotify_data()
	cover_num = covers(data)
	plt.figure(figsize=(10, 10), dpi=dpi, layout="tight")
	plt.title("Number of Covers (Aproximate)")
	plt.pie(x=[len(data)-cover_num, cover_num], labels=["Original Songs", "Covers"], pctdistance=.85,
					autopct=lambda pct: auto_pct(pct, [len(data)-cover_num, cover_num]))
	plt.savefig("covers_graph.png")
	graph_url = cloudinary.uploader.upload(
		"covers_graph.png",
		public_id="covers_graph",
		overwrite=True)["secure_url"]
	text_me("Here is the ratio of covers in your library.", graph_url)
	os.remove("covers_graph.png")

def send_decade_graph():
	if log_command("send_decade_graph"):
		return
	data, track_num = read_spotify_data()
	release_decades, release_nums, release_range = release_date_data(data)
	plt.figure(figsize=(10, 10), dpi=dpi)
	plt.title("Songs from Each Decade", pad=40, fontdict={'fontsize': 20})
	plt.pie(x=release_nums, labels=release_decades, autopct=lambda pct: auto_pct(pct, release_nums),
					pctdistance=.85, labeldistance=1.05)
	plt.savefig("decade_graph.png")
	graph_url = cloudinary.uploader.upload(
		"decade_graph.png",
		public_id="decade_graph",
		overwrite=True)["secure_url"]
	text_me("Here are the decades your songs were released in.", graph_url)
	os.remove("decade_graph.png")

def send_episode_graph():
	if log_command("send_episode_graph"):
		return
	data, track_num = read_spotify_data()
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
	text_me("Here are the podcasts you listen to.", graph_url)
	os.remove("episode_graph.png")

def send_podcast_runtime_graph():
	if log_command("send_podcast_runtime_graph"):
		return
	data, track_num = read_spotify_data()
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
	text_me("Here are the podcasts you listen to.", graph_url)
	os.remove("podcast_runtime_graph.png")

def desc():
	if log_command("desc"):
		return
	message = '''I am Evan's personal bot.
	If I am going crazy and you need to terminate me, text "kill".
	If you would like to see my commands, text "commands".
	I will pass all suggestions along to my developer.
	Have an amazing day :)
	'''
	text_me(message)

def commands():
	if log_command("commands"):
		return
	command_lst = [
		"alarm -> toggles all alarms"
		, "temp -> sends the current temperature"
		, "spam ___ -> spams any message"
		, "weather -> sends the current weather conditions"
		, "quote -> sends a random quote"
		, "school -> sends how much school is left"
		, "scan ___ -> searches through all the unused quotes that contain that word/phrase"
		, "bday -> sends 5 famous people that were born today"
		, "today -> sends the day of the month, week, and school cycle"
		, "clean -> performs some functions that keep this bot running"
		, "weight ___-> logs your weight"
		, "weight_graph -> sends a graph of your weight over time"
		, "spotify -> sends some data about your spotify account"
		, "artists -> sends a graph of your top artists"
		, "durations -> sends a graph of your longest songs"
		, "genres -> sends a graph of your top genres"
		, "explicit -> sends a graph of the ratio of explicit songs in your library"
		, "covers -> sends a graph of the ratio of covers in your library"
		, "decades -> sends a graph of the decades your songs were released in"
		, "episodes -> sends a graph of the podcasts you listen to"
		, "runtimes -> sends a graph of the runtimes of the podcasts you listen to"
		, "desc -> sends a description of this bot"
		, "commands -> sends this"]
	length = len(command_lst)
	message1 = "\n".join(command_lst[:length//2])
	message2 = "\n".join(command_lst[length//2:])
	message2 += "\nI also have a few other surprises ;)"
	text_me(message1)
	text_me(message2)



def clear_file(file_name):
	file = open(file_name, "w")
	file.close()

def log_excercise(name, sets, reps, weight):
	if log_command("log_excercise"):
		return
	with open("text_files/current_workout") as workout_file:
		try:
			exercises = list(json.load(workout_file))
		except:
			exercises = []
	exercises.append({"name": name, "reps": reps, "weight": weight, "sets": sets})
	with open("text_files/current_workout", "w") as workout_file:
		json.dump(exercises, workout_file)

def log_workout(start, end, day_type):
	with open("text_files/current_workout") as workout_file:
		exercises = list(json.load(workout_file))
	workout_dict = {"exercises": exercises, "start": str(
		start), "end": end, "day_type": day_type}
	with open("text_files/workout_log") as workout_file:
		try:
			workouts = list(json.load(workout_file))
		except:
			workouts = []
	workouts.append(workout_dict)
	with open("text_files/workout_log", "w") as workout_file:
		json.dump(workouts, workout_file)
	with open("text_files/current_workout", "w") as workout_file:
		json.dump("", workout_file)

def log_response(response):
	log_message(response, "evan")
	if log_command("log_response"):
		return
	with open("text_files/response", "w") as message_file:
		message_file.write(response)

def clear_response():
	if log_command("clear_response"):
		return
	clear_file("text_files/response")

def get_response():
	if log_command("get_response"):
		return
	start = time.time()
	while True:
		with open("text_files/response") as message_file:
			response = message_file.read().strip()
		if response != "":
			return response
		if time.time() - start > 300:
			text_me("nvm")
			return None
		time.sleep(.5)

def get_weight():
	if log_command("get_weight"):
		return
	text_me("What is your weight?")
	set_in_conversation(True)
	response = get_response()
	set_in_conversation(False)
	clear_response()
	if response is None:
		return
	log_weight(response)
	text_me("Got it")

def set_in_conversation(is_in_conversation):
	if log_command("set_in_conversation"):
		return
	with open("text_files/in_conversation", "w") as message_file:
		message_file.write(str(is_in_conversation))

def in_conversation():
	if log_command("in_conversation"):
		return
	with open("text_files/in_conversation") as message_file:
		conversation_bool = message_file.read().strip() == "True"
	return conversation_bool

def log_message(message, sender):
	if log_command("log_message"):
		return
	with open("text_files/conversation_log", "a") as message_file:
		message_file.write(f"{sender}: {message}\n")

def error_report(name):
	time_stamp = rn("%y/%m/%d/%H/%M/%S")
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
	else:
		with open("text_files/errors", "a") as error_list:
			error_list.write(f"{name}:{time_stamp}\n")

def get_weather(data="full"):
	try:
		weather_page = requests.get(
			"https://forecast.weather.gov/MapClick.php?lat=40.2549&lon=-75.2429#.YXWhSOvMK02")
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
		weather_data = {"conditions":weather_conditions,"temp":temp,"humidity":humidity,
									"wind_speed": wind_speed, "dewpoint":dewpoint,"vis":vis}
		return weather_data
	except:
		error_report("get_weather")
		return "error"

def formatted_weather():
	weather = get_weather()
	try:
		conditions = weather["conditions"] # type: ignore
		temp = weather["temp"] # type: ignore
		humidity = weather["humidity"] # type: ignore
		wind_speed = weather["wind_speed"] # type: ignore
		dewpoint = weather["dewpoint"] # type: ignore
	except:
		error_report("formatted_weather")
		return "error"
	message = ""
	message += f"Temperature - {temp}°\n"
	message += f"Conditions - {conditions}\n"
	if 62 <dewpoint<69: # type: ignore
		message += "Humidity - Above Average\n"
	elif 69<=dewpoint: # type: ignore
		message += "Humidity - High\n"
	elif humidity<=30: # type: ignore
		message += "Humidity - Very Low\n"
	elif humidity<=45: # type: ignore
		message += "Humidity - Low\n"
	else:
		message += "Humidity - Average\n"
	if wind_speed>=25: # type: ignore
		message += "Wind Speed - Extremely High\n"
	elif 17<=wind_speed<25: # type: ignore
		message += "Wind Speed - Very High\n"
	elif 10<=wind_speed<17: # type: ignore
		message += "Wind Speed - Windy\n"
	elif 5<=wind_speed<10: # type: ignore
		message += "Wind Speed - Light Breeze\n"
	else:
		message += "Wind Speed - Negligible\n"
	message += f'''Visibility - {weather["vis"].replace("10.00", "10")}''' # type: ignore
	return message.replace("Fog/Mist", "Foggy")


def uncancel(name):
	with open("text_files/cancel") as cancel_file:
		cancels = cancel_file.readlines()
	name += "\n"
	if name in cancels:
		cancels.remove(name)
	else:
		return
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
	if scan == None:
		quote = quote_list[0]
	else:
		keyword_quotes = [i for i in quote_list if scan in i]
		message += f"Total Number of Quotes: {len(quote_list)}\n"
		message += f"Number of Matching Quotes: {len(keyword_quotes)}\n"
		if len(keyword_quotes) == 0:
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

def date_to_num(date):
	weight = date.split(":")[1]
	date = date.split(":")[0].split("/")
	date = str(int(date[0])*30 + int(date[1]) + int(date[2])*365)
	return date + ":" + weight

def moving_avg(data, window):
	avg = []
	for i in range(window, len(data)):
		avg.append(np.mean(data[i-window:i]))
	for i in range(window):
		avg.insert(0, avg[0])
	return avg

def create_graph(x, y, data_type, plot_attributes):
	show_points = plot_attributes[data_type]["show_points"]
	show_regression_line = plot_attributes[data_type]["show_regression_line"]
	show_moving_avg = plot_attributes[data_type]["show_moving_avg"]
	window = plot_attributes[data_type]["window_size"]
	if show_points:
		plt.scatter(x, y)
	if show_moving_avg:
		avg = moving_avg(y, window)
		plt.plot(x, avg)
	if show_regression_line:
		slope, intercept, r, p, std_err = stats.linregress(x, y)
		def slope_func(x):
			return slope * x + intercept
		regression_line = list(map(slope_func, x))
		plt.plot(x, regression_line)
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
	plt.grid(axis=plot_attributes[data_type]["grid"])
	plt.xticks(year_position, year)
	plt.title(plot_attributes[data_type]["title"])
	plt.xlabel(plot_attributes[data_type]["xlabel"])
	plt.ylabel(plot_attributes[data_type]["ylabel"])
	plt.savefig(plot_attributes[data_type]["filename"], dpi=dpi)

# start of spotify functions

def iterations(length, max_request=50):
	if length % max_request == 0:
		return int((length/50)-1)
	return int(str(length/50).split(".")[0])

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

def format_track(song):
	if "added_at" in song.keys():
		added = song["added_at"]
		song = dict(song["track"])
	else:
		added = None
	song["added_at"] = added
	song["formatted_name"] = format_song_name(song["name"])
	try:
		del song["album"]["available_markets"]
	except KeyError:
		pass
	del song["album"]["external_urls"]
	del song["album"]["href"]
	del song["album"]["images"]
	del song["album"]["uri"]
	song["album"]["artists"] = [
		format_artist(i) for i in song["album"]["artists"]]
	song["artists"] = [format_artist(i) for i in song["artists"]]
	try:
		song["available_markets"]
	except KeyError:
		pass
	del song["external_ids"]
	del song["external_urls"]
	del song["href"]
	del song["preview_url"]
	del song["uri"]
	song["artist_num"] = len(song["artists"])
	return song

def format_podcast(podcast):
	if "added_at" in podcast.keys():
		added = podcast["added_at"]
		podcast = dict(podcast["episode"])
	else:
		added = None
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

def get_all_songs(spotify_client):
	raw_data = dict(spotify_client.current_user_saved_tracks(
		limit=50, market="US", offset=0))
	playlist_len = int(raw_data["total"])
	data_list = [format_track(i) for i in raw_data["items"]]
	for i in range(iterations(playlist_len)):
		offset = i*50+51
		raw_data = dict(spotify_client.current_user_saved_tracks(
			limit=50, market="US", offset=offset))
		data_list.extend([format_track(i) for i in raw_data["items"]])
	with open("text_files/tracks.json", "w") as data_file:
		json.dump({"data": data_list}, data_file)

def get_genres(spotify_client):
	with open("text_files/tracks.json") as data_file:
		data = dict(json.load(data_file))["data"]
	genre_list = []
	artist_ids = []
	for song in data:
		for artist in song["artists"]:
			artist_ids.append(artist["id"])
	artist_ids = list(set(artist_ids))
	for i in range(iterations(len(artist_ids))):
		batch_genres = dict(spotify_client.artists(artist_ids[i*50:(i+1)*50]))
		for artist in batch_genres["artists"]:
			genre_list.extend(artist["genres"])
	genre_dict = dict(Counter(genre_list))
	with open("text_files/genres.json", "w") as data_file:
		json.dump(genre_dict, data_file)

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
	return data, len(data)

def duration_graph_organization(data, bars_per_graph):
	maxes, durations = [], []
	shortest = {data[0]["duration_ms"]: data[0]["formatted_name"]}
	for i in data:
		duration = i["duration_ms"]
		if len(maxes) < bars_per_graph:
			maxes.append({duration: i["formatted_name"]})
		maxes_min = min([list(i.keys())[0] for i in maxes])
		if duration > maxes_min:
			for j in range(len(maxes)):
				if list(maxes[j].keys())[0] == maxes_min:
					maxes[j] = {duration: i["formatted_name"]}
					break
		if duration < list(shortest.keys())[0]:
			shortest = {duration: i["formatted_name"]}
		durations.append(duration)
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
	if explicits["Unknown"] == 0:
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

def auto_pct(pct, allvalues):
	absolute = int(pct / 100.*np.sum(allvalues))
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


def daily_funcs():
	clear_file("text_files/cancel")


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

def on_start():
	clear_response()
	set_in_conversation(False)
	threading.Thread(target=event_loop).start()
	threading.Thread(target=update_spotify_data).start()


def event_loop():
	event_id = int(time.time())
	with open("text_files/event_id", "w") as event_id_file:
		event_id_file.write(str(event_id))
	while True:
		duplicate_check_frequency = 5
		if int(rn("%S")) % duplicate_check_frequency == 0:
			with open("text_files/event_id") as event_id_file:
				if int(event_id_file.readline()) != event_id:
					print("duplicate process detected, aborting...")
					duplicate_check_frequency = 60
					break
		if rn() == "16:00":
			get_weight()
			time.sleep(60)
		if rn() == "09:30":
			if log_command("morning"):
				time.sleep(60)
			else:
				message = "Good Morning!\n"
				day_num = int(rn("%d"))
				suffix = num_suffix(int(rn("%d")[1]))
				message += f'''Today is {rn(f"%A, %B {day_num}{suffix}")}\n'''
				message += f'''You move out in {days_until("09/15/2023", return_days=True)} days\n'''
				message += "Here's today's weather:\n\t"
				message += formatted_weather().replace("\n", "\n\t")
				text_me(message)
				with open("text_files/errors") as errors:
					error_list = list(errors.readlines())
					if len(error_list) > 100000:
						text_me("OVER 100,000 ERRORS, FIX IMMEDIATELY!")
					elif len(error_list) > 10000:
						text_me("Over 10,000 errors, fix it soon.")
					elif len(error_list) > 1000:
						text_me("Over 1,000 erros, check it out sometime soon.")
				time.sleep(60)
		if rn() == "11:01":
			if log_command("morning quote"):
				time.sleep(10)
			else:
				text_me(f"Here's today's quote:\n{get_quote()}")
				time.sleep(60)
		if rn() == "06:00": # daily operations
			daily_funcs()
		time.sleep(5)


if __name__ == "__main__":
	on_start()
	app.run(host="0.0.0.0", port=port, debug=True)
