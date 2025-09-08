"""
Q&A 라우터 (스텁)
- 사용자 질문을 받아 VectorDB에서 유사 데이터를 검색하고
  LLM과 결합하여 답변을 생성하는 흐름을 연결할 예정.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class QARequest(BaseModel):
    """Q&A 요청 페이로드
    - question: 사용자 질문 텍스트
    - top_k: 검색 상위 개수
    """
    question: str
    top_k: int = 5

@router.post("/")
def query_qa(req: QARequest):
    """질문 처리 엔드포인트 (현재는 스텁 응답)"""
    # TODO: VectorDB 검색 및 LLM 생성로직 연결
    return {"question": req.question, "answers": [], "top_k": req.top_k}
