import os
import reflex as rx

config = rx.Config(
    app_name="pau_elite",
    frontend_port=int(os.environ.get("PORT", 3000)),
)
