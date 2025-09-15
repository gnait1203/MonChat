import os
import sys
from pathlib import Path


def main() -> None:
    # 프로젝트 루트 추가(절대 임포트 지원)
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # 환경변수 설정: mock_data CSV 사용 및 2일치(오늘+어제)
    os.environ["ETL_DAYS"] = "2"
    os.environ["MOCK_DB_ENABLED"] = "true"
    os.environ["VECTORDB_ENABLED"] = "true"
    os.environ["MOCK_DB_DIR"] = "mock_data"
    # 로컬 허깅페이스 모델 경로 주입(있다면 사용). 기본은 EMBEDDING_MODEL의 repo name을 사용
    from backend.app.settings import settings  # 지연 임포트
    # 사용자가 이미 HF_LOCAL_MODEL_DIR를 환경에 지정했다면 그대로 사용
    if not os.environ.get("HF_LOCAL_MODEL_DIR"):
        repo_name = settings.EMBEDDING_MODEL.split("/")[-1]
        candidate_dir = (project_root / "hf" / repo_name).resolve()
        if candidate_dir.is_dir():
            os.environ["HF_LOCAL_MODEL_DIR"] = str(candidate_dir)
    # 모델/변환기 경량화 플래그
    os.environ["TRANSFORMERS_NO_TF"] = "1"
    os.environ["TRANSFORMERS_NO_FLAX"] = "1"
    os.environ["TRANSFORMERS_NO_TORCHVISION"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    from etl.pipeline import run_etl

    run_etl()


if __name__ == "__main__":
    main()


