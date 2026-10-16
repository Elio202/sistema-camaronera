"""Aplica database/00_esquema_completo_railway.sql sobre la base configurada en DB_*.

Es idempotente (CREATE IF NOT EXISTS, INSERT IGNORE, CREATE OR REPLACE VIEW):
no borra ni modifica datos existentes. Railway lo ejecuta antes de iniciar server.py.
No imprime credenciales.
"""
from pathlib import Path
import os, re, sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
import server  # carga .env y expone la conexión configurada

if not server.USE_MARIADB:
    print("Sin DB_PASSWORD: se usa SQLite de demostración, no se aplica el esquema.")
    sys.exit(0)

text = (ROOT / "00_esquema_completo_railway.sql").read_text(encoding="utf-8")
text = "\n".join(line for line in text.splitlines() if not line.strip().startswith("--"))
statements = [s.strip() for s in re.split(r";\s*\n", text) if s.strip()]

conn = server.MariaConnection()
try:
    for statement in statements:
        conn.cursor.execute(statement.rstrip(";"))
    conn.conn.commit()
finally:
    conn.cursor.close(); conn.conn.close()
print(f"Esquema verificado: {len(statements)} sentencias aplicadas.")
