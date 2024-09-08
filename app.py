import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# 세션 상태 초기화
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

def analyze_diary(content):
    try:
        # OpenAI API를 사용한 감정 분석
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "당신은 일기의 감정을 분석하는 AI입니다. '좋음', '보통', '나쁨' 중 하나로만 대답해주세요."},
                {"role": "user", "content": f"다음 일기의 감정을 분류해주세요:\n\n{content}"}
            ]
        )
        emotion = response.choices[0].message.content.strip()

        # 감정에 따른 색상 지정
        color = {'좋음': '#4CAF50', '보통': '#FFC107', '나쁨': '#F44336'}.get(emotion, '#9E9E9E')

        # AI 피드백 생성
        feedback_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "당신은 초, 중학생을 대상으로 하는 사회정서 지원 AI입니다. 친근하고 밝은 톤으로 대화하며, 이모티콘을 많이 사용하세요. 학생들의 감정을 이해하고 공감하며, 긍정적인 에너지를 전달해주세요."},
                {"role": "user", "content": f"다음 일기에 대해 피드백을 해주세요:\n\n{content}"}
            ]
        )
        feedback = feedback_response.choices[0].message.content.strip()

        return emotion, color, feedback
    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")
        return None, None, None

def chat_with_ai(message):
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "당신은 초, 중학생을 대상으로 하는 사회정서 지원 AI입니다. 친근하고 밝은 톤으로 대화하며, 이모티콘을 많이 사용하세요. 학생들의 감정을 이해하고 공감하며, 긍정적인 에너지를 전달해주세요."},
                {"role": "user", "content": message}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")
        return None

st.title('AI 일기 친구 🤖📔')

st.write("""
AI 일기 친구는 여러분의 일기를 분석하고 감정을 이해하여 따뜻한 피드백을 제공합니다. 
일기를 작성하고 '분석하기' 버튼을 누르면, AI가 여러분의 감정을 분석하고 응원의 메시지를 전달합니다.
그 후 AI와 추가로 대화를 나눌 수 있어요! 😊
""")

diary_content = st.text_area("오늘의 일기를 작성해주세요:", height=200)

if st.button('분석하기'):
    with st.spinner('AI가 열심히 분석 중이에요... 🤔'):
        emotion, color, feedback = analyze_diary(diary_content)
    
    if emotion and color and feedback:
        st.subheader('감정 분석 결과')
        st.markdown(f"<p style='color:{color};font-size:20px;'>감정: {emotion}</p>", unsafe_allow_html=True)
        
        st.subheader('AI 피드백')
        st.info(feedback)
        
        st.session_state.chat_history = []
        st.session_state.chat_history.append(("AI", feedback))

if 'chat_history' in st.session_state and st.session_state.chat_history:
    st.subheader('AI와 대화하기')
    for i in range(3):
        user_message = st.text_input(f"메시지 {i+1}", key=f"user_input_{i}")
        if user_message:
            st.session_state.chat_history.append(("User", user_message))
            ai_response = chat_with_ai(user_message)
            if ai_response:
                st.session_state.chat_history.append(("AI", ai_response))
    
    st.subheader('대화 내용')
    for role, message in st.session_state.chat_history:
        if role == "User":
            st.text_input("You:", message, disabled=True)
        else:
            st.info(message)
