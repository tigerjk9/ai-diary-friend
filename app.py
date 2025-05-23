import streamlit as st
import altair as alt
import pandas as pd
from openai import OpenAI
import os
import re
from dotenv import load_dotenv
import httpx # httpx import 추가

# .env 파일에서 환경 변수 로드
load_dotenv()

# --- 초기 설정 ---
# OpenAI 클라이언트 및 API 키 관련 변수
client = None # 전역 변수로 client 선언
OPENAI_API_KEY_FROM_ENV = os.getenv('OPENAI_API_KEY')

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

    # 세션 상태에 클라이언트 초기화 성공 여부 저장 변수 초기화
    if 'client_init_success' not in st.session_state:
        st.session_state.client_init_success = False
    if 'current_client_api_key' not in st.session_state:
        st.session_state.current_client_api_key = None

    if final_api_key:
        # API 키가 변경되었거나, 클라이언트가 아직 초기화되지 않은 경우 (또는 이전에 초기화 실패한 경우)
        if st.session_state.current_client_api_key != final_api_key or not st.session_state.client_init_success:
            st.sidebar.info("OpenAI 클라이언트 초기화를 시도합니다...")
            try:
                # OpenAI 클라이언트 초기화 시도
                # 중요: 아래 오류 발생 시 가장 먼저 확인할 사항:
                # 1. OpenAI 라이브러리 버전: 터미널/명령 프롬프트에서 `pip show openai` 실행하여 버전 확인.
                #    `openai` 버전 1.0.0 이상이어야 합니다. 낮다면 `pip install --upgrade openai`로 업그레이드하세요.
                # 2. 프록시 설정: 만약 회사 네트워크 등 프록시 환경에 있다면, 시스템 환경변수(HTTP_PROXY, HTTPS_PROXY) 설정이
                #    영향을 줄 수 있습니다. 아래 `custom_http_client` 설정을 통해 프록시를 명시적으로 제어할 수 있습니다.

                # 옵션 1: 표준 httpx 클라이언트 사용 (시스템 프록시 자동 감지)
                # custom_http_client = httpx.Client()

                # 옵션 2: 프록시 사용 안 함 (시스템 프록시 무시) - 프록시 관련 문제 발생 시 시도
                custom_http_client = httpx.Client(proxies=None)
                
                # 옵션 3: 특정 프록시 명시적 설정
                # proxies = {"http://": "http://your-proxy-url:port", "https://": "https://your-proxy-url:port"}
                # custom_http_client = httpx.Client(proxies=proxies)

                # 전역 client 변수에 할당
                globals()['client'] = OpenAI(
                    api_key=final_api_key,
                    http_client=custom_http_client # 명시적으로 http_client 전달
                )
                st.session_state.current_client_api_key = final_api_key
                st.session_state.client_init_success = True
                st.sidebar.success("OpenAI 클라이언트가 성공적으로 초기화되었습니다! 🎉")
            
            except TypeError as te:
                error_message = f"OpenAI 클라이언트 초기화 실패 (TypeError): {te}\n"
                if "got an unexpected keyword argument 'proxies'" in str(te):
                    error_message += ("**이 오류는 `OpenAI` 라이브러리 버전이 매우 오래되었거나, "
                                      "프록시 설정과 관련된 예기치 않은 문제일 수 있습니다.**\n"
                                      "1. **터미널에서 `pip install --upgrade openai` 명령을 실행하여 라이브러리를 최신 버전으로 업그레이드해주세요.** (권장)\n"
                                      "2. 만약 프록시 환경 문제로 의심된다면, 코드 내에서 `custom_http_client = httpx.Client(proxies=None)` 설정을 확인해보세요.\n"
                                      "3. 그래도 문제가 지속되면 시스템 환경 변수(HTTP_PROXY, HTTPS_PROXY) 설정을 점검해주세요.")
                st.sidebar.error(error_message)
                globals()['client'] = None
                st.session_state.current_client_api_key = None # 실패 시 현재 키 정보도 초기화
                st.session_state.client_init_success = False
            except Exception as e:
                st.sidebar.error(f"OpenAI 클라이언트 초기화 중 예상치 못한 오류 발생: {e}")
                globals()['client'] = None
                st.session_state.current_client_api_key = None # 실패 시 현재 키 정보도 초기화
                st.session_state.client_init_success = False
        elif st.session_state.client_init_success: # 이미 성공적으로 초기화된 경우
             st.sidebar.info("OpenAI 클라이언트가 이미 초기화되어 있습니다.")


    else: # API 키가 없는 경우
        if st.session_state.client_init_success: # 이전에 성공했으나 키가 제거된 경우
            st.sidebar.info("API 키가 제거되어 OpenAI 클라이언트가 비활성화되었습니다.")
        globals()['client'] = None # client를 None으로 설정
        st.session_state.current_client_api_key = None
        st.session_state.client_init_success = False


    st.markdown("---")
    st.markdown('<p class="creator-info">만든이: 대전장대초 김진관(닷커넥터)</p>', unsafe_allow_html=True)


# --- 세션 상태 초기화 ---
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'feedback' not in st.session_state:
    st.session_state.feedback = None
if 'emotion_score' not in st.session_state:
    st.session_state.emotion_score = None

