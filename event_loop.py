import time

from main import *


def on_start():
	threading.Thread(target=clean).start()
	set_in_conversation(False)
	end_workout(True)


def event_loop():
	on_start()
	while True:
		if rn() == "08:30" and log_command("morning"):
			time.sleep(60)
		elif rn() == "08:30":
			message_user(morning_message())
			time.sleep(60)
		elif rn() == "11:00" and log_command("morning quote"):
			time.sleep(60)
		elif rn() == "11:00":
			message_user(f"Here's today's quote:")
			time.sleep(1)
			message_user(get_quote())
			time.sleep(60)
		elif rn("%M") == "00":
			clean()
		time.sleep(5)

event_loop()
