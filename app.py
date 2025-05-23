# -*- coding: utf-8 -*-
# 위 라인은 파일 최상단에 추가하여 UTF-8 인코딩을 명시하는 것이 좋습니다.
# 또는, 파일을 저장할 때 반드시 UTF-8 인코딩으로 저장해주세요.

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
# OpenAI 클라이언트, 초기화 성공 여부, 현재 사용된 API 키를 세션 상태에 저장
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

    # 사용할 최종 API 키 결정
    final_api_key = None
    if user_provided_api_key:
        final_api_key = user_provided_api_key
    elif OPENAI_API_KEY_FROM_ENV:
        final_api_key = OPENAI_API_KEY_FROM_ENV

    # API 키가 있거나 변경된 경우 클라이언트 (재)초기화
    if final_api_key:
        if st.session_state.current_client_api_key != final_api_key or not st.session_state.client_init_success:
            st.sidebar.info("OpenAI 클라이언트 초기화를 시도합니다...")
            try:
                # 프록시 문제 발생 시도 (시스템 프록시 무시)
                # 필요한 경우, 특정 프록시 서버 주소를 설정할 수 있습니다. 예: proxies={"http://": "http://proxy.example.com:8080", "https://": "https://proxy.example.com:8080"}
                custom_http_client = httpx.Client(proxies=None) 
                
                st.session_state.openai_client = OpenAI(
                    api_key=final_api_key,
                    http_client=custom_http_client # 명시적으로 http_client 전달
                )
                # 테스트 API 호출 (예: 모델 목록 가져오기)로 키 유효성 검사 (선택 사항이지만 권장)
                # st.session_state.openai_client.models.list() # 이 부분은 실제 API 호출을 발생시키므로, 필요에 따라 주석 처리 또는 활성화

                st.session_state.current_client_api_key = final_api_key
                st.session_state.client_init_success = True
                st.sidebar.success("OpenAI 클라이언트가 성공적으로 초기화되었습니다! 🎉")
            
            except TypeError as te:
                # OpenAI 라이브러리 버전 관련 TypeError 처리
                error_message = f"OpenAI 클라이언트 초기화 실패 (TypeError): {te}\n"
                if "got an unexpected keyword argument 'proxies'" in str(te) or "unexpected keyword argument 'http_client'" in str(te):
                    error_message += (
                        "**이 오류는 `OpenAI` 라이브러리 버전이 오래되었거나 호환되지 않을 수 있음을 나타냅니다.**\n"
                        "1. **터미널에서 `pip install --upgrade openai httpx` 명령을 실행하여 라이브러리를 최신 버전으로 업그레이드해주세요.** (권장)\n"
                        "2. 만약 프록시 환경 문제로 의심된다면, 코드 내에서 `custom_http_client = httpx.Client(proxies=...)` 설정을 확인해보세요.\n"
                        "3. 그래도 문제가 지속되면 시스템 환경 변수(HTTP_PROXY, HTTPS_PROXY) 설정을 점검해주세요."
                    )
                st.sidebar.error(error_message)
                st.session_state.openai_client = None
                st.session_state.current_client_api_key = None 
                st.session_state.client_init_success = False
            except Exception as e:
                # 기타 예외 처리 (API 키 오류, 네트워크 오류 등)
                st.sidebar.error(f"OpenAI 클라이언트 초기화 중 예상치 못한 오류 발생: {e}")
                st.session_state.openai_client = None
                st.session_state.current_client_api_key = None 
                st.session_state.client_init_success = False
        elif st.session_state.client_init_success: 
            st.sidebar.info("OpenAI 클라이언트가 이미 초기화되어 있습니다.")
    else: 
        # API 키가 없는 경우 클라이언트 비활성화
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
        # 감정 점수 분석 요청
        score_response = current_client.chat.completions.create(
            model="gpt-4", # 또는 "gpt-3.5-turbo" 등 사용 가능한 모델
            messages=[
                {"role": "system", "content": "너는 10대 학생들의 일기를 분석하고 감정을 이해하는 AI야. 일기 내용을 바탕으로 감정 점수를 0에서 10 사이의 정수 숫자로만 응답해줘 (예: 7). 다른 설명이나 문장은 절대 포함하지 마."},
                {"role": "user", "content": f"다음 일기의 감정을 분석하고 감정 점수를 알려줘:\n\n{content}"}
            ]
        )
        emotion_text = score_response.choices[0].message.content.strip()
        
        emotion_score = None
        # 1. 정확히 숫자만 있는지 확인 (예: "7")
        match_strict = re.fullmatch(r'\s*(\d{1,2})\s*', emotion_text)
        if match_strict:
            score = int(match_strict.group(1))
            if 0 <= score <= 10:
                emotion_score = score
            else:
                st.warning(f"AI가 반환한 감정 점수({score})가 유효한 범위(0-10)를 벗어났습니다. AI 응답: '{emotion_text}'")
        
        # 2. 만약 위에서 못 찾았으면, 응답에서 숫자 추출 시도 (예: "감정 점수는 7점입니다.")
        if emotion_score is None:
            matches_fallback = re.findall(r'\d+', emotion_text)
            if matches_fallback:
                # 여러 숫자가 있다면 마지막 숫자를 점수로 가정 (가장 가능성 높은 시나리오)
                potential_score = int(matches_fallback[-1]) 
                if 0 <= potential_score <= 10:
                    emotion_score = potential_score
                    st.info(f"AI 응답에서 감정 점수를 '{emotion_score}'(으)로 추출했습니다 (폴백 로직 사용). AI 응답: '{emotion_text}'")
                else:
                    st.error(f"AI 응답에서 유효한 감정 점수(0-10)를 추출할 수 없습니다 (폴백). AI 응답: '{emotion_text}'")
                    return None, None # 점수 추출 실패 시 여기서 중단
            else:
                st.error(f"AI 응답에서 감정 점수를 찾을 수 없습니다. AI 응답: '{emotion_text}'")
                return None, None # 점수 추출 실패 시 여기서 중단

        # 최종적으로 점수 확정 실패 시
        if emotion_score is None:
            st.error(f"감정 점수를 최종적으로 확정할 수 없었습니다. AI 응답: '{emotion_text}'")
            return None, None

        # 피드백 요청
        feedback_response = current_client.chat.completions.create(
            model="gpt-4", # 또는 "gpt-3.5-turbo"
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
        # 오류 발생 시 어떤 API 호출에서 문제였는지 파악하기 위해 추가 정보 로깅 가능
        # 예: print(f"Error during OpenAI API call: {e}") 
        return None, None

def plot_emotion_spectrum(score):
    """감정 점수를 Altair 스펙트럼 차트로 시각화합니다."""
    if score is None:
        return None
    
    # 데이터프레임 생성: x축은 0부터 score까지, y는 0으로 고정
    df = pd.DataFrame({'x_start': [0], 'x_end': [score], 'y': [0], 'score': [score]})
    
    # 점수에 따른 색상 결정
    color = '#4CAF50' if score > 7 else '#FFC107' if score > 3 else '#F44336'

    # 라인 차트 생성
    line_chart = alt.Chart(df).mark_rule( # mark_line 대신 mark_rule 사용 고려 (단일 선분) 또는 mark_bar
        color=color, 
        strokeWidth=15, 
        opacity=0.8,
        strokeCap='round' 
    ).encode(
        x=alt.X('x_start:Q', scale=alt.Scale(domain=[0, 10]), axis=alt.Axis(title='감정 점수 (0-10)', values=list(range(11)), labelAngle=0, grid=False), title=""),
        x2='x_end:Q',
        y=alt.Y('y:Q', axis=None),
        tooltip=[alt.Tooltip('score:Q', title='현재 점수')]
    ).properties(
        width='container', # use_container_width=True 와 유사하게 동작
        height=50, 
        title=alt.TitleParams(text='나의 감정 스펙트럼', anchor='middle', fontSize=16, dy=-10) # dy로 타이틀 위치 조정
    )
    
    # 점수 텍스트 추가
    text_mark = alt.Chart(pd.DataFrame({'x': [score], 'y': [0], 'text': [f'{score}']})).mark_text(
        align='center',
        baseline='middle', 
        dy=-25, # 텍스트 위치 조정 (라인 위로)
        fontSize=18, 
        fontWeight='bold',
        color=color
    ).encode(
        x='x:Q',
        y='y:Q',
        text='text:N'
    )
    
    # 차트와 텍스트 결합
    # Altair는 layer 연산자를 사용하여 차트를 겹칠 수 있습니다.
    # 여기서는 라인 위에 텍스트가 오도록 구성합니다.
    # 단, mark_rule은 x, x2를 사용하므로, 텍스트 위치를 정확히 맞추려면 x축 스케일을 공유해야 합니다.
    # 더 간단하게는, st.altair_chart 이후에 st.markdown으로 점수를 표시하는 방법도 있습니다.
    # 여기서는 차트 내에 포함하는 시도를 유지합니다.
    
    # x축의 위치를 명확히 하기 위해 point 마크를 투명하게 추가하고 그 위에 텍스트를 올리는 방법도 고려할 수 있습니다.
    # 또는, 라인 차트의 데이터를 [0, score]로 하고, 텍스트는 score 위치에만 표시합니다.
    # 현재 코드는 라인과 텍스트를 별도로 생성 후 더하는 방식인데, x축 스케일 공유가 중요합니다.
    # plot_emotion_spectrum 함수는 현재 구조로도 동작할 수 있으나, Altair의 layer 기능을 사용하면 더 정교한 제어가 가능합니다.
    # 예시: return alt.layer(line_chart, text_mark).resolve_scale(x='shared')
    
    # 현재 방식(덧셈)으로도 대부분의 경우 잘 동작합니다.
    return line_chart + text_mark


def get_emotion_circle(score):
    """감정 점수에 따라 이모티콘 동그라미를 반환합니다."""
    if score is None: return "❓"
    if score <= 3: return "🔴" # 슬픔, 우울
    elif score <= 7: return "🟡" # 보통, 그럭저럭
    else: return "🟢" # 기쁨, 긍정

def chat_with_ai(message_history):
    """AI와 채팅 응답을 생성합니다."""
    if not st.session_state.get('client_init_success', False) or not st.session_state.openai_client:
        st.error("AI 기능을 사용하려면 OpenAI API 키를 설정하고 클라이언트가 성공적으로 초기화되어야 합니다.")
        return None
    
    current_client = st.session_state.openai_client
    
    # OpenAI API에 전달할 메시지 형식으로 변환
    formatted_messages = [{"role": "system", "content": "너는 10대 학생들을 위한 에너지 넘치고 친근한 AI 상담사야. 학생들의 감정을 깊이 이해하고 공감하며, 그들의 눈높이에 맞는 쉬운 언어로 대화해. 격식 없는 친근한 말투를 사용하고, 적절한 이모티콘도 활용해. 이전 대화 내용을 참고하여 자연스럽게 이어가줘."}]
    for role, content in message_history:
        # 사용자의 이전 메시지는 "user", AI의 이전 메시지는 "assistant" 역할로 전달
        formatted_messages.append({"role": "user" if role == "User" else "assistant", "content": content})

    try:
        response = current_client.chat.completions.create(
            model="gpt-4", # 또는 "gpt-3.5-turbo"
            messages=formatted_messages
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"채팅 중 오류가 발생했어요: {str(e)}")
        return None

# --- UI 구성 ---
st.title('AI 일기 친구 🤖📔')

# API 키 설정 및 클라이언트 초기화 상태에 따른 안내 메시지
if not st.session_state.get('client_init_success', False):
    st.warning("⚠️ OpenAI API 키가 설정되지 않았거나 클라이언트 초기화에 실패했습니다. 왼쪽 사이드바에서 API 키를 입력하고 초기화를 시도해주세요. 키가 없으면 AI 기능이 작동하지 않습니다.")

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
    elif not diary_content.strip(): # strip()으로 공백만 있는 경우도 체크
        st.warning("일기 내용을 입력해주세요! ✍️")
    else:
        with st.spinner('AI가 당신의 일기를 열심히 읽고 있어요... 🤔'):
            emotion_score, feedback = analyze_diary(diary_content)
        
        if emotion_score is not None and feedback is not None:
            # 분석 성공 시, 이전 채팅 기록 초기화 및 새 피드백으로 시작
            st.session_state.chat_history = [] 
            st.session_state.chat_history.append(("AI", feedback)) 
            st.success("일기 분석 완료! 아래에서 결과를 확인하고 대화를 시작해보세요. 👇")
            # 분석 후 일기 내용 초기화 (선택 사항)
            # st.session_state.diary_input = "" 


# 감정 분석 결과 표시
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

# 채팅 인터페이스
if st.session_state.get('client_init_success', False) and st.session_state.openai_client:
    st.subheader('💬 AI 친구와 더 이야기하기')

    # 채팅 메시지 표시 영역
    chat_display_container = st.container() 
    with chat_display_container:
        for role, message in st.session_state.chat_history:
            if role == "User":
                # HTML/CSS를 사용한 메시지 표시
                st.markdown(f'<div class="chat-message user"><div class="message">👤 **나:** {message}</div></div>', unsafe_allow_html=True)
            else: 
                st.markdown(f'<div class="chat-message bot"><div class="message">🤖 **AI:** {message}</div></div>', unsafe_allow_html=True)

    # 채팅 입력 처리 함수
    def handle_chat_submit():
        user_message = st.session_state.get("chat_input_text", "")
        if user_message.strip(): # 공백만 있는 메시지 방지
            st.session_state.chat_history.append(("User", user_message))
            # AI 응답 생성 중 스피너 표시 (선택 사항)
            with st.spinner("AI가 답변을 생각하고 있어요... 🤔"):
                ai_response = chat_with_ai(st.session_state.chat_history) 
            
            if ai_response:
                st.session_state.chat_history.append(("AI", ai_response))
            else:
                # AI 응답 실패 시 사용자에게 알림 (chat_with_ai 함수 내에서 st.error로 이미 처리될 수 있음)
                # st.warning("AI 응답을 받지 못했습니다. 다시 시도해주세요.")
                pass # chat_with_ai 내부에서 오류 메시지 표시
            st.session_state.chat_input_text = "" # 입력 필드 초기화
        else:
            # 빈 메시지 입력 시 경고 (선택 사항)
            # st.toast("메시지를 입력해주세요.", icon="✍️") 
            pass


    # 채팅 입력 필드
    # 사용자가 Enter를 누르거나 포커스를 잃을 때 on_change가 호출될 수 있습니다.
    # 버튼을 사용하거나, st.chat_input을 사용하는 것을 고려할 수 있습니다.
    # 현재 코드는 on_change를 사용합니다.
    # 파일 인코딩 문제 (U+FFFD)는 이 부분의 코드를 직접 타이핑하거나,
    # 파일 전체가 UTF-8로 올바르게 저장되었는지 확인하는 것이 중요합니다.
    st.text_input(
        "AI에게 메시지를 보내보세요:", 
        key="chat_input_text", 
        on_change=handle_chat_submit, # Enter 키 입력 시 콜백 실행
        placeholder="하고 싶은 말을 자유롭게 적고 Enter를 누르세요..."
    )
    
    # 만약 Enter 키 대신 버튼으로 전송하고 싶다면:
    # user_input_for_button = st.text_input("AI에게 메시지를 보내보세요:", key="chat_input_for_button_key", placeholder="하고 싶은 말을 자유롭게 적으세요...")
    # if st.button("전송", key="send_chat_button"):
    #    if user_input_for_button.strip():
    #        st.session_state.chat_history.append(("User", user_input_for_button))
    #        # ... (ai 응답 로직) ...
    #        st.rerun() # UI 즉시 업데이트

else:
    # API 키가 설정되지 않았지만, 이전에 분석 결과가 있는 경우 안내
    if st.session_state.emotion_score is not None: 
        st.info("AI와 대화를 계속하려면 사이드바에서 유효한 OpenAI API 키를 설정하고 클라이언트 초기화를 완료해주세요.")

# 페이지 하단 여백
st.markdown("<br><br>", unsafe_allow_html=True)

# 디버깅을 위한 추가 정보 (선택 사항):
# st.write("Current session state:", st.session_state)
