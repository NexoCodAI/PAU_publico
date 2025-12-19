import reflex as rx
import datetime
import pytz
import os
from supabase import create_client, Client

# ==========================================
# 1. CONFIGURACIÓN Y CONSTANTES
# ==========================================

# ⚠️ REEMPLAZA ESTO CON TUS CREDENCIALES DE SUPABASE
SUPABASE_URL = "TU_URL_DE_SUPABASE_AQUI"
SUPABASE_KEY = "TU_KEY_ANON_DE_SUPABASE_AQUI"

# Configuración del Syllabus (Copiado de tu script original)
DEFAULT_SYLLABUS = {
    "Matemáticas II": {"category": "science", "topics": [
        "1. Límites y Continuidad", "2. Derivadas", "3. Representación de Funciones", 
        "4. Integral Indefinida", "5. Integral Definida", "6. Matrices", 
        "7. Determinantes", "8. Sistemas de Ecuaciones", "9. Vectores", 
        "10. Rectas y Planos", "11. Posiciones Relativas", "12. Ángulos y Distancias"
    ]},
    "Física": {"category": "science", "topics": [
        "Herramientas matemáticas", "Vibraciones: M.A.S.", "Ondas Mecánicas", 
        "Óptica Geométrica", "Campo Gravitatorio", "Campo Eléctrico", 
        "Campo Magnético", "Inducción Electromagnética", "Física Moderna", 
        "Física Cuántica", "Física Nuclear"
    ]},
    "Química": {"category": "science", "topics": [
        "T1: Estructura de la materia", "T2: Enlace Químico", "T3: Termoquímica", 
        "T4: Cinética Química", "T5: Equilibrio Químico", "T6: Reacciones Ácido-Base", 
        "T7: Reacciones REDOX", "T8: Química del Carbono"
    ]},
    "Historia de España": {"category": "memory", "topics": [
        "Tema 1: Prehistoria", "Tema 2: Edad Media", "Tema 3: Edad Moderna", 
        "Tema 4: Crisis Antiguo Régimen", "Tema 5: Estado Liberal", 
        "Tema 6: Restauración", "Tema 7: SXIX Econ/Soc", "Tema 8: Alfonso XIII", 
        "Tema 9: Segunda República", "Tema 10: Guerra Civil", "Tema 11: Franquismo", 
        "Tema 12: Transición", "Tema 13: Democracia", "Tema 14: Europa", "Tema 15: Mundo"
    ]},
    "Inglés": {"category": "skills", "topics": [
        "Grammar: Tenses Mix", "Grammar: Reported Speech", "Grammar: Conditionals", 
        "Writing: Opinion Essay", "Reading Practice"
    ]}
}

# ==========================================
# 2. ESTADO (STATE) - CEREBRO DE LA APP
# ==========================================

