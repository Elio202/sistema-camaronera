"""Aplica database/schema/schema.sql sobre la base configurada en DB_*.

Utilizar únicamente durante una instalación o actualización controlada, con una
cuenta que tenga permisos DDL. La aplicación normal debe usar una cuenta limitada.
No imprime credenciales.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import server  # carga .env y expone la conexión configurada

if not server.USE_MARIADB:
    print("Sin DB_PASSWORD: se usa SQLite de demostración, no se aplica el esquema.")
    sys.exit(0)
confirmation=input("Escriba APLICAR para crear los objetos faltantes del esquema: ").strip()
if confirmation!="APLICAR":
    print("Operación cancelada.")
    sys.exit(1)
print(f"Esquema verificado: {server.apply_schema()} sentencias procesadas.")
