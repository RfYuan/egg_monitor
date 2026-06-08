from loguru import logger
import sys
from config.settings import settings

def setup_logger():
    settings.ensure_dirs()
    
    logger.remove()
    
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    logger.add(
        settings.LOG_DIR / "app_{time:YYYY-MM-DD}.log",
        level=settings.LOG_LEVEL,
        rotation="00:00",
        retention="30 days",
        compression="zip"
    )
    
    logger.add(
        settings.LOG_DIR / "error_{time:YYYY-MM-DD}.log",
        level="ERROR",
        rotation="00:00",
        retention="30 days",
        compression="zip"
    )
    
    return logger

log = setup_logger()
