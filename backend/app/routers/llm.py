"""
LLM 라우터
- 단일 턴 채팅 API 프록시: /llm/chat
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from ..llm import LLMClient, extract_response_text
from ..settings import settings


router = APIRouter()


class ChatRequest(BaseModel):
    prompt: str = Field(..., description="사용자 입력 프롬프트")
    model: Optional[str] = Field(default=None, description="사용할 모델명(미지정 시 기본값)")
    stream: Optional[bool] = Field(default=None, description="스트리밍 여부")


class ChatResponse(BaseModel):
    model: str
    text: str
    raw: dict


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not settings.LLM_ENABLED:
        raise HTTPException(status_code=400, detail="LLM is disabled by configuration")

    client = LLMClient()
    try:
        resp_json = client.chat(prompt=req.prompt, model=req.model, stream=req.stream)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM upstream error: {str(e)}")

    text = extract_response_text(resp_json)
    model_used = (req.model or settings.LLM_DEFAULT_MODEL)
    return ChatResponse(model=model_used, text=text, raw=resp_json)


