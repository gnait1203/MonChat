"""
Q&A 라우터
- 사용자 질문을 받아 임베딩 → VectorDB 유사도 검색 → 결과 반환
- VectorDB 비활성화 시, mock 데이터에서 키워드 기반 간이 검색 폴백
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict
import re
from pathlib import Path

from ..settings import settings


router = APIRouter()


class QARequest(BaseModel):
    """Q&A 요청 페이로드
    - question: 사용자 질문 텍스트
    - top_k: 검색 상위 개수
    """
    question: str
    top_k: int = 5


def _to_vector_literal(vec: List[float]) -> str:
    """pgvector용 벡터 리터럴 문자열로 변환: '[v1,v2,...]'"""
    return "[" + ",".join(f"{float(x):.6f}" for x in vec) + "]"


def _keyword_score(text: str, tokens: List[str]) -> int:
    score = 0
    for t in tokens:
        if not t:
            continue
        # 대소문자 무시 포함 여부 체크
        if re.search(re.escape(t), text, flags=re.IGNORECASE):
            score += 1
    return score


def _mock_search(question: str, top_k: int) -> List[Dict]:
    """VectorDB 미사용 시 간이 키워드 검색
    - mock_data 디렉토리의 최근 파일들에서 라인 단위 텍스트를 수집하여 매칭 개수로 정렬
    """
    base = Path(settings.MOCK_DB_DIR)
    candidates: List[str] = []
    # 지원 파일 패턴들
    patterns = [
        "history_*.csv",
        "event_history_*.csv",
        "was_event_*.csv",
        "db_event_*.csv",
        "history_*.txt",
        "event_history_*.txt",
    ]

    for pat in patterns:
        for p in sorted(base.glob(pat), reverse=True)[:7]:  # 최근 파일 위주로 제한
            try:
                # CSV/텍스트를 통일적으로 라인 기반으로 읽음
                with p.open("r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            candidates.append(line)
            except Exception:
                continue

    # 간단한 토큰화: 공백/구두점 기준 분리 (한글 단어는 공백 단위)
    raw_tokens = re.split(r"\s+|[\,\.;:!\?\(\)\[\]\{\}\-_/]", question)
    tokens = [t for t in raw_tokens if len(t) >= 2]

    scored = [
        {
            "content": txt,
            "score": _keyword_score(txt, tokens),
            "source": "mock",
        }
        for txt in candidates
    ]
    # 점수 0은 제거하고 상위 top_k만 반환
    ranked = [r for r in scored if r["score"] > 0]
    ranked.sort(key=lambda r: r["score"], reverse=True)
    return ranked[:top_k]


@router.post("/")
def query_qa(req: QARequest):
    """질문 처리 엔드포인트

    - VectorDB 사용 시: 질문 임베딩 → 코사인 유사도 top_k 검색
    - 미사용 시: mock 데이터에서 키워드 기반 상위 top_k 라인 반환
    """
    question = req.question.strip()
    top_k = max(1, min(50, req.top_k or 5))

    if not question:
        return {"question": req.question, "answers": [], "top_k": top_k}

    if settings.VECTORDB_ENABLED:
        try:
            # 임베딩 → pgvector 검색
            # 지연 임포트로 무거운 의존성(임베딩/psycopg2)을 필요 시에만 로딩
            from ..embeddings import embed_text
            from ..db.vector import search_similar

            vec = embed_text(question)
            vec_lit = _to_vector_literal(vec)
            rows = search_similar(vec_lit, top_k=top_k)
            answers = [
                {
                    "id": r.get("id"),
                    "source": r.get("source"),
                    "content": r.get("content"),
                    "score": float(r.get("score", 0.0)),
                }
                for r in rows
            ]
        except Exception:
            # 임베딩/DB 오류 발생 시 자동 폴백
            answers = _mock_search(question, top_k)
    else:
        # 폴백: 키워드 기반 간이 검색
        answers = _mock_search(question, top_k)

    return {"question": req.question, "answers": answers, "top_k": top_k}
