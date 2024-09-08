import streamlit as st
import altair as alt
import pandas as pd
import os
import re
from openai import OpenAI

# OpenAI API Key 환경 변수로부터 불러오기
api_key = os.getenv("OPENAI_API_KEY")

# OpenAI 클라이언트 초기화
if api_key:
    client = OpenAI(api_key=api_key)
else:
    st.error("OpenAI API 키가 필요합니다. 환경 변수에 API 키를 설정해주세요.")

# 세션 상태 초기화
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'feedback' not in st.session_state:
    st.session_state.feedback = ""  # 피드백을 저장하기 위한 변수

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
        st.write("API Response: ", response)  # API 응답 확인

        emotion_text = response.choices[0].message.content.strip()

        # 감정 점수만 추출 (정규 표현식 사용)
        match = re.search(r'\d+', emotion_text)
        if match:
            emotion_score = int(match.group())  # 첫 번째로 발견된 숫자를 추출
        else:
            st.error("감정 점수를 추출할 수 없습니다.")
            return None, None

        # AI 피드백 생성
        feedback_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "당신은 초, 중학생을 대상으로 하는 사회정서 지원 AI입니다. 친근하고 밝은 톤으로 대화하며, 이모티콘을 많이 사용하세요. 학생들의 감정을 이해하고 공감하며, 긍정적인 에너지를 전달해주세요."},
                {"role": "user", "content": f"다음 일기에 대해 피드백을 해주세요:\n\n{content}"}
            ]
        )
        feedback = feedback_response.choices[0].message.content.strip()

        # 피드백을 세션 상태에 저장하여 유지
        st.session_state.feedback = feedback

        return emotion_score, feedback
    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")
        return None, None

# 감정 스펙트럼 시각화 (Altair 사용)
def plot_emotion_spectrum(score):
    # 기본 데이터 생성
    base_data = pd.DataFrame({
        'x': range(11),
        'y': [0] * 11
    })

    st.write("Base Data for Spectrum: ", base_data)  # 데이터 확인

    # 스펙트럼 색상 설정
    colors = ['#F44336', '#FF9800', '#FFC107', '#FFEB3B', '#CDDC39', 
              '#8BC34A', '#4CAF50', '#009688', '#00BCD4', '#03A9F4', '#2196F3']
    
    # 기본 차트 생성 (배경 스펙트럼)
    base_chart = alt.Chart(base_data).mark_rect().encode(
        x=alt.X('x:Q', scale=alt.Scale(domain=[0, 10]), axis=alt.Axis(title='감정 점수', values=list(range(11)))),
        x2=alt.X2('x2:Q', scale=alt.Scale(domain=[0, 10])),
        color=alt.Color('x:Q', scale=alt.Scale(domain=[0, 10], range=colors), legend=None)
    ).transform_calculate(
        x2="datum.x + 1"
    )

    # 현재 점수 표시를 위한 데이터
    score_data = pd.DataFrame({
        'score': [score],
        'y': [0]
    })

    st.write("Score Data: ", score_data)  # 점수 데이터 확인

    # 현재 점수 표시 (삼각형 마커)
    score_marker = alt.Chart(score_data).mark_triangle(
        size=300,
        color='black',
        opacity=0.7
    ).encode(
        x='score:Q',
        y='y:Q'
    )

    # 점수 라벨
    score_label = alt.Chart(score_data).mark_text(
        align='center',
        baseline='bottom',
        dy=-10,
        fontSize=20,
        fontWeight='bold'
    ).encode(
        x='score:Q',
        y='y:Q',
        text='score:Q'
    )

    # 라벨 데이터
    label_data = pd.DataFrame({
        'x': [0, 10],
        'y': [0, 0],
        'label': ['매우 나쁨', '매우 좋음']
    })

    # 라벨 차트
    labels = alt.Chart(label_data).mark_text(
        align='center',
        baseline='top',
        dy=10,
        fontSize=14
    ).encode(
        x='x:Q',
        y='y:Q',
        text='label:N'
    )

    # 차트 조합
    final_chart = alt.layer(
        base_chart, score_marker, score_label, labels
    ).properties(
        width=600,
        height=100,
        title='감정 스펙트럼'
    )

    return final_chart

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

# 분석하기 버튼 복구
if st.button("분석하기"):
    if api_key:
        with st.spinner('AI가 열심히 분석 중이에요... 🤔'):
            emotion_score, feedback = analyze_diary(diary_content)
        
        if emotion_score is not None and feedback:
            st.subheader('감정 분석 결과')
            st.write(f"감정 점수: {emotion_score}")

            # 감정 스펙트럼 시각화 (Altair 사용)
            chart = plot_emotion_spectrum(emotion_score)
            st.altair_chart(chart, use_container_width=True)
            
            st.subheader('AI 피드백')
            st.info(feedback)  # 피드백 한 번만 표시
            
            st.session_state.chat_history.append(("AI", feedback))
    else:
        st.error("OpenAI API 키가 필요합니다. 입력 후 다시 시도하세요.")

# 채팅 UI - 사용자 입력 및 대화 내용 표시
st.subheader('AI와 이어서 대화하기')

chat_container = st.container()  # 대화 내용을 담을 컨테이너

# 이전 대화 내용 출력
with chat_container:
    for role, message in st.session_state.chat_history:
        if role == "User":
            st.markdown(f"**You:** {message}")
        else:
            st.markdown(f"**AI:** {message}")

# 채팅 입력 필드 및 콜백 함수
def submit_chat():
    user_message = st.session_state.chat_input
    st.write("User Input: ", user_message)  # 입력 확인
    if user_message:
        st.session_state.chat_history.append(("User", user_message))  # 사용자의 메시지를 기록
        ai_response = chat_with_ai(user_message)
        if ai_response:
            st.session_state.chat_history.append(("AI", ai_response))  # AI의 응답을 기록
        st.session_state.chat_input = ""  # 입력 필드를 비움

# 채팅 입력 필드
st.text_input("메시지 입력 후, Enter키를 누르세요", key="chat_input", placeholder="메시지 입력 후, Enter키를 누르세요", on_change=submit_chat)
