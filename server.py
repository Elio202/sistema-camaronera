from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import hashlib, hmac, json, os, re, secrets, sqlite3
from datetime import datetime, timedelta, timezone

try: import pymysql
except ImportError: pymysql = None

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "sistema.db"
PUBLIC = ROOT / "public"
ITERATIONS = 310_000
USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,50}$")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

def valid_password(value):
    return len(value) >= 8 and bool(re.search(r"[A-Z]",value)) and bool(re.search(r"[a-z]",value)) and bool(re.search(r"\d",value))

def load_env():
    path=ROOT/".env"
    if path.exists():
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip() and not raw.lstrip().startswith("#") and "=" in raw:
                key,value=raw.split("=",1); os.environ.setdefault(key.strip(),value.strip())

load_env()
USE_MARIADB=bool(os.getenv("DB_PASSWORD"))
INTEGRITY_ERRORS=(sqlite3.IntegrityError,pymysql.err.IntegrityError) if pymysql else (sqlite3.IntegrityError,)

def now(): return datetime.now(timezone.utc)
def iso(dt=None): return (dt or now()).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
BUSINESS_TZ=timezone(timedelta(hours=-6))
def business_iso(): return now().astimezone(BUSINESS_TZ).strftime("%Y-%m-%d %H:%M:%S")

def refresh_activity_statuses(c):
    current=business_iso()
    c.execute("""UPDATE actividades SET estado='Pendiente'
        WHERE estado='Vencida' AND COALESCE(fecha_fin,fecha_limite)>=?""",(current,))
    c.execute("""UPDATE actividades SET estado='Vencida'
        WHERE estado='Pendiente' AND COALESCE(fecha_fin,fecha_limite)<?""",(current,))

def alerts_table_ready(c=None):
    try:
        if c is not None: c.execute("SELECT 1 FROM alertas LIMIT 1")
        else:
            with db() as connection: connection.execute("SELECT 1 FROM alertas LIMIT 1")
        return True
    except Exception: return False

def sync_alerts(c):
    """Mantiene una sola alerta abierta por cada condición operativa."""
    refresh_activity_statuses(c)
    timestamp=business_iso()
    sources=(
        ("Inventario","stock_bajo","Advertencia","SELECT id,codigo,nombre,stock_actual,stock_minimo,unidad FROM productos_alimento WHERE estado=1 AND stock_actual<=stock_minimo"),
        ("Personal","actividad_vencida","Crítica","SELECT id,descripcion,COALESCE(fecha_fin,fecha_limite) fecha_fin FROM actividades WHERE estado='Vencida'")
    )
    for module,key,level,sql in sources:
        active=set()
        for row in c.execute(sql).fetchall():
            reference=int(row["id"]); active.add(reference)
            latest=c.execute("SELECT id,estado FROM alertas WHERE modulo=? AND clave=? AND referencia_id=? ORDER BY id DESC LIMIT 1",(module,key,reference)).fetchone()
            if latest and latest["estado"]!="Resuelta": continue
            if key=="stock_bajo":
                title=f"Stock bajo: {row['nombre']}"
                description=f"{row['codigo']} tiene {row['stock_actual']} {row['unidad']}; el mínimo es {row['stock_minimo']} {row['unidad']}."
            else:
                title="Actividad vencida"
                description=f"{row['descripcion']} finalizó el {row['fecha_fin']} sin confirmarse."
            c.execute("INSERT INTO alertas(modulo,referencia_id,clave,titulo,descripcion,nivel,generada_en) VALUES(?,?,?,?,?,?,?)",(module,reference,key,title,description,level,timestamp))
        opened=c.execute("SELECT id,referencia_id FROM alertas WHERE modulo=? AND clave=? AND estado IN ('Pendiente','Atendida')",(module,key)).fetchall()
        for alert in opened:
            if int(alert["referencia_id"]) not in active:
                c.execute("UPDATE alertas SET estado='Resuelta',resuelta_en=? WHERE id=?",(timestamp,alert["id"]))

class MariaConnection:
    def __init__(self):
        self.conn=pymysql.connect(host=os.getenv("DB_HOST","127.0.0.1"),port=int(os.getenv("DB_PORT","3306")),user=os.getenv("DB_USER"),password=os.getenv("DB_PASSWORD"),database=os.getenv("DB_NAME","pacific_gold"),charset="utf8mb4",cursorclass=pymysql.cursors.DictCursor,autocommit=False)
        self.cursor=self.conn.cursor()
    def execute(self,sql,args=()):
        self.cursor.execute(sql.replace("?","%s"),args)
        return self.cursor
    def __enter__(self): return self
    def __exit__(self,typ,value,tb): self.conn.rollback() if typ else self.conn.commit(); self.cursor.close(); self.conn.close()

def db():
    if USE_MARIADB:
        if not pymysql: raise RuntimeError("Falta instalar PyMySQL")
        return MariaConnection()
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def password_hash(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"

def password_ok(password, encoded):
    try:
        _, iterations, salt, expected = encoded.split("$")
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError): return False

