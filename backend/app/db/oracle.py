"""
Oracle 연결 유틸리티 (싱글 인스턴스 + RAC 지원)
- python-oracledb(thin) 사용: 별도 클라이언트 없이 동작, Windows 빌드 도구 불요
- RAC의 경우 ADDRESS_LIST 기반 DSN을 생성하여 로드밸런싱/페일오버를 지원
"""

import oracledb
from typing import Optional
from ..settings import settings


def _build_single_dsn() -> str:
    """싱글 인스턴스용 DSN 문자열 생성"""
    return oracledb.makedsn(
        host=settings.ORACLE_HOST,
        port=settings.ORACLE_PORT,
        service_name=settings.ORACLE_SERVICE_NAME,
    )


def _build_rac_dsn() -> str:
    """RAC용 DSN 문자열 생성 (ADDRESS_LIST 구성)

    예시 형식:
    (DESCRIPTION=
      (LOAD_BALANCE=on)
      (FAILOVER=on)
      (ADDRESS_LIST=
        (ADDRESS=(PROTOCOL=TCP)(HOST=h1)(PORT=1521))
        (ADDRESS=(PROTOCOL=TCP)(HOST=h2)(PORT=1521))
      )
      (CONNECT_DATA=(SERVICE_NAME=orcl))
    )
    """
    hosts = [h.strip() for h in settings.ORACLE_RAC_HOSTS.split(",") if h.strip()]
    protocol = settings.ORACLE_PROTOCOL
    port = settings.ORACLE_RAC_PORT

    address_list = "".join(
        [f"(ADDRESS=(PROTOCOL={protocol})(HOST={h})(PORT={port}))" for h in hosts]
    )

    description = (
        f"(DESCRIPTION=(LOAD_BALANCE={'on' if settings.ORACLE_LOAD_BALANCE else 'off'})"
        f"(FAILOVER={'on' if settings.ORACLE_FAILOVER else 'off'})"
        f"(ADDRESS_LIST={address_list})"
        f"(CONNECT_DATA=(SERVICE_NAME={settings.ORACLE_SERVICE_NAME})))"
    )
    return description


def get_oracle_connection() -> oracledb.Connection:
    """Oracle 연결 생성 (SINGLE/RAC 모드 모두 지원)

    python-oracledb는 기본 thin 모드로 동작하여 별도의 Instant Client가 필요 없다.
    """
    if settings.ORACLE_MODE.upper() == "RAC":
        dsn = _build_rac_dsn()
    else:
        dsn = _build_single_dsn()

    conn = oracledb.connect(
        user=settings.ORACLE_USER,
        password=settings.ORACLE_PASSWORD,
        dsn=dsn,
        encoding="UTF-8",
        nencoding="UTF-8",
    )
    return conn


def fetch_table_rows_by_date(table_prefix: str, date_str: str) -> list[str]:
    """프리픽스와 날짜로 실제 테이블명을 조합하여 텍스트 리스트로 반환

    - table_prefix: history 또는 event_history
    - date_str: YYYYMMDD
    """
    table_name = f"{table_prefix}_{date_str}"
    sql = f"SELECT * FROM {table_name}"
    rows_text: list[str] = []

    try:
        with get_oracle_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                col_names = [d[0] for d in cur.description]
                for r in cur.fetchall():
                    # 간단히 'col=value' 공백 구분으로 직렬화 (후처리시 파싱 용이)
                    pairs = [f"{c}={v}" for c, v in zip(col_names, r)]
                    rows_text.append(" ".join(pairs))
    except oracledb.DatabaseError:
        # 테이블 미존재 등은 조용히 무시하고 빈 리스트 반환 (필요 시 로깅)
        return []

    return rows_text
