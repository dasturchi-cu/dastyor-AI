# Quick script to clear any webhooks before starting polling
import requests
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if BOT_TOKEN:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True"
    response = requests.get(url)
    print(f"Webhook cleared: {response.json()}")
else:
    print("No BOT_TOKEN found")