class State(rx.State):
    # --- Variables de Sesión ---
    auth_token: str = rx.Cookie("")
    user_id: str = ""
    is_logged_in: bool = False
    
    # --- Variables de la App ---
    topics: list[dict] = []
    notes: list[dict] = []
    current_block_name: str = "Cargando..."
    current_block_type: str = "free"
    time_remaining: str = "--:--"
    target_hour_display: str = ""
    
    # --- Freemium Logic ---
    is_premium: bool = False  # Cambiar esto con lógica de Stripe en el futuro
    
    # --- Input Variables ---
    email: str = ""
    password: str = ""
    new_note_text: str = ""
    search_query: str = ""
    error_report_text: str = ""

    # ================= FUNCIONES DE SUPABASE =================
    
    @property
    def supabase(self) -> Client:
        return create_client(SUPABASE_URL, SUPABASE_KEY)

    def login(self):
        """Inicia sesión con Supabase Auth"""
        try:
            res = self.supabase.auth.sign_in_with_password({"email": self.email, "password": self.password})
            self.auth_token = res.session.access_token
            self.user_id = res.user.id
            self.is_logged_in = True
            self.check_initial_data()
            self.load_data()
        except Exception as e:
            return rx.window_alert(f"Error de login: {str(e)}")

    def logout(self):
        self.auth_token = ""
        self.is_logged_in = False
        self.topics = []

    def check_initial_data(self):
        """Si el usuario es nuevo, inyecta el Syllabus por defecto en la BD"""
        # Verificamos si tiene datos
        res = self.supabase.table("topics").select("id").eq("user_id", self.user_id).execute()
        if len(res.data) == 0:
            # Inserción masiva inicial
            bulk_data = []
            for subj, info in DEFAULT_SYLLABUS.items():
                for topic_name in info["topics"]:
                    bulk_data.append({
                        "user_id": self.user_id,
                        "subject": subj,
                        "name": topic_name,
                        "category": info["category"],
                        "unlocked": False,
                        "level": 0,
                        "next_review": str(datetime.date.today())
                    })
            self.supabase.table("topics").insert(bulk_data).execute()

    def load_data(self):
        """Descarga temas y notas de Supabase"""
        if not self.is_logged_in: return
        
        # Cargar Temas
        t_res = self.supabase.table("topics").select("*").eq("user_id", self.user_id).order("id").execute()
        self.topics = t_res.data
        
        # Cargar Notas
        n_res = self.supabase.table("notes").select("*").eq("user_id", self.user_id).order("created_at", desc=True).execute()
        self.notes = n_res.data

    # ================= FUNCIONES DE LÓGICA =================

    def update_clock(self):
        """Calcula el bloque actual (Lógica portada de tu script)"""
        tz = pytz.timezone('Europe/Madrid')
        now = datetime.datetime.now(tz)
        weekday = now.weekday()
        hour = now.hour + now.minute / 60.0

        b_type, b_name, duration, end_h = "free", "⏳ Tiempo Libre", 0, 0.0

        # Implementación simplificada de tu lógica de horarios
        if weekday in [0, 1, 2, 3]: # L-J
            if 16.0 <= hour < 17.5: b_type, b_name, end_h = "science", "🔄 Tareas / Estudio", 17.5
            elif 17.5 <= hour < 19.0: b_type, b_name, end_h = "gym", "🏋️ Gimnasio", 19.0
            elif 19.0 <= hour < 20.5: b_type, b_name, end_h = "science", "🧪 Bloque Ciencia", 20.5
            elif 21.5 <= hour < 23.0: b_type, b_name, end_h = "memory", "🧠 Bloque Memoria", 23.0
            elif hour >= 23.0: b_type, b_name, end_h = "sleep", "😴 Dormir", 24.0
        elif weekday == 5: # Sábado
            if 9.5 <= hour < 13.5: b_type, b_name, end_h = "simulacro", "📝 SIMULACRO REAL", 13.5
        
        self.current_block_name = b_name
        self.current_block_type = b_type
        
        if end_h > 0:
            target_dt = now.replace(hour=int(end_h), minute=int((end_h % 1) * 60), second=0)
            diff = target_dt - now
            if diff.total_seconds() > 0:
                mins, secs = divmod(diff.total_seconds(), 60)
                hours, mins = divmod(mins, 60)
                self.time_remaining = f"{int(hours):02}:{int(mins):02}:{int(secs):02}"
                self.target_hour_display = f"Fin: {int(end_h):02}:{int((end_h % 1) * 60):02}"
            else:
                self.time_remaining = "00:00:00"

    def review_topic(self, topic_id: int, rating: str):
        """Algoritmo de Repaso Espaciado (Leitner)"""
        # Encontrar el tema en la lista local para actualizar rápido UI
        topic_idx = next((i for i, t in enumerate(self.topics) if t["id"] == topic_id), -1)
        if topic_idx == -1: return

        topic = self.topics[topic_idx]
        new_level = topic["level"]
        extra_q = False
        today = datetime.date.today()
        
        if rating == "ok":
            new_level = min(topic["level"] + 1, 5)
            days = (new_level * 5) + 3
            next_rev = today + datetime.timedelta(days=days)
        elif rating == "mid":
            days = 3
            next_rev = today + datetime.timedelta(days=days)
        elif rating == "bad":
            new_level = 1
            days = 1
            next_rev = today + datetime.timedelta(days=days)
            # Marcar para reporte de error (se maneja en UI)
            
        # Actualizar DB
        self.supabase.table("topics").update({
            "level": new_level,
            "next_review": str(next_rev),
            "extra_queue": False
        }).eq("id", topic_id).execute()
        
        # Actualizar Local
        self.load_data()

    def report_fail(self, topic_id: int, error_text: str):
        self.supabase.table("topics").update({"last_error": error_text}).eq("id", topic_id).execute()
        self.load_data()

    def clear_error(self, topic_id: int):
        self.supabase.table("topics").update({"last_error": ""}).eq("id", topic_id).execute()
        self.load_data()

    def toggle_unlock(self, topic_id: int, current_val: bool):
        self.supabase.table("topics").update({"unlocked": not current_val}).eq("id", topic_id).execute()
        self.load_data()

    def add_note(self):
        if self.new_note_text:
            self.supabase.table("notes").insert({"user_id": self.user_id, "text": self.new_note_text}).execute()
            self.new_note_text = ""
            self.load_data()
    
    def delete_note(self, note_id: int):
        self.supabase.table("notes").delete().eq("id", note_id).execute()
        self.load_data()

