import streamlit as st
import altair as alt
import pandas as pd
import os
import re
from openai import OpenAI

# ... (이전 코드는 그대로 유지)

# 감정 스펙트럼 시각화 (Altair 사용) - 개선된 버전
def plot_emotion_spectrum(score):
    # 기본 데이터 생성
    base_data = pd.DataFrame({
        'x': range(11),
        'y': [0] * 11
    })

    # 스펙트럼 색상 데이터
    color_scale = alt.Scale(
        domain=[0, 5, 10],
        range=['#F44336', '#FFC107', '#4CAF50']
    )

    # 기본 스펙트럼 차트
    base_chart = alt.Chart(base_data).mark_line(
        strokeWidth=10
    ).encode(
        x=alt.X('x:Q', scale=alt.Scale(domain=[0, 10]), axis=alt.Axis(title='감정 점수', values=list(range(11)))),
        y='y:Q',
        color=alt.Color('x:Q', scale=color_scale, legend=None)
    )

    # 현재 점수 표시
    score_data = pd.DataFrame({'x': [score], 'y': [0]})
    score_point = alt.Chart(score_data).mark_circle(
        size=200,
        color='black'
    ).encode(
        x='x:Q',
        y='y:Q'
    )

    score_text = alt.Chart(score_data).mark_text(
        align='center',
        baseline='bottom',
        dy=-15,
        fontSize=20,
        fontWeight='bold'
    ).encode(
        x='x:Q',
        y='y:Q',
        text=alt.value(f'{score}')
    )

    # 라벨 추가
    label_data = pd.DataFrame({
        'x': [0, 5, 10],
        'y': [0, 0, 0],
        'label': ['나쁨', '보통', '좋음']
    })

    labels = alt.Chart(label_data).mark_text(
        align='center',
        baseline='top',
        dy=20,
        fontSize=14
    ).encode(
        x='x:Q',
        y='y:Q',
        text='label'
    )

    # 차트 조합
    final_chart = (base_chart + score_point + score_text + labels).properties(
        width=600,
        height=100,
        title='감정 스펙트럼'
    )

    return final_chart

# ... (나머지 코드는 그대로 유지)
