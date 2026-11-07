"""Punto de entrada compatible para desarrollo local y Railway."""

import sys

from app import core
from app.application import run
from app.routes.http_routes import App


if __name__ == "__main__":
    run()
else:
    # Conserva compatibilidad con pruebas y herramientas que importan `server`.
    core.App = App
    core.run = run
    sys.modules[__name__] = core
