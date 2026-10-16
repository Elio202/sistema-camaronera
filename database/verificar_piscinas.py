"""Verifica la carga de piscinas usando las credenciales de la aplicación."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server import db  # noqa: E402


with db() as connection:
    totals = connection.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM fincas) AS fincas,
            (SELECT COUNT(*) FROM modulos) AS modulos,
            (SELECT COUNT(*) FROM piscinas) AS piscinas,
            (SELECT COUNT(*) FROM ciclos_piscina) AS ciclos
        """
    ).fetchone()
    examples = connection.execute(
        """
        SELECT codigo_productivo
        FROM vista_piscinas_ciclo_actual
        ORDER BY piscina
        LIMIT 4
        """
    ).fetchall()

print(dict(totals))
print([row["codigo_productivo"] for row in examples])
