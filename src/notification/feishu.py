import requests
import json
from config.settings import settings
from src.utils.logger import log

def send_feishu_message(title: str, content: str, level: str = "info"):
    if not settings.FEISHU_WEBHOOK_URL:
        log.warning("FEISHU_WEBHOOK_URL not configured, skip sending message")
        return False
    
    color_map = {
        "info": "blue",
        "warning": "orange",
        "danger": "red"
    }
    
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": title
                },
                "template": color_map.get(level, "blue")
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": content
                    }
                }
            ]
        }
    }
    
    try:
        response = requests.post(
            settings.FEISHU_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        if result.get("code") == 0:
            log.info(f"Feishu message sent: {title}")
            return True
        else:
            log.error(f"Feishu message failed: {result}")
            return False
    except Exception as e:
        log.error(f"Failed to send feishu message: {e}")
        return False
