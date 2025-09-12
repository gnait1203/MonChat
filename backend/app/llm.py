"""
사내 LLM(Ollama 기반) 동기 클라이언트
- Chat API: POST {LLM_BASE_URL}{LLM_CHAT_PATH}
- 요청/응답 스키마 단순 래핑 및 에러 처리
"""

from typing import Dict, Any, Optional
import requests

from .settings import settings


class LLMClient:
    """내부 LLM 호출용 간단한 동기 클라이언트"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        chat_path: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: Optional[int] = None,
        stream: Optional[bool] = None,
    ) -> None:
        self.base_url = (base_url or settings.LLM_BASE_URL).rstrip("/")
        self.chat_path = chat_path or settings.LLM_CHAT_PATH
        self.default_model = default_model or settings.LLM_DEFAULT_MODEL
        self.timeout = timeout or settings.LLM_TIMEOUT
        self.stream = settings.LLM_STREAM if stream is None else stream

    def chat(self, prompt: str, model: Optional[str] = None, stream: Optional[bool] = None) -> Dict[str, Any]:
        """Chat API 호출

        Args:
            prompt: 사용자 프롬프트(단일 턴)
            model: 사용할 모델명(미지정 시 기본값)
            stream: 스트리밍 여부(기본 False 권장)
        Returns:
            LLM 서버 원본 응답(JSON dict)
        """
        if not settings.LLM_ENABLED:
            raise RuntimeError("LLM is disabled by configuration (LLM_ENABLED=false)")

        payload = {
            "model": model or self.default_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": settings.LLM_STREAM if stream is None else stream,
        }

        url = f"{self.base_url}{self.chat_path}"
        resp = requests.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()


def extract_response_text(response_json: Dict[str, Any]) -> str:
    """서버 응답에서 텍스트를 안전하게 추출

    서버 예시 스펙이 일부 상이하여 다음 우선순위로 추출:
    - response_json["message"]["content"]
    - response_json["messages"][-1]["content"]
    - response_json.get("response")
    - 빈 문자열
    """
    try:
        message = response_json.get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return message["content"]
    except Exception:
        pass

    try:
        messages = response_json.get("messages")
        if isinstance(messages, list) and messages:
            last = messages[-1]
            if isinstance(last, dict) and isinstance(last.get("content"), str):
                return last["content"]
    except Exception:
        pass

    try:
        text = response_json.get("response")
        if isinstance(text, str):
            return text
    except Exception:
        pass

    return ""


