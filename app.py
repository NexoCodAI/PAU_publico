import streamlit as st
import json
import datetime
import time
import pytz
import hashlib
import pandas as pd
from streamlit.components.v1 import html as components_html

# Manejo robusto de psycopg2
try:
    import psycopg2
    DB_AVAILABLE = True
except ImportError as e:
    st.error(f"⚠️ Error al importar psycopg2: {e}")
    st.info("💡 Asegúrate de tener 'packages.txt' con libpq-dev en tu repositorio")
    DB_AVAILABLE = False
    psycopg2 = None

# ========================================== 
# 1. CONFIGURACIÓN Y ESTILO (LOOK & FEEL PREMIUM) 
# ========================================== 
st.set_page_config(
    page_title="PAU TRACKER ELITE",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Paleta de colores y CSS personalizado
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: bold;
    }
    div[data-testid="stExpander"] {
        background-color: rgba(255,255,255,0.05);
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ========================================== 
# 2. BASE DE DATOS MAESTRA (TEMARIO COMPLETO) 
# ========================================== 
DEFAULT_SYLLABUS = {
    "Matemáticas II": {
        "category": "science",
        "icon": "📐",
        "topics": [
            "Matrices y Determinantes", "Sistemas de Ecuaciones", "Vectores en el Espacio",
            "Rectas y Planos", "Problemas Métricos (Distancias/Ángulos)", "Límites y Continuidad",
            "Derivadas y Aplicaciones", "Representación de Funciones", "Integrales Indefinidas",
            "Integrales Definidas y Áreas", "Probabilidad", "Estadística"
        ]
    },
    "Física": {
        "category": "science",
        "icon": "⚡",
        "topics": [
            "Interacción Gravitatoria", "Campo Eléctrico", "Campo Magnético",
            "Inducción Electromagnética", "Movimiento Armónico Simple", "Movimiento Ondulatorio",
            "Óptica Geométrica", "Física Relativista", "Física Cuántica", "Física Nuclear"
        ]
    },
    "Química": {
        "category": "science",
        "icon": "🧪",
        "topics": [
            "Estructura Atómica", "Sistema Periódico", "Enlace Químico", "Termoquímica",
            "Cinética Química", "Equilibrio Químico", "Reacciones Ácido-Base",
            "Reacciones REDOX", "Química Orgánica: Formulación", "Química Orgánica: Reactividad"
        ]
    },
    "Historia de España": {
        "category": "memory",
        "icon": "🏰",
        "topics": [
            "Raíces Históricas (Prehistoria-Reyes Católicos)", "Siglo XVI y XVII (Austrias)",
            "Siglo XVIII (Borbones)", "Crisis del Antiguo Régimen (1808-1833)",
            "Construcción Estado Liberal (1833-1868)", "Sexenio Democrático (1868-1874)",
            "La Restauración (1875-1902)", "Crisis de la Restauración (1902-1931)",
            "II República (1931-1936)", "Guerra Civil (1936-1939)",
            "Franquismo (1939-1975)", "Transición y Democracia"
        ]
    },
    "Lengua y Literatura": {
        "category": "skills",
        "icon": "📖",
        "topics": [
            "Morfología", "Sintaxis: Oración Simple", "Sintaxis: Oración Compuesta",
            "Coherencia y Cohesión", "Tipología Textual", "Literatura S.XX (Poesía)",
            "Literatura S.XX (Novela)", "Literatura S.XX (Teatro)",
            "Generación del 98", "Generación del 27"
        ]
    },
    "Inglés": {
        "category": "skills",
        "icon": "🇬🇧",
        "topics": [
            "Tenses Mix", "Passive Voice", "Reported Speech", "Conditionals & Wish",
            "Modals", "Relative Clauses", "Connectors", "Writing: Opinion Essay",
            "Writing: Email/Letter", "Reading Comprehension"
        ]
    }
}

# ========================================== 
# 3. GESTIÓN DE BASE DE DATOS (SUPABASE) 
# ========================================== 
def get_db_connection():
    try:
        # Intentamos conectar con los datos del secret
        conn = psycopg2.connect(
            host=st.secrets["supabase"]["host"],
            user=st.secrets["supabase"]["user"],
            password=st.secrets["supabase"]["password"],
            dbname=st.secrets["supabase"]["dbname"],
            port=st.secrets["supabase"]["port"],
            connect_timeout=5
        )
        return conn
    except Exception as e:
        # Si falla, mostramos el error técnico real para saber si es 
        # la contraseña, el host o la red.
        st.error(f"🚨 Error técnico real: {e}")
        return None

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def create_defaults():
    new_data = {"general_notes": [], "pomodoro_stats": {"total_minutes": 0, "sessions": 0}}
    for subject, info in DEFAULT_SYLLABUS.items():
        new_data[subject] = []
        for topic in info["topics"]:
            new_data[subject].append({
                "name": topic,
                "icon": info["icon"],
                "category": info["category"],
                "unlocked": False,
                "level": 0,
                "next_review": str(datetime.date.today()),
                "last_review": None
            })
    return new_data

# --- Funciones de Usuario ---
def add_user(username, password):
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute('INSERT INTO users(username, password, is_premium) VALUES (%s, %s, %s)',
                    (username, make_hashes(password), 0))
        defaults = json.dumps(create_defaults())
        cur.execute('INSERT INTO user_data(username, data) VALUES (%s, %s)', (username, defaults))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except psycopg2.IntegrityError:
        conn.rollback()
        conn.close()
        return False
    except Exception as e:
        st.error(e)
        conn.close()
        return False

def login_user(username, password):
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM users WHERE username = %s AND password = %s',
                    (username, make_hashes(password)))
        data = cur.fetchall()
        cur.close()
        conn.close()
        return data
    except:
        return None

