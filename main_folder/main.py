'''
all dates are in month/day/year

'''

from flask import Flask, request
import requests
from pprint import pprint
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
import sys
import cloudinary.uploader
from scipy import stats
import threading


load_dotenv()

app = Flask(__name__)
port = 5000
twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
client = Client(twilio_account_sid, twilio_auth_token)
bot_num = os.getenv("TWILIO_PHONE_NUMBER")
my_num = os.getenv("MY_PHONE_NUMBER")
cloudinary_cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
cloudinary_api_key = os.getenv("CLOUDINARY_API_KEY")
cloudinary_api_secret = os.getenv("CLOUDINARY_API_SECRET")
tz = pytz.timezone("America/New_York")
start_keyword = "--start--"
request_header = {
	'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'
}

plot_attributes = {
	"weight": {
		"grid": "y",
		"title":"Weight Over Time",
		"xlabel": "Year",
		"ylabel": "Weight(lbs)",
		"filename": "main_folder/weight.png",
		"show_points": False,
		"show_moving_avg": True,
		"show_regression_line": True,
		"window_size": 7,
		"bulk_dates":["01/28/2023"],
		"cut_dates":["06/06/2023"]
	}
}

def text_me(body, media_url=None):
	try:
		message = client.messages.create(body=body, from_=bot_num, to=my_num, media_url=media_url)
	except:
		pass


@app.route("/", methods=["POST"])
def hook():
	message = str(dict(request.values)["Body"])
	if " " in message:
		message = message.split(" ")
	else:
		message = [message, ""]
	args = message[1:]
	message = message[0]
	if message == "KILL":
		kill()
	elif message == "Kill":
		kill()
	elif message == "kill":
		kill()
	elif message == "alarm":
		text_me(alarm())
	elif message == "temp":
		if not log_command("temp"):
			text_me(f"{get_weather('temp')}°")
	elif message == "spam":
		spam(args)
	elif message == "weather":
		if not log_command("weather"):
			text_me(formatted_weather())
	elif message == "quote":
		if not log_command("quote"):
			text_me(get_quote())
	elif message == "school":
		school()
	elif message == "scan":
		if not log_command("scan"):
			text_me(get_quote(args[0]))
	elif message == "bday":
		text_me(bday())
	elif message == "today":
		today()
	elif message == "desc":
		desc()
	elif message == "commands":
		commands()
	elif message == "clean":
		clean()
	elif message == "work":
		schedule_work(args)
	elif message == "weight":
		text_me(log_weight(args))
	elif message == "calories":
		text_me(log_calories(args))
	elif message == "graph":
		send_weight_graph()
	elif message.lower() == "hi":
		text_me("Hello!")
	else:
		text_me("That command does not exist.\nTo see a list of all commands, text \"commands\".")
	return "200"


def kill():
	os.abort()


def rn(target="%H:%M"):
	now = datetime.now(tz)
	return now.strftime(target)


def log_command(name):
	with open("main_folder/text_files/command_list", "a") as command_file:
		command_file.write(f"{name}\n")
	with open("main_folder/text_files/cancel") as cancel_file:
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
	with open("main_folder/text_files/alarm") as alarm_file:
		alarm_on = bool(int(alarm_file.readline()))
	with open("main_folder/text_files/alarm", "w") as alarm_file:
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
	month = rn('%B').lower()
	day = str(int(rn('%d')))
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
			message.append(f"{i['name']}({i['birth']}-{i['death']}): {i['job']}")
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

def log_weight(pounds):
	if log_command("log_weight"):
		return
	with open("main_folder/text_files/weight", "a") as weight_file:
		weight_file.write(f"{rn('%m/%d/%Y')}:{pounds[0]}\n")
	return "Logged"

def send_weight_graph():
	if log_command("send_weight_graph"):
		return
	with open("main_folder/text_files/weight") as f:
		raw_weights = f.readlines()
	data = [date_to_num(i).split(":") for i in raw_weights]
	data = sorted(data)
	x = [int(i[0]) for i in data]
	y = [float(i[1]) for i in data]
	create_graph(x, y, "weight")
	cloudinary.config(
		cloud_name= cloudinary_cloud_name,
		api_key= cloudinary_api_key,
		api_secret= cloudinary_api_secret
	)
	graph_url = cloudinary.uploader.upload(
		"main_folder/weight.png",
		public_id="weight_graph",
		overwrite=True)["secure_url"]
	text_me("Here is your weight graph", graph_url)
	os.remove("main_folder/weight.png")


