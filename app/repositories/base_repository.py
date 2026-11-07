"""Operaciones reutilizables de lectura para los repositorios del sistema."""

from app.database import db


def fetch_all(sql, params=()):
    """Ejecuta una consulta de lectura y devuelve una lista de diccionarios."""
    with db() as connection:
        return [dict(row) for row in connection.execute(sql, params).fetchall()]


def fetch_one(sql, params=()):
    """Ejecuta una consulta de lectura y devuelve un diccionario o ``None``."""
    with db() as connection:
        row = connection.execute(sql, params).fetchone()
        return dict(row) if row else None