def init_db():
    if USE_MARIADB: return init_mariadb()
    DB.parent.mkdir(exist_ok=True)
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS roles(id INTEGER PRIMARY KEY, nombre TEXT UNIQUE NOT NULL, descripcion TEXT, estado INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS permisos(id INTEGER PRIMARY KEY, modulo TEXT NOT NULL, funcion TEXT NOT NULL, UNIQUE(modulo, funcion));
        CREATE TABLE IF NOT EXISTS rol_permisos(rol_id INTEGER REFERENCES roles(id), permiso_id INTEGER REFERENCES permisos(id), PRIMARY KEY(rol_id, permiso_id));
        CREATE TABLE IF NOT EXISTS usuarios(id INTEGER PRIMARY KEY, nombre_usuario TEXT UNIQUE NOT NULL COLLATE NOCASE, nombre TEXT NOT NULL, correo TEXT UNIQUE NOT NULL COLLATE NOCASE, password_hash TEXT NOT NULL, rol_id INTEGER NOT NULL REFERENCES roles(id), estado INTEGER NOT NULL DEFAULT 1, creado_en TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sesiones(id INTEGER PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL, usuario_id INTEGER NOT NULL REFERENCES usuarios(id), fecha_inicio TEXT NOT NULL, fecha_fin TEXT, expira_en TEXT NOT NULL);
        """)
        roles = [(1,"Administrador","Configuración y acceso total"),(2,"Jefe de producción","Supervisión integral de la operación"),(3,"Encargado de piscina","Operación de piscinas asignadas"),(4,"Técnico de calidad","Control de parámetros del agua"),(5,"Gerencia","Consulta de indicadores y reportes"),(6,"Encargado de Bodega","Control de entradas y salidas de alimento")]
        c.executemany("INSERT OR IGNORE INTO roles(id,nombre,descripcion) VALUES(?,?,?)", roles)
        c.executemany("UPDATE roles SET nombre=?,descripcion=? WHERE id=?", ((name,description,role_id) for role_id,name,description in roles))
        permissions = [*(('usuarios',x) for x in ('ver','crear','editar','cambiar_estado')),*(('roles',x) for x in ('ver','editar')),*(('piscinas',x) for x in ('ver','crear','editar','cambiar_estado')),*(('aireacion',x) for x in ('ver','operar')),*(('inventario',x) for x in ('ver','registrar')),*(('personal',x) for x in ('ver','crear','editar','cambiar_estado','asignar','confirmar')),*(('calidad_agua',x) for x in ('ver','registrar','atender_alertas')),*(('reportes',x) for x in ('ver','exportar')),*(('alertas',x) for x in ('ver','atender'))]
        for module, function in permissions:
            c.execute("INSERT OR IGNORE INTO permisos(modulo,funcion) VALUES(?,?)", (module,function))
        c.execute("INSERT OR IGNORE INTO rol_permisos SELECT 1,id FROM permisos")
        role_permissions = {2:[('aireacion','ver'),('aireacion','operar'),('inventario','ver'),('personal','ver'),('personal','asignar'),('calidad_agua','ver'),('reportes','ver'),('reportes','exportar'),('alertas','ver'),('alertas','atender')],3:[('aireacion','ver'),('inventario','ver'),('inventario','registrar'),('personal','ver'),('personal','confirmar'),('calidad_agua','ver'),('calidad_agua','registrar'),('alertas','ver')],4:[('aireacion','ver'),('calidad_agua','ver'),('calidad_agua','registrar'),('calidad_agua','atender_alertas'),('reportes','ver'),('alertas','ver'),('alertas','atender')],5:[('aireacion','ver'),('inventario','ver'),('personal','ver'),('calidad_agua','ver'),('reportes','ver'),('reportes','exportar'),('alertas','ver')],6:[('inventario','ver'),('inventario','registrar'),('alertas','ver')]}
        for role_id, allowed in role_permissions.items():
            for module, function in allowed:
                c.execute("INSERT OR IGNORE INTO rol_permisos SELECT ?,id FROM permisos WHERE modulo=? AND funcion=?",(role_id,module,function))
        if not c.execute("SELECT 1 FROM usuarios").fetchone():
            c.execute("INSERT INTO usuarios(nombre_usuario,nombre,correo,password_hash,rol_id,creado_en) VALUES(?,?,?,?,1,?)", ("admin","Administrador del sistema","admin@orodelpacifico.local",password_hash("Admin123!"),iso()))

def init_mariadb():
    roles=[(1,"Administrador","Configuración y acceso total"),(2,"Jefe de producción","Supervisión integral de la operación"),(3,"Encargado de piscina","Operación de piscinas asignadas"),(4,"Técnico de calidad","Control de parámetros del agua"),(5,"Gerencia","Consulta de indicadores y reportes"),(6,"Encargado de Bodega","Control de entradas y salidas de alimento")]
    permissions=[*(('usuarios',x) for x in ('ver','crear','editar','cambiar_estado')),*(('roles',x) for x in ('ver','editar')),*(('piscinas',x) for x in ('ver','crear','editar','cambiar_estado')),*(('aireacion',x) for x in ('ver','operar')),*(('inventario',x) for x in ('ver','registrar')),*(('personal',x) for x in ('ver','crear','editar','cambiar_estado','asignar','confirmar')),*(('calidad_agua',x) for x in ('ver','registrar','atender_alertas')),*(('reportes',x) for x in ('ver','exportar')),*(('alertas',x) for x in ('ver','atender'))]
    role_permissions={2:[('aireacion','ver'),('aireacion','operar'),('inventario','ver'),('personal','ver'),('personal','asignar'),('calidad_agua','ver'),('reportes','ver'),('reportes','exportar'),('alertas','ver'),('alertas','atender')],3:[('aireacion','ver'),('inventario','ver'),('inventario','registrar'),('personal','ver'),('personal','confirmar'),('calidad_agua','ver'),('calidad_agua','registrar'),('alertas','ver')],4:[('aireacion','ver'),('calidad_agua','ver'),('calidad_agua','registrar'),('calidad_agua','atender_alertas'),('reportes','ver'),('alertas','ver'),('alertas','atender')],5:[('aireacion','ver'),('inventario','ver'),('personal','ver'),('calidad_agua','ver'),('reportes','ver'),('reportes','exportar'),('alertas','ver')],6:[('inventario','ver'),('inventario','registrar'),('alertas','ver')]}
    with db() as c:
        for role in roles: c.execute("INSERT INTO roles(id,nombre,descripcion) VALUES(?,?,?) ON DUPLICATE KEY UPDATE nombre=VALUES(nombre),descripcion=VALUES(descripcion)",role)
        for permission in permissions: c.execute("INSERT IGNORE INTO permisos(modulo,funcion) VALUES(?,?)",permission)
        c.execute("INSERT IGNORE INTO rol_permisos SELECT 1,id FROM permisos")
        for role_id,allowed in role_permissions.items():
            for module,function in allowed: c.execute("INSERT IGNORE INTO rol_permisos SELECT ?,id FROM permisos WHERE modulo=? AND funcion=?",(role_id,module,function))
        if not c.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone():
            c.execute("INSERT INTO usuarios(nombre_usuario,nombre,correo,password_hash,rol_id,creado_en) VALUES(?,?,?,?,1,?)",("admin","Administrador del sistema","emarroquin@esteromar.gt",password_hash("Admin123!"),iso()))

def user_payload(c, uid):
    user = c.execute("SELECT u.id,u.nombre_usuario,u.nombre,u.correo,u.estado,r.id rol_id,r.nombre rol FROM usuarios u JOIN roles r ON r.id=u.rol_id WHERE u.id=?",(uid,)).fetchone()
    if not user: return None
    out = dict(user)
    out["permisos"] = [f"{p['modulo']}.{p['funcion']}" for p in c.execute("SELECT p.modulo,p.funcion FROM permisos p JOIN rol_permisos rp ON rp.permiso_id=p.id WHERE rp.rol_id=?",(user["rol_id"],))]
    return out

def module_tables_ready():
    try:
        with db() as c:
            c.execute("SELECT 1 FROM piscinas LIMIT 1")
            return True
    except Exception:
        return False

def clean_text(data, key, minimum=1, maximum=255):
    value=str(data.get(key,"")).strip()
    return value if minimum <= len(value) <= maximum else None

def positive_number(value):
    try:
        number=float(value)
        return number if number > 0 else None
    except (TypeError,ValueError): return None

def nonnegative_number(value):
    try:
        number=float(value)
        return number if number >= 0 else None
    except (TypeError,ValueError): return None

def report_dates(parsed):
    query=parse_qs(parsed.query)
    start=query.get("desde",[""])[0].strip()
    end=query.get("hasta",[""])[0].strip()
    try:
        if start: datetime.strptime(start,"%Y-%m-%d")
        if end: datetime.strptime(end,"%Y-%m-%d")
    except ValueError: return None
    if start and end and start>end: return None
    return start,end

class App(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(PUBLIC),**kwargs)
    def end_headers(self):
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control","no-store, no-cache, must-revalidate")
        super().end_headers()
    def log_message(self, fmt, *args): print(f"[{self.log_date_time_string()}] {fmt % args}")
    def json(self, status, payload, cookie=None):
        body=json.dumps(payload,ensure_ascii=False,default=lambda value: value.isoformat() if isinstance(value,(datetime,)) else str(value)).encode()
        self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(body)))
        self.send_header("Cache-Control","no-store"); self.send_header("X-Content-Type-Options","nosniff")
        if cookie: self.send_header("Set-Cookie",cookie)
        self.end_headers(); self.wfile.write(body)
    def body(self):
        try:
            size=int(self.headers.get("Content-Length","0")); return json.loads(self.rfile.read(size)) if 0 < size <= 100_000 else {}
        except (ValueError,json.JSONDecodeError): return {}
    def session(self):
        cookie=SimpleCookie(self.headers.get("Cookie")); morsel=cookie.get("session")
        if not morsel: return None
        token_hash=hashlib.sha256(morsel.value.encode()).hexdigest()
        with db() as c:
            row=c.execute("SELECT usuario_id FROM sesiones WHERE token_hash=? AND fecha_fin IS NULL AND expira_en>?",(token_hash,iso())).fetchone()
            return user_payload(c,row["usuario_id"]) if row else None
    def require(self, permission=None):
        user=self.session()
        if not user: self.json(401,{"error":"Sesión no válida o vencida."}); return None
        if permission and permission not in user["permisos"]: self.json(403,{"error":"No tiene permiso para esta función."}); return None
        return user
    def do_GET(self):
        parsed=urlparse(self.path); path=parsed.path
        if path=="/api/me":
            user=self.require(); return self.json(200,{"usuario":user}) if user else None
        if path=="/api/roles":
            if not self.require("usuarios.ver"): return
            with db() as c: return self.json(200,{"roles":[dict(x) for x in c.execute("SELECT id,nombre,descripcion FROM roles WHERE estado=1 ORDER BY nombre")]})
        if path=="/api/roles-config":
            if not self.require("roles.ver"): return
            with db() as c:
                roles=[dict(x) for x in c.execute("""SELECT r.id,r.nombre,r.descripcion,r.estado,
                    (SELECT COUNT(*) FROM usuarios u WHERE u.rol_id=r.id) usuarios
                    FROM roles r ORDER BY r.id""").fetchall()]
                permissions=[dict(x) for x in c.execute("SELECT id,modulo,funcion FROM permisos ORDER BY modulo,funcion").fetchall()]
                assigned=c.execute("SELECT rol_id,permiso_id FROM rol_permisos").fetchall()
                by_role={role["id"]:[] for role in roles}
                for row in assigned: by_role.setdefault(row["rol_id"],[]).append(row["permiso_id"])
                for role in roles: role["permisos"]=by_role.get(role["id"],[])
                return self.json(200,{"roles":roles,"permisos":permissions})
        if path=="/api/usuarios":
            if not self.require("usuarios.ver"): return
            with db() as c:
                rows=c.execute("SELECT u.id,u.nombre_usuario,u.nombre,u.correo,u.estado,u.creado_en,r.id rol_id,r.nombre rol FROM usuarios u JOIN roles r ON r.id=u.rol_id ORDER BY u.id").fetchall()
                return self.json(200,{"usuarios":[dict(x) for x in rows]})
        if path=="/api/resumen":
            if not self.require(): return
            if not module_tables_ready(): return self.json(503,{"error":"Ejecute la migración de módulos en MariaDB."})
            with db() as c:
                refresh_activity_statuses(c)
                alerts_ready=alerts_table_ready(c)
                if alerts_ready: sync_alerts(c)
                data={
                    "piscinas_disponibles":c.execute("""SELECT COUNT(*) total FROM piscinas p
                        WHERE p.estado=1 AND NOT EXISTS (
                            SELECT 1 FROM ciclos_piscina c
                            WHERE c.piscina_id=p.id AND c.estado='Sembrado'
                        )""").fetchone()["total"],
                    "piscinas_activas":c.execute("""SELECT COUNT(*) total FROM piscinas p
                        WHERE p.estado=1 AND EXISTS (
                            SELECT 1 FROM ciclos_piscina c
                            WHERE c.piscina_id=p.id AND c.estado='Sembrado'
                        )""").fetchone()["total"],
                    "colaboradores":c.execute("SELECT COUNT(*) total FROM colaboradores WHERE estado=1").fetchone()["total"],
                    "pendientes":c.execute("SELECT COUNT(*) total FROM actividades WHERE estado='Pendiente'").fetchone()["total"],
                    "vencidas":c.execute("SELECT COUNT(*) total FROM actividades WHERE estado='Vencida'").fetchone()["total"],
                    "productos_bajos":c.execute("SELECT COUNT(*) total FROM productos_alimento WHERE estado=1 AND stock_actual<=stock_minimo").fetchone()["total"],
                    "alertas_pendientes":c.execute("SELECT COUNT(*) total FROM alertas WHERE estado='Pendiente'").fetchone()["total"] if alerts_ready else 0}
                return self.json(200,{"resumen":data})
        if path=="/api/alertas":
            if not self.require("alertas.ver"): return
            with db() as c:
                if not alerts_table_ready(c): return self.json(503,{"error":"Ejecute la migración 09_crear_alertas.sql en HeidiSQL."})
                sync_alerts(c)
                rows=c.execute("""SELECT a.*,u.nombre atendida_por_nombre
                    FROM alertas a LEFT JOIN usuarios u ON u.id=a.atendida_por
                    ORDER BY FIELD(a.estado,'Pendiente','Atendida','Resuelta'),a.generada_en DESC,a.id DESC
                    LIMIT 500""").fetchall()
                totals={state:c.execute("SELECT COUNT(*) total FROM alertas WHERE estado=?",(state,)).fetchone()["total"] for state in ("Pendiente","Atendida","Resuelta")}
                return self.json(200,{"alertas":[dict(row) for row in rows],"totales":totals})
        if path=="/api/reportes":
            if not self.require("reportes.ver"): return
            dates=report_dates(parsed)
            if dates is None:return self.json(400,{"error":"El rango de fechas no es válido."})
            start,end=dates
            report_type=parse_qs(parsed.query).get("tipo",["piscinas"])[0]
            reports={
                "piscinas":{
                    "titulo":"Catálogo de piscinas y ciclo actual",
                    "columnas":[("codigo_productivo","Código productivo"),("finca","Finca"),("modulo","Módulo"),("tipo","Tipo"),("area_m2","Área m²"),("estado_ciclo","Estado del ciclo")],
                    "sql":"SELECT codigo_productivo,finca,modulo,tipo,area_m2,COALESCE(estado_ciclo,'Sin ciclo') estado_ciclo FROM vista_piscinas_ciclo_actual ORDER BY finca,modulo,piscina",
                    "fecha":None},
                "ciclos":{
                    "titulo":"Historial de ciclos",
                    "columnas":[("codigo","Código"),("finca","Finca"),("modulo","Módulo"),("estado","Estado"),("siembra","Siembra"),("cosecha","Cosecha")],
                    "sql":"SELECT CONCAT(p.codigo,'-',c.numero_ciclo) codigo,f.nombre finca,m.codigo modulo,c.estado,c.fecha_siembra siembra,c.fecha_cosecha cosecha FROM ciclos_piscina c JOIN piscinas p ON p.id=c.piscina_id JOIN modulos m ON m.id=p.modulo_id JOIN fincas f ON f.id=m.finca_id",
                    "fecha":"COALESCE(c.fecha_siembra,DATE(c.creado_en))"},
                "colaboradores":{
                    "titulo":"Catálogo de colaboradores",
                    "columnas":[("codigo","Código"),("nombre","Nombre"),("puesto","Puesto"),("ingreso","Fecha de ingreso"),("estado","Estado")],
                    "sql":"SELECT codigo_empleado codigo,nombre,puesto,fecha_ingreso ingreso,IF(estado=1,'Activo','Inactivo') estado FROM colaboradores",
                    "fecha":"fecha_ingreso"},
                "actividades":{
                    "titulo":"Actividades del personal",
                    "columnas":[("actividad","Actividad"),("responsable","Responsable"),("piscina","Piscina"),("inicio","Inicio"),("fin","Finalización"),("estado","Estado")],
                    "sql":"SELECT a.descripcion actividad,c.nombre responsable,COALESCE(v.codigo_productivo,p.codigo) piscina,a.fecha_inicio inicio,COALESCE(a.fecha_fin,a.fecha_limite) fin,a.estado FROM actividades a JOIN colaboradores c ON c.id=a.colaborador_id JOIN piscinas p ON p.id=a.piscina_id LEFT JOIN vista_piscinas_ciclo_actual v ON v.piscina_id=p.id",
                    "fecha":"DATE(COALESCE(a.fecha_inicio,a.fecha_limite))"},
                "inventario":{
                    "titulo":"Movimientos de inventario",
                    "columnas":[("fecha","Fecha"),("tipo","Movimiento"),("producto","Producto"),("cantidad","Cantidad"),("unidad","Unidad"),("lote","Lote"),("piscina","Piscina"),("responsable","Responsable")],
                    "sql":"SELECT mi.creado_en fecha,mi.tipo,pa.nombre producto,mi.cantidad,pa.unidad,mi.lote,COALESCE(v.codigo_productivo,p.codigo,'—') piscina,COALESCE(c.nombre,'—') responsable FROM movimientos_inventario mi JOIN productos_alimento pa ON pa.id=mi.producto_id LEFT JOIN piscinas p ON p.id=mi.piscina_id LEFT JOIN vista_piscinas_ciclo_actual v ON v.piscina_id=p.id LEFT JOIN colaboradores c ON c.id=mi.responsable_id",
                    "fecha":"DATE(mi.creado_en)"},
                "alertas":{
                    "titulo":"Historial de alertas",
                    "columnas":[("fecha","Fecha"),("modulo","Módulo"),("titulo","Alerta"),("nivel","Nivel"),("estado","Estado"),("atendida_por","Atendida por")],
                    "sql":"SELECT a.generada_en fecha,a.modulo,a.titulo,a.nivel,a.estado,COALESCE(u.nombre,'—') atendida_por FROM alertas a LEFT JOIN usuarios u ON u.id=a.atendida_por",
                    "fecha":"DATE(a.generada_en)"}
            }
            config=reports.get(report_type)
            if not config:return self.json(400,{"error":"El reporte seleccionado no existe."})
            sql=config["sql"]; args=[]
            if config["fecha"] and (start or end):
                conditions=[]
                if start:conditions.append(f"{config['fecha']}>=?");args.append(start)
                if end:conditions.append(f"{config['fecha']}<=?");args.append(end)
                sql+=f" WHERE {' AND '.join(conditions)}"
            if report_type!="piscinas":sql+=" ORDER BY 1 DESC"
            with db() as c:
                if report_type=="actividades":refresh_activity_statuses(c)
                if report_type=="alertas":
                    if not alerts_table_ready(c):return self.json(503,{"error":"Ejecute primero la migración del módulo de alertas."})
                    sync_alerts(c)
                rows=[dict(row) for row in c.execute(sql,args).fetchall()]
            columns=[{"campo":field,"titulo":title} for field,title in config["columnas"]]
            return self.json(200,{"reporte":{"tipo":report_type,"titulo":config["titulo"],"columnas":columns,"filas":rows,"desde":start,"hasta":end}})
        if path=="/api/reportes-dashboard":
            if not self.require("reportes.ver"): return
            dates=report_dates(parsed)
            if dates is None:return self.json(400,{"error":"El rango de fechas no es válido."})
            start,end=dates; query=parse_qs(parsed.query)
            try:
                farm_id=int(query.get("finca",[""])[0]) if query.get("finca",[""])[0] else None
                module_id=int(query.get("modulo",[""])[0]) if query.get("modulo",[""])[0] else None
            except ValueError:return self.json(400,{"error":"La finca o el módulo seleccionado no es válido."})
            def conditions(date_field=None,include_scope=True):
                parts=[];values=[]
                if date_field and start:parts.append(f"{date_field}>=?");values.append(start)
                if date_field and end:parts.append(f"{date_field}<=?");values.append(end)
                if include_scope and farm_id:parts.append("f.id=?");values.append(farm_id)
                if include_scope and module_id:parts.append("m.id=?");values.append(module_id)
                return (" WHERE "+" AND ".join(parts) if parts else ""),values
            with db() as c:
                refresh_activity_statuses(c)
                farms=[dict(row) for row in c.execute("SELECT id,nombre FROM fincas WHERE estado=1 ORDER BY nombre").fetchall()]
                modules=[dict(row) for row in c.execute("SELECT id,finca_id,codigo FROM modulos WHERE estado=1 ORDER BY codigo").fetchall()]
                where,args=conditions()
                pool=c.execute("""SELECT COUNT(*) total,
                    SUM(CASE WHEN COALESCE(v.estado_ciclo,'')='Sembrado' THEN 1 ELSE 0 END) sembradas,
                    SUM(CASE WHEN COALESCE(v.estado_ciclo,'')<>'Sembrado' THEN 1 ELSE 0 END) disponibles,
                    SUM(CASE WHEN v.estado_ciclo='Cosechado' THEN 1 ELSE 0 END) cosechadas
                    FROM piscinas p JOIN modulos m ON m.id=p.modulo_id JOIN fincas f ON f.id=m.finca_id
                    LEFT JOIN vista_piscinas_ciclo_actual v ON v.piscina_id=p.id"""+where,args).fetchone()
                where,args=conditions("DATE(COALESCE(c.fecha_siembra,c.creado_en))")
                cycles=c.execute("""SELECT c.estado etiqueta,COUNT(*) valor FROM ciclos_piscina c
                    JOIN piscinas p ON p.id=c.piscina_id JOIN modulos m ON m.id=p.modulo_id JOIN fincas f ON f.id=m.finca_id"""+where+" GROUP BY c.estado ORDER BY valor DESC",args).fetchall()
                where,args=conditions("DATE(COALESCE(a.fecha_inicio,a.fecha_limite))")
                activities=c.execute("""SELECT a.estado etiqueta,COUNT(*) valor FROM actividades a
                    JOIN piscinas p ON p.id=a.piscina_id JOIN modulos m ON m.id=p.modulo_id JOIN fincas f ON f.id=m.finca_id"""+where+" GROUP BY a.estado ORDER BY valor DESC",args).fetchall()
                where,args=conditions("DATE(mi.creado_en)")
                movements=c.execute("""SELECT mi.tipo etiqueta,COALESCE(SUM(mi.cantidad),0) valor FROM movimientos_inventario mi
                    LEFT JOIN piscinas p ON p.id=mi.piscina_id LEFT JOIN modulos m ON m.id=p.modulo_id LEFT JOIN fincas f ON f.id=m.finca_id"""+where+" GROUP BY mi.tipo ORDER BY mi.tipo",args).fetchall()
                alert_where,alert_args=conditions("DATE(a.generada_en)",False)
                alert_rows=[]
                if alerts_table_ready(c):
                    sync_alerts(c)
                    alert_rows=c.execute("SELECT a.estado etiqueta,COUNT(*) valor FROM alertas a"+alert_where+" GROUP BY a.estado ORDER BY valor DESC",alert_args).fetchall()
                metrics={
                    "piscinas":int(pool["total"] or 0),"disponibles":int(pool["disponibles"] or 0),"sembradas":int(pool["sembradas"] or 0),"cosechadas":int(pool["cosechadas"] or 0),
                    "colaboradores":c.execute("SELECT COUNT(*) total FROM colaboradores WHERE estado=1").fetchone()["total"],
                    "stock_bajo":c.execute("SELECT COUNT(*) total FROM productos_alimento WHERE estado=1 AND stock_actual<=stock_minimo").fetchone()["total"],
                    "alertas":sum(int(row["valor"]) for row in alert_rows if row["etiqueta"]=="Pendiente")}
            return self.json(200,{"dashboard":{"metricas":metrics,"ciclos":[dict(row) for row in cycles],"actividades":[dict(row) for row in activities],"movimientos":[dict(row) for row in movements],"alertas":[dict(row) for row in alert_rows],"fincas":farms,"modulos":modules,"desde":start,"hasta":end}})
        if path=="/api/piscinas":
            if not self.require("piscinas.ver"): return
            if not module_tables_ready(): return self.json(503,{"error":"Ejecute la migración de módulos en MariaDB."})
            with db() as c:
                rows=c.execute("SELECT piscina_id id,ciclo_id,piscina codigo,codigo_productivo,finca,modulo,tipo,area_m2,piscina_activa estado,numero_ciclo,estado_ciclo FROM vista_piscinas_ciclo_actual ORDER BY finca,modulo,piscina").fetchall()
                return self.json(200,{"piscinas":[dict(x) for x in rows]})
        if path=="/api/modulos":
            if not self.require("piscinas.ver"): return
            with db() as c:
                rows=c.execute("SELECT m.id,m.codigo,f.nombre finca FROM modulos m JOIN fincas f ON f.id=m.finca_id WHERE m.estado=1 AND f.estado=1 ORDER BY f.nombre,m.codigo").fetchall()
                return self.json(200,{"modulos":[dict(x) for x in rows]})
        if path=="/api/ciclos":
            if not self.require("piscinas.ver"): return
            try: piscina_id=int(parse_qs(parsed.query).get("piscina_id",[""])[0])
            except (TypeError,ValueError): return self.json(400,{"error":"Seleccione una piscina válida."})
            with db() as c:
                rows=c.execute("""SELECT c.id,c.numero_ciclo,c.estado,c.fecha_siembra,c.fecha_cosecha,
                    c.creado_en,CONCAT(p.codigo,'-',c.numero_ciclo) codigo_productivo
                    FROM ciclos_piscina c JOIN piscinas p ON p.id=c.piscina_id
                    WHERE c.piscina_id=? ORDER BY c.numero_ciclo DESC""",(piscina_id,)).fetchall()
                return self.json(200,{"ciclos":[dict(x) for x in rows]})
        if path=="/api/colaboradores":
            if not self.require("personal.ver"): return
            with db() as c: return self.json(200,{"colaboradores":[dict(x) for x in c.execute("SELECT * FROM colaboradores ORDER BY nombre").fetchall()]})
        if path=="/api/actividades":
            if not self.require("personal.ver"): return
            with db() as c:
                refresh_activity_statuses(c)
                rows=c.execute("SELECT a.*,c.nombre colaborador,COALESCE(v.codigo_productivo,p.codigo) piscina,u.nombre asignado_por FROM actividades a JOIN colaboradores c ON c.id=a.colaborador_id JOIN piscinas p ON p.id=a.piscina_id LEFT JOIN vista_piscinas_ciclo_actual v ON v.piscina_id=p.id JOIN usuarios u ON u.id=a.usuario_asigna ORDER BY COALESCE(a.fecha_inicio,a.fecha_limite) DESC").fetchall()
                return self.json(200,{"actividades":[dict(x) for x in rows]})
        if path=="/api/productos":
            if not self.require("inventario.ver"): return
            with db() as c: return self.json(200,{"productos":[dict(x) for x in c.execute("SELECT * FROM productos_alimento ORDER BY nombre").fetchall()]})
        if path=="/api/movimientos":
            if not self.require("inventario.ver"): return
            with db() as c:
                rows=c.execute("SELECT m.*,pr.nombre producto,pr.unidad,COALESCE(v.codigo_productivo,p.codigo) piscina,p.tipo tipo_piscina,c.nombre responsable,u.nombre registrado_por FROM movimientos_inventario m JOIN productos_alimento pr ON pr.id=m.producto_id LEFT JOIN piscinas p ON p.id=m.piscina_id LEFT JOIN vista_piscinas_ciclo_actual v ON v.piscina_id=p.id LEFT JOIN colaboradores c ON c.id=m.responsable_id JOIN usuarios u ON u.id=m.usuario_id ORDER BY m.id DESC LIMIT 250").fetchall()
                return self.json(200,{"movimientos":[dict(x) for x in rows]})
        if path=="/": self.path="/login.html"
        return super().do_GET()
    def do_POST(self):
        path=urlparse(self.path).path; data=self.body()
        if path=="/api/login":
            identity=str(data.get("usuario","")).strip(); password=str(data.get("password",""))
            with db() as c:
                row=c.execute("SELECT u.* FROM usuarios u JOIN roles r ON r.id=u.rol_id WHERE u.nombre_usuario=? AND r.estado=1",(identity,)).fetchone()
                if not row or not row["estado"] or not password_ok(password,row["password_hash"]): return self.json(401,{"error":"Usuario o contraseña incorrectos."})
                token=secrets.token_urlsafe(32); expiry=now()+timedelta(hours=8)
                c.execute("INSERT INTO sesiones(token_hash,usuario_id,fecha_inicio,expira_en) VALUES(?,?,?,?)",(hashlib.sha256(token.encode()).hexdigest(),row["id"],iso(),iso(expiry)))
                cookie=f"session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800"
                return self.json(200,{"usuario":user_payload(c,row["id"])},cookie)
        if path=="/api/logout":
            cookie=SimpleCookie(self.headers.get("Cookie")); morsel=cookie.get("session")
            if morsel:
                with db() as c: c.execute("UPDATE sesiones SET fecha_fin=? WHERE token_hash=?",(iso(),hashlib.sha256(morsel.value.encode()).hexdigest()))
            return self.json(200,{"ok":True},"session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
        if path=="/api/usuarios":
            if not self.require("usuarios.crear"): return
            required=[str(data.get(x,"")).strip() for x in ("nombre_usuario","nombre","correo","password")]
            try: role=int(data.get("rol_id"))
            except (ValueError,TypeError): role=0
            if any(not x for x in required): return self.json(400,{"error":"Todos los campos son obligatorios."})
            if not USERNAME_RE.fullmatch(required[0]): return self.json(400,{"error":"El usuario debe tener entre 3 y 50 caracteres y usar solo letras, números, punto, guion o guion bajo."})
            if len(required[1]) < 3 or len(required[1]) > 120: return self.json(400,{"error":"El nombre debe tener entre 3 y 120 caracteres."})
            if not EMAIL_RE.fullmatch(required[2]) or len(required[2]) > 150: return self.json(400,{"error":"Ingrese un correo electrónico válido."})
            if not valid_password(required[3]): return self.json(400,{"error":"La contraseña debe tener al menos 8 caracteres, mayúscula, minúscula y número."})
            with db() as c:
                if not c.execute("SELECT 1 FROM roles WHERE id=? AND estado=1",(role,)).fetchone(): return self.json(400,{"error":"El rol seleccionado no es válido."})
            try:
                with db() as c:
                    c.execute("INSERT INTO usuarios(nombre_usuario,nombre,correo,password_hash,rol_id,creado_en) VALUES(?,?,?,?,?,?)",(*required[:3],password_hash(required[3]),role,iso()))
                return self.json(201,{"ok":True})
            except INTEGRITY_ERRORS: return self.json(409,{"error":"El usuario o correo ya existe, o el rol no es válido."})
        if path=="/api/roles-config":
            if not self.require("roles.editar"): return
            nombre=clean_text(data,"nombre",3,60); descripcion=clean_text(data,"descripcion",0,255) or ""
            if not nombre:return self.json(400,{"error":"El nombre del rol debe tener entre 3 y 60 caracteres."})
            try:
                with db() as c:
                    c.execute("INSERT INTO roles(nombre,descripcion,estado) VALUES(?,?,1)",(nombre,descripcion))
                    role_id=c.cursor.lastrowid if USE_MARIADB else c.execute("SELECT last_insert_rowid() id").fetchone()["id"]
                return self.json(201,{"ok":True,"id":role_id})
            except INTEGRITY_ERRORS:return self.json(409,{"error":"Ya existe un rol con ese nombre."})
        if path=="/api/piscinas":
            if not self.require("piscinas.crear"): return
            codigo=clean_text(data,"codigo",2,20); tipo=data.get("tipo"); area=positive_number(data.get("area_m2"))
            try: modulo_id=int(data.get("modulo_id"))
            except (TypeError,ValueError): modulo_id=0
            if not codigo or not modulo_id or tipo not in ("Engorde","Precría") or not area: return self.json(400,{"error":"Módulo, código, tipo y área válida son obligatorios."})
            try:
                with db() as c: c.execute("INSERT INTO piscinas(modulo_id,codigo,tipo,area_m2) VALUES(?,?,?,?)",(modulo_id,codigo.upper(),tipo,area))
                return self.json(201,{"ok":True})
            except INTEGRITY_ERRORS: return self.json(409,{"error":"El código de piscina ya existe."})
        if path=="/api/ciclos":
            if not self.require("piscinas.editar"): return
            try:
                piscina_id=int(data.get("piscina_id"))
                numero=int(data.get("numero_ciclo"))
            except (TypeError,ValueError): return self.json(400,{"error":"Piscina y número de ciclo son obligatorios."})
            if numero < 1: return self.json(400,{"error":"El número de ciclo debe ser mayor que cero."})
            fecha=str(data.get("fecha_siembra") or datetime.now().date().isoformat())
            try: datetime.strptime(fecha,"%Y-%m-%d")
            except ValueError: return self.json(400,{"error":"La fecha de siembra no es válida."})
            try:
                with db() as c:
                    piscina=c.execute("SELECT id,estado FROM piscinas WHERE id=? FOR UPDATE",(piscina_id,)).fetchone()
                    if not piscina or not piscina["estado"]: return self.json(400,{"error":"La piscina no existe o está inactiva."})
                    ultimo=c.execute("SELECT id,numero_ciclo,estado FROM ciclos_piscina WHERE piscina_id=? ORDER BY numero_ciclo DESC LIMIT 1 FOR UPDATE",(piscina_id,)).fetchone()
                    if ultimo and ultimo["estado"] in ("Planificado","Sembrado"):
                        return self.json(409,{"error":"Primero debe cosechar o cancelar el ciclo actual."})
                    esperado=(int(ultimo["numero_ciclo"]) if ultimo and ultimo["estado"]=="Cancelado" else int(ultimo["numero_ciclo"])+1) if ultimo else 1
                    if numero != esperado:
                        return self.json(400,{"error":f"El siguiente ciclo debe ser el número {esperado}."})
                    if ultimo and ultimo["estado"]=="Cancelado":
                        c.execute("""UPDATE ciclos_piscina SET estado='Sembrado',fecha_siembra=?,
                            fecha_cosecha=NULL
                            WHERE id=?""",(fecha,ultimo["id"]))
                    else:
                        c.execute("INSERT INTO ciclos_piscina(piscina_id,numero_ciclo,estado,fecha_siembra) VALUES(?,?,'Sembrado',?)",(piscina_id,numero,fecha))
                return self.json(201,{"ok":True,"numero_ciclo":numero})
            except INTEGRITY_ERRORS: return self.json(409,{"error":"Ese ciclo ya existe para la piscina."})
        if path=="/api/colaboradores":
            if not self.require("personal.crear"): return
            codigo=clean_text(data,"codigo_empleado",2,30); nombre=clean_text(data,"nombre",3,150); puesto=clean_text(data,"puesto",2,100); celular=clean_text(data,"celular",0,20) or ""
            fecha_ingreso=str(data.get("fecha_ingreso","")).strip()
            try: datetime.strptime(fecha_ingreso,"%Y-%m-%d")
            except ValueError: return self.json(400,{"error":"Código, nombre, puesto y fecha de ingreso válida son obligatorios."})
            if not codigo or not nombre or not puesto: return self.json(400,{"error":"Código, nombre, puesto y fecha de ingreso válida son obligatorios."})
            try:
                with db() as c: c.execute("INSERT INTO colaboradores(codigo_empleado,nombre,puesto,fecha_ingreso,celular) VALUES(?,?,?,?,?)",(codigo.upper(),nombre,puesto,fecha_ingreso,celular))
                return self.json(201,{"ok":True})
            except INTEGRITY_ERRORS: return self.json(409,{"error":"El código de empleado ya existe."})
        if path=="/api/actividades":
            user=self.require("personal.asignar")
            if not user:return
            descripcion=clean_text(data,"descripcion",5,300)
            inicio=str(data.get("fecha_inicio","")).replace("T"," ")
            fin=str(data.get("fecha_fin","")).replace("T"," ")
            try:
                colaborador=int(data.get("colaborador_id")); piscina=int(data.get("piscina_id"))
                inicio_dt=datetime.fromisoformat(inicio); fin_dt=datetime.fromisoformat(fin)
            except (TypeError,ValueError): return self.json(400,{"error":"Complete colaborador, piscina, inicio y finalización válidos."})
            if not descripcion: return self.json(400,{"error":"La descripción debe contener entre 5 y 300 caracteres."})
            if inicio_dt.date()!=fin_dt.date(): return self.json(400,{"error":"La actividad debe iniciar y finalizar el mismo día."})
            if fin_dt<=inicio_dt: return self.json(400,{"error":"La hora de finalización debe ser posterior a la hora de inicio."})
            with db() as c:
                valid=c.execute("""SELECT 1 FROM colaboradores c,piscinas p
                    WHERE c.id=? AND c.estado=1
                    AND (UPPER(TRIM(c.puesto)) LIKE 'AUXILIAR%%' OR UPPER(TRIM(c.puesto)) LIKE 'SUPERVISOR%%')
                    AND p.id=? AND p.estado=1""",(colaborador,piscina)).fetchone()
                if not valid:return self.json(400,{"error":"Solo puede asignar actividades a auxiliares o supervisores activos y a piscinas habilitadas."})
                overlap=c.execute("""SELECT 1 FROM actividades
                    WHERE colaborador_id=? AND estado IN ('Pendiente','En proceso')
                    AND fecha_inicio IS NOT NULL
                    AND fecha_inicio<? AND COALESCE(fecha_fin,fecha_limite)>?
                    LIMIT 1""",(colaborador,fin,inicio)).fetchone()
                if overlap:return self.json(409,{"error":"El colaborador ya tiene una actividad asignada dentro de ese horario."})
                c.execute("""INSERT INTO actividades(
                    colaborador_id,piscina_id,descripcion,fecha_inicio,fecha_fin,fecha_limite,usuario_asigna
                    ) VALUES(?,?,?,?,?,?,?)""",(colaborador,piscina,descripcion,inicio,fin,fin,user["id"]))
            return self.json(201,{"ok":True})
        if path=="/api/productos":
            if not self.require("inventario.registrar"): return
            codigo=clean_text(data,"codigo",2,30); nombre=clean_text(data,"nombre",3,120); marca=clean_text(data,"marca",2,80); unidad=clean_text(data,"unidad",1,20); minimo=nonnegative_number(data.get("stock_minimo"))
            if not all((codigo,nombre,marca,unidad)) or minimo is None: return self.json(400,{"error":"Complete todos los datos del producto con valores válidos."})
            try:
                with db() as c:c.execute("INSERT INTO productos_alimento(codigo,nombre,marca,unidad,stock_minimo) VALUES(?,?,?,?,?)",(codigo.upper(),nombre,marca,unidad,minimo))
                return self.json(201,{"ok":True})
            except INTEGRITY_ERRORS:return self.json(409,{"error":"El código de producto ya existe."})
        if path=="/api/movimientos":
            user=self.require("inventario.registrar")
            if not user:return
            tipo=data.get("tipo"); cantidad=positive_number(data.get("cantidad"))
            try: producto=int(data.get("producto_id")); piscina=int(data["piscina_id"]) if data.get("piscina_id") else None; responsable=int(data["responsable_id"]) if data.get("responsable_id") else None
            except (TypeError,ValueError):return self.json(400,{"error":"Los datos del movimiento no son válidos."})
            if tipo not in ("Entrada","Salida") or not cantidad:return self.json(400,{"error":"Tipo y cantidad positiva son obligatorios."})
            if tipo=="Salida" and (not piscina or not responsable):return self.json(400,{"error":"Toda salida requiere piscina y responsable."})
            expiry=data.get("fecha_vencimiento") or None
            if expiry:
                try: datetime.strptime(str(expiry),"%Y-%m-%d")
                except ValueError:return self.json(400,{"error":"La fecha de vencimiento no es válida."})
            with db() as c:
                product=c.execute("SELECT stock_actual,estado FROM productos_alimento WHERE id=? FOR UPDATE",(producto,)).fetchone()
                if not product or not product["estado"]:return self.json(400,{"error":"El producto no está disponible."})
                if tipo=="Salida":
                    destination=c.execute("""SELECT 1 FROM piscinas p,colaboradores c
                        WHERE p.id=? AND p.estado=1 AND c.id=? AND c.estado=1""",(piscina,responsable)).fetchone()
                    if not destination:return self.json(400,{"error":"La piscina y el responsable deben estar activos."})
                stock=float(product["stock_actual"])
                if tipo=="Salida" and cantidad>stock:return self.json(400,{"error":"La salida supera la existencia disponible."})
                nuevo=stock+cantidad if tipo=="Entrada" else stock-cantidad
                c.execute("UPDATE productos_alimento SET stock_actual=? WHERE id=?",(nuevo,producto))
                c.execute("INSERT INTO movimientos_inventario(producto_id,tipo,cantidad,piscina_id,lote,fecha_vencimiento,responsable_id,usuario_id,observacion) VALUES(?,?,?,?,?,?,?,?,?)",(producto,tipo,cantidad,piscina,clean_text(data,"lote",0,50),expiry,responsable,user["id"],clean_text(data,"observacion",0,255)))
            return self.json(201,{"ok":True,"stock_actual":nuevo})
        self.json(404,{"error":"Ruta no encontrada."})
    def do_DELETE(self):
        path=urlparse(self.path).path
        if path=="/api/actividades":
            if not self.require("personal.asignar"):return
            with db() as c:
                total=c.execute("SELECT COUNT(*) total FROM actividades").fetchone()["total"]
                c.execute("DELETE FROM actividades")
            return self.json(200,{"ok":True,"eliminadas":total})
        parts=path.strip("/").split("/")
        if len(parts)!=3 or parts[0]!="api":return self.json(404,{"error":"Ruta no encontrada."})
        resource=parts[1]
        try:record_id=int(parts[2])
        except ValueError:return self.json(400,{"error":"Identificador no válido."})
        if resource=="actividades":
            if not self.require("personal.asignar"):return
            with db() as c:
                exists=c.execute("SELECT 1 FROM actividades WHERE id=?",(record_id,)).fetchone()
                if not exists:return self.json(404,{"error":"La actividad no existe."})
                c.execute("DELETE FROM actividades WHERE id=?",(record_id,))
            return self.json(200,{"ok":True})
        if resource=="usuarios":
            user=self.require("usuarios.editar")
            if not user:return
            if record_id in (1,user["id"]):return self.json(400,{"error":"No puede eliminar al administrador principal ni la cuenta que está utilizando."})
            try:
                with db() as c:
                    c.execute("DELETE FROM sesiones WHERE usuario_id=?",(record_id,))
                    c.execute("DELETE FROM recuperaciones_password WHERE usuario_id=?",(record_id,))
                    c.execute("DELETE FROM usuarios WHERE id=?",(record_id,))
                return self.json(200,{"ok":True})
            except INTEGRITY_ERRORS:return self.json(409,{"error":"El usuario tiene actividades o movimientos relacionados y no puede eliminarse."})
        if resource=="colaboradores":
            if not self.require("personal.editar"):return
            try:
                with db() as c:c.execute("DELETE FROM colaboradores WHERE id=?",(record_id,))
                return self.json(200,{"ok":True})
            except INTEGRITY_ERRORS:return self.json(409,{"error":"El colaborador tiene actividades o movimientos relacionados. Elimine primero esos registros."})
        if resource=="ciclos":
            if not self.require("piscinas.editar"):return
            with db() as c:
                cycle=c.execute("SELECT piscina_id,numero_ciclo FROM ciclos_piscina WHERE id=?",(record_id,)).fetchone()
                if not cycle:return self.json(404,{"error":"El ciclo no existe."})
                latest=c.execute("SELECT MAX(numero_ciclo) numero FROM ciclos_piscina WHERE piscina_id=?",(cycle["piscina_id"],)).fetchone()["numero"]
                if cycle["numero_ciclo"]!=latest:return self.json(409,{"error":"Solo puede eliminarse el ciclo más reciente de la piscina."})
                c.execute("DELETE FROM ciclos_piscina WHERE id=?",(record_id,))
            return self.json(200,{"ok":True})
        if resource=="piscinas":
            if not self.require("piscinas.editar"):return
            try:
                with db() as c:c.execute("DELETE FROM piscinas WHERE id=?",(record_id,))
                return self.json(200,{"ok":True})
            except INTEGRITY_ERRORS:return self.json(409,{"error":"La piscina tiene ciclos, actividades o movimientos relacionados y no puede eliminarse."})
        if resource=="movimientos":
            if not self.require("inventario.registrar"):return
            with db() as c:
                move=c.execute("SELECT producto_id,tipo,cantidad FROM movimientos_inventario WHERE id=? FOR UPDATE",(record_id,)).fetchone()
                if not move:return self.json(404,{"error":"El movimiento no existe."})
                product=c.execute("SELECT stock_actual FROM productos_alimento WHERE id=? FOR UPDATE",(move["producto_id"],)).fetchone()
                stock=float(product["stock_actual"]); amount=float(move["cantidad"])
                adjusted=stock-amount if move["tipo"]=="Entrada" else stock+amount
                if adjusted<0:return self.json(409,{"error":"No puede eliminarse esta entrada porque dejaría el stock negativo."})
                c.execute("UPDATE productos_alimento SET stock_actual=? WHERE id=?",(adjusted,move["producto_id"]))
                c.execute("DELETE FROM movimientos_inventario WHERE id=?",(record_id,))
            return self.json(200,{"ok":True})
        if resource=="productos":
            if not self.require("inventario.registrar"):return
            try:
                with db() as c:c.execute("DELETE FROM productos_alimento WHERE id=?",(record_id,))
                return self.json(200,{"ok":True})
            except INTEGRITY_ERRORS:return self.json(409,{"error":"El producto tiene movimientos relacionados. Elimine primero esos movimientos."})
        if resource=="roles-config":
            if not self.require("roles.editar"):return
            if record_id<=6:return self.json(400,{"error":"Los roles base del sistema están protegidos."})
            try:
                with db() as c:
                    c.execute("DELETE FROM rol_permisos WHERE rol_id=?",(record_id,))
                    c.execute("DELETE FROM roles WHERE id=?",(record_id,))
                return self.json(200,{"ok":True})
            except INTEGRITY_ERRORS:return self.json(409,{"error":"El rol tiene usuarios asignados y no puede eliminarse."})
        return self.json(404,{"error":"Ruta no encontrada."})
    def do_PATCH(self):
        parts=urlparse(self.path).path.strip("/").split("/")
        if len(parts)!=3:return self.json(404,{"error":"Ruta no encontrada."})
        data=self.body()
        resource=parts[1]
        if resource=="alertas":
            user=self.require("alertas.atender")
            if not user:return
            try:alert_id=int(parts[2])
            except ValueError:return self.json(400,{"error":"Alerta no válida."})
            if data.get("estado")!="Atendida":return self.json(400,{"error":"La alerta solo puede marcarse como atendida."})
            with db() as c:
                if not alerts_table_ready(c):return self.json(503,{"error":"Ejecute la migración 09_crear_alertas.sql en HeidiSQL."})
                alert=c.execute("SELECT estado FROM alertas WHERE id=?",(alert_id,)).fetchone()
                if not alert:return self.json(404,{"error":"La alerta no existe."})
                if alert["estado"]!="Pendiente":return self.json(409,{"error":"La alerta ya fue atendida o resuelta."})
                c.execute("UPDATE alertas SET estado='Atendida',atendida_en=?,atendida_por=? WHERE id=?",(business_iso(),user["id"],alert_id))
            return self.json(200,{"ok":True})
        if resource in ("piscinas","colaboradores","productos"):
            config={"piscinas":("piscinas","piscinas",("modulo_id","tipo","area_m2","estado")),"colaboradores":("colaboradores","personal",("nombre","puesto","fecha_ingreso","fecha_baja","celular","estado")),"productos":("productos_alimento","inventario",("nombre","marca","unidad","stock_minimo","estado"))}[resource]
            permission=f"{config[1]}.{'cambiar_estado' if set(data)=={'estado'} and resource!='productos' else 'editar'}"
            if resource=="productos":permission="inventario.registrar"
            if not self.require(permission):return
            try:record_id=int(parts[2])
            except ValueError:return self.json(400,{"error":"Identificador no válido."})
            if resource=="colaboradores":
                for date_field in ("fecha_ingreso","fecha_baja"):
                    if data.get(date_field):
                        try: datetime.strptime(str(data[date_field]),"%Y-%m-%d")
                        except ValueError: return self.json(400,{"error":"La fecha laboral no es válida."})
                if set(data)=={"estado"}:
                    data["fecha_baja"]=datetime.now().date().isoformat() if not data["estado"] else None
            if resource=="productos":
                if "nombre" in data and not clean_text(data,"nombre",3,120):return self.json(400,{"error":"El nombre debe tener entre 3 y 120 caracteres."})
                if "marca" in data and not clean_text(data,"marca",2,80):return self.json(400,{"error":"La marca debe tener entre 2 y 80 caracteres."})
                if "unidad" in data and not clean_text(data,"unidad",1,20):return self.json(400,{"error":"La unidad no es válida."})
                if "stock_minimo" in data:
                    minimum=nonnegative_number(data["stock_minimo"])
                    if minimum is None:return self.json(400,{"error":"El stock mínimo no puede ser negativo."})
                    data["stock_minimo"]=minimum
                if "estado" in data and not isinstance(data["estado"],(bool,int)):return self.json(400,{"error":"El estado no es válido."})
            fields=[];values=[]
            for field in config[2]:
                if field in data:fields.append(f"{field}=?");values.append(data[field])
            if not fields:return self.json(400,{"error":"No hay cambios."})
            with db() as c:
                if not c.execute(f"SELECT 1 FROM {config[0]} WHERE id=?",(record_id,)).fetchone():return self.json(404,{"error":"El registro no existe."})
                c.execute(f"UPDATE {config[0]} SET {','.join(fields)} WHERE id=?",(*values,record_id))
            return self.json(200,{"ok":True})
        if resource=="actividades":
            if not self.require("personal.confirmar"):return
            try:activity_id=int(parts[2])
            except ValueError:return self.json(400,{"error":"Actividad no válida."})
            estado=data.get("estado")
            if estado not in ("Pendiente","Realizada"):return self.json(400,{"error":"Estado no válido."})
            with db() as c:c.execute("UPDATE actividades SET estado=?,realizada_en=? WHERE id=?",(estado,iso() if estado=="Realizada" else None,activity_id))
            return self.json(200,{"ok":True})
        if resource=="ciclos":
            if not self.require("piscinas.editar"):return
            try: ciclo_id=int(parts[2])
            except ValueError:return self.json(400,{"error":"Ciclo no válido."})
            estado=data.get("estado")
            if estado not in ("Cosechado","Cancelado"):return self.json(400,{"error":"Solo puede cosechar o cancelar un ciclo activo."})
            fecha=data.get("fecha_cosecha") or datetime.now().date().isoformat()
            if estado=="Cosechado":
                try: datetime.strptime(str(fecha),"%Y-%m-%d")
                except ValueError:return self.json(400,{"error":"La fecha de cosecha no es válida."})
            with db() as c:
                ciclo=c.execute("SELECT estado,fecha_siembra FROM ciclos_piscina WHERE id=? FOR UPDATE",(ciclo_id,)).fetchone()
                if not ciclo:return self.json(404,{"error":"El ciclo no existe."})
                if ciclo["estado"] not in ("Planificado","Sembrado"):return self.json(409,{"error":"El ciclo ya fue cerrado."})
                if estado=="Cosechado" and ciclo["fecha_siembra"] and str(fecha)<str(ciclo["fecha_siembra"]):
                    return self.json(400,{"error":"La cosecha no puede ser anterior a la siembra."})
                c.execute("UPDATE ciclos_piscina SET estado=?,fecha_cosecha=? WHERE id=?",(estado,fecha if estado=="Cosechado" else None,ciclo_id))
            return self.json(200,{"ok":True})
        if resource=="roles-config":
            if not self.require("roles.editar"):return
            try:role_id=int(parts[2])
            except ValueError:return self.json(400,{"error":"Rol no válido."})
            if role_id==1:return self.json(400,{"error":"El rol Administrador conserva siempre todos los permisos."})
            nombre=clean_text(data,"nombre",3,60); descripcion=clean_text(data,"descripcion",0,255) or ""
            permission_ids=data.get("permisos",[])
            if not nombre or not isinstance(permission_ids,list):return self.json(400,{"error":"Los datos del rol no son válidos."})
            try: permission_ids=sorted(set(int(value) for value in permission_ids))
            except (TypeError,ValueError):return self.json(400,{"error":"La selección de permisos no es válida."})
            try:
                with db() as c:
                    if permission_ids:
                        marks=','.join('?' for _ in permission_ids)
                        valid=c.execute(f"SELECT COUNT(*) total FROM permisos WHERE id IN ({marks})",permission_ids).fetchone()["total"]
                        if valid!=len(permission_ids):return self.json(400,{"error":"Uno de los permisos no existe."})
                    c.execute("UPDATE roles SET nombre=?,descripcion=? WHERE id=?",(nombre,descripcion,role_id))
                    c.execute("DELETE FROM rol_permisos WHERE rol_id=?",(role_id,))
                    for permission_id in permission_ids:c.execute("INSERT INTO rol_permisos(rol_id,permiso_id) VALUES(?,?)",(role_id,permission_id))
                return self.json(200,{"ok":True})
            except INTEGRITY_ERRORS:return self.json(409,{"error":"El nombre del rol ya está en uso."})
        if resource!="usuarios":return self.json(404,{"error":"Ruta no encontrada."})
        permission="usuarios.cambiar_estado" if set(data)=={"estado"} else "usuarios.editar"
        if not self.require(permission): return
        try: uid=int(parts[2])
        except ValueError: return self.json(400,{"error":"Usuario no válido."})
        fields=[]; values=[]
        if "nombre" in data and not (3 <= len(str(data["nombre"]).strip()) <= 120): return self.json(400,{"error":"El nombre debe tener entre 3 y 120 caracteres."})
        if "correo" in data and (not EMAIL_RE.fullmatch(str(data["correo"]).strip()) or len(str(data["correo"]).strip()) > 150): return self.json(400,{"error":"Ingrese un correo electrónico válido."})
        if "rol_id" in data:
            with db() as c:
                if not c.execute("SELECT 1 FROM roles WHERE id=? AND estado=1",(data["rol_id"],)).fetchone(): return self.json(400,{"error":"El rol seleccionado no es válido."})
        for source,column in (("nombre","nombre"),("correo","correo"),("rol_id","rol_id"),("estado","estado")):
            if source in data: fields.append(f"{column}=?"); values.append(data[source])
        if data.get("password"):
            if not valid_password(str(data["password"])): return self.json(400,{"error":"La contraseña debe tener al menos 8 caracteres, mayúscula, minúscula y número."})
            fields.append("password_hash=?"); values.append(password_hash(str(data["password"])))
        if not fields: return self.json(400,{"error":"No hay cambios."})
        try:
            with db() as c: c.execute(f"UPDATE usuarios SET {','.join(fields)} WHERE id=?",(*values,uid))
            return self.json(200,{"ok":True})
        except INTEGRITY_ERRORS: return self.json(409,{"error":"Los datos ingresados ya están en uso o no son válidos."})

if __name__=="__main__":
    init_db(); print("Sistema disponible en http://localhost:8000"); ThreadingHTTPServer(("127.0.0.1",8000),App).serve_forever()
