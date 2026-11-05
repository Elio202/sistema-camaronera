"""Comprueba las tablas requeridas por la versión final."""

import os
from urllib.parse import urlparse

import pymysql


REQUIRED = {
    "roles", "permisos", "rol_permisos", "usuarios", "sesiones",
    "fincas", "modulos", "piscinas", "ciclos_piscina",
    "colaboradores", "actividades", "productos_alimento",
    "movimientos_inventario", "alertas", "rangos_calidad_agua",
    "mediciones_calidad_agua", "aireadores", "eventos_aireacion",
}


def main():
    url = os.getenv("MYSQL_PUBLIC_URL") or os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("No se encontró MYSQL_PUBLIC_URL ni DATABASE_URL.")
    parsed = urlparse(url)
    connection = pymysql.connect(
        host=parsed.hostname,
        port=parsed.port or 3306,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path.lstrip("/"),
        cursorclass=pymysql.cursors.DictCursor,
    )
    with connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT TABLE_NAME FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA=DATABASE()"
        )
        existing = {row["TABLE_NAME"] for row in cursor.fetchall()}
    missing = sorted(REQUIRED - existing)
    if missing:
        raise SystemExit("Faltan tablas: " + ", ".join(missing))
    print(f"Esquema final verificado: {len(REQUIRED)} tablas requeridas disponibles.")


if __name__ == "__main__":
    main()
