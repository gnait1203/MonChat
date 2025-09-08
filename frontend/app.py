"""
Streamlit 프론트엔드
- Q&A, 시각화, 상태 탭을 제공
- API 서버 주소는 환경변수(API_HOST, API_PORT)로 제어 가능
"""

import streamlit as st
import requests
import os

# API 서버 위치는 환경변수로 제어
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = os.getenv("API_PORT", "8000")
API_BASE = f"http://{API_HOST}:{API_PORT}"

st.set_page_config(page_title="MonChat", layout="wide")

st.title("MonChat - 성능/오류 데이터 Q&A")

# 탭 구성: Q&A / 시각화 / 상태
tabs = st.tabs(["Q&A", "시각화", "상태"])

with tabs[0]:
    st.subheader("질문하기")
    q = st.text_input("질문을 입력하세요", placeholder="어제 가장 많이 발생한 에러 코드는?")
    top_k = st.slider("TopK", 1, 10, 5)
    if st.button("검색") and q:
        try:
            # 백엔드 /qa 엔드포인트 호출
            res = requests.post(f"{API_BASE}/qa", json={"question": q, "top_k": top_k}, timeout=30)
            data = res.json()
            st.write("Question:", data.get("question"))
            st.write("Answers:", data.get("answers"))
        except Exception as e:
            st.error(str(e))

with tabs[1]:
    st.subheader("시각화 (예시 자리)")
    st.info("백엔드에 지표 API 추가 후 연동 예정")

with tabs[2]:
    st.subheader("상태 체크")
    try:
        # 헬스체크 엔드포인트
        res = requests.get(f"{API_BASE}/health/ready", timeout=10)
        st.write(res.json())
    except Exception as e:
        st.error(str(e))
