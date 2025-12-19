import reflex as rx
import datetime
import pytz
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURACIÓN ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# --- DATOS POR DEFECTO ---
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
# 🧠 STATE (Lógica del Negocio)
# ==========================================

class State(rx.State):
    # Sesión
    auth_token: str = rx.Cookie("")
    user_id: str = ""
    is_logged_in: bool = False
    
    # Datos Principales
    topics: list[dict] = []
    notes: list[dict] = []
    
    # Estado del Dashboard
    current_block_name: str = "Cargando..."
    current_block_type: str = "free"
    time_remaining: str = "--:--"
    target_hour_display: str = ""
    
    # Freemium
    is_premium: bool = False 
    show_upgrade_dialog: bool = False

    # Inputs
    email: str = ""
    password: str = ""
    new_note_text: str = ""
    search_query: str = ""

    # --- COMPUTED VARS (LA SOLUCIÓN AL ERROR) ---
    
    @rx.var
    def tasks_due(self) -> list[dict]:
        """Filtra y devuelve SOLO las tareas que hay que hacer hoy."""
        today = str(datetime.date.today())
        # Esta lógica se ejecuta en Python (Backend), evitando el error en el Frontend
        return [
            t for t in self.topics 
            if t["unlocked"] and t["next_review"] <= today
        ]

    @rx.var
    def total_progress(self) -> int:
        """Calcula el % de maestría total."""
        if not self.topics: return 0
        total_levels = len(self.topics) * 5
        current_levels = sum(t["level"] for t in self.topics)
        return int((current_levels / total_levels) * 100) if total_levels > 0 else 0

    # --- CONEXIÓN SUPABASE ---
    
    @property
    def supabase(self) -> Client:
        return create_client(SUPABASE_URL, SUPABASE_KEY)

    def login(self):
        try:
            res = self.supabase.auth.sign_in_with_password({"email": self.email, "password": self.password})
            self.auth_token = res.session.access_token
            self.user_id = res.user.id
            self.is_logged_in = True
            self.check_initial_data()
            self.load_data()
        except Exception as e:
            return rx.window_alert(f"Error de acceso: {str(e)}")

    def logout(self):
        self.auth_token = ""
        self.is_logged_in = False
        self.topics = []
        self.notes = []

    def check_initial_data(self):
        res = self.supabase.table("topics").select("id").eq("user_id", self.user_id).execute()
        if len(res.data) == 0:
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
        if not self.is_logged_in: return
        t_res = self.supabase.table("topics").select("*").eq("user_id", self.user_id).order("id").execute()
        self.topics = t_res.data
        n_res = self.supabase.table("notes").select("*").eq("user_id", self.user_id).order("created_at", desc=True).execute()
        self.notes = n_res.data

    # --- LOGICA DEL RELOJ Y HORARIO ---

    def update_clock(self):
        tz = pytz.timezone('Europe/Madrid')
        now = datetime.datetime.now(tz)
        weekday = now.weekday()
        hour = now.hour + now.minute / 60.0

        b_type, b_name, end_h = "free", "⏳ Tiempo Libre", 0.0

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
        else:
            self.time_remaining = "--:--"
            self.target_hour_display = ""

    # --- LOGICA DE REPASO ---

    def review_topic(self, topic_id: int, rating: str):
        topic_idx = next((i for i, t in enumerate(self.topics) if t["id"] == topic_id), -1)
        if topic_idx == -1: return

        topic = self.topics[topic_idx]
        new_level = topic["level"]
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
            
        self.supabase.table("topics").update({
            "level": new_level,
            "next_review": str(next_rev),
            "extra_queue": False
        }).eq("id", topic_id).execute()
        
        self.load_data()

    def toggle_unlock(self, topic_id: int, current_val: bool):
        self.supabase.table("topics").update({"unlocked": not current_val}).eq("id", topic_id).execute()
        self.load_data()

    def add_note(self):
        if not self.is_premium and len(self.notes) >= 3:
            self.show_upgrade_dialog = True
            return

        if self.new_note_text:
            self.supabase.table("notes").insert({"user_id": self.user_id, "text": self.new_note_text}).execute()
            self.new_note_text = ""
            self.load_data()
    
    def delete_note(self, note_id: int):
        self.supabase.table("notes").delete().eq("id", note_id).execute()
        self.load_data()

    def upgrade_to_premium(self):
        self.is_premium = True # Simulación
        self.show_upgrade_dialog = False
        return rx.window_alert("¡Bienvenido al plan Elite! (Simulación)")

