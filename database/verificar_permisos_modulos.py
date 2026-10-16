"""Verifica permisos operativos sin modificar la base de datos."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server import db  # noqa: E402


with db() as connection:
    rows = connection.execute(
        """
        SELECT modulo, funcion
        FROM permisos
        WHERE modulo IN ('piscinas', 'personal', 'inventario')
        ORDER BY modulo, funcion
        """
    ).fetchall()

print([f"{row['modulo']}.{row['funcion']}" for row in rows])
