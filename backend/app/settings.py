"""
환경설정 모듈
- pydantic-settings를 사용하여 .env와 환경변수에서 설정 값을 로드한다.
- DB/WAS/로그 경로/포트 등은 모두 환경변수로 변경 가능하도록 구성했다.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pydantic import field_validator


class Settings(BaseSettings):
    """애플리케이션 전역 설정

    .env 파일과 OS 환경변수에서 값을 로드한다. 기본값은 개발 환경 기준으로 지정되어 있다.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # 애플리케이션 공통
    APP_NAME: str = Field(default="MonChat")
    ENV: str = Field(default="dev")
    DEBUG: bool = Field(default=True)
    FRONTEND_ORIGIN: str = Field(default="http://localhost:8501")

    # Vector DB (PostgreSQL + pgvector)
    VECTORDB_ENABLED: bool = Field(default=False)
    VECTORDB_HOST: str = Field(default="localhost")
    VECTORDB_PORT: int = Field(default=5432)
    VECTORDB_DB: str = Field(default="monchat")
    VECTORDB_USER: str = Field(default="monchat")
    VECTORDB_PASSWORD: str = Field(default="monchat")
    VECTORDB_SSLMODE: str = Field(default="disable")
    EMBEDDING_DIM: int = Field(default=384)

    # Oracle (상품처리계)
    ORACLE_ENABLED: bool = Field(default=False)
    # 연결 모드: SINGLE | RAC
    ORACLE_MODE: str = Field(default="SINGLE")
    # 싱글 또는 SCAN 호스트
    ORACLE_HOST: str = Field(default="localhost")
    ORACLE_PORT: int = Field(default=1521)
    ORACLE_SERVICE_NAME: str = Field(default="ORCLCDB")
    ORACLE_USER: str = Field(default="app_user")
    ORACLE_PASSWORD: str = Field(default="app_password")
    # RAC 주소 리스트(콤마 구분) 예: host1,host2,host3
    ORACLE_RAC_HOSTS: str = Field(default="")
    ORACLE_RAC_PORT: int = Field(default=1521)
    ORACLE_PROTOCOL: str = Field(default="TCP")
    # RAC 연결 옵션
    ORACLE_LOAD_BALANCE: bool = Field(default=True)
    ORACLE_FAILOVER: bool = Field(default=True)
    ORACLE_CONNECT_TIMEOUT: int = Field(default=5)  # 초
    ORACLE_RETRY_COUNT: int = Field(default=3)
    ORACLE_RETRY_DELAY: int = Field(default=1)  # 초

    # Mock DB (파일 기반 대체 수집)
    MOCK_DB_ENABLED: bool = Field(default=False)
    MOCK_DB_DIR: str = Field(default="mock_data")

    # 로그 소스 경로/활성화
    LOG_WAS_ENABLED: bool = Field(default=False)
    LOG_DB_ENABLED: bool = Field(default=False)
    WAS_LOG_DIR: str = Field(default="/swlog/was")
    DB_LOG_DIR: str = Field(default="/swlog/db")

    # ETL 및 스케줄러 설정
    ETL_DAYS: int = Field(default=7)
    SCHEDULER_ENABLED: bool = Field(default=False)
    SCHEDULER_CRON: str = Field(default="0 3 * * *")

    # 임베딩 모델 설정
    EMBEDDING_MODEL: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    EMBEDDING_BATCH_SIZE: int = Field(default=16)
    # auto | cpu | cuda
    EMBEDDING_DEVICE: str = Field(default="auto")

    # Hugging Face 설정
    # 개인 토큰(프라이빗 모델 접근 시 사용), 캐시/로컬 모델 디렉터리
    HF_TOKEN: str = Field(default="")
    HF_CACHE_DIR: str = Field(default="")
    HF_LOCAL_MODEL_DIR: str = Field(default="")

    # API 서버 설정
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)

    # 내부 LLM 설정 (Ollama 기반 사내 서버)
    LLM_ENABLED: bool = Field(default=False)
    LLM_BASE_URL: str = Field(default="http://pgaiap09:11434")
    LLM_CHAT_PATH: str = Field(default="/api/chat")
    LLM_DEFAULT_MODEL: str = Field(default="qwen3:8b")
    LLM_TIMEOUT: int = Field(default=120)
    LLM_STREAM: bool = Field(default=False)

    # Streamlit 설정
    STREAMLIT_PORT: int = Field(default=8501)

    # NOTE: 불리언 환경변수 값 앞뒤 공백으로 인한 파싱 실패 방지
    @field_validator(
        "VECTORDB_ENABLED",
        "ORACLE_ENABLED",
        "LOG_WAS_ENABLED",
        "LOG_DB_ENABLED",
        "SCHEDULER_ENABLED",
        "DEBUG",
        "LLM_ENABLED",
        "LLM_STREAM",
        mode="before",
    )
    @classmethod
    def _strip_bool_strings(cls, v):  # type: ignore[override]
        if isinstance(v, str):
            return v.strip()
        return v

    # NOTE: 문자열 기반 경로/토큰의 앞뒤 공백 제거 (HF 계열)
    @field_validator(
        "HF_TOKEN",
        "HF_CACHE_DIR",
        "HF_LOCAL_MODEL_DIR",
        mode="before",
    )
    @classmethod
    def _strip_hf_strings(cls, v):  # type: ignore[override]
        if isinstance(v, str):
            return v.strip()
        return v

settings = Settings()
