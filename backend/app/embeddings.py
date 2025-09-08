"""
문장 임베딩 유틸리티
- sentence-transformers 모델을 로드하여 텍스트를 벡터로 변환한다.
- 모델은 LRU 캐시로 1회만 로딩하여 성능을 최적화한다.
"""

from sentence_transformers import SentenceTransformer
from functools import lru_cache
from .settings import settings


@lru_cache(maxsize=1)
def get_embedding_model():
    """임베딩 모델 싱글톤 로더

    첫 호출 시 모델을 다운로드/로딩하고 이후에는 캐시된 인스턴스를 재사용한다.
    """
    return SentenceTransformer(settings.EMBEDDING_MODEL)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """여러 문장을 임베딩하여 벡터 리스트 반환"""
    model = get_embedding_model()
    return model.encode(texts, batch_size=settings.EMBEDDING_BATCH_SIZE, convert_to_numpy=False).tolist()


def embed_text(text: str) -> list[float]:
    """단일 문장을 임베딩하여 벡터 반환"""
    return embed_texts([text])[0]
