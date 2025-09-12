# MonChat - 상품처리계 성능/오류 데이터 분석 Q&A

Streamlit + FastAPI + pgvector 기반의 데이터 분석 Q&A 시스템 예제 구현입니다.

## 구성 요소
- UI(Frontend): Streamlit
- API(Backend): FastAPI
- VectorDB: PostgreSQL + pgvector (Docker)
- ETL: Oracle/로그 수집 → 임베딩 → VectorDB 적재, APScheduler
 - 내부 LLM: 사내 Ollama API 연동(`/llm/chat`)

## 빠른 시작
1) 의존성 설치
```bash
# Linux/macOS
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) 환경변수 파일 준비
```bash
copy .env.example .env  # Windows
# 필요 값 수정 (DB, 로그 경로 등)
```

LLM 연동을 사용하려면 `.env`에 아래 항목이 설정되어야 합니다.
```
LLM_ENABLED=true
LLM_BASE_URL=http://pgaiap09:11434
LLM_CHAT_PATH=/api/chat
LLM_DEFAULT_MODEL=qwen3:8b   # 또는 gemma3:27b-it-q4_0
LLM_STREAM=false
LLM_TIMEOUT=120
```

3) VectorDB 실행 (Docker)
```bash
cd infra
docker compose up -d
```

4) 백엔드 실행
```bash
# Linux/macOS - 일반 실행 (개발용)
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# Linux/macOS - 백그라운드 실행 (운영용)
nohup uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &

# 또는 Python 모듈로 백그라운드 실행
nohup python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
```

5) 프론트엔드 실행
```bash
# Linux/macOS - 일반 실행 (개발용)
streamlit run frontend/app.py --server.port 8501

# Linux/macOS - 백그라운드 실행 (운영용)
nohup streamlit run frontend/app.py --server.port 8501 > frontend.log 2>&1 &

# 또는 Python 모듈로 백그라운드 실행
nohup python -m streamlit run frontend/app.py --server.port 8501 > frontend.log 2>&1 &
```

6) LLM 프록시 테스트
```bash
curl -X POST http://127.0.0.1:8000/llm/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt":"회의 내용을 요약해줘.", "model":"qwen3:8b", "stream": false}'
```

7) ETL 실행(수동)
```bash
# 프로젝트 루트에서 모듈로 실행 (권장)
python -m etl.pipeline

# 또는 PYTHONPATH 설정 후 실행
export PYTHONPATH=$PWD:$PYTHONPATH  # Linux/macOS
python etl/pipeline.py

# Windows에서는
set PYTHONPATH=%CD%;%PYTHONPATH%    # Windows CMD
python etl/pipeline.py
```

8) 스케줄러 실행(옵션)
```bash
# 모듈로 실행 (권장)
python -m etl.sched

# 또는 PYTHONPATH 설정 후 실행
python etl/sched.py
```

## 환경변수
모든 DB/WAS/DB 로그/임베딩/스케줄 설정은 .env로 관리됩니다. 예시는 `.env.example` 참고.

## 문제 해결
### "ModuleNotFoundError: No module named 'pydantic_settings'" 오류 시
의존성 설치가 완료되지 않은 상태입니다.

**해결방법:**
```bash
# 1. 가상환경이 활성화되어 있는지 확인
# 프롬프트 앞에 (.venv) 표시가 있어야 함

# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

# 2. 의존성 재설치
pip install -r requirements.txt

# 또는 특정 패키지만 설치
pip install pydantic-settings>=2.2.1

# 3. 설치 확인
pip list | grep pydantic
```

### "ModuleNotFoundError: No module named 'backend'" 오류 시
ETL 실행 시 발생하는 모듈 경로 문제입니다.

**해결방법 1: 모듈로 실행 (권장)**
```bash
# 프로젝트 루트 디렉토리에서
python -m etl.pipeline
python -m etl.sched
```

**해결방법 2: PYTHONPATH 설정**
```bash
# Linux/macOS
export PYTHONPATH=$PWD:$PYTHONPATH
python etl/pipeline.py

# Windows CMD
set PYTHONPATH=%CD%;%PYTHONPATH%
python etl/pipeline.py

# Windows PowerShell
$env:PYTHONPATH="$PWD;$env:PYTHONPATH"
python etl/pipeline.py
```

### "uvicorn, streamlit 명령어를 찾을 수 없음" 오류 시
1) **가상환경 활성화 확인**:
```bash
# Linux/macOS
source .venv/bin/activate

# Windows PowerShell  
.venv\Scripts\Activate.ps1

# 활성화 확인: 프롬프트 앞에 (.venv) 표시되어야 함
```

2) **의존성 재설치**:
```bash
pip install -r requirements.txt

# 특정 패키지만 설치
pip install uvicorn[standard] streamlit
```

3) **Python 모듈로 직접 실행**:
```bash
# uvicorn 대신
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# streamlit 대신  
python -m streamlit run frontend/app.py --server.port 8501
```

## 주의
- 최초 실행 시 임베딩 모델 다운로드가 이루어질 수 있습니다(인터넷 필요).
- 실제 Oracle/로그 소스가 없을 경우 해당 수집은 비활성화하세요.

## 변경 이력
- 2025-09-12: 내부 LLM(Ollama) 연동 추가, `/llm/chat` 엔드포인트 및 프론트 "LLM 대화" 탭 지원
