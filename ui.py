# ui.py
import streamlit as st
import pandas as pd
import datetime

def show_kpi_metrics(data):
    total_topics = 0
    mastered_topics = 0
    pending_today = 0
    today = str(datetime.date.today())
    
    for subj, topics in data.items():
        if subj in ["general_notes", "pomodoro_stats"]:
            continue
        for t in topics:
            if t["unlocked"]:
                total_topics += 1
            if t["level"] >= 4:
                mastered_topics += 1
            if t["next_review"] <= today:
                pending_today += 1
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Tareas para hoy", pending_today, delta_color="inverse")
    c2.metric("Temas Desbloqueados", total_topics)
    c3.metric("Temas Dominados", mastered_topics)

def render_subject_progress(data):
    progress_data = []
    for subj, topics in data.items():
        if subj in ["general_notes", "pomodoro_stats"]:
            continue
        total = len(topics)
        unlocked = sum(1 for t in topics if t["unlocked"])
        progress_data.append({"Asignatura": subj, "Progreso": (unlocked/total)*100})
    
    df = pd.DataFrame(progress_data)
    st.dataframe(
        df.style.bar(subset=["Progreso"], color='#ff4b4b', vmin=0, vmax=100),
        use_container_width=True,
        hide_index=True
    )
