from src.notification.feishu import send_feishu_message
from src.storage.crud import create_alert_record
from src.storage.database import SessionLocal
from src.utils.logger import log

def send_notification(title: str, content: str, level: str = "info", rule_id: str = "", data_snapshot: dict = None):
    try:
        send_feishu_message(title, content, level)
        
        db = SessionLocal()
        try:
            create_alert_record(db, {
                "level": level,
                "title": title,
                "content": content,
                "rule_id": rule_id,
                "data_snapshot": data_snapshot,
                "status": "pending"
            })
        finally:
            db.close()
            
        log.info(f"Notification sent: {title}")
        return True
    except Exception as e:
        log.error(f"Failed to send notification: {e}")
        return False
