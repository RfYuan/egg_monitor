import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.database import init_db
from src.scheduler.jobs import start_scheduler
from src.utils.logger import log
from config.settings import settings

if __name__ == "__main__":
    log.info("Starting Egg Futures Monitor...")
    settings.ensure_dirs()
    init_db()
    log.info("Database initialized.")
    
    try:
        log.info("Starting scheduler...")
        start_scheduler()
    except (KeyboardInterrupt, SystemExit):
        log.info("Monitor stopped.")
