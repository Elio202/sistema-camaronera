import csv
from collections import Counter
from pathlib import Path

path = Path(__file__).with_name("empleados_original.csv")
with path.open(encoding="utf-8-sig", errors="replace", newline="") as source:
    rows = list(csv.DictReader(source, delimiter=";"))

print(f"FILAS={len(rows)}")
print(f"COLUMNAS={len(rows[0]) if rows else 0}")
print("CAMPO|VACIOS|PORCENTAJE_VACIO|DISTINTOS|DUPLICADOS_NO_VACIOS")
for field in rows[0] if rows else []:
    values = [(row.get(field) or "").strip() for row in rows]
    nonempty = [value for value in values if value]
    empty = len(values) - len(nonempty)
    counts = Counter(nonempty)
    duplicates = sum(count - 1 for count in counts.values() if count > 1)
    print(f"{field}|{empty}|{empty/len(values)*100:.1f}%|{len(counts)}|{duplicates}")

for candidate in ("Codigo", "CodigoEtalent", "DPI", "NIT", "SeguroSocial"):
    values = [(row.get(candidate) or "").strip() for row in rows]
    nonempty = [value for value in values if value]
    print(f"CLAVE_{candidate}: presentes={len(nonempty)}, unicos={len(set(nonempty))}, duplicados={len(nonempty)-len(set(nonempty))}")

print("CATEGORIAS")
for field in ("FechaBaja","Sexo","EstadoCivil","Estado","PaisNacimiento","Etnia","Nacionalidad","PaisDPI","VencimientoDPI","Telefono","PermisoTrabajo","TituloPersonal","TipoSangre","Beneficiario"):
    counts = Counter((row.get(field) or "").strip() for row in rows)
    summary = ", ".join(f"{value!r}:{count}" for value, count in counts.most_common(15))
    print(f"{field}={summary}")
