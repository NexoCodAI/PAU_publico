import streamlit as st
import json
import datetime
import time
import pytz
import sqlite3
import hashlib
from streamlit.components.v1 import html as components_html

# ==========================================
# 1. CONFIGURACIÓN Y ESTILO
# ==========================================

st.set_page_config(
    page_title="PAU Tracker Elite", 
    page_icon="🎓", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Constantes del Sistema
MIN_MINUTES_PER_TASK = 40 

# Estilos CSS Personalizados
st.markdown("""
    <style>
    .stButton button { width: 100%; border-radius: 6px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;}
    div[data-testid="stMetricValue"] { font-size: 2.2rem; color: #ff4b4b; font-weight: 700;}
    h1, h2, h3 { font-family: 'Helvetica Neue', sans-serif; }
    .css-1d391kg { padding-top: 1rem; }
    div.stProgress > div > div > div > div { background-color: #ff4b4b; }
    .premium-lock { border: 1px solid #ffd700; padding: 15px; border-radius: 10px; background-color: rgba(255, 215, 0, 0.1); text-align: center; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. BASE DE DATOS (SYLLABUS COMPLETO 2025)
# ==========================================

DEFAULT_SYLLABUS = {
    "Matemáticas II": {
        "category": "science",
        "topics": [
            "1. Límites y Continuidad (Asíntotas, Bolzano)",
            "2. Derivadas (Reglas, L'Hôpital, Rolle/Lagrange)",
            "3. Representación de Funciones (Optimización, Curvatura)",
            "4. Integral Indefinida",
            "5. Integral Definida (Áreas, Barrow)",
            "6. Matrices (Operaciones, Rango, Inversa)",
            "7. Determinantes (Sarrus, Propiedades)",
            "8. Sistemas de Ecuaciones (Gauss, Cramer)",
            "9. Vectores (Producto Escalar, Vectorial)",
            "10. Rectas y Planos",
            "11. Posiciones Relativas",
            "12. Ángulos y Distancias"
        ]
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
        "topics": ["Tenses Mix", "Passive Voice", "Reported Speech", "Conditionals", "Modals", "Connectors", "Writing Essay", "Reading"]
    }
}

# ==========================================
# 3. GESTIÓN DE BASE DE DATOS (SQLITE MULTI-USUARIO)
# ==========================================

def init_db():
    """Inicializa la base de datos local SQLite"""
    conn = sqlite3.connect('pau_tracker.db')
    c = conn.cursor()
    # Tabla usuarios
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT, is_premium INTEGER)''')
    # Tabla datos (json blob por usuario)
    c.execute('''CREATE TABLE IF NOT EXISTS user_data
                 (username TEXT PRIMARY KEY, data TEXT)''')
    conn.commit()
    conn.close()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

def add_user(username, password):
    conn = sqlite3.connect('pau_tracker.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users(username, password, is_premium) VALUES (?,?,?)', 
                  (username, make_hashes(password), 0)) # 0 = Free, 1 = Premium
        conn.commit()
        # Crear datos por defecto
        defaults = create_defaults()
        c.execute('INSERT INTO user_data(username, data) VALUES (?,?)', 
                  (username, json.dumps(defaults)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect('pau_tracker.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, make_hashes(password)))
    data = c.fetchall()
    conn.close()
    return data

def get_user_data(username):
    conn = sqlite3.connect('pau_tracker.db')
    c = conn.cursor()
    c.execute('SELECT data FROM user_data WHERE username = ?', (username,))
    result = c.fetchone()
    conn.close()
    if result:
        return json.loads(result[0])
    return create_defaults()

def save_user_data(username, data):
    conn = sqlite3.connect('pau_tracker.db')
    c = conn.cursor()
    c.execute('UPDATE user_data SET data = ? WHERE username = ?', (json.dumps(data), username))
    conn.commit()
    conn.close()

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

# Inicializar DB al arrancar
init_db()

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

    # Lógica simplificada para ejemplo
    if weekday < 5: # Lunes a Viernes
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
    
    # Cargar datos específicos del usuario
    if 'data' not in st.session_state or st.session_state.get('data_user') != user:
        st.session_state.data = get_user_data(user)
        st.session_state.data_user = user

    data = st.session_state.data
    real_type, block_name, duration, end_hour = get_current_block()

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("PAU TRACKER")
        if is_premium:
            st.caption("🌟 PLAN ELITE (PREMIUM)")
        else:
            st.caption("👤 PLAN GRATUITO")
            if st.button("💎 PASAR A PREMIUM", type="primary"):
                st.markdown("[Click aquí para comprar Licencia](https://stripe.com)", unsafe_allow_html=True)
        
        st.divider()
        show_modern_clock(end_hour)
        
        st.markdown("### Estado")
        # FEATURE PREMUM 1: Modo Intenso
        force_study = st.checkbox("🔥 MODO INTENSO", value=False, disabled=not is_premium)
        if not is_premium and force_study:
            st.warning("Solo usuarios Premium")
            
        st.info(f"**{block_name}**")
        
        if st.button("Cerrar Sesión"):
            st.session_state['logged_in'] = False
            st.rerun()

    # --- TABS ---
    tab1, tab2, tab3, tab4 = st.tabs(["🚀 Agenda", "📚 Temario", "📓 Notas", "⚙️ Ajustes"])

    # === TAB 1: AGENDA ===
    with tab1:
        st.header(f"Plan: {block_name}")
        
        # Algoritmo de Tareas (Simplificado para brevedad)
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
            # FEATURE PREMIUM 2: Ver más de 3 tareas
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
                # Añadir tema nuevo
                n_t = st.text_input(f"Nuevo tema en {subj}", key=f"nt_{subj}")
                if st.button("Añadir", key=f"btn_{subj}") and n_t:
                    data[subj].append({"name": n_t, "category": "memory", "unlocked": True, "level": 0, "next_review": str(datetime.date.today()), "last_error": "", "extra_queue": False})
                    save_user_data(user, data)
                    st.rerun()
                
                # Listar temas
                for i, t in enumerate(data[subj]):
                    chk = st.checkbox(t["name"], value=t["unlocked"], key=f"c_{subj}_{i}")
                    if chk != t["unlocked"]:
                        t["unlocked"] = chk
                        save_user_data(user, data)
                        st.rerun()

    # === TAB 3: NOTAS ===
    with tab3:
        st.subheader("📓 Notas Personales")
        txt = st.text_area("Bloc de notas", value="\n".join([n['text'] for n in data['general_notes']]), height=200)
        if st.button("Guardar Notas"):
            # Lógica simple: reemplazar todo por una nota nueva (mejorar en prod)
            data["general_notes"] = [{"text": txt, "date": str(datetime.date.today())}]
            save_user_data(user, data)
            st.success("Guardado")

    # === TAB 4: AJUSTES & UPGRADE ===
    with tab4:
        st.header("Cuenta")
        st.write(f"Usuario: **{user}**")
        st.write(f"Estado: **{'PREMIUM 🌟' if is_premium else 'GRATIS (Limitado)'}**")
        
        if not is_premium:
            st.markdown("""
            <div class="premium-lock">
                <h3>🚀 Desbloquea PAU TRACKER ELITE</h3>
                <p>Consigue acceso ilimitado a tareas, estadísticas avanzadas y modo foco.</p>
                <p><b>Precio: 9.99€ / Único pago</b></p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("💳 ACTUALIZAR AHORA"):
                st.markdown("Redirigiendo a pasarela de pago...", unsafe_allow_html=True)
                # Aquí iría tu link de Stripe Payment Link
        
        if st.button("Borrar mis datos (Reset)"):
            data = create_defaults()
            save_user_data(user, data)
            st.rerun()

# ==========================================
# 6. GESTIÓN DE SESIÓN (LOGIN/REGISTER)
# ==========================================

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🎓 PAU Tracker | Acceso")
    
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
        st.warning("⚠️ Crea tu cuenta para guardar tu progreso.")
        new_user = st.text_input("Elige un Usuario")
        new_password = st.text_input("Elige una Contraseña", type='password')
        
        if st.button("Crear Cuenta"):
            if add_user(new_user, new_password):
                st.success("Cuenta creada. Ve a 'Iniciar Sesión'.")
                st.balloons()
            else:
                st.error("Ese usuario ya existe.")

else:
    main_app()
