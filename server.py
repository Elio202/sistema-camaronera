"""Punto de entrada compatible para desarrollo local y Railway."""

import sys

from app.controllers import application_controller


if __name__ == "__main__":
    application_controller.run()
else:
    # Conserva compatibilidad con pruebas y herramientas que importan `server`.
    sys.modules[__name__] = application_controller
