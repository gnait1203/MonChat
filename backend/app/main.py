"""
FastAPI 애플리케이션 엔트리 포인트
- CORS 설정으로 Streamlit 프론트엔드에서의 접근을 허용한다.
- 헬스체크/QA 라우터를 등록한다.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .settings import settings
from .routers import health, qa
from .routers import llm as llm_router

# 애플리케이션 인스턴스 생성
app = FastAPI(title=settings.APP_NAME)

# CORS 설정: 프론트엔드 오리진에서의 호출 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(health.router, prefix="/health", tags=["health"]) 
app.include_router(qa.router, prefix="/qa", tags=["qa"])
app.include_router(llm_router.router, prefix="/llm", tags=["llm"])

@app.get("/")
def root():
    """루트 엔드포인트: 앱/환경 정보를 반환"""
    return {"app": settings.APP_NAME, "env": settings.ENV}
