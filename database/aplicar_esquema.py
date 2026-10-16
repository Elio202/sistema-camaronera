"""Aplica database/00_esquema_completo_railway.sql sobre la base configurada en DB_*.

Es idempotente (CREATE IF NOT EXISTS, INSERT IGNORE, CREATE OR REPLACE VIEW):
no borra ni modifica datos existentes. server.py lo hace solo cuando la base está
vacía; este script permite repetirlo a mano. No imprime credenciales.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server  # carga .env y expone la conexión configurada

if not server.USE_MARIADB:
    print("Sin DB_PASSWORD: se usa SQLite de demostración, no se aplica el esquema.")
    sys.exit(0)
print(f"Esquema verificado: {server.apply_schema()} sentencias aplicadas.")
