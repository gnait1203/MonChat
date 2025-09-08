"""
pgvector(PostgreSQL) 연결 및 유사도 검색 유틸리티
- 환경변수는 `backend.app.settings.Settings`에서 로드됨
- 이 모듈은 DB 연결, 스키마 생성, 벡터 유사도 검색 기능을 제공
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from ..settings import settings


def get_pg_connection():
    """PostgreSQL(pgvector) 연결 생성

    환경변수로부터 접속 정보를 읽어 연결을 생성한다.
    반환된 커넥션은 context manager(with)와 함께 사용하는 것을 권장한다.
    """
    conn = psycopg2.connect(
        host=settings.VECTORDB_HOST,
        port=settings.VECTORDB_PORT,
        dbname=settings.VECTORDB_DB,
        user=settings.VECTORDB_USER,
        password=settings.VECTORDB_PASSWORD,
        cursor_factory=RealDictCursor,
        sslmode=settings.VECTORDB_SSLMODE,
    )
    return conn


def ensure_schema():
    """pgvector 확장/테이블/인덱스 생성 보장

    - vector 확장이 없으면 생성
    - `documents` 테이블이 없으면 생성 (임베딩 벡터 컬럼 포함)
    - 벡터 검색 성능을 위한 ivfflat 인덱스 생성(없으면)
    """
    create_ext = "CREATE EXTENSION IF NOT EXISTS vector;"
    create_table = f"""
    CREATE TABLE IF NOT EXISTS documents (
        id SERIAL PRIMARY KEY,
        source TEXT,
        content TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        embedding vector({settings.EMBEDDING_DIM})
    );
    """
    # cosine 유사도 기반 인덱스. 검색은 <-> 연산자를 사용
    create_index = "CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents USING ivfflat (embedding vector_cosine_ops);"

    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_ext)
            cur.execute(create_table)
            cur.execute(create_index)
        conn.commit()


def search_similar(query_vec, top_k=5):
    """질의 벡터에 대한 유사 문서 검색

    매칭 점수(score)는 1 - cosine_distance 로 계산하여 1에 가까울수록 유사함을 의미한다.
    - 정렬에는 `<->`(distance) 사용
    - 점수 계산에는 `<=>`(cosine distance) 사용 후 1 - distance 변환
    """
    sql = "SELECT id, source, content, 1 - (embedding <=> %s::vector) AS score FROM documents ORDER BY embedding <-> %s::vector LIMIT %s;"
    params = (query_vec, query_vec, top_k)
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return rows
