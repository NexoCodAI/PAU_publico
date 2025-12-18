import streamlit as st
import json
import datetime
import time
import pytz
import hashlib
import pandas as pd
import plotly.graph_objects as go
from streamlit.components.v1 import html as components_html

try:
    import psycopg2
    DB_AVAILABLE = True
except ImportError as e:
    st.error(f"⚠️ Error al importar psycopg2: {e}")
    st.info("💡 Asegúrate de tener 'packages.txt' con libpq-dev en tu repositorio")
    DB_AVAILABLE = False
    # Modo fallback sin BD
    psycopg2 = None

# ==========================================
# 1. CONFIGURACIÓN Y ESTILO
# ==========================================

st.set_page_config(
    page_title="PAU Tracker Elite", 
    page_icon="🎓", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Constantes
MIN_MINUTES_PER_TASK = 40 

# Estilos CSS
st.markdown("""
    <style>
    .stButton button { width: 100%; border-radius: 6px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;}
    div[data-testid="stMetricValue"] { font-size: 2.2rem; color: #ff4b4b; font-weight: 700;}
    h1, h2, h3 { font-family: 'Helvetica Neue', sans-serif; }
    .premium-lock { border: 1px solid #ffd700; padding: 15px; border-radius: 10px; background-color: rgba(255, 215, 0, 0.1); text-align: center; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. BASE DE DATOS (SYLLABUS)
# ==========================================

DEFAULT_SYLLABUS = {
    "Matemáticas II": {
        "category": "science",
        "topics": ["Límites y Continuidad", "Derivadas", "Representación Funciones", "Integral Indefinida", "Integral Definida", "Matrices", "Determinantes", "Sistemas Ecuaciones", "Vectores", "Rectas y Planos", "Posiciones Relativas", "Ángulos y Distancias"]
    },
    "Física": {
        "category": "science",
        "topics": ["Vectores", "M.A.S.", "Ondas", "Óptica", "Gravitatorio", "Eléctrico", "Magnético", "Inducción", "Relatividad", "Cuántica", "Nuclear"]
    },
    "Química": {
        "category": "science",
        "topics": ["Estructura materia", "Enlace Químico", "Termoquímica", "Cinética", "Equilibrio", "Ácido-Base", "REDOX", "Orgánica"]
    },
    "Historia de España": {
        "category": "memory",
        "topics": ["Prehistoria", "Edad Media", "Reyes Católicos", "S.XVIII Borbones", "Guerra Independencia", "Isabel II", "Restauración", "II República", "Guerra Civil", "Franquismo", "Transición"]
    },
    "Inglés": {
        "category": "skills",
        "topics": ["Grammar Mix", "Passive Voice", "Reported Speech", "Conditionals", "Writing Essay", "Reading"]
    }
}

# ==========================================
# 3. GESTIÓN DE BASE DE DATOS (SUPABASE / POSTGRESQL)
# ==========================================

# Función para conectar a Supabase usando st.secrets
def get_db_connection():
    try:
        return psycopg2.connect(
            host=st.secrets["supabase"]["DB_HOST"],
            user=st.secrets["supabase"]["DB_USER"],
            password=st.secrets["supabase"]["DB_PASSWORD"],
            dbname=st.secrets["supabase"]["DB_NAME"],
            port=st.secrets["supabase"]["DB_PORT"]
        )
    except Exception as e:
        st.error(f"Error conectando a la base de datos: {e}")
        return None

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def create_defaults():
    new_data = {"general_notes": []}
    for subject, info in DEFAULT_SYLLABUS.items():
        new_data[subject] = []
        for topic in info["topics"]:
            new_data[subject].append({
                "name": topic,
                "category": info["category"],
                "unlocked": False, "level": 0,
                "next_review": str(datetime.date.today()),
                "last_error": "", "extra_queue": False
            })
    return new_data

def add_user(username, password):
    conn = get_db_connection()
    if not conn: return False
    try:
        cur = conn.cursor()
        # 1. Crear usuario
        cur.execute('INSERT INTO users(username, password, is_premium) VALUES (%s, %s, %s)', 
                    (username, make_hashes(password), 0))
        
        # 2. Crear datos por defecto
        defaults = json.dumps(create_defaults())
        cur.execute('INSERT INTO user_data(username, data) VALUES (%s, %s)', 
                    (username, defaults))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except psycopg2.IntegrityError:
        conn.rollback() # Usuario ya existe
        conn.close()
        return False
    except Exception as e:
        st.error(e)
        conn.close()
        return False

def login_user(username, password):
    conn = get_db_connection()
    if not conn: return None
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, make_hashes(password)))
    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

def get_user_data(username):
    conn = get_db_connection()
    if not conn: return create_defaults()
    cur = conn.cursor()
    cur.execute('SELECT data FROM user_data WHERE username = %s', (username,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    if result:
        return json.loads(result[0])
    return create_defaults()

def save_user_data(username, data):
    conn = get_db_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        json_data = json.dumps(data)
        cur.execute('UPDATE user_data SET data = %s WHERE username = %s', (json_data, username))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        st.error(f"Error guardando: {e}")

# ==========================================
# 4. COMPONENTES VISUALES
# ==========================================

def show_modern_clock(target_hour_float):
    if not target_hour_float: return
    th = int(target_hour_float)
    tm = int(round((target_hour_float - th) * 60))
    uid = f"clock_{int(time.time()*1000)}"
    html = f"""
    <div class="clock-container"><div class="clock-box">
      <div class="clock-label">TIEMPO RESTANTE</div>
      <div id="{uid}" class="clock-time">--:--:--</div>
      <div class="clock-target">Objetivo: {th:02d}:{tm:02d}</div>
    </div></div>
    <style>
      .clock-container {{ display: flex; justify-content: center; padding: 5px; font-family: sans-serif; }}
      .clock-box {{ background: #11141c; border: 2px solid #ff4b4b; border-radius: 12px; padding: 10px; text-align: center; width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
      .clock-time {{ font-size: 2rem; font-weight: 700; color: #ff4b4b; margin: 5px 0; }}
      .clock-label {{ color: #cfcfcf; font-size: 0.7rem; letter-spacing: 1.5px; }}
      .clock-target {{ color: #888; font-size: 0.8rem; }}
    </style>
    <script>
    (function(){{
      function update() {{
        const el = document.getElementById("{uid}");
        if(!el) return;
        const now = new Date();
        const target = new Date();
        target.setHours({th}, {tm}, 0, 0);
        let diff = target - now;
        if (diff <= 0) {{ el.innerText = "00:00:00"; return; }}
        const h = Math.floor(diff / 3600000);
        const m = Math.floor((diff % 3600000) / 60000);
        const s = Math.floor((diff % 60000) / 1000);
        el.innerText = (h<10?"0"+h:h) + ":" + (m<10?"0"+m:m) + ":" + (s<10?"0"+s:s);
      }}
      setInterval(update, 1000);
    }})();
    </script>
    """
    components_html(html, height=130, scrolling=False)

def get_current_block():
    madrid_tz = pytz.timezone('Europe/Madrid')
    now = datetime.datetime.now(madrid_tz) 
    weekday = now.weekday() 
    hour = now.hour + now.minute / 60.0

    if weekday < 5: 
        if 16.0 <= hour < 18.0: return "science", "🔄 Bloque Estudio 1", 120, 18.0
        if 18.0 <= hour < 20.0: return "memory", "🧠 Bloque Memoria", 120, 20.0
        if 20.0 <= hour < 21.0: return "break", "🚿 Descanso", 60, 21.0
    return "free", "⏳ Tiempo Libre", 0, 0

# ==========================================
# 5. LÓGICA DE APLICACIÓN
# ==========================================

def main_app():
    user = st.session_state['username']
    is_premium = st.session_state['is_premium']
    
    if 'data' not in st.session_state or st.session_state.get('data_user') != user:
        st.session_state.data = get_user_data(user)
        st.session_state.data_user = user

    data = st.session_state.data
    real_type, block_name, duration, end_hour = get_current_block()

    with st.sidebar:
        st.title("PAU TRACKER")
        if is_premium:
            st.caption("🌟 PLAN ELITE (PREMIUM)")
        else:
            st.caption("👤 PLAN GRATUITO")
            if st.button("💎 PASAR A PREMIUM", type="primary"):
                st.markdown("[Comprar Licencia](https://stripe.com)", unsafe_allow_html=True)
        
        st.divider()
        show_modern_clock(end_hour)
        
        st.markdown("### Estado")
        force_study = st.checkbox("🔥 MODO INTENSO", value=False, disabled=not is_premium)
        if not is_premium and force_study: st.warning("Solo Premium")
            
        st.info(f"**{block_name}**")
        
        if st.button("Cerrar Sesión"):
            st.session_state['logged_in'] = False
            st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(["🚀 Agenda", "📚 Temario", "📓 Notas", "⚙️ Ajustes"])

    # === TAB 1: AGENDA ===
    with tab1:
        st.header(f"Plan: {block_name}")
        tasks = []
        today = str(datetime.date.today())
        for subj, topics in data.items():
            if subj == "general_notes": continue
            for i, t in enumerate(topics):
                if t["unlocked"] and (t["next_review"] <= today or t["extra_queue"]):
                     tasks.append({"s": subj, "t": t, "i": i})
        
        if not tasks:
            st.success("✅ Todo al día. Avanza temario.")
        else:
            limit = 100 if is_premium else 3
            if not is_premium and len(tasks) > 3:
                st.info(f"🔒 Tienes {len(tasks)} tareas. Versión Free limitada a 3.")
            
            for task in tasks[:limit]:
                topic = task["t"]
                with st.container(border=True):
                    c1, c2 = st.columns([0.7, 0.3])
                    c1.markdown(f"**{topic['name']}** ({task['s']})")
                    c1.progress(topic['level']/5)
                    b1, b2, b3 = c2.columns(3)
                    
                    if b1.button("✅", key=f"ok_{task['i']}_{task['s']}"):
                        topic["level"] = min(topic["level"]+1, 5)
                        topic["next_review"] = str(datetime.date.today() + datetime.timedelta(days=topic["level"]*3))
                        save_user_data(user, data)
                        st.rerun()
                    if b3.button("❌", key=f"bad_{task['i']}_{task['s']}"):
                        topic["level"] = 1
                        topic["next_review"] = str(datetime.date.today() + datetime.timedelta(days=1))
                        save_user_data(user, data)
                        st.rerun()

    # === TAB 2: TEMARIO ===
    with tab2:
        st.subheader("📚 Gestión de Temario")
        for subj in [k for k in data.keys() if k != "general_notes"]:
            with st.expander(subj):
                n_t = st.text_input(f"Nuevo tema en {subj}", key=f"nt_{subj}")
                if st.button("Añadir", key=f"btn_{subj}") and n_t:
                    data[subj].append({"name": n_t, "category": "memory", "unlocked": True, "level": 0, "next_review": str(datetime.date.today()), "last_error": "", "extra_queue": False})
                    save_user_data(user, data)
                    st.rerun()
                for i, t in enumerate(data[subj]):
                    chk = st.checkbox(t["name"], value=t["unlocked"], key=f"c_{subj}_{i}")
                    if chk != t["unlocked"]:
                        t["unlocked"] = chk
                        save_user_data(user, data)
                        st.rerun()

    # === TAB 3: NOTAS ===
    with tab3:
        st.subheader("📓 Notas Personales")
        # Asegurar que existe general_notes si la BD es antigua
        if "general_notes" not in data: data["general_notes"] = []
        
        current_notes = "\n".join([n.get('text', '') for n in data['general_notes']])
        txt = st.text_area("Bloc de notas", value=current_notes, height=200)
        
        if st.button("Guardar Notas"):
            data["general_notes"] = [{"text": txt, "date": str(datetime.date.today())}]
            save_user_data(user, data)
            st.success("Guardado")

    # === TAB 4: AJUSTES ===
    with tab4:
        st.header("Cuenta")
        st.write(f"Usuario: **{user}**")
        st.write(f"Estado: **{'PREMIUM 🌟' if is_premium else 'GRATIS'}**")
        
        if not is_premium:
            st.markdown("""
            <div class="premium-lock">
                <h3>🚀 Desbloquea PAU TRACKER ELITE</h3>
                <p>Acceso ilimitado a tareas y modo foco.</p>
            </div>
            """, unsafe_allow_html=True)
            st.button("💳 ACTUALIZAR AHORA")

        if st.button("Borrar mis datos (Reset)"):
            data = create_defaults()
            save_user_data(user, data)
            st.rerun()

# ==========================================
# 6. GESTIÓN DE SESIÓN
# ==========================================

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🎓 PAU Tracker | Acceso Cloud")
    choice = st.selectbox("Menu", ["Iniciar Sesión", "Registrarse"])
    
    if choice == "Iniciar Sesión":
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type='password')
        if st.button("Entrar"):
            user_result = login_user(username, password)
            if user_result:
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.session_state['is_premium'] = bool(user_result[0][2])
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
                
    elif choice == "Registrarse":
        new_user = st.text_input("Elige un Usuario")
        new_password = st.text_input("Elige una Contraseña", type='password')
        if st.button("Crear Cuenta"):
            if add_user(new_user, new_password):
                st.success("Cuenta creada. Ve a 'Iniciar Sesión'.")
                st.balloons()
            else:
                st.error("Error: Usuario ya existe o fallo de conexión.")

else:
    main_app()