# ==========================================
# 🎨 UI COMPONENTS (Modernos)
# ==========================================

def login_page():
    return rx.center(
        rx.card(
            rx.vstack(
                rx.heading("PAU Elite", size="8", weight="bold", color_scheme="tomato"),
                rx.text("Tu segundo cerebro para Selectividad", color="gray", size="2"),
                rx.input(placeholder="Email", on_change=State.set_email, size="3", width="100%"),
                rx.input(placeholder="Password", type="password", on_change=State.set_password, size="3", width="100%"),
                rx.button("Iniciar Sesión", on_click=State.login, width="100%", size="3", variant="solid"),
                rx.text("Accede con tus credenciales de Supabase", font_size="xs", color="gray"),
                spacing="4",
                align_items="center"
            ),
            size="4",
            width="400px",
            variant="surface"
        ),
        height="100vh",
        background="radial-gradient(circle at center, #1a1a1a 0%, #000000 100%)"
    )

def stat_card(label: str, value: str, icon: str, color: str):
    return rx.card(
        rx.hstack(
            rx.avatar(fallback=icon, variant="solid", color_scheme=color, size="4"),
            rx.vstack(
                rx.text(label, size="1", weight="bold", color="gray"),
                rx.heading(value, size="5"),
                spacing="1"
            ),
            align_items="center"
        ),
        size="2"
    )

def task_card(topic: dict):
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.badge(topic["subject"], color_scheme="indigo", variant="soft"),
                rx.spacer(),
                rx.badge(f"Nivel {topic['level']}", variant="outline")
            ),
            rx.heading(topic["name"], size="4", weight="medium"),
            rx.progress(value=topic["level"]*20, width="100%", color_scheme="tomato", height="8px"),
            rx.divider(),
            rx.hstack(
                rx.button("Fácil", on_click=lambda: State.review_topic(topic["id"], "ok"), flex="1", color_scheme="grass", variant="soft"),
                rx.button("Regular", on_click=lambda: State.review_topic(topic["id"], "mid"), flex="1", color_scheme="amber", variant="soft"),
                rx.button("Difícil", on_click=lambda: State.review_topic(topic["id"], "bad"), flex="1", color_scheme="tomato", variant="soft"),
                width="100%",
                spacing="3"
            ),
            spacing="3"
        ),
        variant="surface",
        margin_bottom="1em"
    )

def syllabus_row(topic: dict):
    return rx.hstack(
        rx.checkbox(
            checked=topic["unlocked"], 
            on_change=lambda x: State.toggle_unlock(topic["id"], topic["unlocked"])
        ),
        rx.vstack(
            rx.text(topic["name"], weight="medium", font_size="0.95em"),
            rx.text(topic["subject"], font_size="0.7em", color="gray"),
            spacing="0",
            align_items="start"
        ),
        rx.spacer(),
        rx.cond(
            topic["unlocked"],
            rx.badge("Activo", color_scheme="green", variant="surface"),
            rx.badge("Bloqueado", color_scheme="gray", variant="surface"),
        ),
        width="100%",
        padding="0.8em",
        border_bottom="1px solid #222",
        align_items="center"
    )

