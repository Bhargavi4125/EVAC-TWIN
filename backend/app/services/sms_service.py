import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.textbee.dev/api/v1/gateway/send-sms"

def send_sms(message):
    api_key = os.getenv("TEXTBEE_API_KEY")
    phones = os.getenv("ALERT_PHONES", "")

    recipients = [
        phone.strip()
        for phone in phones.split(",")
        if phone.strip()
    ]

    if not api_key or not recipients:
        print("Textbee configuration missing")
        return False

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    data = {
        "recipients": recipients,
        "message": message
    }

    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json=data,
            timeout=20
        )

        print("Textbee response:", response.status_code, response.text)
        response.raise_for_status()
        return True

    except requests.RequestException as e:
        print("SMS Error:", e)
        return False