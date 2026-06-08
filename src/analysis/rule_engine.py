import yaml
from pathlib import Path
from src.storage.database import SessionLocal
from src.storage.crud import get_futures_quotes
from src.notification.notifier import send_notification
from src.utils.logger import log
from src.collectors.futures_collector import SUPPORTED_SYMBOLS

BASE_DIR = Path(__file__).parent.parent.parent
RULES_PATH = BASE_DIR / "config" / "alert_rules.yaml"

def load_rules():
    try:
        with open(RULES_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config.get("rules", [])
    except Exception as e:
        log.error(f"Failed to load rules: {e}")
        return []

def check_price_rule(rule, latest_price):
    condition = rule["condition"]
    rule_type = condition["type"]
    
    if rule_type == "price_below" and latest_price < condition["threshold"]:
        return True
    if rule_type == "price_above" and latest_price > condition["threshold"]:
        return True
    
    return False

def run_all_checks():
    rules = load_rules()
    db = SessionLocal()
    try:
        for symbol in SUPPORTED_SYMBOLS:
            symbol_upper = symbol.upper()
            quotes = get_futures_quotes(db, symbol_upper, limit=1)
            if not quotes:
                log.warning(f"No futures data for {symbol_upper} rule check")
                continue

            latest_quote = quotes[0]
            latest_price = float(latest_quote.close)

            for rule in rules:
                try:
                    condition = rule.get("condition", {})
                    rule_symbol = condition.get("symbol", "").upper()
                    # 规则指定了合约时，只检查对应合约；未指定时对所有合约检查
                    if rule_symbol and rule_symbol != symbol_upper:
                        continue

                    if check_price_rule(rule, latest_price):
                        log.info(f"Rule {rule['id']} triggered for {symbol_upper}!")
                        send_notification(
                            title=rule["name"],
                            content=rule["action"]["message"],
                            level=rule["level"],
                            rule_id=rule["id"],
                            data_snapshot={"symbol": symbol_upper, "price": latest_price}
                        )
                except Exception as e:
                    log.error(f"Failed to check rule {rule['id']}: {e}")
    finally:
        db.close()
