import json
import threading
import time

from main import (check_brentford_file, check_error_file, check_quote_file,
                  check_weight_file, clear_file, end_workout,
                  get_day_exercises, get_quote, get_response, is_first_set,
                  log, log_set, message_user, morning_message, rn,
                  set_in_conversation, update_spotify_data, remove_job, clean)

bro_split = ["Legs", "Chest + Shoulders", "Arms", "Back + Abs"]
ppl = ["Legs", "Pull", "Push"]
workout_splits = {
	"bro_split": bro_split,
	"ppl": ppl
}
all_exercises = list(json.load(open("text_files/exercises.json")))

# def clean(updates=True):
# 	if log("clean"):
# 		return
# 	if updates:
# 		threading.Thread(target=update_spotify_data).start()
# 	clear_file("text_files/cancel")
# 	check_quote_file()
# 	check_brentford_file()
# 	check_weight_file()
# 	check_error_file()

def event_loop_start():
	threading.Thread(target=clean).start()
	set_in_conversation(False)
	end_workout(True)

def workout_loop(params):
	wait_between_sets = 60 * 3
	quit_workout = False
	while not quit_workout:
		print("looping")
		raw_todays_exercises = get_day_exercises(all_exercises)
		todays_exercises = []
		for i in raw_todays_exercises:
			todays_exercises.append(f'''{i["num"]}: {i["name"]}''')
		todays_exercises ="\n".join(todays_exercises)
		exercise_list = "Pick an exercise(0 to end the workout)\n\n"+todays_exercises
		exercise_num = get_response(exercise_list, wait_time=900)
		print("got response")
		if not exercise_num:
			clear_file("text_files/current_workout.json")
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

def check_for_jobs():
	with open("text_files/jobs.json") as f:
		jobs = list(json.load(f))
	return jobs

def event_loop():
	event_loop_start()
	while True:
		jobs = check_for_jobs()
		if jobs:
			for job in jobs:
				if job["name"] == "start_workout":
					threading.Thread(target=workout_loop).start()
				remove_job(job["name"])
		if rn() == "08:30" and log("morning"):
			time.sleep(60)
		elif rn() == "08:30":
			message_user(morning_message())
			time.sleep(60)
		elif rn() == "11:00" and log("morning quote"):
			time.sleep(60)
		elif rn() == "11:00":
			message_user("Here's today's quote:")
			time.sleep(1)
			message_user(get_quote())
			time.sleep(60)
		elif rn("%M") == "00":
			print(f"{rn()}:Cleaning...")
			clean()
			time.sleep(55)
		time.sleep(3)

print("\nRunning...")
event_loop()
