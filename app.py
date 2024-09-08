import streamlit as st
from openai import OpenAI
import re

# Streamlit Secrets에서 API 키 가져오기
api_key = st.secrets.get("OPENAI_API_KEY")

if api_key:
    client = OpenAI(api_key=api_key)
else:
    st.error("OpenAI API 키가 설정되지 않았습니다.")
    st.stop()

# 세션 상태 초기화
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'feedback' not in st.session_state:
    st.session_state.feedback = ""

# 감정 분석 함수
def analyze_diary(content):
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "당신은 일기의 감정을 분석하는 AI입니다. 감정을 0에서 10까지의 숫자로 나타내세요. 0은 매우 나쁨, 10은 매우 좋음입니다."},
                {"role": "user", "content": f"다음 일기의 감정을 분류해주세요:\n\n{content}"}
            ]
        )
        emotion_text = response.choices[0].message.content.strip()

        match = re.search(r'\d+', emotion_text)
        if match:
            emotion_score = int(match.group())
        else:
            st.error("감정 점수를 추출할 수 없습니다.")
            return None, None

        feedback_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "당신은 초, 중학생을 대상으로 하는 사회정서 지원 AI입니다. 친근하고 밝은 톤으로 대화하며, 이모티콘을 많이 사용하세요. 학생들의 감정을 이해하고 공감하며, 긍정적인 에너지를 전달해주세요."},
                {"role": "user", "content": f"다음 일기에 대해 피드백을 해주세요:\n\n{content}"}
            ]
        )
        feedback = feedback_response.choices[0].message.content.strip()

        st.session_state.feedback = feedback

        return emotion_score, feedback
    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")
        return None, None

# AI와 채팅 함수
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

# UI
st.title('AI 일기 친구 🤖📔')

st.write("""
AI 일기 친구는 여러분의 일기를 분석하고 감정을 이해하여 따뜻한 피드백을 제공합니다.
일기를 작성하고 '분석하기' 버튼을 누르면, AI가 여러분의 감정을 분석하고 응원의 메시지를 전달합니다.
그 후 AI와 이어서 대화할 수 있어요! 😊
""")

diary_content = st.text_area("오늘의 일기를 작성해주세요:", height=200)

if st.button("분석하기"):
    with st.spinner('AI가 열심히 분석 중이에요... 🤔'):
        emotion_score, feedback = analyze_diary(diary_content)
    
    if emotion_score is not None and feedback:
        st.subheader('감정 분석 결과')
        st.write(f"감정 점수: {emotion_score}/10")
        
        st.subheader('AI 피드백')
        st.info(feedback)
        
        st.session_state.chat_history.append(("AI", feedback))

st.subheader('AI와 이어서 대화하기')

chat_container = st.container()

with chat_container:
    for role, message in st.session_state.chat_history:
        if role == "User":
            st.markdown(f"**You:** {message}")
        else:
            st.markdown(f"**AI:** {message}")

def submit_chat():
    user_message = st.session_state.chat_input
    if user_message:
        st.session_state.chat_history.append(("User", user_message))
        ai_response = chat_with_ai(user_message)
        if ai_response:
            st.session_state.chat_history.append(("AI", ai_response))
        st.session_state.chat_input = ""

st.text_input("메시지 입력 후, Enter키를 누르세요", key="chat_input", on_change=submit_chat)
