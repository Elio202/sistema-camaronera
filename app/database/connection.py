"""Acceso centralizado a MariaDB/MySQL o SQLite local."""

from app.core import MariaConnection, apply_schema, db, init_db, init_mariadb

__all__ = ["MariaConnection", "db", "init_db", "init_mariadb", "apply_schema"]
