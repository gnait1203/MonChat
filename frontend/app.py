"""
Streamlit 프론트엔드
- Q&A, 시각화, 상태 탭을 제공
- API 서버 주소는 환경변수(API_HOST, API_PORT)로 제어 가능
"""

import streamlit as st
import requests
import os
import json
from pathlib import Path
from datetime import datetime

# API 서버 위치는 환경변수로 제어
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = os.getenv("API_PORT", "8000")
API_BASE = f"http://{API_HOST}:{API_PORT}"

st.set_page_config(page_title="MonChat", layout="wide")

# 채팅 이력 파일 경로 (사용자 홈 디렉토리)
HISTORY_DIR = Path.home() / ".monchat"
HISTORY_FILE = HISTORY_DIR / "chat_history.jsonl"


def _ensure_history_dir():
    """이력 저장 디렉토리 생성 보장"""
    try:
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def load_history() -> list:
    """jsonl 형식 이력을 모두 로드"""
    if not HISTORY_FILE.exists():
        return []
    records = []
    try:
        with HISTORY_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    # 손상된 라인은 건너뜀
                    continue
    except Exception:
        return []
    return records


def append_history(record: dict) -> None:
    """이력 레코드를 jsonl로 추가 저장"""
    try:
        _ensure_history_dir()
        with HISTORY_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        # 저장 실패는 앱 동작에 영향 주지 않도록 무시
        pass


def clear_history_files() -> None:
    try:
        if HISTORY_FILE.exists():
            HISTORY_FILE.unlink(missing_ok=True)
    except Exception:
        pass

st.title("MonChat - 성능/오류 데이터 Q&A")

# 세션 상태 초기화
if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_history()
if "persist_history" not in st.session_state:
    st.session_state.persist_history = True

# 탭 구성: Q&A / 시각화 / 상태 / 이력
tabs = st.tabs(["Q&A", "시각화", "상태", "이력"])

# 사이드바: 이력 저장 ON/OFF, 다운로드, 초기화
with st.sidebar:
    st.subheader("채팅 이력")
    st.session_state.persist_history = st.checkbox(
        "이력 영구 저장", value=st.session_state.persist_history, help="홈 디렉토리(.monchat)에 저장"
    )

    # 다운로드 버튼 (현재 메모리 상의 이력을 jsonl 텍스트로 변환)
    if st.session_state.chat_history:
        jsonl_text = "\n".join(
            [json.dumps(r, ensure_ascii=False) for r in st.session_state.chat_history]
        )
        st.download_button(
            label="이력 다운로드 (jsonl)",
            data=jsonl_text,
            file_name="chat_history.jsonl",
            mime="application/json",
        )

    if st.button("이력 초기화"):
        st.session_state.chat_history = []
        clear_history_files()
        st.success("이력을 초기화했습니다.")

with tabs[0]:
    st.subheader("질문하기")
    q = st.text_input("질문을 입력하세요", placeholder="어제 가장 많이 발생한 에러 코드는?")
    top_k = st.slider("TopK", 1, 10, 5)
    if st.button("검색") and q:
        try:
            # 백엔드 /qa 엔드포인트 호출
            res = requests.post(f"{API_BASE}/qa", json={"question": q, "top_k": top_k}, timeout=30)
            res.raise_for_status()
            data = res.json()
            # 화면 출력
            st.write("Question:", data.get("question"))
            st.write("Answers:", data.get("answers"))
            # 이력 저장
            record = {
                "ts": datetime.utcnow().isoformat() + "Z",
                "question": data.get("question", q),
                "answers": data.get("answers", []),
                "top_k": top_k,
            }
            st.session_state.chat_history.append(record)
            if st.session_state.persist_history:
                append_history(record)
        except Exception as e:
            st.error(str(e))

    # (이전 이력 표시는 '이력' 탭으로 이동)

with tabs[1]:
    st.subheader("시각화 (예시 자리)")
    st.info("백엔드에 지표 API 추가 후 연동 예정")

with tabs[2]:
    st.subheader("상태 체크")
    backend = API_BASE
    col1, col2 = st.columns(2)
    ready_ok, live_ok, app_info = False, False, {}

    # 준비 상태
    try:
        res = requests.get(f"{backend}/health/ready", timeout=5)
        ready_ok = res.ok and res.json().get("status") == "ok"
    except Exception:
        ready_ok = False

    # 생존 상태
    try:
        res = requests.get(f"{backend}/health/live", timeout=5)
        live_ok = res.ok and res.json().get("status") == "alive"
    except Exception:
        live_ok = False

    # 앱 정보
    try:
        res = requests.get(f"{backend}/", timeout=5)
        if res.ok:
            app_info = res.json()
    except Exception:
        app_info = {}

    with col1:
        st.markdown("**백엔드 주소**")
        st.code(backend, language="text")
        st.markdown("**준비 상태**")
        st.success("✅ Ready") if ready_ok else st.error("❌ Not Ready")
        st.markdown("**생존 상태**")
        st.success("✅ Alive") if live_ok else st.error("❌ Not Alive")

    with col2:
        st.markdown("**앱 정보**")
        if app_info:
            st.markdown(f"- 앱: {app_info.get('app','-')}")
            st.markdown(f"- 환경: {app_info.get('env','-')}")
        else:
            st.info("앱 정보를 가져올 수 없습니다.")

with tabs[3]:
    st.subheader("TimeLine")
    st.caption("[TimeLine] 질문 :  / 답변 :  형식으로 표시합니다.")
    if not st.session_state.chat_history:
        st.info("표시할 이력이 없습니다. 질문을 입력해 보세요.")
    else:
        # 최신 순으로 표시
        for rec in reversed(st.session_state.chat_history):
            ts = rec.get("ts", "")
            qtext = rec.get("question", "")
            answers = rec.get("answers", [])
            if isinstance(answers, list):
                # 답변 리스트를 '; '로 이어 붙여 간결히 표기
                answer_text = "; ".join([str(a) for a in answers]) if answers else "(없음)"
            else:
                answer_text = str(answers) if answers else "(없음)"
            st.markdown(f"- [{ts}] 질문 : {qtext} / 답변 : {answer_text}")
