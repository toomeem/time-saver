import os
from dotenv import load_dotenv
import requests
import json

load_dotenv()

api_key = os.getenv("TELEGRAM_API_KEY")
url = f"https://api.telegram.org/bot{api_key}/"

