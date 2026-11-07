"""Definición y agrupación de rutas HTTP de la aplicación."""

from .api_routes import ROUTE_GROUPS
from .http_routes import App

__all__ = ["App", "ROUTE_GROUPS"]
