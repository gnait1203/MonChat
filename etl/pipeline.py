"""
ETL 파이프라인
- 최근 N일(기본 7일) 범위의 데이터 소스(Oracle, 로그)를 수집
- 텍스트 정제/임베딩 후 pgvector DB에 적재
"""

import os
from datetime import datetime, timedelta
from backend.app.settings import settings
from backend.app.embeddings import embed_texts
from backend.app.db.vector import ensure_schema, get_pg_connection
from backend.app.db.oracle import fetch_table_rows_by_date


def date_range(days: int):
    """오늘을 기준으로 최근 N일의 날짜 문자열(YYYYMMDD) 생성"""
    end = datetime.now().date()
    for i in range(days):
        yield (end - timedelta(days=i)).strftime("%Y%m%d")


def collect_oracle_rows(date_str: str):
    """Oracle(RAC/SINGLE)에서 해당 일자의 history/event_history 데이터를 수집"""
    if not settings.ORACLE_ENABLED:
        return []
    rows = []
    # 성능/오류 테이블 프리픽스 정의
    rows += fetch_table_rows_by_date("history", date_str)
    rows += fetch_table_rows_by_date("event_history", date_str)
    return rows


def collect_logs(date_str: str, base_dir: str, prefix: str):
    """로그 디렉토리에서 해당 일자 파일을 읽어 라인 단위 텍스트 리스트 반환"""
    path = os.path.join(base_dir, f"{prefix}_{date_str}")
    if not os.path.exists(path):
        return []
    lines = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(line)
    return lines


def run_etl():
    """ETL 실행: 스키마 보장 → 수집 → 임베딩 → 적재"""
    ensure_schema()

    for d in date_range(settings.ETL_DAYS):
        texts = []
        # Oracle 수집(옵션; RAC 설정은 oracle 유틸에서 자동 적용)
        texts += collect_oracle_rows(d)
        # WAS 로그 수집(옵션)
        if settings.LOG_WAS_ENABLED:
            texts += collect_logs(d, settings.WAS_LOG_DIR, "middleware")
        # DB 로그 수집(옵션)
        if settings.LOG_DB_ENABLED:
            texts += collect_logs(d, settings.DB_LOG_DIR, "db")

        if not texts:
            continue

        # 임베딩 변환
        vectors = embed_texts(texts)

        # pgvector에 적재
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                for text, vec in zip(texts, vectors):
                    cur.execute(
                        "INSERT INTO documents (source, content, embedding) VALUES (%s, %s, %s)",
                        (d, text, vec),
                    )
            conn.commit()

if __name__ == "__main__":
    run_etl()
