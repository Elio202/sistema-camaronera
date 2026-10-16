"""Verifica colaboradores con las credenciales limitadas de la aplicación."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server import db  # noqa: E402


with db() as connection:
    summary = connection.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN estado = TRUE THEN 1 ELSE 0 END) AS activos,
            SUM(CASE WHEN fecha_ingreso IS NULL THEN 1 ELSE 0 END) AS sin_fecha,
            COUNT(DISTINCT codigo_empleado) AS codigos_unicos
        FROM colaboradores
        """
    ).fetchone()

print(dict(summary))
