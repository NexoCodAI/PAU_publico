# config.py
import datetime

PAGE_CONFIG = {
    "page_title": "PAU TRACKER ELITE",
    "page_icon": "🎓",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

CUSTOM_CSS = """
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
"""

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
