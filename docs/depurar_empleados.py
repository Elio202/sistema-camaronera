"""Crea una copia operacional del CSV sin modificar ni exponer el original."""
import csv
from pathlib import Path

folder = Path(__file__).parent
source_path = folder / "empleados_original.csv"
output_path = folder / "empleados_depurado.csv"

columns = [
    "codigo_empleado", "primer_nombre", "segundo_nombre", "tercer_nombre",
    "primer_apellido", "segundo_apellido", "apellido_casada", "celular",
    "fecha_ingreso", "fecha_baja", "estado", "puesto",
]

def clean(value):
    value = (value or "").strip()
    return "" if value.upper() in {"NULL", "N/A", "NA", "NONE"} else value

with source_path.open(encoding="utf-8-sig", errors="replace", newline="") as source, output_path.open("w", encoding="utf-8-sig", newline="") as output:
    reader = csv.DictReader(source, delimiter=";")
    writer = csv.DictWriter(output, fieldnames=columns, delimiter=";")
    writer.writeheader()
    for row in reader:
        writer.writerow({
            "codigo_empleado": clean(row["CodigoEtalent"]),
            "primer_nombre": clean(row["PrimerNombre"]),
            "segundo_nombre": clean(row["SegundoNombre"]),
            "tercer_nombre": clean(row["TercerNombre"]),
            "primer_apellido": clean(row["PrimerApellido"]),
            "segundo_apellido": clean(row["SegundoApellido"]),
            "apellido_casada": clean(row["ApellidoCasada"]),
            "celular": clean(row["Celular"]),
            "fecha_ingreso": clean(row["FechaIngreso"]),
            "fecha_baja": clean(row["FechaBaja"]),
            "estado": clean(row["Estado"]),
            "puesto": "",  # El archivo original no contiene el puesto laboral.
        })

print(f"Generado: {output_path.name}")