# ==========================================
# 3. INTERFAZ GRÁFICA (UI) - MODERNA
# ==========================================

def login_page():
    return rx.center(
        rx.card(
            rx.vstack(
                rx.heading("PAU Elite Login", size="6"),
                rx.input(placeholder="Email", on_change=State.set_email),
                rx.input(placeholder="Password", type="password", on_change=State.set_password),
                rx.button("Entrar", on_click=State.login, width="100%", size="3"),
                rx.text("Si no tienes cuenta, regístrate en Supabase o implementa sign-up.", font_size="xs", color="gray"),
            ),
            padding="2em",
            width="400px"
        ),
        height="100vh",
        background="#0a0a0a"
    )

def clock_widget():
    return rx.box(
        rx.vstack(
            rx.text("TIEMPO RESTANTE BLOQUE", font_size="0.7em", letter_spacing="2px", color="gray"),
            rx.heading(State.time_remaining, font_size="3em", color="#ff4b4b", font_weight="bold"),
            rx.text(State.target_hour_display, font_size="0.9em", color="gray"),
            align_items="center",
            spacing="1"
        ),
        padding="1.5em",
        border="1px solid #333",
        border_radius="15px",
        background="#111",
        width="100%",
        # Hook para actualizar el reloj cada segundo
        on_mount=State.update_clock
    )

def task_card(topic: dict):
    """Tarjeta de tarea pendiente"""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.badge(topic["subject"], color_scheme="purple"),
                rx.spacer(),
                rx.cond(topic["last_error"] != "", rx.badge("⚠️ Error Previo", color_scheme="red"))
            ),
            rx.heading(topic["name"], size="4"),
            rx.progress(value=topic["level"]*20, width="100%", color_scheme="tomato"),
            rx.divider(),
            rx.hstack(
                rx.button("✅ Bien", on_click=lambda: State.review_topic(topic["id"], "ok"), flex="1", color_scheme="green"),
                rx.button("🆗 Normal", on_click=lambda: State.review_topic(topic["id"], "mid"), flex="1", color_scheme="gray"),
                rx.button("❌ Mal", on_click=lambda: State.review_topic(topic["id"], "bad"), flex="1", color_scheme="red"),
                width="100%"
            ),
            # Input de error condicional podría ir aquí con un Dialog
        ),
        margin_bottom="1em"
    )

