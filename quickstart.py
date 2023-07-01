import datetime
import os.path
from pprint import pprint
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = ["https://www.googleapis.com/auth/calendar"]
time_zone = "America/New_York"
yr = 2023



def get_creds():
	creds = None
	if os.path.exists('token.json'):
		creds = Credentials.from_authorized_user_file('token.json', SCOPES)
	if not creds or not creds.valid or True:
		if creds and creds.expired and creds.refresh_token and False:
			creds.refresh(Request())
		else:
			flow = InstalledAppFlow.from_client_secrets_file('token.json', SCOPES)
			creds = flow.run_local_server(port=0)
		with open('credentials3.json', 'w') as token:
			token.write(creds.to_json())
	return creds


creds = get_creds()

service = build('calendar', 'v3', credentials=creds)
now = datetime.datetime.utcnow().isoformat() + 'Z'

event = {
	"summary": "Work",
	"location": "Hotline",
	"start": {
		"dateTime": str(datetime.datetime(year=yr, month=6, day=29, hour=16)),
		"timeZone": time_zone
	},
	"end": {
		"dateTime": str(datetime.datetime(year=yr, month=6, day=29, hour=21)),
		"timeZone": time_zone
	}
}

created_event = service.events().insert(calendarId='primary', body=event).execute()
pprint("Event created")