# --- 핵심 기능 함수 ---
def analyze_diary(content):
    """일기 내용을 분석하여 감정 점수와 피드백을 반환합니다."""
    # client 변수가 로컬 스코프에 없을 수 있으므로 globals()를 통해 접근
    current_client = globals().get('client')
    if not st.session_state.get('client_init_success', False) or not current_client:
        st.error("AI 기능을 사용하려면 OpenAI API 키를 설정하고 클라이언트가 성공적으로 초기화되어야 합니다.")
        return None, None
    try:
        # 감정 점수 분석 요청
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
            score = int(match_strict.group(1))
            if 0 <= score <= 10:
                emotion_score = score
            else:
                st.warning(f"AI가 반환한 감정 점수({score})가 유효한 범위(0-10)를 벗어났습니다. AI 응답: '{emotion_text}'")
        
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

        # AI 피드백 생성 요청
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
        st.error(f"일기 분석 중 오류가 발생했어요: {str(e)}")
        return None, None

def plot_emotion_spectrum(score):
    """감정 점수를 Altair 스펙트럼 차트로 시각화합니다."""
    if score is None:
        return None
    df = pd.DataFrame({'x': [0, score], 'y': [0, 0], 'score': [score, score]})
    
    color_scale = alt.Scale(
        domain=[0, 3, 7, 10],
        range=['#F44336', '#FFC107', '#4CAF50', '#4CAF50'] # 마지막 색상 중복으로 경계값 처리
    )
    color = '#4CAF50' if score > 7 else '#FFC107' if score > 3 else '#F44336'


    chart = alt.Chart(df).mark_line(
        # color=alt.Color('score:Q', scale=color_scale, legend=None), # 점수에 따른 색상 변화 시도 (단일 선에는 부적합)
        color=color, # 단일 색상 사용
        strokeWidth=15, 
        opacity=0.8,
        strokeCap='round' 
    ).encode(
        x=alt.X('x:Q', scale=alt.Scale(domain=[0, 10]), axis=alt.Axis(title='감정 점수 (0-10)', values=list(range(11)), labelAngle=0)),
        y=alt.Y('y:Q', axis=None),
        tooltip=[alt.Tooltip('score:Q', title='현재 점수')]
    ).properties(
        width=alt.Step(50), 
        height=50, 
        title=alt.TitleParams(text='나의 감정 스펙트럼', anchor='middle', fontSize=16)
    )
    
    text = alt.Chart(pd.DataFrame({'x': [score], 'y': [0], 'text': [f'{score}']})).mark_text(
        align='center',
        baseline='middle', 
        dy=-25, 
        fontSize=18, 
        fontWeight='bold',
        color=color
    ).encode(
        x='x:Q',
        y='y:Q',
        text='text:N'
    )
    return chart + text

def get_emotion_circle(score):
    """감정 점수에 따라 이모티콘 동그라미를 반환합니다."""
    if score is None: return "❓"
    if score <= 3: return "🔴"
    elif score <= 7: return "🟡"
    else: return "🟢"

def chat_with_ai(message_history):
    """AI와 채팅 응답을 생성합니다."""
    current_client = globals().get('client')
    if not st.session_state.get('client_init_success', False) or not current_client:
        st.error("AI 기능을 사용하려면 OpenAI API 키를 설정하고 클라이언트가 성공적으로 초기화되어야 합니다.")
        return None
    
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
        st.error(f"채팅 중 오류가 발생했어요: {str(e)}")
        return None

# --- UI 구성 ---
st.title('AI 일기 친구 �📔')

if not st.session_state.get('client_init_success', False):
    st.warning("⚠️ OpenAI API 키가 설정되지 않았거나 클라이언트 초기화에 실패했습니다. 왼쪽 사이드바에서 API 키를 입력하고 초기화를 시도해주세요. 키가 없으면 AI 기능이 작동하지 않습니다.")

st.markdown("""
안녕하세요! 저는 당신의 일기를 읽고 감정을 이해하며 함께 이야기 나눌 AI 친구예요.  
오늘 하루 어떤 일이 있었는지, 어떤 감정을 느꼈는지 솔직하게 적어보세요.  
'분석하기' 버튼을 누르면 당신의 감정을 분석하고 따뜻한 응원 메시지를 보내드릴게요.  
그 후에는 저와 자유롭게 대화를 이어갈 수 있답니다! 😊
""")

diary_content = st.text_area("오늘의 일기를 자유롭게 써보세요:", height=250, placeholder="여기에 일기를 작성해주세요...")

if st.button("✏️ 일기 분석하기", type="primary"):
    current_client = globals().get('client') # client 확인
    if not st.session_state.get('client_init_success', False) or not current_client:
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
        # analyze_diary 내부에서 오류 메시지 처리

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

current_client = globals().get('client') # client 확인
if st.session_state.get('client_init_success', False) and current_client:
    st.subheader('💬 AI 친구와 더 이야기하기')

    chat_container = st.container() 
    with chat_container:
        for role, message in st.session_state.chat_history:
            if role == "User":
                st.markdown(f'<div class="chat-message user"><div class="message">👤 **나:** {message}</div></div>', unsafe_allow_html=True)
            else: 
                st.markdown(f'<div class="chat-message bot"><div class="message">🤖 **AI:** {message}</div></div>', unsafe_allow_html=True)

    def handle_chat_submit():
        user_message = st.session_state.get("chat_input_text", "")
        if user_message:
            st.session_state.chat_history.append(("User", user_message))
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
�
