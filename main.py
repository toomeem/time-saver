'''
all dates are in month/day/year


ngrok authtoken
2M5EGMAKqjQcKZJlslUHSrFWOYn_3e5FMxonCXeFjfZa62Mph
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
import uvicorn


app = Flask(__name__)
port = 5000
account_sid = "AC9dcfe6b1a8638baaa231fcd0f92d66bc"
auth_token = "bfb0bd3c5dc7540b8d8d95920f0b47b7"
client = Client(account_sid, auth_token)
bot_num = +18444177372
my_num = +12674361580
start_keyword = "--start--"

my_schedule = {
	"22:21":"test"
}
school_schedule = {# norm/early/hr_early/2hr_delay
	"08:28/07:59": {"A": "C39", "B": "C39", "C": "C39", "D": "C39", "E": "E14", "F": "C39"},
	"09:17/08:35": {"A": "K30", "B": "C39", "C": "GYM", "D": "AUDN", "E": "C39", "F": "GYM"},
	"10:06/09:11": "A11",
	"10:55/09:47": "E127",
	"11:43/10:23": {"A": "GYM", "B": "FOOD", "C": "FOOD", "D": "GYM", "E": "FOOD", "F": "Food"},
	"12:30/10:59": "E26",
	"13:19/11:35": "E141",
	"14:10/12:10": "Pack up"}
school_times = {
	"norm": ["07:21", "14:12"],
	"early": ["07:21", "11:00"],
}
no_eat = ["milk", "ravioli", "fruit cup", "pasta", "sausage", "macaroni",
			"cheese", "salad", "pretzel", "spanish beans", "muffin", "max sticks",
			"bosco", "broccoli", "nacho", "vegetable", "juice", "mozzarella", "roll",
			"buffalo", "spartan", "sweet and sour", "parm", "sausage", "knights",
			"100%", "chicken bowl", "carrot", "celery", "pizza"]
months = ["january", "february", "march", "april", "may", "june", "july", "august",
				"september", "october", "november", "december"]


def text(body):
	message = client.messages.create(body=body, from_=bot_num, to=my_num)

@app.route("/", methods=["POST"])
def hook():
	message = str(dict(request.values)["Body"])
	if message == start_keyword:
			text("process started")
			daily_funcs()
			event_loop()
	else:
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
			alarm()
		elif message == "temp":
			temp()
		elif message == "spam":
			spam(args)
		elif message == "weather":
			weather()
		elif message == "quote":
			quote()
		elif message == "school":
			school()
		elif message == "scan":
			scan(args)
		elif message == "bday":
			bday()
		elif message == "today":
			today()
		elif message == "desc":
			desc()
		elif message == "commands":
			commands()
		elif message == "clean":
			clean()
		else:
			text("That command does not exist.\nTo see a list of all commands, text \"commands\".")
	return "200"


def kill():
	os.abort()


def text(body):
	message = client.messages.create(body=body, from_=bot_num, to=my_num)


def rn(target="%H:%M"):
	now = datetime.now(pytz.timezone("America/New_York"))
	return now.strftime(target)


def log_command(name):
	with open("text_files/command_list", "a") as command_file:
		command_file.write(f"{name}\n")
	with open("text_files/cancel") as cancel_file:
		cancels = cancel_file.readlines()
	return(name in cancels)


def days_until(target, start=None):
	if log_command("days_until"):
		return
	target = target.split("/")
	target = date(year=int(target[2]), month=int(target[0]), day=int(target[1]))
	if start == None:
		start = date.today()
	else:
		start = start.split("/")
		start = date(year=int(start[2]), month=int(start[0]), day=int(start[1]))
	difference = target - start
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
		text(f"Your alarm is now {alarm_state}")


def temp():
	if log_command("temp"):
		return
	temp = get_weather("temp")
	text(f"{temp}°")


def spam(message):
	if log_command("spam"):
		return
	for i in range(5):
		text(message)
		time.sleep(2)


def weather():
	if log_command("weather"):
		return
	formatted = formatted_weather()
	text(formatted)


def quote():
	if log_command("quote"):
		return
	text(get_quote())


def school():
	if log_command("school"):
		return
	left = int(days_until("09/15/2023").days)
	total = int(days_until("09/15/2023", "06/15/2023").days)
	message = f"Summer completed - {round((1-(left/total))*100, 1)}%\n"
	message += f"Days till I move out - {left}"
	text(message)


def scan(keyword):
	if log_command("scan"):
		return
	text(get_quote(keyword[0]))


def bday():
	if log_command("bday"):
		return
	bday_page = requests.get("https://www.brainyquote.com/")
	bday_soup = BeautifulSoup(bday_page.content, "html.parser").get_text()
	bdays = re.findall("- .+", bday_soup)[1:6]
	if len(bdays) != 5:
		error_report("bday")
		return
	message = ""
	message += "Famous People Born Today:\n\n"
	for i in bdays:
		message += str(i[2:])+"\n"
	text(message)


def today():
	if log_command("today"):
		return
	day_num = int(rn("%d"))
	suffix = num_suffix(int(rn("%d")[1]))
	message = rn(f"Today is %A, %b {day_num}{suffix}") + "\n"
	if during_school("day"):
		letr_day = letter_day()
		if letr_day != "error":
			if letr_day in "AEF":
				message += f"It is an {letr_day} day"
			else:
				message += f"It is a {letr_day} day"
	text(message)


def desc():
	if log_command("desc"):
		return
	message = '''I am Evan's personal bot.
