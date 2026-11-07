"""Configuración, conexión e inicialización de la base de datos."""

from .connection import db, init_db

__all__ = ["db", "init_db"]