def syllabus_row(topic: dict):
    return rx.hstack(
        rx.checkbox(
            checked=topic["unlocked"], 
            on_change=lambda x: State.toggle_unlock(topic["id"], topic["unlocked"])
        ),
        rx.text(topic["name"], font_weight="medium"),
        rx.spacer(),
        rx.badge(f"Lv. {topic['level']}", variant="outline"),
        width="100%",
        padding="0.5em",
        border_bottom="1px solid #222"
    )

def main_dashboard():
    # Filtro de Tareas Pendientes
    today_str = datetime.date.today().isoformat()
    
    # Esta lambda filtra en Python, idealmente se haría en DB pero para MVP está bien
    # rx.foreach no soporta iteradores complejos, así que State.topics debe iterarse
    return rx.hstack(
        # --- SIDEBAR ---
        rx.vstack(
            rx.heading("🎓 PAU ELITE", size="5", margin_bottom="1em"),
            clock_widget(),
            rx.divider(margin_y="1em"),
            rx.text(State.current_block_name, font_weight="bold", color="white"),
            rx.spacer(),
            rx.button("Cerrar Sesión", on_click=State.logout, variant="ghost", color_scheme="gray"),
            width="250px",
            height="100vh",
            padding="1.5em",
            background="#0e0e0e",
            border_right="1px solid #333",
            position="sticky",
            top="0"
        ),
        
        # --- CONTENIDO PRINCIPAL ---
        rx.container(
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger("🚀 Agenda", value="tab1"),
                    rx.tabs.trigger("📚 Temario", value="tab2"),
                    rx.tabs.trigger("📓 Notas", value="tab3"),
                ),
                rx.tabs.content(
                    rx.vstack(
                        rx.heading(f"Misión: {State.current_block_name}", size="6", margin_y="0.5em"),
                        # Lista de tareas (Simulamos filtrado visualizando todos los pendientes)
                        rx.foreach(
                            State.topics,
                            lambda t: rx.cond(
                                (t["unlocked"] & (t["next_review"] <= today_str)),
                                task_card(t),
                                rx.box() # Return empty if not due
                            )
                        ),
                        width="100%"
                    ),
                    value="tab1",
                    padding="1em"
                ),
                rx.tabs.content(
                    rx.vstack(
                        rx.heading("Gestión de Temario", size="5"),
                        rx.input(placeholder="Buscar tema...", on_change=State.set_search_query),
                        rx.foreach(
                            State.topics,
                            syllabus_row
                        )
                    ),
                    value="tab2",
                    padding="1em"
                ),
                rx.tabs.content(
                    rx.vstack(
                        rx.heading("Notas Rápidas", size="5"),
                        rx.hstack(
                            rx.input(placeholder="Nueva nota...", on_change=State.set_new_note_text, value=State.new_note_text),
                            rx.button("Añadir", on_click=State.add_note)
                        ),
                        rx.foreach(
                            State.notes,
                            lambda n: rx.hstack(
                                rx.text(n["text"]),
                                rx.spacer(),
                                rx.button("🗑️", on_click=lambda: State.delete_note(n["id"]), variant="ghost", color_scheme="red"),
                                width="100%",
                                border_bottom="1px solid #333",
                                padding="0.5em"
                            )
                        )
                    ),
                    value="tab3",
                    padding="1em"
                ),
                default_value="tab1",
                width="100%"
            ),
            max_width="900px",
            padding_top="2em"
        ),
        background="#111",
        min_height="100vh",
        align_items="start"
    )

def index():
    # Usamos un rx.cond para mostrar Login o Dashboard
    return rx.cond(
        State.is_logged_in,
        main_dashboard(),
        login_page()
    )

# ==========================================
# 4. LANZAMIENTO
# ==========================================

app = rx.App(
    theme=rx.theme(
        appearance="dark", 
        accent_color="tomato", 
        radius="large"
    )
)
app.add_page(index)
