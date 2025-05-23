# -*- coding: utf-8 -*-
# 위 라인은 파일 최상단에 추가하여 UTF-8 인코딩을 명시하는 것이 좋습니다.
# 또는, 파일을 저장할 때 반드시 UTF-8 인코딩으로 저장해주세요.

import streamlit as st
import altair as alt
import pandas as pd
from openai import OpenAI # OpenAI 임포트
import os
import re
from dotenv import load_dotenv
import httpx # httpx는 여전히 다른 곳에서 사용될 수 있으므로 임포트는 유지합니다.

# .env 파일에서 환경 변수 로드
load_dotenv()

# --- 초기 설정 ---
# OpenAI API 키 환경 변수
OPENAI_API_KEY_FROM_ENV = os.getenv('OPENAI_API_KEY')

# Streamlit 페이지 설정
st.set_page_config(page_title="AI 일기 친구", page_icon="📔", layout="wide")

# CSS를 사용하여 한글 폰트, 채팅 UI 스타일, 그리고 만든이 정보 스타일 적용
st.markdown("""
<style>
    /* Nanum Gothic 폰트 로드 */
    @import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@400;700&display=swap');
    /* Pretendard 폰트 로드 */
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    /* 기본 폰트 설정 */
    html, body, [class*="css"] {
        font-family: 'Nanum Gothic', sans-serif;
    }
    /* 채팅 메시지 스타일 */
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
        align-self: flex-end; /* 사용자 메시지를 오른쪽으로 정렬 */
        max-width: 80%; /* 메시지 최대 너비 설정 */
    }
    .chat-message.bot {
        background-color: #475063;
        color: #ffffff;
        align-self: flex-start; /* AI 메시지를 왼쪽으로 정렬 */
        max-width: 80%; /* 메시지 최대 너비 설정 */
    }
    .chat-message .message {
        width: 100%;
    }
    /* 만든이 정보 스타일 */
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

# --- 세션 상태 초기화 ---
if 'openai_client' not in st.session_state:
    st.session_state.openai_client = None
if 'client_init_success' not in st.session_state:
    st.session_state.client_init_success = False
if 'current_client_api_key' not in st.session_state:
    st.session_state.current_client_api_key = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'feedback' not in st.session_state:
    st.session_state.feedback = None
if 'emotion_score' not in st.session_state:
    st.session_state.emotion_score = None

# --- API 키 및 클라이언트 초기화 (사이드바) ---
with st.sidebar:
    st.header("API 설정 🔑")
    user_provided_api_key = st.text_input(
        "OpenAI API 키를 입력하세요:",
        type="password",
        help="키를 입력하지 않으면 환경 변수(.env 파일)의 키를 사용합니다."
    )

    final_api_key = None
    if user_provided_api_key:
        final_api_key = user_provided_api_key
    elif OPENAI_API_KEY_FROM_ENV:
        final_api_key = OPENAI_API_KEY_FROM_ENV

    if final_api_key:
        if st.session_state.current_client_api_key != final_api_key or not st.session_state.client_init_success:
            st.sidebar.info("OpenAI 클라이언트 초기화를 시도합니다...")
            try:
                # ==================================================================
                # OpenAI 클라이언트 초기화 방식 변경
                # 이전 코드:
                # custom_http_client = httpx.Client(proxies=None)
                # st.session_state.openai_client = OpenAI(
                # api_key=final_api_key,
                # http_client=custom_http_client
                # )
                # 변경된 코드: OpenAI 라이브러리가 내부 기본 httpx 클라이언트를 사용하도록 함
                st.session_state.openai_client = OpenAI(
                    api_key=final_api_key
                )
                # ==================================================================
                
                st.session_state.current_client_api_key = final_api_key
                st.session_state.client_init_success = True # 우선 성공으로 간주, 실제 API 호출 시 최종 확인
                st.sidebar.success("OpenAI 클라이언트가 성공적으로 초기화되었습니다! (실제 API 사용 시 유효성 최종 확인)")


            except TypeError as te:
                error_message = f"OpenAI 클라이언트 초기화 실패 (TypeError): {te}\n"
                if "got an unexpected keyword argument 'proxies'" in str(te) or "Client.__init__()" in str(te):
                    error_message += (
                        "**이 오류는 `OpenAI` 라이브러리 버전 또는 `httpx`와의 호환성 문제일 가능성이 높습니다.**\n"
                        "1. **`requirements.txt` 파일에서 `openai`와 `httpx`를 최신 안정 버전으로 명시했는지 확인해주세요.** (예: `openai>=1.20.0`, `httpx>=0.27.0`)\n"
                        "2. GitHub에 변경사항을 푸시한 후, Streamlit Cloud 앱을 **재부팅(Reboot)**하고, 필요한 경우 **빌드 캐시를 삭제(Clear build cache)** 해보세요.\n"
                        "3. 현재 코드는 `OpenAI(api_key=...)` 방식으로 클라이언트를 초기화하고 있습니다. 이 방식이 최신 라이브러리 버전과 호환되어야 합니다."
                    )
                else: # 기타 TypeError
                     error_message += (
                        "**이 오류는 `OpenAI` 라이브러리 버전이 오래되었거나 호환되지 않을 수 있음을 나타냅니다.**\n"
                        "1. **`requirements.txt`에서 `openai`와 `httpx` 버전을 확인하고 최신 버전으로 업데이트 후 Streamlit Cloud 앱을 재부팅해주세요.**\n"
                    )
                st.sidebar.error(error_message)
                st.session_state.openai_client = None
                st.session_state.current_client_api_key = None 
                st.session_state.client_init_success = False
            except Exception as e: 
                st.sidebar.error(f"OpenAI 클라이언트 초기화 중 예상치 못한 오류 발생: {e}")
                st.session_state.openai_client = None
                st.session_state.current_client_api_key = None 
                st.session_state.client_init_success = False
        elif st.session_state.client_init_success: 
            st.sidebar.info("OpenAI 클라이언트가 이미 초기화되어 있습니다.")
    else: 
        if st.session_state.client_init_success: 
            st.sidebar.info("API 키가 제거되어 OpenAI 클라이언트가 비활성화되었습니다.")
        st.session_state.openai_client = None 
        st.session_state.current_client_api_key = None
        st.session_state.client_init_success = False

    st.markdown("---")
    st.markdown('<p class="creator-info">만든이: 대전장대초 김진관(닷커넥터)</p>', unsafe_allow_html=True)

# --- 핵심 기능 함수 ---
def analyze_diary(content):
    """일기 내용을 분석하여 감정 점수와 피드백을 반환합니다."""
    if not st.session_state.get('client_init_success', False) or not st.session_state.openai_client:
        st.error("AI 기능을 사용하려면 OpenAI API 키를 설정하고 클라이언트가 성공적으로 초기화되어야 합니다.")
        return None, None
    
    current_client = st.session_state.openai_client
    try:
        score_response = current_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "너는 10대 학생들의 일기를 분석하고 감정을 이해하는 AI야. 일기 내용을 바탕으로 감정 점수를 0에서 10 사이의 정수 숫자로만 응답해줘 (예: 7). 다른 설명이나 문장은 절대 포함하지 마."},
                {"role": "user", "content": f"다음 일기의 감정을 분석하고 감정 점수를 알려줘:\n\n{content}"}
            ]
        )
        emotion_text = score_response.choices[0].message.content.strip()
        
        emotion_score = None
        match_strict = re.fullmatch(r'\s*(\d{1,2})\s*', emotion_text)
        if match_strict:
            score_val = int(match_strict.group(1))
            if 0 <= score_val <= 10:
                emotion_score = score_val
            else:
                st.warning(f"AI가 반환한 감정 점수({score_val})가 유효한 범위(0-10)를 벗어났습니다. AI 응답: '{emotion_text}'")
        
        if emotion_score is None:
            matches_fallback = re.findall(r'\d+', emotion_text)
            if matches_fallback:
                potential_score = int(matches_fallback[-1]) 
                if 0 <= potential_score <= 10:
                    emotion_score = potential_score
                    st.info(f"AI 응답에서 감정 점수를 '{emotion_score}'(으)로 추출했습니다 (폴백 로직 사용). AI 응답: '{emotion_text}'")
                else:
                    st.error(f"AI 응답에서 유효한 감정 점수(0-10)를 추출할 수 없습니다 (폴백). AI 응답: '{emotion_text}'")
                    return None, None
            else:
                st.error(f"AI 응답에서 감정 점수를 찾을 수 없습니다. AI 응답: '{emotion_text}'")
                return None, None

        if emotion_score is None:
            st.error(f"감정 점수를 최종적으로 확정할 수 없었습니다. AI 응답: '{emotion_text}'")
            return None, None

        feedback_response = current_client.chat.completions.create(
            model="gpt-4", 
            messages=[
                {"role": "system", "content": "너는 10대 학생들을 위한 에너지 넘치고 친근한 AI 상담사야. 학생들의 감정을 깊이 이해하고 공감하며, 그들의 눈높이에 맞는 쉬운 언어로 대화해. 격식 없는 친근한 말투를 사용하고, 적절한 이모티콘도 활용해. 상담사로서의 전문성을 유지하면서도 학생들이 편하게 대화할 수 있는 분위기를 만들어줘."},
                {"role": "user", "content": f"내 일기 내용은 다음과 같아. 이 일기에 대해 따뜻하고 친근한 말투로 공감과 격려의 피드백을 해줘:\n\n{content}\n\n(참고: 내 감정 점수는 {emotion_score}/10점이야.)"}
            ]
        )
        feedback = feedback_response.choices[0].message.content.strip()

        st.session_state.feedback = feedback
        st.session_state.emotion_score = emotion_score
        return emotion_score, feedback

    except Exception as e: 
        st.error(f"일기 분석 중 OpenAI API 호출 오류가 발생했어요: {str(e)}")
        return None, None

def plot_emotion_spectrum(score):
    """감정 점수를 Altair 스펙트럼 차트(수평 막대)로 시각화합니다."""
    if score is None:
        return None
    
    # 데이터프레임 생성: y축은 점수, x축은 0으로 고정 (수평 막대이므로 y가 값을 나타냄)
    # 더 명확한 시각화를 위해 전체 스펙트럼 배경과 현재 점수 막대를 분리합니다.
    
    # 전체 스펙트럼 배경 (0-10점 회색 막대)
    source_bg = pd.DataFrame({'category': ['점수'], 'value': [10], 'text_label': ['']}) # 배경용
    
    # 현재 점수 데이터
    source_score = pd.DataFrame({'category': ['점수'], 'value': [score], 'text_label': [str(score)]})
    
    # 점수에 따른 색상 결정
    color = '#4CAF50' if score > 7 else '#FFC107' if score > 3 else '#F44336'

    # 배경 막대 (전체 범위)
    background_bar = alt.Chart(source_bg).mark_bar(
        color='lightgray', # 배경색
        opacity=0.5,
        cornerRadius=5 # 모서리 둥글게
    ).encode(
        x=alt.X('value:Q', 
                scale=alt.Scale(domain=[0, 10]), 
                axis=alt.Axis(title='감정 점수', values=list(range(11)), labelAngle=0, grid=True),
                title="감정 점수 (0-10)"
               ),
        y=alt.Y('category:N', axis=None, title="") # y축 라벨 숨김
    )

    # 현재 점수 막대
    score_bar = alt.Chart(source_score).mark_bar(
        color=color,
        opacity=0.9,
        cornerRadius=5 # 모서리 둥글게
    ).encode(
        x='value:Q', # x축에 현재 점수 값
        y='category:N' # y축은 동일한 카테고리
    )
    
    # 점수 텍스트 (막대 위에 표시)
    score_text = alt.Chart(source_score).mark_text(
        align='left', # 텍스트를 막대 오른쪽에 표시하기 위해 left 정렬
        baseline='middle',
        dx=7, # 막대 오른쪽으로 약간 이동
        fontSize=16,
        fontWeight='bold',
        color=color 
    ).encode(
        x='value:Q', # x 위치는 점수 값
        y='category:N', # y 위치는 카테고리
        text='text_label:N' # 표시할 텍스트
    )

    # 차트 레이어링: 배경 -> 점수 막대 -> 점수 텍스트
    # 너비와 높이 설정
    # title 파라미터는 mark_* 가 아닌 Chart() 에 직접 적용
    chart = alt.layer(
        background_bar, 
        score_bar, 
        score_text
    ).properties(
        title=alt.TitleParams(
            text='나의 감정 스펙트럼', 
            anchor='middle', 
            fontSize=18,
            dy=-15 # 제목 위치 조정
        ),
        height=alt.Step(40) # 막대의 높이 (카테고리별 간격)
    ).configure_view(
        strokeWidth=0 # 차트 전체 테두리 제거
    )
    
    return chart


def get_emotion_circle(score):
    """감정 점수에 따라 이모티콘 동그라미를 반환합니다."""
    if score is None: return "❓"
    if score <= 3: return "🔴" 
    elif score <= 7: return "🟡" 
    else: return "🟢" 

def chat_with_ai(message_history):
    """AI와 채팅 응답을 생성합니다."""
    if not st.session_state.get('client_init_success', False) or not st.session_state.openai_client:
        st.error("AI 기능을 사용하려면 OpenAI API 키를 설정하고 클라이언트가 성공적으로 초기화되어야 합니다.")
        return None
    
    current_client = st.session_state.openai_client
    formatted_messages = [{"role": "system", "content": "너는 10대 학생들을 위한 에너지 넘치고 친근한 AI 상담사야. 학생들의 감정을 깊이 이해하고 공감하며, 그들의 눈높이에 맞는 쉬운 언어로 대화해. 격식 없는 친근한 말투를 사용하고, 적절한 이모티콘도 활용해. 이전 대화 내용을 참고하여 자연스럽게 이어가줘."}]
    for role, content in message_history:
        formatted_messages.append({"role": "user" if role == "User" else "assistant", "content": content})

    try:
        response = current_client.chat.completions.create(
            model="gpt-4", 
            messages=formatted_messages
        )
        return response.choices[0].message.content.strip()
    except Exception as e: 
        st.error(f"채팅 중 OpenAI API 호출 오류가 발생했어요: {str(e)}")
        return None

# --- UI 구성 ---
st.title('AI 일기 친구 🤖📔')

if not st.session_state.get('client_init_success', False) and not final_api_key: 
    st.warning("⚠️ OpenAI API 키를 설정해주세요. 왼쪽 사이드바에서 API 키를 입력하고 초기화를 시도해주세요. 키가 없으면 AI 기능이 작동하지 않습니다.")
elif not st.session_state.get('client_init_success', False) and final_api_key: 
    st.error("⚠️ OpenAI 클라이언트 초기화에 실패했습니다. 입력하신 API 키가 유효한지, 네트워크 연결에 문제가 없는지 확인해주세요. 사이드바의 오류 메시지를 참고하세요.")


st.markdown("""
안녕하세요! 저는 당신의 일기를 읽고 감정을 이해하며 함께 이야기 나눌 AI 친구예요.  
오늘 하루 어떤 일이 있었는지, 어떤 감정을 느꼈는지 솔직하게 적어보세요.  
'분석하기' 버튼을 누르면 당신의 감정을 분석하고 따뜻한 응원 메시지를 보내드릴게요.  
그 후에는 저와 자유롭게 대화를 이어갈 수 있답니다! 😊
""")

diary_content = st.text_area("오늘의 일기를 자유롭게 써보세요:", height=250, placeholder="여기에 일기를 작성해주세요...", key="diary_input")

if st.button("✏️ 일기 분석하기", type="primary", key="analyze_button"):
    if not st.session_state.get('client_init_success', False) or not st.session_state.openai_client:
        st.error("먼저 사이드바에서 OpenAI API 키를 설정하고 클라이언트 초기화를 성공적으로 완료해주세요.")
    elif not diary_content.strip(): 
        st.warning("일기 내용을 입력해주세요! ✍️")
    else:
        with st.spinner('AI가 당신의 일기를 열심히 읽고 있어요... 🤔'):
            emotion_score, feedback = analyze_diary(diary_content)
        
        if emotion_score is not None and feedback is not None:
            st.session_state.chat_history = [] 
            st.session_state.chat_history.append(("AI", feedback)) 
            st.success("일기 분석 완료! 아래에서 결과를 확인하고 대화를 시작해보세요. 👇")

if st.session_state.emotion_score is not None:
    st.subheader('📊 나의 감정 분석 결과')
    emotion_circle = get_emotion_circle(st.session_state.emotion_score)
    
    emotion_category = "알 수 없음"
    if st.session_state.emotion_score <= 3: emotion_category = "조금 힘든 날"
    elif st.session_state.emotion_score <= 7: emotion_category = "그럭저럭 괜찮은 날"
    else: emotion_category = "기분 좋은 날!"

    st.markdown(f"**감정 점수:** **{st.session_state.emotion_score}점** / 10점 - _{emotion_category}_ {emotion_circle}")

    altair_chart = plot_emotion_spectrum(st.session_state.emotion_score)
    if altair_chart:
        st.altair_chart(altair_chart, use_container_width=True)
    st.markdown("---")

if st.session_state.get('client_init_success', False) and st.session_state.openai_client:
    st.subheader('💬 AI 친구와 더 이야기하기')

    chat_display_container = st.container() 
    with chat_display_container:
        for role, message in st.session_state.chat_history:
            if role == "User":
                st.markdown(f'<div class="chat-message user"><div class="message">👤 **나:** {message}</div></div>', unsafe_allow_html=True)
            else: 
                st.markdown(f'<div class="chat-message bot"><div class="message">🤖 **AI:** {message}</div></div>', unsafe_allow_html=True)

    def handle_chat_submit():
        user_message = st.session_state.get("chat_input_text", "")
        if user_message.strip():
            st.session_state.chat_history.append(("User", user_message))
            with st.spinner("AI가 답변을 생각하고 있어요... 🤔"):
                ai_response = chat_with_ai(st.session_state.chat_history) 
            
            if ai_response:
                st.session_state.chat_history.append(("AI", ai_response))
            st.session_state.chat_input_text = "" 
    
    st.text_input(
        "AI에게 메시지를 보내보세요:", 
        key="chat_input_text", 
        on_change=handle_chat_submit,
        placeholder="하고 싶은 말을 자유롭게 적고 Enter를 누르세요..."
    )
else:
    if st.session_state.emotion_score is not None: 
        st.info("AI와 대화를 계속하려면 사이드바에서 유효한 OpenAI API 키를 설정하고 클라이언트 초기화를 완료해주세요.")

st.markdown("<br><br>", unsafe_allow_html=True)
