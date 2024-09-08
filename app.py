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

# CSS를 사용하여 한글 폰트 및 채팅 UI 스타일 적용
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@400;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Nanum Gothic', sans-serif;
    }
    .chat-message {
        padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem; display: flex
    }
    .chat-message.user {
        background-color: #2b313e
    }
    .chat-message.bot {
        background-color: #475063
    }
    .chat-message .avatar {
      width: 20%;
    }
    .chat-message .avatar img {
      max-width: 78px;
      max-height: 78px;
      border-radius: 50%;
      object-fit: cover;
    }
    .chat-message .message {
      width: 80%;
      padding: 0 1.5rem;
      color: #fff;
    }
</style>
""", unsafe_allow_html=True)

# OpenAI 키 입력받기 (좌측 상단으로 이동하기 위해 사이드바 사용)
with st.sidebar:
    user_api_key = st.text_input("OpenAI 키 값을 입력하세요. 시험 삼아 테스트하려면 빈칸으로 두세요.")
    if user_api_key:
        api_key = user_api_key
    else:
        api_key = os.getenv('OPENAI_API_KEY')

if api_key:
    client = OpenAI(api_key=api_key)
else:
    st.warning("OpenAI API 키가 필요합니다. 키를 입력하거나 테스트 모드를 사용하세요.")

# 세션 상태 초기화
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'feedback' not in st.session_state:
    st.session_state.feedback = ""  # 피드백을 저장하기 위한 변수

if 'emotion_score' not in st.session_state:
    st.session_state.emotion_score = None

# 감정 분석 함수
def analyze_diary(content):
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "너는 10대 학생들의 일기를 분석하고 감정을 이해하는 AI야. 감정을 0에서 10까지의 숫자로 나타내줘. 0은 매우 나쁨, 10은 매우 좋음이야."},
                {"role": "user", "content": f"다음 일기의 감정을 분석해줘:\n\n{content}"}
            ]
        )
        emotion_text = response.choices[0].message.content.strip()

        # 감정 점수만 추출 (정규 표현식 사용)
        match = re.search(r'\d+', emotion_text)
        if match:
            emotion_score = int(match.group())  # 첫 번째로 발견된 숫자를 추출
        else:
            st.error("감정 점수를 추출할 수 없어요.")
            return None, None

        # AI 피드백 생성
        feedback_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "너는 10대 학생들을 위한 에너지 넘치고 친근한 AI 상담사야. 학생들의 감정을 깊이 이해하고 공감하며, 그들의 눈높이에 맞는 쉬운 언어로 대화해. 격식 없는 친근한 말투를 사용하고, 적절한 이모티콘도 활용해. 상담사로서의 전문성을 유지하면서도 학생들이 편하게 대화할 수 있는 분위기를 만들어줘."},
                {"role": "user", "content": f"다음 일기에 대해 피드백을 해줘:\n\n{content}"}
            ]
        )
        feedback = feedback_response.choices[0].message.content.strip()

        # 피드백을 세션 상태에 저장하여 유지
        st.session_state.feedback = feedback
        st.session_state.emotion_score = emotion_score

        return emotion_score, feedback
    except Exception as e:
        st.error(f"오류가 발생했어요: {str(e)}")
        return None, None

# 감정 스펙트럼 시각화 (Altair 사용, 영어로 표시)
def plot_emotion_spectrum(score):
    # 데이터 프레임 생성
    df = pd.DataFrame({'x': [0, score], 'y': [0, 0]})
    
    # 색상 결정
    color = '#4CAF50' if score > 7 else '#FFC107' if score > 3 else '#F44336'
    
    # Altair 차트 생성 (영어로 표시)
    chart = alt.Chart(df).mark_line(
        color=color,
        strokeWidth=10
    ).encode(
        x=alt.X('x', scale=alt.Scale(domain=[0, 10]), axis=alt.Axis(title='Emotion Score (0 to 10)', values=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])),
        y=alt.Y('y', axis=None)
    ).properties(
        width=600,
        height=100,
        title='Emotion Spectrum'
    )
    
    # 점수 표시
    text = alt.Chart(pd.DataFrame({'x': [score], 'y': [0], 'text': [f'{score}']})).mark_text(
        align='center',
        baseline='bottom',
        dy=-5
    ).encode(
        x='x',
        y='y',
        text='text'
    )
    
    # 차트와 텍스트 결합
    final_chart = chart + text
    
    return final_chart

# 감정 점수에 따른 동그라미 색상 결정
def get_emotion_circle(score):
    if score <= 3:
        return "🔴"  # 빨간 동그라미
    elif score <= 7:
        return "🟡"  # 노란 동그라미
    else:
        return "🟢"  # 초록 동그라미

# AI와 채팅 함수
def chat_with_ai(message):
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "너는 10대 학생들을 위한 에너지 넘치고 친근한 AI 상담사야. 학생들의 감정을 깊이 이해하고 공감하며, 그들의 눈높이에 맞는 쉬운 언어로 대화해. 격식 없는 친근한 말투를 사용하고, 적절한 이모티콘도 활용해. 상담사로서의 전문성을 유지하면서도 학생들이 편하게 대화할 수 있는 분위기를 만들어줘."},
                {"role": "user", "content": message}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"오류가 발생했어요: {str(e)}")
        return None

# UI
st.title('AI 일기 친구 🤖📔')

st.write("""
안녕! 나는 너의 일기를 읽고 감정을 이해하는 AI 친구야. 
일기를 쓰고 '분석하기' 버튼을 누르면, 네 감정을 분석하고 응원 메시지를 보내줄게. 
그 다음엔 계속 대화도 할 수 있어! 어때, 같이 이야기 나눠볼까? 😊
""")

diary_content = st.text_area("오늘의 일기를 자유롭게 써봐:", height=200)

# 분석하기 버튼
if st.button("분석하기"):
    if api_key:
        with st.spinner('열심히 분석 중이야... 🤔'):
            emotion_score, feedback = analyze_diary(diary_content)
        
        if emotion_score is not None and feedback:
            st.session_state.chat_history = []  # 채팅 기록 초기화
            st.session_state.chat_history.append(("AI", feedback))
    else:
        st.error("OpenAI API 키가 필요해. 입력하고 다시 시도해줘!")

# 감정 분석 결과 표시 (항상 표시)
if st.session_state.emotion_score is not None:
    st.subheader('감정 분석 결과')
    emotion_circle = get_emotion_circle(st.session_state.emotion_score)
    if st.session_state.emotion_score <= 3:
        emotion_text = "나쁨"
    elif st.session_state.emotion_score <= 7:
        emotion_text = "보통"
    else:
        emotion_text = "좋음"
    st.write(f"감정 점수: {st.session_state.emotion_score} - {emotion_text} {emotion_circle}")

    # 감정 스펙트럼 시각화 (Altair 사용, 영어로 표시)
    chart = plot_emotion_spectrum(st.session_state.emotion_score)
    st.altair_chart(chart, use_container_width=True)

# 채팅 UI - 사용자 입력 및 대화 내용 표시
st.subheader('나랑 더 이야기하기')

# 이전 대화 내용 출력
for i, (role, message) in enumerate(st.session_state.chat_history):
    if role == "User":
        st.markdown(f'<div class="chat-message user"><div class="avatar"><img src="https://i.ibb.co/37nsPXm/user1.png"/></div><div class="message">{message}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="chat-message bot"><div class="avatar"><img src="https://i.ibb.co/6WHGxv5/DDD.png"/></div><div class="message">{message}</div></div>', unsafe_allow_html=True)

# 채팅 입력 필드 및 콜백 함수
def submit_chat():
    user_message = st.session_state.chat_input
    if user_message:
        st.session_state.chat_history.append(("User", user_message))  # 사용자의 메시지를 기록
        ai_response = chat_with_ai(user_message)
        if ai_response:
            st.session_state.chat_history.append(("AI", ai_response))  # AI의 응답을 기록
        st.session_state.chat_input = ""  # 입력 필드를 비움

# 채팅 입력 필드
st.text_input("여기에 메시지를 입력하고 Enter 키를 눌러봐!", key="chat_input", on_change=submit_chat)
