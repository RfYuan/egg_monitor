from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from src.collectors.futures_collector import collect_and_save_latest, SUPPORTED_SYMBOLS
from src.collectors.spot_collector import collect_and_save_spot
from src.collectors.cnfowl_spider import collect_cnfowl_spot
from src.collectors.futures_receipt_collector import collect_and_save_receipt
from src.collectors.futures_holding_collector import collect_and_save_holding
from src.analysis.rule_engine import run_all_checks
from src.notification.daily_report import job_send_daily_report
from src.notification.daily_summary import send_daily_summary
from src.utils.backup import run_backup
from src.utils.black_swan_monitor import check_black_swan
from src.utils.logger import log

def job_collect_futures():
    log.info("Running futures collection job...")
    collect_and_save_latest(SUPPORTED_SYMBOLS)
    run_all_checks()

def job_collect_spot():
    log.info("Running spot price collection job...")
    # 优先使用养殖网爬虫采集现货价格
    log.info("[Spot] 尝试使用养殖网爬虫采集现货价格...")
    success = collect_cnfowl_spot(use_local=False)
    if success:
        log.info("[Spot] 养殖网爬虫采集成功")
    else:
        # 养殖网失败，使用备用数据源
        log.warning("[Spot] 养殖网爬虫采集失败，使用备用数据源")
        collect_and_save_spot()

def job_collect_receipt():
    log.info("Running DCE receipt collection job...")
    collect_and_save_receipt()

def job_collect_holding():
    log.info("Running DCE holding collection job...")
    collect_and_save_holding("JD2609")

def job_daily_summary():
    log.info("Running daily summary push job...")
    send_daily_summary()

def job_black_swan():
    log.info("Running black swan monitoring job...")
    check_black_swan()

def job_backup():
    log.info("Running weekly backup job...")
    run_backup()

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

    # 每日数据汇总推送（盘后完整数据）
    scheduler.add_job(
        job_daily_summary,
        trigger=CronTrigger(hour=16, minute=30),
        id="daily_summary"
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

    # 黑天鹅关键词监测（每日早9点）
    scheduler.add_job(
        job_black_swan,
        trigger=CronTrigger(hour=9, minute=0),
        id="black_swan_monitor"
    )

    # 数据备份（每周日0点）
    scheduler.add_job(
        job_backup,
        trigger=CronTrigger(day_of_week="sun", hour=0, minute=0),
        id="weekly_backup"
    )

    log.info("Scheduler started. Waiting for jobs...")
    log.info("Scheduled jobs:")
    log.info("  - futures_morning: 09:30")
    log.info("  - futures_afternoon: 15:40")
    log.info("  - daily_report: 16:00")
    log.info("  - daily_summary: 16:30")
    log.info("  - spot_daily: 10:00")
    log.info("  - dce_receipt: 16:30 (每日)")
    log.info("  - dce_holding: 每周五 17:00")
    log.info("  - black_swan_monitor: 每日 09:00")
    log.info("  - weekly_backup: 每周日 00:00")
    scheduler.start()
