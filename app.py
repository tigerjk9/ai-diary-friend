import streamlit as st
import altair as alt
import pandas as pd
from openai import OpenAI
import os
import re
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI 클라이언트 초기화
api_key = None

# Streamlit 페이지 설정
st.set_page_config(page_title="AI 일기 친구", page_icon="📔", layout="wide")

# CSS를 사용하여 한글 폰트, 채팅 UI 스타일, 그리고 만든이 정보 스타일 적용
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@400;700&display=swap');
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, [class*="css"] {
        font-family: 'Nanum Gothic', sans-serif;
    }
    .chat-message {
        padding: 1rem; 
        border-radius: 0.5rem; 
        margin-bottom: 1rem; 
        display: flex;
        flex-direction: column;
    }
    .chat-message.user {
        background-color: #2b313e;
        color: #ffffff;
    }
    .chat-message.bot {
        background-color: #475063;
        color: #ffffff;
    }
    .chat-message .message {
      width: 100%;
    }
    .creator-info {
        font-family: 'Pretendard', sans-serif;
        font-weight: 600;
        font-size: 0.9em;
        color: #4a4a4a;
        margin-top: 20px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# OpenAI 키 입력받기 (사이드바 사용)
with st.sidebar:
    user_api_key = st.text_input("OpenAI 키 값을 입력하세요. 시험 삼아 테스트하려면 빈칸으로 두세요.")
    if user_api_key:
        api_key = user_api_key
    else:
        api_key = os.getenv('OPENAI_API_KEY')
    
    # 만든이 정보 추가
    st.markdown('<p class="creator-info">만든이: 대전장대초 김진관(닷커넥터)</p>', unsafe_allow_html=True)

if api_key:
    client = OpenAI(api_key=api_key)
else:
    st.warning("OpenAI API 키가 필요합니다. 키를 입력하거나 테스트 모드를 사용하세요.")

# 이하 코드는 이전과 동일하게 유지...

# (이전 코드의 나머지 부분을 여기에 그대로 유지)
