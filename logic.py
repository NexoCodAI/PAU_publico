# logic.py
import datetime
import pytz

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
    # Algoritmo simple de Repaso Espaciado
    days = [1, 3, 7, 14, 30]
    idx = max(0, min(level - 1, len(days) - 1))
    return str(datetime.date.today() + datetime.timedelta(days=days[idx]))
