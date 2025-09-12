"""
ETL 파이프라인
- 최근 N일(기본 7일) 범위의 데이터 소스(Oracle, 로그)를 수집
- 텍스트 정제/임베딩 후 pgvector DB에 적재
"""

import os
import sys
from pathlib import Path

# 스크립트 직접 실행 시 루트 경로를 PYTHONPATH에 추가하여 절대 임포트 지원
_THIS_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _THIS_DIR.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))
from datetime import datetime, timedelta
import csv
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
    """ETL 실행: 스키마 보장 → 수집 → 임베딩 → 적재

    - MOCK_DB_ENABLED일 경우 파일 기반(history_/event_history_) 텍스트를 로드한다.
    - VECTORDB_ENABLED가 False이면 로컬 파일에 적재 결과를 저장한다(mock 출력).
    """
    print(
        f"[ETL] start | ETL_DAYS={settings.ETL_DAYS} MOCK_DB_ENABLED={settings.MOCK_DB_ENABLED} "
        f"VECTORDB_ENABLED={settings.VECTORDB_ENABLED} MOCK_DB_DIR={settings.MOCK_DB_DIR}"
    )
    def collect_mock_db_rows(date_str: str) -> list[str]:
        base = Path(settings.MOCK_DB_DIR)
        rows: list[str] = []
        # history CSV (1분 단위)
        hist_csv = base / f"history_{date_str}.csv"
        if hist_csv.exists():
            with hist_csv.open("r", encoding="utf-8", errors="ignore", newline="") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    parts = [
                        "type=history",
                        f"ts={r.get('YYYYMMDDHHmmss','')}",
                        f"Hostname={r.get('Hostname','')}",
                        f"IP={r.get('IP','')}",
                        f"CPU_Usage={r.get('CPU_Usage','')}",
                        f"Memory_Usage={r.get('Memory_Usage','')}",
                        f"Swap_Usage={r.get('Swap_Usage','')}",
                        f"Filesystem_Usage={r.get('Filesystem_Usage','')}",
                        f"Ping_Status={r.get('Ping_Status','')}",
                    ]
                    rows.append(" ".join(parts))
        # event_history CSV (1분 단위)
        evt_csv = base / f"event_history_{date_str}.csv"
        if evt_csv.exists():
            with evt_csv.open("r", encoding="utf-8", errors="ignore", newline="") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    parts = [
                        "type=event_history",
                        f"ts={r.get('YYYYMMDDHHmmss','')}",
                        f"Hostname={r.get('Hostname','')}",
                        f"IP={r.get('IP','')}",
                        f"Severity={r.get('Severity','')}",
                        f"Event_Message={r.get('Event_Message','')}",
                    ]
                    rows.append(" ".join(parts))
        # WAS 이벤트 CSV (1분 단위)
        was_csv = base / f"was_event_{date_str}.csv"
        if was_csv.exists():
            with was_csv.open("r", encoding="utf-8", errors="ignore", newline="") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    parts = [
                        "type=WAS_Event",
                        f"ts={r.get('YYYYMMDDHHmmss','')}",
                        f"Hostname={r.get('Hostname','')}",
                        f"Event_Message={r.get('Event_Message','')}",
                    ]
                    rows.append(" ".join(parts))
        # DB 이벤트 CSV (1분 단위)
        db_csv = base / f"db_event_{date_str}.csv"
        if db_csv.exists():
            with db_csv.open("r", encoding="utf-8", errors="ignore", newline="") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    parts = [
                        "type=DB_Event",
                        f"ts={r.get('YYYYMMDDHHmmss','')}",
                        f"Hostname={r.get('Hostname','')}",
                        f"Event_Message={r.get('Event_Message','')}",
                    ]
                    rows.append(" ".join(parts))
        return rows

    if settings.VECTORDB_ENABLED:
        print("[ETL] ensuring pgvector schema ...")
        ensure_schema()

    for d in date_range(settings.ETL_DAYS):
        texts = []
        # Oracle/Mock DB 수집
        if settings.MOCK_DB_ENABLED:
            texts += collect_mock_db_rows(d)
        else:
            texts += collect_oracle_rows(d)
        # WAS 로그 수집(옵션)
        if settings.LOG_WAS_ENABLED:
            texts += collect_logs(d, settings.WAS_LOG_DIR, "middleware")
        # DB 로그 수집(옵션)
        if settings.LOG_DB_ENABLED:
            texts += collect_logs(d, settings.DB_LOG_DIR, "db")

        if not texts:
            print(f"[ETL] {d} | no texts found, skip")
            continue
        print(f"[ETL] {d} | collected {len(texts)} texts")

        if settings.VECTORDB_ENABLED:
            # 임베딩 변환
            print(f"[ETL] {d} | embedding {len(texts)} texts ...")
            vectors = embed_texts(texts)
            # pgvector는 벡터 문자열 형식('[v1, v2, ...]') 또는 리스트 바인딩을 허용한다.
            # psycopg2 기본 커서에서는 명시적 캐스팅이 안전하다.
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    for text, vec in zip(texts, vectors):
                        # 벡터를 공백 구분 문자열로 변환하고 vector 캐스팅
                        vec_str = "[" + ",".join(f"{float(x):.6f}" for x in vec) + "]"
                        cur.execute(
                            "INSERT INTO documents (source, content, embedding) VALUES (%s, %s, %s::vector)",
                            (d, text, vec_str),
                        )
                conn.commit()
            print(f"[ETL] {d} | inserted {len(texts)} rows")
        else:
            # 로컬 파일로 적재 결과를 기록 (모의 실행)
            out_dir = Path(settings.MOCK_DB_DIR) / "output"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f"documents_{d}.jsonl"
            with out_file.open("w", encoding="utf-8") as f:
                for text in texts:
                    # 벡터는 길어지므로 저장하지 않고 길이만 기록
                    rec = {"source": d, "content": text, "embedding_dim": 0}
                    f.write(str(rec) + "\n")
            print(f"[ETL] {d} | wrote {len(texts)} rows to {out_file}")

if __name__ == "__main__":
    run_etl()
