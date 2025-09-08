"""
헬스체크 라우터
- 애플리케이션의 상태를 간단히 확인하기 위한 엔드포인트를 제공한다.
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/ready")
def ready():
    """준비 상태 확인(의존성 초기화 등)"""
    return {"status": "ok"}

@router.get("/live")
def live():
    """생존 상태 확인(프로세스가 살아있는지)"""
    return {"status": "alive"}