def main_dashboard():
    return rx.hstack(
        # --- SIDEBAR ---
        rx.vstack(
            rx.heading("PAU ELITE", size="6", weight="black", letter_spacing="-1px"),
            rx.cond(
                State.is_premium,
                rx.badge("PLAN ELITE", color_scheme="gold", variant="solid"),
                rx.badge("PLAN GRATUITO", color_scheme="gray", variant="soft")
            ),
            rx.divider(margin_y="1em"),
            
            # Reloj Widget
            rx.card(
                rx.vstack(
                    rx.text("OBJETIVO ACTUAL", font_size="0.65em", weight="bold", color="gray"),
                    rx.text(State.current_block_name, weight="bold", size="3"),
                    rx.heading(State.time_remaining, size="7", color_scheme="tomato", font_variant_numeric="tabular-nums"),
                    rx.text(State.target_hour_display, size="1", color="gray"),
                    align_items="center",
                    spacing="1"
                ),
                variant="classic",
                width="100%"
            ),
            
            rx.spacer(),
            rx.button("Cerrar Sesión", on_click=State.logout, variant="ghost", color_scheme="gray", width="100%"),
            width="280px",
            height="100vh",
            padding="2em",
            background="#111",
            border_right="1px solid #222",
            position="sticky",
            top="0",
            on_mount=State.update_clock
        ),
        
        # --- MAIN CONTENT ---
        rx.container(
            rx.vstack(
                # Stats Header
                rx.grid(
                    stat_card("TEMA ACTUAL", "Repaso", "🎯", "blue"),
                    stat_card("PENDIENTES", f"{State.tasks_due.length()}", "🔥", "tomato"),
                    stat_card("MAESTRÍA", f"{State.total_progress}%", "📈", "green"),
                    columns="3",
                    spacing="4",
                    width="100%"
                ),
                
                rx.tabs.root(
                    rx.tabs.list(
                        rx.tabs.trigger("🚀 Misión de Hoy", value="tab1"),
                        rx.tabs.trigger("📚 Temario", value="tab2"),
                        rx.tabs.trigger("📓 Notas Rápidas", value="tab3"),
                        size="2"
                    ),
                    
                    # TAB 1: AGENDA (Fixed Logic)
                    rx.tabs.content(
                        rx.vstack(
                            rx.heading("Tareas Prioritarias", size="5", margin_y="0.5em"),
                            rx.cond(
                                State.tasks_due.length() > 0,
                                rx.foreach(State.tasks_due, task_card),
                                rx.card(
                                    rx.vstack(
                                        rx.heading("¡Todo limpio!", size="6"), 
                                        rx.text("No tienes repasos pendientes para hoy.", color="gray"),
                                        align_items="center", 
                                        padding="2em"
                                    ),
                                    variant="ghost",
                                    width="100%"
                                )
                            ),
                            width="100%"
                        ),
                        value="tab1",
                        padding_top="1.5em"
                    ),
                    
                    # TAB 2: TEMARIO
                    rx.tabs.content(
                        rx.vstack(
                            rx.heading("Gestión del Temario", size="5"),
                            rx.input(placeholder="Filtrar temas...", on_change=State.set_search_query, variant="soft"),
                            rx.scroll_area(
                                rx.vstack(
                                    rx.foreach(State.topics, syllabus_row),
                                    width="100%"
                                ),
                                type="always",
                                scrollbars="vertical",
                                style={"height": "500px"}
                            )
                        ),
                        value="tab2",
                        padding_top="1.5em"
                    ),
                    
                    # TAB 3: NOTAS (Freemium Check)
                    rx.tabs.content(
                        rx.vstack(
                            rx.heading("Cuaderno de Notas", size="5"),
                            rx.hstack(
                                rx.input(
                                    placeholder="Nueva idea...", 
                                    value=State.new_note_text,
                                    on_change=State.set_new_note_text, 
                                    width="100%"
                                ),
                                rx.button("Guardar", on_click=State.add_note)
                            ),
                            rx.foreach(
                                State.notes,
                                lambda n: rx.card(
                                    rx.hstack(
                                        rx.text(n["text"]),
                                        rx.spacer(),
                                        rx.button(
                                            rx.icon("trash"), 
                                            on_click=lambda: State.delete_note(n["id"]), 
                                            variant="ghost", 
                                            color_scheme="red",
                                            size="1"
                                        )
                                    ),
                                    size="1"
                                )
                            )
                        ),
                        value="tab3",
                        padding_top="1.5em"
                    ),
                    default_value="tab1",
                    width="100%"
                ),
                width="100%",
                max_width="900px",
                padding_y="2em",
                spacing="6"
            ),
            size="3"
        ),
        
        # --- DIALOG UPGRADE (Freemium) ---
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title("🚀 Sube de Nivel"),
                rx.dialog.description(
                    "Has alcanzado el límite de notas gratuitas (3). Pásate a Elite para notas ilimitadas y estadísticas avanzadas.",
                ),
                rx.flex(
                    rx.dialog.close(
                        rx.button("Cancelar", color_scheme="gray", variant="soft"),
                    ),
                    rx.dialog.close(
                        rx.button("Desbloquear Elite", on_click=State.upgrade_to_premium),
                    ),
                    spacing="3",
                    margin_top="16px",
                    justify="end",
                ),
            ),
            open=State.show_upgrade_dialog,
            on_open_change=State.set_show_upgrade_dialog
        ),

        background="#0a0a0a",
        min_height="100vh",
        align_items="start"
    )

def index():
    return rx.cond(
        State.is_logged_in,
        main_dashboard(),
        login_page()
    )

# ==========================================
# 🚀 APP LAUNCH
# ==========================================

app = rx.App(
    theme=rx.theme(
        appearance="dark", 
        accent_color="tomato", 
        radius="large",
        panel_background="translucent"
    )
)
app.add_page(index, title="PAU Elite | Tu Segundo Cerebro")
