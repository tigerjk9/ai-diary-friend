import streamlit as st
import altair as alt
import pandas as pd
import os
import re
from openai import OpenAI

# ... (이전 코드는 그대로 유지) ...

# 감정 스펙트럼 시각화 (Altair 사용)
def plot_emotion_spectrum(score):
    # 기본 데이터 생성
    base_data = pd.DataFrame({
        'x': range(11),
        'y': [0] * 11
    })

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

# ... (이후 코드는 그대로 유지) ...
