"""Composici?n y arranque del backend."""

import os
import threading
from http.server import ThreadingHTTPServer

from app.core import WHATSAPP_ALERTS_ENABLED, init_db, whatsapp_alert_worker
from app.routes.http_routes import App


def run():
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    init_db()
    if WHATSAPP_ALERTS_ENABLED:
        threading.Thread(
            target=whatsapp_alert_worker, daemon=True, name="whatsapp-alerts"
        ).start()
    print(f"Sistema disponible en http://{host}:{port}")
    ThreadingHTTPServer((host, port), App).serve_forever()
