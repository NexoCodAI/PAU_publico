# main.py
import streamlit as st
import datetime
import time
from config import PAGE_CONFIG, CUSTOM_CSS, DEFAULT_SYLLABUS
from database import login_user, add_user, get_user_data, save_user_data
from logic import get_current_block_info, calculate_next_review
from ui import show_kpi_metrics, render_subject_progress

# 1. Configuración Inicial
st.set_page_config(**PAGE_CONFIG)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# 2. Gestión de Estado de Sesión
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# 3. Función Principal de la App (Dashboard)
def run_dashboard():
    user = st.session_state['username']
    is_premium = st.session_state['is_premium']
    
    if 'data' not in st.session_state:
        st.session_state.data = get_user_data(user)
    data = st.session_state.data
    
    block_name, block_type, block_color = get_current_block_info()
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.title("🎓 PAU TRACKER")
        if is_premium:
            st.markdown('<div style="background: linear-gradient(90deg, #FFD700, #FFA500); padding: 10px; border-radius: 10px; text-align: center; font-weight: bold;">🌟 ELITE MEMBER</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="background: #2c3e50; padding: 10px; border-radius: 10px; text-align: center;">👤 FREE PLAN</div>', unsafe_allow_html=True)
        
        st.markdown(f"Hola, **{user}**")
        st.markdown("---")
        st.markdown(f"### 🕒 Ahora: {block_name}")
        st.caption(f"Enfoque sugerido: {block_type}")
        st.progress(0.5)
        st.markdown("---")
        
        if not is_premium:
            with st.container(border=True):
                st.markdown("**🚀 PÁSATE A ELITE**")
                st.caption("Desbloquea tareas ilimitadas.")
                st.button("💎 ACTUALIZAR", type="primary")
        
        if st.button("🚪 Cerrar Sesión"):
            st.session_state['logged_in'] = False
            st.rerun()
    
    # --- MAIN CONTENT ---
    st.markdown(f"# Tu Panel de Control")
    show_kpi_metrics(data)
    
    tab_agenda, tab_temario, tab_stats, tab_pomodoro = st.tabs(
        ["📅 Agenda Hoy", "📚 Temario", "📊 Estadísticas", "⏱️ Pomodoro"]
    )
    
    # --- TAB 1: AGENDA ---
    with tab_agenda:
        st.subheader("📝 Tareas de Repaso Pendientes")
        today = str(datetime.date.today())
        tasks = []
        
        for subj, topics in data.items():
            if subj in ["general_notes", "pomodoro_stats"]: continue
            for i, t in enumerate(topics):
                if t["unlocked"] and t["next_review"] <= today:
                    tasks.append({"subj": subj, "topic": t, "idx": i})
        
        if not tasks:
            st.success("🎉 ¡Todo limpio! Has completado tus repasos de hoy.")
            st.balloons()
        else:
            limit = 999 if is_premium else 3
            if not is_premium and len(tasks) > limit:
                st.warning(f"🔒 Tienes {len(tasks)} tareas, pero el plan GRATIS muestra 3.")
            
            for i, task in enumerate(tasks[:limit]):
                t = task['topic']
                s = task['subj']
                with st.container(border=True):
                    c1, c2 = st.columns([0.7, 0.3])
                    with c1:
                        st.markdown(f"**{t['icon']} {s}**")
                        st.markdown(f"### {t['name']}")
                        st.caption(f"Nivel actual: {t['level']}/5")
                        st.progress(t['level']/5)
                    with c2:
                        st.write("")
                        if st.button("✅ BIEN", key=f"ok_{s}_{i}", type="primary"):
                            t["level"] = min(t["level"] + 1, 5)
                            t["next_review"] = calculate_next_review(t["level"])
                            t["last_review"] = today
                            save_user_data(user, data)
                            st.toast("¡Buen trabajo!", icon="📅")
                            time.sleep(0.5)
                            st.rerun()
                        if st.button("❌ MAL", key=f"bad_{s}_{i}"):
                            t["level"] = max(1, t["level"] - 1)
                            t["next_review"] = str(datetime.date.today() + datetime.timedelta(days=1))
                            save_user_data(user, data)
                            st.toast("Repasamos mañana.", icon="💪")
                            time.sleep(0.5)
                            st.rerun()

    # --- TAB 2: TEMARIO ---
    with tab_temario:
        st.info("Activa los temas vistos en clase.")
        for subj_name, info in DEFAULT_SYLLABUS.items():
            user_topics = data.get(subj_name, [])
            with st.expander(f"{info['icon']} {subj_name}"):
                for i, t in enumerate(user_topics):
                    col_check, col_name, col_lvl = st.columns([0.1, 0.7, 0.2])
                    is_checked = col_check.checkbox("Activar", value=t["unlocked"], key=f"chk_{subj_name}_{i}", label_visibility="collapsed")
                    if is_checked != t["unlocked"]:
                        t["unlocked"] = is_checked
                        if is_checked: t["next_review"] = str(datetime.date.today())
                        save_user_data(user, data)
                        st.rerun()
                    col_name.write(t["name"])
                    col_lvl.caption(f"Nvl {t['level']}" if t["unlocked"] else "🔒")

    # --- TAB 3: ESTADÍSTICAS ---
    with tab_stats:
        st.subheader("📈 Tu Evolución")
        render_subject_progress(data)

    # --- TAB 4: POMODORO ---
    with tab_pomodoro:
        st.subheader("⏱️ Focus Timer")
        st.markdown("<div style='text-align: center; font-size: 4rem; font-weight: bold;'>25:00</div>", unsafe_allow_html=True)
        if st.button("▶️ START"): st.toast("Temporizador iniciado")

# 4. Flujo de Login / Registro
if not st.session_state['logged_in']:
    col_center = st.columns([1, 2, 1])
    with col_center[1]:
        st.title("🎓 PAU TRACKER")
        tab_login, tab_reg = st.tabs(["Entrar", "Crear Cuenta"])
        
        with tab_login:
            username = st.text_input("Usuario", key="l_user")
            password = st.text_input("Contraseña", type='password', key="l_pass")
            if st.button("Iniciar Sesión", type="primary"):
                user_result = login_user(username, password)
                if user_result:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.session_state['is_premium'] = bool(user_result[0][2])
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
        
        with tab_reg:
            new_user = st.text_input("Elige Usuario", key="r_user")
            new_pass = st.text_input("Elige Contraseña", type='password', key="r_pass")
            if st.button("Registrarse"):
                if len(new_pass) < 4:
                    st.warning("Contraseña muy corta.")
                else:
                    if add_user(new_user, new_pass):
                        st.success("¡Cuenta creada! Inicia sesión.")
                    else:
                        st.error("Error al crear usuario.")
else:
    run_dashboard()
