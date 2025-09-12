r"""
허깅페이스 모델 사전 다운로드 스크립트

용도:
- 오프라인/내부망 환경 대비를 위해 모델 가중치와 토크나이저 파일을 미리 캐시에 다운로드한다.

사용 예시:
    python tools/download_hf_model.py --model jhgan/ko-sbert-nli --cache-dir ./.hf-cache --token <HF_TOKEN>

윈도우 파워셸 예시:
    python .\tools\download_hf_model.py -m jhgan/ko-sbert-nli -c .\.hf-cache
"""

import argparse
import os
from pathlib import Path

from huggingface_hub import snapshot_download


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", "-m", required=True, help="허깅페이스 모델 ID 또는 로컬 경로")
    parser.add_argument("--cache-dir", "-c", default=os.environ.get("HUGGINGFACE_HUB_CACHE", ""), help="캐시 디렉터리")
    parser.add_argument("--token", "-t", default=os.environ.get("HF_TOKEN", ""), help="허깅페이스 액세스 토큰(필요 시)")
    parser.add_argument("--ca-bundle", "-b", default=os.environ.get("REQUESTS_CA_BUNDLE", ""), help="사내(기업) 루트 CA 번들 파일(.pem) 경로")
    args = parser.parse_args()

    cache_dir = args.cache_dir or ".hf-cache"
    Path(cache_dir).mkdir(parents=True, exist_ok=True)

    # 기업 프록시/SSL 가로채기 환경: CA 번들 지정 시 Requests가 해당 루트를 신뢰하도록 설정
    if args.ca_bundle:
        if os.path.exists(args.ca_bundle):
            os.environ["REQUESTS_CA_BUNDLE"] = args.ca_bundle
            os.environ["CURL_CA_BUNDLE"] = args.ca_bundle
            print(f"[HF] using CA bundle: {args.ca_bundle}")
        else:
            raise FileNotFoundError(f"CA 번들 경로가 존재하지 않습니다: {args.ca_bundle}")

    print(f"[HF] downloading model='{args.model}' to cache_dir='{cache_dir}' ...")
    revision = None  # latest
    snapshot_download(
        repo_id=args.model,
        cache_dir=cache_dir,
        token=args.token or None,
        revision=revision,
        local_files_only=False,
        allow_patterns=None,
        ignore_patterns=None,
        resume_download=True,
    )
    print("[HF] done")


if __name__ == "__main__":
    main()