def log_calories(cals):
	if log_command("log_calories"):
		return
	with open("main_folder/text_files/calories", "a") as calories_file:
		calories_file.write(f"{rn('%m/%d/%Y')}:{cals[0]}\n")
	return "Logged"


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
		, "desc -> sends a description of this bot"
		, "commands -> sends this"]
	length = len(command_lst)
	message1 = "\n".join(command_lst[:length//2])
	message2 = "\n".join(command_lst[length//2:])
	message2 += "\nI also have a few other surprises ;)"
	text_me(message1)
	text_me(message2)


def clean():
	if log_command("clean"):
		return
	daily_funcs()
	with open("main_folder/text_files/quotes") as quotes_file:
		quotes = list(set(quotes_file.readlines()))
	with open("main_folder/text_files/used_quotes") as used_quotes_file:
		used_quotes = list(set(used_quotes_file.readlines()))
	for i in quotes:
		if i in used_quotes:
			quotes.remove(i)
			used_quotes.append(i)
	quote_fix = False
	used_fix = False
	with open("main_folder/text_files/quotes") as quotes_file:
		if quotes != quotes_file.readlines():
			quote_fix = True
	with open("main_folder/text_files/used_quotes") as used_quotes_file:
		if used_quotes != used_quotes_file.readlines():
			used_fix = True
	if quote_fix:
		with open("main_folder/text_files/quotes", "w") as quotes_file:
			quotes_file.writelines(quotes)
	if used_fix:
		with open("main_folder/text_files/used_quotes", "w") as used_quotes_file:
			used_quotes_file.writelines(used_quotes)
	with open("main_folder/text_files/alarm") as alarm_file:
		alarm_bool = alarm_file.readline()
		try:
			x = int(alarm_bool)
		except:
			text_me("error in alarm file")
			error_report("alarm_file")
	text_me("All Clean!")


def schedule_work(work):
	pass


def error_report(name):
	time_stamp = rn("%y/%m/%d/%H/%M/%S")
	with open("main_folder/text_files/errors") as error_file:
		errors = error_file.readlines()
	if len(errors) >=40:
			errors = errors[30:]
	elif len(errors)>=10:
		errors=errors[10:]
	elif len(errors)>=5:
			errors = errors[5:]
	if len(errors) >5 and errors.count(errors[0])==len(errors):
		with open("main_folder/text_files/cancel") as cancel_file:
			cancels = cancel_file.readlines()
		cancels.append(name+"\n")
		cancels = list(set(cancels))
		with open("main_folder/text_files/cancel", "w") as cancel_file:
			cancel_file.writelines(cancels)
	else:
		with open("main_folder/text_files/errors", "a") as error_list:
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
	message += f"Visibility - {weather['vis'].replace('10.00', '10')}" # type: ignore
	return message.replace("Fog/Mist", "Foggy")


def uncancel(name):
	with open("main_folder/text_files/cancel") as cancel_file:
		cancels = cancel_file.readlines()
	name += "\n"
	if name in cancels:
		cancels.remove(name)
	else:
		return
	with open("main_folder/text_files/cancel", "w") as cancel_file:
		cancel_file.writelines(cancels)


def get_quote(scan=None):
	with open("main_folder/text_files/used_quotes") as used_quotes_file:
		used_quotes = (used_quotes_file.readlines())
	with open("main_folder/text_files/quotes") as quotes_file:
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
	with open("main_folder/text_files/quotes", "w") as quotes_file:
		quotes_file.writelines(quote_list)
	with open("main_folder/text_files/used_quotes", "a") as used_quotes_file:
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

def create_graph(x, y, data_type):
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
	plt.savefig(plot_attributes[data_type]["filename"], dpi=1000)


def daily_funcs():
	os.remove("main_folder/text_files/cancel")
	open("main_folder/text_files/cancel", "x")


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


def event_loop():
	event_id = int(time.time())
	with open("main_folder/text_files/event_id", "w") as event_id_file:
		event_id_file.write(str(event_id))
	while True:
		if int(rn("%M")) % 5 == 0:
			with open("main_folder/text_files/event_id") as event_id_file:
				if int(event_id_file.readline()) != event_id:
					print("duplicate process detected, aborting...")
					break
		if rn() == "10:30":
			if log_command("morning"):
				time.sleep(60)
			else:
				message = "Good Morning!\n"
				day_num = int(rn("%d"))
				suffix = num_suffix(int(rn("%d")[1]))
				message += f"Today is {rn(f'%A, %B {day_num}{suffix}')}\n"
				message += f"You move out in {days_until('09/15/2023', return_days=True)} days\n"
				message += "Here's today's weather:\n\t"
				message += formatted_weather().replace("\n", "\n\t")
				text_me(message)
				with open("main_folder/text_files/errors") as errors:
					error_list = list(errors.readlines())
					if len(error_list) > 100000:
						text_me("OVER 100,000 ERRORS, FIX IMMEDIATELY!")
					elif len(error_list) > 10000:
						text_me("Over 10,000 errors, fix it soon.")
					elif len(error_list) > 1000:
						text_me("Over 1,000 erros, check it out sometime soon.")
				time.sleep(60)
		if rn() == "11:00":
			if log_command("morning quote"):
				time.sleep(1)
			else:
				text_me(get_quote())
				time.sleep(50)
		if rn() == "06:00": # daily operations
			daily_funcs()
		time.sleep(5)

threading.Thread(target=event_loop).start()

if __name__ == "__main__":
	app.run(host="0.0.0.0", port=port, debug=True)
