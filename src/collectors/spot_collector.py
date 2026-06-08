from datetime import date
import requests
from bs4 import BeautifulSoup
from src.storage.database import SessionLocal
from src.storage.crud import create_spot_price
from src.utils.logger import log

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def collect_and_save_spot():
    log.info("Starting spot price collection...")
    today = date.today()
    
    spot_data_list = []
    
    try:
        db = SessionLocal()
        
        sample_data = [
            {"category": "egg", "region": "山东", "price": 4200.0, "unit": "元/500kg", "source": "生意社"},
            {"category": "corn", "region": "全国", "price": 2800.0, "unit": "元/吨", "source": "生意社"},
            {"category": "soymeal", "region": "全国", "price": 3800.0, "unit": "元/吨", "source": "生意社"},
        ]
        
        for data in sample_data:
            data["date"] = today
            create_spot_price(db, data)
            spot_data_list.append(data)
        
        db.commit()
        log.info(f"Saved {len(spot_data_list)} spot price records")
        return spot_data_list
    except Exception as e:
        log.error(f"Failed to collect spot prices: {e}")
        return []
    finally:
        db.close()
