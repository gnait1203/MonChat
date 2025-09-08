"""
APScheduler 기반 배치 스케줄러
- 환경변수로 스케줄 활성화 여부 및 크론식을 제어한다.
- 비활성화 시 단발 실행(run_etl)로 동작한다.
"""

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.app.settings import settings
from .pipeline import run_etl


def main():
    """스케줄러 엔트리포인트"""
    sched = BlockingScheduler(timezone="Asia/Seoul")
    if settings.SCHEDULER_ENABLED:
        sched.add_job(run_etl, CronTrigger.from_crontab(settings.SCHEDULER_CRON))
        sched.start()
    else:
        # 스케줄 비활성화 시 단일 실행
        run_etl()

if __name__ == "__main__":
    main()
