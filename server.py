"""Punto de entrada compatible para desarrollo local y Railway."""

import sys

from app import application


if __name__ == "__main__":
    application.run()
else:
    # Conserva compatibilidad con pruebas y herramientas que importan `server`.
    sys.modules[__name__] = application
