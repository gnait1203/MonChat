"""
문장 임베딩 유틸리티
- sentence-transformers 모델을 로드하여 텍스트를 벡터로 변환한다.
- 모델은 LRU 캐시로 1회만 로딩하여 성능을 최적화한다.
"""

import os
# 불필요한 백엔드 로딩 방지(TensorFlow/Flax/TorchVision)
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("TRANSFORMERS_NO_FLAX", "1")
os.environ.setdefault("TRANSFORMERS_NO_TORCHVISION", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from sentence_transformers import SentenceTransformer
import torch
from functools import lru_cache
from .settings import settings


@lru_cache(maxsize=1)
def get_embedding_model():
    """임베딩 모델 싱글톤 로더

    첫 호출 시 모델을 다운로드/로딩하고 이후에는 캐시된 인스턴스를 재사용한다.
    """
    device_arg = None
    if settings.EMBEDDING_DEVICE.lower() == "cuda":
        device_arg = "cuda" if torch.cuda.is_available() else "cpu"
    elif settings.EMBEDDING_DEVICE.lower() == "cpu":
        device_arg = "cpu"
    else:
        device_arg = "cuda" if torch.cuda.is_available() else "cpu"
    # 성능 최적화 플래그
    try:
        if device_arg == "cuda":
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            torch.backends.cudnn.benchmark = True
    except Exception:
        pass

    # HF 캐시 디렉터리 지정(옵션)
    if settings.HF_CACHE_DIR:
        os.environ.setdefault("HUGGINGFACE_HUB_CACHE", settings.HF_CACHE_DIR)

    model_kwargs = {}
    if device_arg == "cuda":
        try:
            model_kwargs = {"torch_dtype": torch.float16}
        except Exception:
            model_kwargs = {}

    # 로컬 디렉터리가 지정되어 있으면 우선 사용, 아니면 모델 ID에서 폴더명 유추 자동 감지
    local_dir = (settings.HF_LOCAL_MODEL_DIR.strip() if settings.HF_LOCAL_MODEL_DIR else "")
    # 상대 경로로 들어온 경우 프로젝트 루트 기준 절대 경로로 변환
    if local_dir and not os.path.isabs(local_dir):
        project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
        candidate = os.path.normpath(os.path.join(project_root, local_dir))
        if os.path.isdir(candidate):
            local_dir = candidate
    if not local_dir:
        # 프로젝트 루트의 hf/<repo-name> 자동 감지 (예: hf/bge-m3, hf/all-MiniLM-L6-v2)
        repo_name = settings.EMBEDDING_MODEL.split("/")[-1]
        default_local = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "hf", repo_name))
        if os.path.isdir(default_local):
            local_dir = default_local

    if local_dir:
        # 로컬 경로를 사용하는 경우 네트워크 접근 차단(오프라인 모드)
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        model_source = local_dir
    else:
        model_source = settings.EMBEDDING_MODEL
    loader_kwargs = {
        "device": device_arg,
        "model_kwargs": model_kwargs or None,
    }
    if settings.HF_CACHE_DIR:
        loader_kwargs["cache_folder"] = settings.HF_CACHE_DIR
    # 프라이빗 모델 접근용 토큰
    if settings.HF_TOKEN:
        # sentence-transformers는 use_auth_token 인자를 지원
        loader_kwargs["use_auth_token"] = settings.HF_TOKEN

    return SentenceTransformer(
        model_source,
        **loader_kwargs,
    )


def embed_texts(texts: list[str]) -> list[list[float]]:
    """여러 문장을 임베딩하여 벡터 리스트 반환"""
    model = get_embedding_model()
    embeddings = model.encode(
        texts,
        batch_size=settings.EMBEDDING_BATCH_SIZE,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_tensor=False,
    )
    # SentenceTransformers가 리스트/넘파이/텐서를 상황에 따라 반환하므로 안전 변환
    if hasattr(embeddings, "tolist"):
        return embeddings.tolist()
    if isinstance(embeddings, list):
        out: list[list[float]] = []
        for v in embeddings:
            if hasattr(v, "tolist"):
                out.append(v.tolist())
            elif isinstance(v, (tuple, list)):
                out.append([float(x) for x in v])
            else:
                out.append([float(v)])
        return out
    # 최후의 수단: 단일 벡터로 온 경우 래핑
    return [[float(x) for x in embeddings]]


def embed_text(text: str) -> list[float]:
    """단일 문장을 임베딩하여 벡터 반환"""
    return embed_texts([text])[0]
