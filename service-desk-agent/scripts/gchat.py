import os
import logging
import requests

def send_card(title, subtitle, facts):
    """Sends a Google Chat Card v2 message for business notifications."""
    webhook_url = os.getenv("GCHAT_WEBHOOK_URL")
    if not webhook_url:
        logging.warning("GCHAT_WEBHOOK_URL not set, skipping notification")
        return

    widgets = []
    for key, value in facts.items():
        widgets.append({
            "textParagraph": {
                "text": f"<b>{key}:</b> {value}"
            }
        })

    payload = {
        "cardsV2": [{
            "cardId": "notification_card",
            "card": {
                "header": {
                    "title": title,
                    "subtitle": subtitle,
                    "imageUrl": "https://fonts.gstatic.com/s/i/short-term/release/googlegss/robot/default/24px.svg"
                },
                "sections": [{
                    "widgets": widgets
                }]
            }
        }]
    }

    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
    except Exception as e:
        logging.error(f"Error sending GChat notification: {e}")
