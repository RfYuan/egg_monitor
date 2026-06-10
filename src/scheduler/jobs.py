from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from src.collectors.futures_collector import collect_and_save_latest, SUPPORTED_SYMBOLS
from src.collectors.spot_collector import collect_and_save_spot
from src.collectors.futures_receipt_collector import collect_and_save_receipt
from src.collectors.futures_holding_collector import collect_and_save_holding
from src.analysis.rule_engine import run_all_checks
from src.notification.daily_report import job_send_daily_report
from src.utils.logger import log

def job_collect_futures():
    log.info("Running futures collection job...")
    collect_and_save_latest(SUPPORTED_SYMBOLS)
    run_all_checks()

def job_collect_spot():
    log.info("Running spot price collection job...")
    collect_and_save_spot()

def job_collect_receipt():
    log.info("Running DCE receipt collection job...")
    collect_and_save_receipt()

def job_collect_holding():
    log.info("Running DCE holding collection job...")
    collect_and_save_holding("JD2609")

def start_scheduler():
    scheduler = BlockingScheduler()
    
    # 期货行情采集 + 预警检查（盘前）
    scheduler.add_job(
        job_collect_futures,
        trigger=CronTrigger(hour=9, minute=30),
        id="futures_morning"
    )
    
    # 期货行情采集 + 预警检查（盘后）
    scheduler.add_job(
        job_collect_futures,
        trigger=CronTrigger(hour=15, minute=40),
        id="futures_afternoon"
    )
    
    # 每日数据推送（盘后数据更新后）
    scheduler.add_job(
        job_send_daily_report,
        trigger=CronTrigger(hour=16, minute=0),
        id="daily_report"
    )
    
    # 现货价格采集
    scheduler.add_job(
        job_collect_spot,
        trigger=CronTrigger(hour=10, minute=0),
        id="spot_daily"
    )
    
    # 大商所仓单数据采集（每日16:30，大商所更新后）
    scheduler.add_job(
        job_collect_receipt,
        trigger=CronTrigger(hour=16, minute=30),
        id="dce_receipt"
    )
    
    # 大商所前20持仓数据采集（每周五17:00）
    scheduler.add_job(
        job_collect_holding,
        trigger=CronTrigger(day_of_week="fri", hour=17, minute=0),
        id="dce_holding"
    )
    
    log.info("Scheduler started. Waiting for jobs...")
    log.info("Scheduled jobs:")
    log.info("  - futures_morning: 09:30")
    log.info("  - futures_afternoon: 15:40")
    log.info("  - daily_report: 16:00")
    log.info("  - spot_daily: 10:00")
    log.info("  - dce_receipt: 16:30 (每日)")
    log.info("  - dce_holding: 每周五 17:00")
    scheduler.start()
