"""Genera el diagrama ER general del proyecto en formato SVG."""
from pathlib import Path
from html import escape

WIDTH, HEIGHT = 2100, 2450
BOX_W, HEADER_H, ROW_H = 360, 42, 25

tables = {
    # Implementadas
    "roles": (50, 90, True, ["PK id", "nombre", "descripcion", "estado"]),
    "permisos": (490, 90, True, ["PK id", "modulo", "funcion"]),
    "rol_permisos": (270, 300, True, ["PK/FK rol_id", "PK/FK permiso_id"]),
    "usuarios": (50, 500, True, ["PK id", "nombre_usuario", "nombre", "correo", "password_hash", "FK rol_id", "estado", "creado_en"]),
    "sesiones": (50, 800, True, ["PK id", "token_hash", "FK usuario_id", "fecha_inicio", "fecha_fin", "expira_en"]),
    "recuperaciones_password": (490, 800, True, ["PK id", "FK usuario_id", "token_hash", "creado_en", "expira_en", "utilizado_en"]),

    # Operación general
    "piscinas": (930, 90, False, ["PK id", "codigo", "nombre", "tipo", "area_m2", "estado"]),
    "colaboradores": (1370, 90, False, ["PK id", "UK codigo_empleado", "FK usuario_id (opcional)", "primer_nombre", "segundo_nombre", "tercer_nombre", "primer_apellido", "segundo_apellido", "apellido_casada", "celular", "puesto", "fecha_ingreso", "fecha_baja", "estado"]),

    # Aireación
    "sensores": (930, 350, False, ["PK id", "FK piscina_id", "codigo", "tipo", "estado", "ultima_calibracion"]),
    "mediciones_oxigeno": (930, 620, False, ["PK id", "FK sensor_id", "FK piscina_id", "valor_mg_l", "fecha_medicion", "origen"]),
    "aireadores": (1370, 560, False, ["PK id", "FK piscina_id", "codigo", "estado", "modo_operacion"]),
    "historial_aireadores": (1370, 820, False, ["PK id", "FK aireador_id", "accion", "motivo", "fecha_inicio", "fecha_fin"]),

    # Inventario
    "productos_alimento": (50, 1130, False, ["PK id", "nombre", "marca", "unidad_medida", "stock_actual", "stock_minimo", "estado"]),
    "ingresos_alimento": (490, 1130, False, ["PK id", "FK producto_id", "cantidad", "lote", "fecha_ingreso", "fecha_vencimiento", "FK usuario_id"]),
    "salidas_alimento": (270, 1430, False, ["PK id", "FK producto_id", "FK piscina_id", "cantidad", "tipo_piscina", "FK colaborador_id", "FK usuario_id", "fecha_salida"]),

    # Personal
    "actividades": (930, 1030, False, ["PK id", "FK colaborador_id", "FK piscina_id", "descripcion", "fecha_asignacion", "hora_limite", "estado", "FK usuario_asigna"]),
    "seguimientos_actividad": (930, 1370, False, ["PK id", "FK actividad_id", "estado_anterior", "estado_actual", "fecha_actualizacion", "observacion"]),
    "alertas_incumplimiento": (1370, 1370, False, ["PK id", "FK actividad_id", "tiempo_atraso", "fecha_generacion", "estado"]),

    # Calidad del agua y alertas
    "rangos_parametros": (50, 1780, False, ["PK id", "parametro", "valor_minimo", "valor_maximo", "unidad", "estado"]),
    "mediciones_calidad_agua": (490, 1780, False, ["PK id", "FK piscina_id", "FK usuario_id", "oxigeno", "temperatura", "ph", "salinidad", "fecha_medicion"]),
    "alertas_calidad_agua": (930, 1780, False, ["PK id", "FK medicion_id", "FK rango_id", "parametro", "valor_detectado", "fecha_generacion", "estado"]),
}