If I am going crazy and you need to terminate me, text "kill".
If you would like to see my commands, text "commands".
I will pass all suggestions along to my developer.
Have an amazing day :)
	'''
	text(message)


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
	text(message1)
	text(message2)


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
			text("error in alarm file")
			error_report("alarm_file")
	with open("text_files/special_days") as special_file:
		special_days = special_file.readlines()
	upcoming_days = []
	for i in special_days:
		yr = int(i[:2])
		month = int(i[3:5])
		day = int(i[6:8])
		if (month > int(rn("%m")) and yr == int(rn("%y"))) or yr > int(rn("%y")):
			upcoming_days.append(i)
			continue
		if month == int(rn("%m")) and yr == int(rn("%y")):
			if day >= int(rn("%d")):
				upcoming_days.append(i)
	upcoming_days.sort()
	with open("text_files/special_days", "w") as special_file:
		for i in (upcoming_days):
			special_file.write(i)
	with open("text_files/raw_lunches") as raw_lunches:
		lunches = list(raw_lunches.readlines())
	month = rn("%B").lower()
	month_index = len(lunches)
	for i in range(len(lunches)):
		if month in lunches[i].lower():
			month_index = i
			break
	lunches = lunches[month_index:]
	with open("text_files/raw_lunches", "w") as raw_lunches:
		raw_lunches.writelines(lunches)
	text("All Clean!")


def during_school(start="07:21", end="14:12"):
	if rn("%a") in "SunSat":
		return False
	day_type = get_day_type()
	if day_type =="off":
		return False
	elif day_type=="early":
		end="12:12"
	elif day_type=="hrearly":
			end = "13:12"
	elif day_type=="2hrdelay":
		start="09:21"
	if start =="day":
		return True
	try:
		start = int(start.split(":")[0])*60+int(start.split(":")[1])
		end = int(end.split(":")[0])*60+int(end.split(":")[1])-start
		now = int(rn("%H"))*60+int(rn("%H"))-start
	except:
		error_report("during_school")
		return
	return(0 <= now<=end)


def letter_day():
	try:
		letr_page = requests.get(
			"https://nphs.npenn.org/our_school/nphs_information/daily_announcements")
		letr_soup = BeautifulSoup(letr_page.content, "html.parser").get_text()
		letr_day = re.search("[ABCDEF] Day", letr_soup).group()[0]
		if letr_day not in "ABCDEF":
			letr_day = 1/0
		uncancel("letter_day")
	except:
		error_report("letter_day")
		return "error"
	return(letr_day)


def schedule(day_type, letr_day):
	if int(rn("%S")) > 15:
		return
	day_index = 0
	if day_type =="early":
			day_index = 1
	elif day_type=="hr_early":
		day_index=2
	elif day_type=="2hr_delay":
			day_index = 3
	found_time = False
	with open("text_files/alarm") as alarm_file:
		alarm_on = bool(str(alarm_file.readline()))
	if alarm_on:
		try:
			response = my_schedule[rn()]
			found_time = True
		except:
			pass
		if during_school("day"):
			for i in school_schedule.keys():
				target = i.split("/")[day_index]
				if target == "no":
					continue
				elif rn() == target:
					response = school_schedule[i]
					found_time = True
	if not found_time:
		return
	elif type_checker(response, "str"):
		return response
	else:
		return send_cycle(response, letr_day)


def send_cycle(response, letr_day):
	if response[letr_day] != "FOOD":
		return response[letr_day]
	with open("text_files/lunches") as lunch_file:
		lunches = lunch_file.readlines()
	todays_lunch = [i for i in lunches]
	for i, food in enumerate(todays_lunch):
		food = food.lower()
		good, chicken_patty = False,True
		if food.startswith(rn("%b")):
			if rn("%d") == int(food.split(" ")[1]):
				good = True
			else:
				break
		for bad in no_eat:
			if bad not in food and good:
				todays_lunch[i] = food
				chicken_patty = False
	message = ["Today you will be eating:"]
	if chicken_patty:
		message.append("Chicken Patty")
	else:
		for item in todays_lunch:
			message.append(f"\t{item.capitalize()}")
	return message


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
	weather_page = requests.get(
		"https://forecast.weather.gov/MapClick.php?lat=40.2549&lon=-75.2429#.YXWhSOvMK02")
	weather_soup = BeautifulSoup(weather_page.content, "html.parser")
	if "Not a current observation" in str(weather_soup):
		error_report("weather")
		return "error"
	full = data == "full"
	if data == "conditions" or full:
		conditions = re.search("\">.+</p", str(weather_soup)).group()[2:-3]
	weather_soup = str(weather_soup.get_text())
	if data == "temp" or full:
		try:
			temp = int(re.search("Wind Chill*\d+°F", weather_soup).group()[10:-2])
		except:
			temp = int(np.round(float(re.search("\d+°F", weather_soup).group()[:-2]),0))
	if data == "humidity" or full:
		humidity = int(re.search("\d+%", weather_soup).group()[:-1])
	if data == "wind_speed" or full:
		wind_speed = int(re.search("\d+\smph", weather_soup).group()[:-4])
		if ("Calm" in weather_soup) and (" Calm" not in weather_soup):
			wind_speed = 0
	if data == "dewpoint" or full:
		dewpoint = int(re.search("Dewpoint\s\d+°F", weather_soup).group()[9:-2])
	if data == "vis" or full:
		vis = re.search("Visibility\n.+", weather_soup).group().replace("Visibility\n","")
	if data == "conditions":
		return conditions
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
	weather_data = {"conditions":conditions,"temp":temp,"humidity":humidity,
								"wind_speed": wind_speed, "dewpoint":dewpoint,"vis":vis}
	return weather_data


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
	message = ""
	message += f"Temperature - {temp}°\n"
	message += f"Conditions - {conditions}\n"
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
	message += f"Visibility - {weather['vis'].replace('10.00', '10')}"
	return message


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


def get_quote(scan=False):
	with open("text_files/used_quotes") as used_quotes_file:
		used_quotes = (used_quotes_file.readlines())
	with open("text_files/quotes") as quotes_file:
		quote_list = list(set(quotes_file.readlines()))
	if "" in quote_list:
		quote_list.remove("")
	if not scan:
		quote = quote_list[0]
	else:
		keyword_quotes = [i for i in quote_list if scan in i]
		message = ""
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


def set_day_type():
	if rn("%a") in "SatSun":
		with open("text_files/day_type", "w") as day_type_file:
			day_type_file.write("off")
	with open("text_files/special_days") as special_day_file:
		special_days = special_day_file.readlines()
	for i in special_days:
		if rn("%y/%m/%d") == i.split(":")[0]:
			with open("text_files/day_type", "w") as day_type:
				day_type.write(i.split(":")[1])
			return
	with open("text_files/day_type", "w") as day_type:
		day_type.write("norm")


def get_day_type():
	with open("text_files/day_type") as day_type_file:
		day_type = day_type_file.readline()
	if day_type != "":
		day_type = day_type.split("\n")[0]
	else:
		set_day_type()
		with open("text_files/day_type") as day_type_file:
			day_type = day_type_file.readline()
	return day_type


def daily_funcs():
	os.remove("text_files/cancel")
	open("text_files/cancel", "x")
	set_day_type()
	setup_lunches()


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


def type_checker(var, assumed_type=None):
	if assumed_type == None:
		return(str(type(var))[8:-2])
	return assumed_type in str(type(var))


def setup_lunches():
	with open("text_files/raw_lunches") as lunch_file:
		raw_lunches = lunch_file.readlines()
	days = []
	day_num = -1
	food = False
	for item in raw_lunches:  # splits by days
		item = item.replace("\n", "").lower()
		if item.split(" ")[0] in months:
			item = item.split(" ")
			days.append(f"{item[0]}/{item[1]}:")
			food = True
			day_num += 1
		elif food:
			days[day_num] += item
			food = False
	days = list(set(days))
	for i, school_day in enumerate(days):  # filters food items
		day = school_day.split(":")[0]+":"
		food = school_day.split(":")[1]
		good = True
		for bad in no_eat:
			if bad in food:
				good = False
		if good:
			day += food
		days[i] = day
	for i, menu_item in enumerate(days):  # final formatting and organizing with days
		day = menu_item.split(":")[0]
		food = menu_item.split(":")[1]
		if " with" in food:
			food = food.split(" with")[0]
		if " on" in food:
			food = food.split(" on")[0]
		if " and" in food:
			food = food.split(" and")[0]
		if int(day.split("/")[1]) < 10:
			day = day.replace("/", "/0")
		days[i] = f"{day}:{food}"
		days[i] = days[i].replace("wg", "").replace(":,", ":").replace("  ", " ")
		if food == "":
			days[i] += "Chicken Patty"
		days[i] += "\n"
	month = rn("%B").lower()
	menu = []
	for i, day in enumerate(days):
		good = True
		for x in ["dismissal", "school", "2021","2022"]:
			if x in day:
				good = False
		day = day.split(":")[0]
		if months.index(day.split("/")[0]) < months.index(month):
			continue
		elif int(day.split("/")[1]) < int(rn("%d")) and day.split("/")[0]==month:
			continue
		elif good:
			final = days[i].split(":")
			final[1] = final[1].title().replace("Bbq", "BBQ").replace("Np","NP")
			menu.append(":".join(final))
	menu.sort()
	with open("text_files/lunches", "w") as lunch_file:
		lunch_file.writelines(menu)


def event_loop():
	event_id = random.randint(0, 10000000000)
	with open("text_files/event_id", "w") as event_id_file:
		event_id_file.write(str(event_id))
	while True:
		if int(rn("%M")) % 5 == 0:
			with open("text_files/event_id") as event_id_file:
				if int(event_id_file.readline()) != event_id:
					print("duplicate process detected, aborting...")
					break
		day_type = get_day_type()
		letr_day = letter_day()
		response = schedule(day_type, letr_day)
		if type_checker(response, "list"):
			for i in response:
				text(i)
				time.sleep(2)
			time.sleep(20)
		elif type_checker(response,"str") and response != "error":
			text(response)
			time.sleep(20)
		if(rn() == "08:00" and during_school("day")) or (rn() == "10:30"and not during_school("day")):
			if log_command("morning"):
				time.sleep(60)
			else:
				message = "Good Morning!\n"
				day_num = int(rn("%d"))
				suffix = num_suffix(int(rn("%d")[1]))
				message += f"Today is{rn(f'%A, %B {day_num}{suffix}')}\n"
				if during_school("day") and letr_day != "error":
					message += f"Letter Day - {letr_day}\n"
				text(message)
				with open("text_files/errors") as errors:
					error_list = list(errors.readlines())
					if len(error_list) > 100000:
						text("OVER 100,000 ERRORS, FIX IMMEDIATELY!")
					elif len(error_list) > 10000:
						text("Over 10,000 errors, fix it soon.")
					elif len(error_list) > 1000:
						text("Over 1,000 erros, check it out sometime soon.")
				time.sleep(50)
		if (rn() == "06:40" and during_school("day")) or (rn() == "11:00" and not during_school("day")):
			if log_command("morning quote"):
				time.sleep(1)
			else:
				text(get_quote())
				time.sleep(50)
		elif rn("%H") in "0103": # daily operations
			daily_funcs()
		time.sleep(5)


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=port, debug=True)
