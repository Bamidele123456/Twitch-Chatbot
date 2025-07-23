import requests, json
import os
import sys
import threading
from dotenv import load_dotenv, set_key

CLIENT_ID = ''
CLIENT_SECRET = ''
TOKEN_FILE = "tokens.json"

load_dotenv()
ENV_FILE='.env'

def exit_after_delay(delay_seconds):
    def _exit():
        print(f"⏳ Time's up! Exiting after {delay_seconds} seconds.")
        sys.exit(1)
    timer = threading.Timer(delay_seconds, _exit)
    timer.start()
def load_tokens():
    with open(TOKEN_FILE, "r") as f:
        return json.load(f)

def save_tokens(data):
    with open(TOKEN_FILE, "w") as f:
        json.dump(data, f)

def refresh_token():
    tokens = load_tokens()
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"],
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }

    r = requests.post("https://id.twitch.tv/oauth2/token", data=payload)
    if r.status_code == 200:
        new_tokens = r.json()
        save_tokens(new_tokens)
        set_key(ENV_FILE, "ACCESS_TOKEN", new_tokens["access_token"])
        return new_tokens["access_token"]

    else:
        raise Exception("Token refresh failed")


refresh_token()