relations = [
    ("roles", "usuarios", "1", "N"), ("roles", "rol_permisos", "1", "N"),
    ("permisos", "rol_permisos", "1", "N"), ("usuarios", "sesiones", "1", "N"),
    ("usuarios", "recuperaciones_password", "1", "N"),
    ("usuarios", "colaboradores", "1", "0..1"),
    ("piscinas", "sensores", "1", "N"), ("sensores", "mediciones_oxigeno", "1", "N"),
    ("piscinas", "mediciones_oxigeno", "1", "N"), ("piscinas", "aireadores", "1", "N"),
    ("aireadores", "historial_aireadores", "1", "N"),
    ("productos_alimento", "ingresos_alimento", "1", "N"),
    ("productos_alimento", "salidas_alimento", "1", "N"),
    ("piscinas", "salidas_alimento", "1", "N"), ("colaboradores", "salidas_alimento", "1", "N"),
    ("colaboradores", "actividades", "1", "N"), ("piscinas", "actividades", "1", "N"),
    ("actividades", "seguimientos_actividad", "1", "N"),
    ("actividades", "alertas_incumplimiento", "1", "N"),
    ("piscinas", "mediciones_calidad_agua", "1", "N"),
    ("mediciones_calidad_agua", "alertas_calidad_agua", "1", "N"),
    ("rangos_parametros", "alertas_calidad_agua", "1", "N"),
]

def height(fields): return HEADER_H + ROW_H * len(fields) + 18
def center(name):
    x, y, _, fields = tables[name]
    return x + BOX_W / 2, y + height(fields) / 2

svg = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
<defs><filter id="shadow"><feDropShadow dx="0" dy="5" stdDeviation="7" flood-opacity=".12"/></filter></defs>
<rect width="100%" height="100%" fill="#f4f8fb"/>
<text x="50" y="45" font-family="Arial" font-size="28" font-weight="700" fill="#082b57">Diagrama entidad-relación general — Sistema Pacific Gold</text>
<rect x="1450" y="20" width="22" height="22" rx="4" fill="#1167b1"/><text x="1482" y="38" font-family="Arial" font-size="16" fill="#38516b">Implementada</text>
<rect x="1650" y="20" width="22" height="22" rx="4" fill="#cf962f"/><text x="1682" y="38" font-family="Arial" font-size="16" fill="#38516b">Planificada</text>
<g stroke="#9aabbc" stroke-width="2" fill="none" opacity=".7">''']

for source, target, one, many in relations:
    x1, y1 = center(source); x2, y2 = center(target)
    svg.append(f'<path d="M{x1:.0f},{y1:.0f} L{x2:.0f},{y2:.0f}"/>')
    svg.append(f'<text x="{x1+8:.0f}" y="{y1-7:.0f}" fill="#60758a" stroke="none" font-family="Arial" font-size="14">{one}</text>')
    svg.append(f'<text x="{x2-20:.0f}" y="{y2-7:.0f}" fill="#60758a" stroke="none" font-family="Arial" font-size="14">{many}</text>')
svg.append('</g>')

for name, (x, y, implemented, fields) in tables.items():
    h = height(fields); color = "#1167b1" if implemented else "#cf962f"
    svg.append(f'<g filter="url(#shadow)"><rect x="{x}" y="{y}" width="{BOX_W}" height="{h}" rx="12" fill="white" stroke="{color}" stroke-width="2"/>')
    svg.append(f'<path d="M{x+12},{y} H{x+BOX_W-12} Q{x+BOX_W},{y} {x+BOX_W},{y+12} V{y+HEADER_H} H{x} V{y+12} Q{x},{y} {x+12},{y}" fill="{color}"/>')
    svg.append(f'<text x="{x+18}" y="{y+28}" font-family="Arial" font-size="18" font-weight="700" fill="white">{escape(name)}</text>')
    for index, field in enumerate(fields):
        fy = y + HEADER_H + 23 + index * ROW_H
        weight = "700" if field.startswith("PK") else "400"
        fill = "#0c4f9c" if "FK" in field or field.startswith("PK") else "#34495e"
        svg.append(f'<text x="{x+18}" y="{fy}" font-family="Consolas,monospace" font-size="14" font-weight="{weight}" fill="{fill}">{escape(field)}</text>')
    svg.append('</g>')

svg.append('<text x="50" y="2410" font-family="Arial" font-size="15" fill="#667b94">Las tablas planificadas representan el diseño propuesto y podrán ajustarse durante el desarrollo de cada módulo.</text></svg>')

Path(__file__).with_name("DIAGRAMA_ER_COMPLETO.svg").write_text("\n".join(svg), encoding="utf-8")
print("DIAGRAMA_ER_COMPLETO.svg generado")