def get_user_data(username):
    conn = get_db_connection()
    if not conn:
        return create_defaults()
    try:
        cur = conn.cursor()
        cur.execute('SELECT data FROM user_data WHERE username = %s', (username,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        if result:
            return json.loads(result[0])
    except:
        pass
    return create_defaults()

def save_user_data(username, data):
    conn = get_db_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        json_data = json.dumps(data)
        cur.execute('UPDATE user_data SET data = %s WHERE username = %s', (json_data, username))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        st.error(f"Error al guardar: {e}")

# ========================================== 
# 4. LÓGICA DE TIEMPO Y ESTUDIO 
# ========================================== 
def get_current_block_info():
    madrid_tz = pytz.timezone('Europe/Madrid')
    now = datetime.datetime.now(madrid_tz)
    hour = now.hour + now.minute / 60.0
    
    if 8 <= hour < 14:
        return "☀️ Mañana de Instituto", "Clases", "#FFD700"
    if 16 <= hour < 18:
        return "🧠 Bloque Intenso", "Ciencias/Práctica", "#ff4b4b"
    if 18 <= hour < 20:
        return "📚 Bloque Memoria", "Historia/Lengua", "#4b9eff"
    if 20 <= hour < 21:
        return "🧘 Repaso y Cierre", "Inglés/Repaso", "#55efc4"
    return "🌙 Descanso", "Tiempo Libre", "#7f8c8d"

def calculate_next_review(level):
    days = [1, 3, 7, 14, 30]
    idx = max(0, min(level - 1, len(days) - 1))
    return str(datetime.date.today() + datetime.timedelta(days=days[idx]))

# ========================================== 
# 5. COMPONENTES DE INTERFAZ 
# ========================================== 
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

# ========================================== 
# 6. APLICACIÓN PRINCIPAL 
# ========================================== 
def main_app():
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
                st.caption("Desbloquea tareas ilimitadas, estadísticas avanzadas y modo foco.")
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
            if subj in ["general_notes", "pomodoro_stats"]:
                continue
            for i, t in enumerate(topics):
                if t["unlocked"] and t["next_review"] <= today:
                    tasks.append({"subj": subj, "topic": t, "idx": i})
        
        if not tasks:
            st.success("🎉 ¡Todo limpio! Has completado tus repasos de hoy.")
            st.balloons()
        else:
            limit = 999 if is_premium else 3
            if not is_premium and len(tasks) > limit:
                st.warning(f"🔒 Tienes {len(tasks)} tareas pendientes, pero el plan GRATIS solo muestra 3.")
            
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
                            st.toast("¡Buen trabajo! Reprogramado.", icon="📅")
                            time.sleep(0.5)
                            st.rerun()
                        if st.button("❌ MAL", key=f"bad_{s}_{i}"):
                            t["level"] = max(1, t["level"] - 1)
                            t["next_review"] = str(datetime.date.today() + datetime.timedelta(days=1))
                            save_user_data(user, data)
                            st.toast("No pasa nada, mañana lo repasamos.", icon="💪")
                            time.sleep(0.5)
                            st.rerun()
    
    # --- TAB 2: TEMARIO ---
    with tab_temario:
        st.info("Aquí activas los temas que has visto en clase para que el sistema empiece a preguntártelos.")
        
        for subj_name, info in DEFAULT_SYLLABUS.items():
            user_topics = data.get(subj_name, [])
            with st.expander(f"{info['icon']} {subj_name}"):
                total = len(user_topics)
                active = sum(1 for t in user_topics if t["unlocked"])
                st.progress(active/total if total > 0 else 0)
                st.caption(f"{active}/{total} temas activados")
                
                for i, t in enumerate(user_topics):
                    col_check, col_name, col_lvl = st.columns([0.1, 0.7, 0.2])
                    is_checked = col_check.checkbox("Activar", value=t["unlocked"], 
                                                    key=f"chk_{subj_name}_{i}", 
                                                    label_visibility="collapsed")
                    if is_checked != t["unlocked"]:
                        t["unlocked"] = is_checked
                        if is_checked:
                            t["next_review"] = str(datetime.date.today())
                        save_user_data(user, data)
                        st.rerun()
                    
                    col_name.write(t["name"])
                    if t["unlocked"]:
                        col_lvl.caption(f"Nvl {t['level']}")
                    else:
                        col_lvl.caption("🔒")
    
    # --- TAB 3: ESTADÍSTICAS ---
    with tab_stats:
        st.subheader("📈 Tu Evolución")
        render_subject_progress(data)
        
        if not is_premium:
            st.info("💡 Desbloquea gráficas de rendimiento histórico y predicción de nota en la versión Elite.")
    
    # --- TAB 4: POMODORO ---
    with tab_pomodoro:
        st.subheader("⏱️ Focus Timer")
        c1, c2, c3 = st.columns(3)
        with c2:
            st.markdown("""
            <div style='text-align: center; padding: 40px; background: rgba(0,0,0,0.3); border-radius: 20px;'>
                <div style='font-size: 4rem; font-weight: bold; color: #fff;'>25:00</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.write("")
        b_col1, b_col2 = st.columns(2)
        if b_col1.button("▶️ START"):
            st.toast("Temporizador iniciado (Simulación)")
        if b_col2.button("⏸️ PAUSE"):
            st.toast("Pausado")

# ========================================== 
# 7. GESTIÓN DE SESIÓN (LOGIN/REGISTER) 
# ========================================== 
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    col_center = st.columns([1, 2, 1])
    with col_center[1]:
        st.title("🎓 PAU TRACKER")
        st.markdown("### Domina la Selectividad.")
        
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
                    st.warning("La contraseña es muy corta.")
                else:
                    if add_user(new_user, new_pass):
                        st.success("¡Cuenta creada! Ahora inicia sesión.")
                    else:
                        st.error("El usuario ya existe o hubo un error.")
else:
    main_app()
