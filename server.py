from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen
import hashlib, hmac, json, os, re, secrets, sqlite3, threading, time
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
    for path in (ROOT/".env",ROOT/".env.sensor",ROOT/".env.whatsapp"):
        if path.exists():
            for raw in path.read_text(encoding="utf-8").splitlines():
                if raw.strip() and not raw.lstrip().startswith("#") and "=" in raw:
                    key,value=raw.split("=",1); os.environ.setdefault(key.strip(),value.strip())

load_env()
USE_MARIADB=bool(os.getenv("DB_PASSWORD"))
# Con HTTPS (Railway) la cookie de sesión debe viajar solo cifrada.
SECURE_COOKIE="; Secure" if os.getenv("COOKIE_SECURE","").lower()=="true" else ""
AUTO_INIT_SCHEMA=os.getenv("AUTO_INIT_SCHEMA","").lower()=="true"
ADMIN_INITIAL_PASSWORD=os.getenv("ADMIN_INITIAL_PASSWORD","")
ADMIN_INITIAL_EMAIL=os.getenv("ADMIN_INITIAL_EMAIL","admin@localhost.invalid")
SENSOR_API_URL=os.getenv("SENSOR_API_URL","").strip()
SENSOR_EXPORT_KEY=os.getenv("SENSOR_EXPORT_KEY","").strip()
WHATSAPP_ALERTS_ENABLED=os.getenv("WHATSAPP_ALERTS_ENABLED","").lower()=="true"
EVOLUTION_API_URL=os.getenv("EVOLUTION_API_URL","").strip().rstrip("/")
EVOLUTION_API_KEY=os.getenv("EVOLUTION_API_KEY","").strip()
EVOLUTION_INSTANCE=os.getenv("EVOLUTION_INSTANCE","").strip()
EVOLUTION_NUMBER=re.sub(r"\D","",os.getenv("EVOLUTION_NUMBER",""))
try:SENSOR_CHECK_SECONDS=max(60,int(os.getenv("SENSOR_CHECK_SECONDS","300")))
except ValueError:SENSOR_CHECK_SECONDS=300
try:SENSOR_REPEAT_HOURS=max(1,int(os.getenv("SENSOR_REPEAT_HOURS","2")))
except ValueError:SENSOR_REPEAT_HOURS=2
INTEGRITY_ERRORS=(sqlite3.IntegrityError,pymysql.err.IntegrityError) if pymysql else (sqlite3.IntegrityError,)
SENSOR_CACHE={"time":0.0,"data":None}
SENSOR_LOCK=threading.Lock()

def now(): return datetime.now(timezone.utc)
def iso(dt=None): return (dt or now()).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
BUSINESS_TZ=timezone(timedelta(hours=-6))
def business_iso(): return now().astimezone(BUSINESS_TZ).strftime("%Y-%m-%d %H:%M:%S")

def sensor_data(force=False):
    """Consulta el proveedor configurado sin exponer la clave al navegador."""
    if not SENSOR_API_URL or not SENSOR_EXPORT_KEY:
        raise RuntimeError("El servicio de monitoreo no está configurado.")
    with SENSOR_LOCK:
        if not force and SENSOR_CACHE["data"] and time.monotonic()-SENSOR_CACHE["time"] < 30:
            return SENSOR_CACHE["data"]
        separator="&" if "?" in SENSOR_API_URL else "?"
        url=f"{SENSOR_API_URL}{separator}exportKey={quote(SENSOR_EXPORT_KEY,safe='')}"
        request=Request(url,headers={"Accept":"application/json","User-Agent":"PacificGold-Monitoreo/1.0"})
        with urlopen(request,timeout=10) as response:
            payload=json.loads(response.read().decode("utf-8"))
        if not isinstance(payload,dict) or not isinstance(payload.get("sensores"),list):
            raise ValueError("El proveedor devolvió un formato inesperado.")
        allowed=("id","nombre","temperaturaC","humedadPct","ultimoDatoEn","estado","tempMinC","tempMaxC","enLinea","bateria")
        clean={"consultadoEn":payload.get("consultadoEn"),"sensores":[]}
        for item in payload["sensores"]:
            if isinstance(item,dict): clean["sensores"].append({key:item.get(key) for key in allowed})
        SENSOR_CACHE.update(time=time.monotonic(),data=clean)
        return clean

def sensor_alert_table_ready():
    try:
        with db() as c:c.execute("SELECT 1 FROM avisos_sensor LIMIT 1")
        return True
    except Exception:return False

def evolution_ready():
    return bool(EVOLUTION_API_URL and EVOLUTION_API_KEY and EVOLUTION_INSTANCE and EVOLUTION_NUMBER)

def send_whatsapp(message):
    """Envía un texto mediante Evolution API sin registrar secretos ni destinatarios."""
    if not evolution_ready(): raise RuntimeError("Evolution API no está configurada.")
    if urlparse(EVOLUTION_API_URL).scheme not in ("http","https"):
        raise RuntimeError("La dirección de Evolution API no es válida.")
    endpoint=f"{EVOLUTION_API_URL}/message/sendText/{quote(EVOLUTION_INSTANCE,safe='')}"
    body=json.dumps({"number":EVOLUTION_NUMBER,"text":message},ensure_ascii=False).encode("utf-8")
    request=Request(endpoint,data=body,method="POST",headers={"Accept":"application/json","Content-Type":"application/json","apikey":EVOLUTION_API_KEY,"User-Agent":"PacificGold-Alertas/1.0"})
    with urlopen(request,timeout=20) as response:
        payload=response.read().decode("utf-8")
        return json.loads(payload) if payload else {"ok":True}

def sensor_conditions(sensor):
    conditions=[]
    name=str(sensor.get("nombre") or "Sensor")
    try:
        temperature=float(sensor.get("temperaturaC")); minimum=float(sensor.get("tempMinC")); maximum=float(sensor.get("tempMaxC"))
        active=temperature < minimum or temperature > maximum
        alert=f"⚠️ ALERTA DE TEMPERATURA\n\nSensor: {name}\nTemperatura actual: {temperature:g} °C\nRango permitido: {minimum:g} °C a {maximum:g} °C\nHora: {now().astimezone(BUSINESS_TZ).strftime('%d/%m/%Y %I:%M %p')}\n\nLa condición requiere revisión."
        recovery=f"✅ TEMPERATURA NORMALIZADA\n\nEl sensor {name} volvió al rango permitido.\nTemperatura actual: {temperature:g} °C."
        conditions.append({"type":"Temperatura","active":active,"value":f"{temperature:g} °C","alert":alert,"recovery":recovery})
    except (TypeError,ValueError): pass
    online=sensor.get("enLinea") is True or str(sensor.get("enLinea")).lower() in ("true","1")
    conditions.append({"type":"Conexion","active":not online,"value":"Desconectado" if not online else "En línea","alert":f"⚠️ SENSOR SIN CONEXIÓN\n\nEl sensor {name} dejó de reportar información. Revise la conexión y alimentación del equipo.","recovery":f"✅ SENSOR EN LÍNEA\n\nEl sensor {name} restableció la conexión."})
    battery=str(sensor.get("bateria") or "").lower()
    conditions.append({"type":"Bateria","active":battery in ("low","baja"),"value":battery or "Sin dato","alert":f"⚠️ BATERÍA BAJA\n\nEl sensor {name} reporta batería baja.","recovery":f"✅ BATERÍA NORMAL\n\nEl sensor {name} ya no reporta batería baja."})
    return conditions

def save_sensor_notice(sensor_id,condition,active,sent_at):
    with db() as c:
        if USE_MARIADB:
            c.execute("""INSERT INTO avisos_sensor(sensor,tipo,activo,valor,ult_env) VALUES(?,?,?,?,?)
                ON DUPLICATE KEY UPDATE activo=VALUES(activo),valor=VALUES(valor),ult_env=VALUES(ult_env)""",(sensor_id,condition["type"],active,condition["value"],sent_at))
        else:
            c.execute("""INSERT INTO avisos_sensor(sensor,tipo,activo,valor,ult_env) VALUES(?,?,?,?,?)
                ON CONFLICT(sensor,tipo) DO UPDATE SET activo=excluded.activo,valor=excluded.valor,ult_env=excluded.ult_env""",(sensor_id,condition["type"],active,condition["value"],sent_at))

def sensor_notice_action(condition,row,repeat_before):
    if condition["active"] and (not row or not row["activo"] or not row["ult_env"] or str(row["ult_env"])<=repeat_before): return "alert"
    if not condition["active"] and row and row["activo"]: return "recovery"
    return None

def process_sensor_alerts():
    if not WHATSAPP_ALERTS_ENABLED or not evolution_ready(): return 0
    if not sensor_alert_table_ready(): raise RuntimeError("Falta aplicar la migración 14 de avisos del sensor.")
    sent=0; current=now(); repeat_before=iso(current-timedelta(hours=SENSOR_REPEAT_HOURS))
    for sensor in sensor_data(True).get("sensores",[]):
        sensor_id=str(sensor.get("id") or sensor.get("nombre") or "sensor")[:100]
        for condition in sensor_conditions(sensor):
            with db() as c: row=c.execute("SELECT activo,ult_env FROM avisos_sensor WHERE sensor=? AND tipo=?",(sensor_id,condition["type"])).fetchone()
            action=sensor_notice_action(condition,row,repeat_before)
            if action:
                send_whatsapp(condition["alert"] if action=="alert" else condition["recovery"])
                save_sensor_notice(sensor_id,condition,condition["active"],iso(current)); sent+=1
    return sent

def whatsapp_alert_worker():
    while True:
        try:
            sent=process_sensor_alerts()
            if sent: print(f"Alertas WhatsApp enviadas: {sent}")
        except Exception as error: print(f"Monitoreo WhatsApp: {error}")
        time.sleep(SENSOR_CHECK_SECONDS)

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
    def sync_conditions(module,key,level,conditions):
        active=set()
        for condition in conditions:
            reference=int(condition["id"]); active.add(reference)
            latest=c.execute("SELECT id,estado FROM alertas WHERE modulo=? AND clave=? AND referencia_id=? ORDER BY id DESC LIMIT 1",(module,key,reference)).fetchone()
            if latest and latest["estado"]!="Resuelta": continue
            c.execute("INSERT INTO alertas(modulo,referencia_id,clave,titulo,descripcion,nivel,generada_en) VALUES(?,?,?,?,?,?,?)",
                (module,reference,key,condition["titulo"],condition["descripcion"],level,timestamp))
        opened=c.execute("SELECT id,referencia_id FROM alertas WHERE modulo=? AND clave=? AND estado IN ('Pendiente','Atendida')",(module,key)).fetchall()
        for alert in opened:
            if int(alert["referencia_id"]) not in active:
                c.execute("UPDATE alertas SET estado='Resuelta',resuelta_en=? WHERE id=?",(timestamp,alert["id"]))
    sources=(
        ("Inventario","stock_bajo","Advertencia","SELECT id,codigo,nombre,stock_actual,stock_minimo,unidad FROM productos_alimento WHERE estado=1 AND stock_actual<=stock_minimo"),
        ("Personal","actividad_vencida","Crítica","SELECT id,descripcion,COALESCE(fecha_fin,fecha_limite) fecha_fin FROM actividades WHERE estado='Vencida'")
    )
    for module,key,level,sql in sources:
        conditions=[]
        for row in c.execute(sql).fetchall():
            if key=="stock_bajo":
                title=f"Stock bajo: {row['nombre']}"
                description=f"{row['codigo']} tiene {row['stock_actual']} {row['unidad']}; el mínimo es {row['stock_minimo']} {row['unidad']}."
            else:
                title="Actividad vencida"
                description=f"{row['descripcion']} finalizó el {row['fecha_fin']} sin confirmarse."
            conditions.append({"id":row["id"],"titulo":title,"descripcion":description})
        sync_conditions(module,key,level,conditions)
    try:
        ranges={str(row["parametro"]).lower():row for row in c.execute(
            "SELECT parametro,minimo,maximo FROM rangos_calidad_agua WHERE activo=1 ORDER BY id"
        ).fetchall()}
        fields=(("oxigeno","oxígeno"),("temp","temperatura"),("ph","ph"),("salinidad","salinidad"))
        quality=[]
        latest=c.execute("""SELECT q.id,q.oxigeno,q.temp,q.ph,q.salinidad,COALESCE(v.codigo_productivo,p.codigo) piscina
            FROM mediciones_calidad_agua q JOIN piscinas p ON p.id=q.piscina_id
            LEFT JOIN vista_piscinas_ciclo_actual v ON v.piscina_id=p.id
            WHERE q.id=(SELECT q2.id FROM mediciones_calidad_agua q2
                WHERE q2.piscina_id=q.piscina_id ORDER BY q2.fecha DESC,q2.id DESC LIMIT 1)""").fetchall()
        for row in latest:
            outside=[]
            for field,key in fields:
                limit=next((value for name,value in ranges.items() if key in name),None)
                if limit and not (float(limit["minimo"])<=float(row[field])<=float(limit["maximo"])):
                    outside.append(limit["parametro"])
            if outside:
                values=f"O2 {row['oxigeno']} mg/L, temperatura {row['temp']} °C, pH {row['ph']} y salinidad {row['salinidad']} ppt"
                quality.append({"id":row["id"],"titulo":f"Calidad fuera de rango: {row['piscina']}","descripcion":f"Parámetros afectados: {', '.join(outside)}. Lectura: {values}."})
        sync_conditions("Calidad del agua","calidad_fuera_rango","Crítica",quality)
    except Exception:
        pass
    try:
        aeration=[]
        rows=c.execute("""SELECT a.id,a.codigo,a.oxigeno,a.umbral_enc,COALESCE(v.codigo_productivo,p.codigo) piscina
            FROM aireadores a JOIN piscinas p ON p.id=a.piscina_id
            LEFT JOIN vista_piscinas_ciclo_actual v ON v.piscina_id=p.id
            WHERE a.activo=1 AND a.oxigeno IS NOT NULL AND a.oxigeno<a.umbral_enc""").fetchall()
        for row in rows:
            aeration.append({"id":row["id"],"titulo":f"Oxígeno bajo: {row['piscina']}",
                "descripcion":f"{row['codigo']} registra {row['oxigeno']} mg/L; el umbral de encendido es {row['umbral_enc']} mg/L."})
        sync_conditions("Aireación","oxigeno_bajo","Crítica",aeration)
    except Exception:
        pass

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
        permissions = [*(('usuarios',x) for x in ('ver','crear','editar','cambiar_estado')),*(('roles',x) for x in ('ver','editar')),*(('piscinas',x) for x in ('ver','crear','editar','cambiar_estado')),*(('aireacion',x) for x in ('ver','operar')),*(('inventario',x) for x in ('ver','registrar')),*(('personal',x) for x in ('ver','crear','editar','cambiar_estado','asignar','confirmar')),*(('calidad_agua',x) for x in ('ver','registrar','atender_alertas')),*(('reportes',x) for x in ('ver','exportar')),*(('alertas',x) for x in ('ver','atender')),('monitoreo','ver')]
        for module, function in permissions:
            c.execute("INSERT OR IGNORE INTO permisos(modulo,funcion) VALUES(?,?)", (module,function))
        c.execute("INSERT OR IGNORE INTO rol_permisos SELECT 1,id FROM permisos")
        role_permissions = {2:[('aireacion','ver'),('aireacion','operar'),('inventario','ver'),('personal','ver'),('personal','asignar'),('calidad_agua','ver'),('reportes','ver'),('reportes','exportar'),('alertas','ver'),('alertas','atender'),('monitoreo','ver')],3:[('aireacion','ver'),('inventario','ver'),('inventario','registrar'),('personal','ver'),('personal','confirmar'),('calidad_agua','ver'),('calidad_agua','registrar'),('alertas','ver')],4:[('aireacion','ver'),('calidad_agua','ver'),('calidad_agua','registrar'),('calidad_agua','atender_alertas'),('reportes','ver'),('alertas','ver'),('alertas','atender'),('monitoreo','ver')],5:[('aireacion','ver'),('inventario','ver'),('personal','ver'),('calidad_agua','ver'),('reportes','ver'),('reportes','exportar'),('alertas','ver'),('monitoreo','ver')],6:[('inventario','ver'),('inventario','registrar'),('alertas','ver'),('monitoreo','ver')]}
        for role_id, allowed in role_permissions.items():
            for module, function in allowed:
                c.execute("INSERT OR IGNORE INTO rol_permisos SELECT ?,id FROM permisos WHERE modulo=? AND funcion=?",(role_id,module,function))
        if not c.execute("SELECT 1 FROM usuarios").fetchone():
            c.execute("INSERT INTO usuarios(nombre_usuario,nombre,correo,password_hash,rol_id,creado_en) VALUES(?,?,?,?,1,?)", ("admin","Administrador del sistema","admin@orodelpacifico.local",password_hash("Admin123!"),iso()))

def apply_schema():
    """Crea objetos faltantes del esquema; requiere una cuenta con permisos DDL."""
    text=(ROOT/"database"/"schema"/"schema.sql").read_text(encoding="utf-8")
    text="\n".join(line for line in text.splitlines() if not line.strip().startswith("--"))
    statements=[s.strip() for s in re.split(r";\s*\n",text) if s.strip()]
    conn=MariaConnection()
    try:
        for statement in statements: conn.cursor.execute(statement.rstrip(";"))
        conn.conn.commit()
    finally: conn.cursor.close(); conn.conn.close()
    return len(statements)

def init_mariadb():
    required={"roles","permisos","rol_permisos","usuarios","sesiones","fincas","modulos","piscinas","ciclos_piscina","colaboradores","actividades","productos_alimento","movimientos_inventario","alertas"}
    with db() as c:
        existing={row["TABLE_NAME"] for row in c.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE()").fetchall()}
    missing=sorted(required-existing)
    if missing and AUTO_INIT_SCHEMA:
        print(f"Esquema incompleto: se aplicaron {apply_schema()} sentencias de instalación.")
        with db() as c:
            existing={row["TABLE_NAME"] for row in c.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE()").fetchall()}
        missing=sorted(required-existing)
    if missing:
        raise RuntimeError("La base de datos no está preparada. Faltan: "+", ".join(missing)+". Aplique el esquema con una cuenta administradora; no otorgue permisos DDL al usuario de la aplicación.")
    roles=[(1,"Administrador","Configuración y acceso total"),(2,"Jefe de producción","Supervisión integral de la operación"),(3,"Encargado de piscina","Operación de piscinas asignadas"),(4,"Técnico de calidad","Control de parámetros del agua"),(5,"Gerencia","Consulta de indicadores y reportes"),(6,"Encargado de Bodega","Control de entradas y salidas de alimento")]
    permissions=[*(('usuarios',x) for x in ('ver','crear','editar','cambiar_estado')),*(('roles',x) for x in ('ver','editar')),*(('piscinas',x) for x in ('ver','crear','editar','cambiar_estado')),*(('aireacion',x) for x in ('ver','operar')),*(('inventario',x) for x in ('ver','registrar')),*(('personal',x) for x in ('ver','crear','editar','cambiar_estado','asignar','confirmar')),*(('calidad_agua',x) for x in ('ver','registrar','atender_alertas')),*(('reportes',x) for x in ('ver','exportar')),*(('alertas',x) for x in ('ver','atender')),('monitoreo','ver')]
    role_permissions={2:[('aireacion','ver'),('aireacion','operar'),('inventario','ver'),('personal','ver'),('personal','asignar'),('calidad_agua','ver'),('reportes','ver'),('reportes','exportar'),('alertas','ver'),('alertas','atender'),('monitoreo','ver')],3:[('aireacion','ver'),('inventario','ver'),('inventario','registrar'),('personal','ver'),('personal','confirmar'),('calidad_agua','ver'),('calidad_agua','registrar'),('alertas','ver')],4:[('aireacion','ver'),('calidad_agua','ver'),('calidad_agua','registrar'),('calidad_agua','atender_alertas'),('reportes','ver'),('alertas','ver'),('alertas','atender'),('monitoreo','ver')],5:[('aireacion','ver'),('inventario','ver'),('personal','ver'),('calidad_agua','ver'),('reportes','ver'),('reportes','exportar'),('alertas','ver'),('monitoreo','ver')],6:[('inventario','ver'),('inventario','registrar'),('alertas','ver'),('monitoreo','ver')]}
    with db() as c:
        for role in roles: c.execute("INSERT INTO roles(id,nombre,descripcion) VALUES(?,?,?) ON DUPLICATE KEY UPDATE nombre=VALUES(nombre),descripcion=VALUES(descripcion)",role)
        for permission in permissions: c.execute("INSERT IGNORE INTO permisos(modulo,funcion) VALUES(?,?)",permission)
        c.execute("INSERT IGNORE INTO rol_permisos SELECT 1,id FROM permisos")
        for role_id,allowed in role_permissions.items():
            for module,function in allowed: c.execute("INSERT IGNORE INTO rol_permisos SELECT ?,id FROM permisos WHERE modulo=? AND funcion=?",(role_id,module,function))
        if not c.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone():
            if not valid_password(ADMIN_INITIAL_PASSWORD):
                raise RuntimeError("Defina ADMIN_INITIAL_PASSWORD con al menos 8 caracteres, mayúscula, minúscula y número antes de crear el primer usuario.")
            c.execute("INSERT INTO usuarios(nombre_usuario,nombre,correo,password_hash,rol_id,creado_en) VALUES(?,?,?,?,1,?)",("admin","Administrador del sistema",ADMIN_INITIAL_EMAIL,password_hash(ADMIN_INITIAL_PASSWORD),iso()))

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
        if path=="/api/monitoreo":
            if not self.require("monitoreo.ver"): return
            force=parse_qs(parsed.query).get("actualizar",[""])[0]=="1"
            try:return self.json(200,{"monitoreo":sensor_data(force)})
            except RuntimeError as error:return self.json(503,{"error":str(error)})
            except HTTPError as error:return self.json(502,{"error":f"El proveedor del sensor respondió con estado {error.code}."})
            except (URLError,TimeoutError):return self.json(502,{"error":"No fue posible conectar con el proveedor del sensor."})
            except (ValueError,json.JSONDecodeError):return self.json(502,{"error":"El proveedor del sensor devolvió información no válida."})
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
                    "alertas_pendientes":c.execute("SELECT COUNT(*) total FROM alertas WHERE estado='Pendiente'").fetchone()["total"] if alerts_ready else 0,
                    "calidad_fuera":c.execute("SELECT COUNT(*) total FROM alertas WHERE clave='calidad_fuera_rango' AND estado IN ('Pendiente','Atendida')").fetchone()["total"] if alerts_ready else 0,
                    "aireadores_encendidos":c.execute("SELECT COUNT(*) total FROM aireadores WHERE activo=1 AND encendido=1").fetchone()["total"],
                    "aireacion_baja":c.execute("SELECT COUNT(*) total FROM alertas WHERE clave='oxigeno_bajo' AND estado IN ('Pendiente','Atendida')").fetchone()["total"] if alerts_ready else 0}
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
        if path=="/api/aireacion":
            if not self.require("aireacion.ver"): return
            try:
                with db() as c:
                    equipment=[dict(row) for row in c.execute("""SELECT a.id,a.piscina_id,a.codigo,a.modo,a.encendido,a.activo,a.oxigeno,
                        a.umbral_enc,a.umbral_apa,a.actualizado,COALESCE(v.codigo_productivo,p.codigo) piscina
                        FROM aireadores a JOIN piscinas p ON p.id=a.piscina_id
                        LEFT JOIN vista_piscinas_ciclo_actual v ON v.piscina_id=p.id
                        ORDER BY a.activo DESC,a.codigo""").fetchall()]
                    events=[dict(row) for row in c.execute("""SELECT e.id,e.accion,e.origen,e.oxigeno,e.detalle,e.creado,
                        a.codigo aireador,COALESCE(v.codigo_productivo,p.codigo) piscina,u.nombre usuario
                        FROM eventos_aireacion e JOIN aireadores a ON a.id=e.aireador_id
                        JOIN piscinas p ON p.id=a.piscina_id LEFT JOIN vista_piscinas_ciclo_actual v ON v.piscina_id=p.id
                        JOIN usuarios u ON u.id=e.usuario_id ORDER BY e.id DESC LIMIT 200""").fetchall()]
                    pools=[dict(row) for row in c.execute("""SELECT p.id,COALESCE(v.codigo_productivo,p.codigo) codigo
                        FROM piscinas p LEFT JOIN vista_piscinas_ciclo_actual v ON v.piscina_id=p.id
                        WHERE p.estado=1 ORDER BY codigo""").fetchall()]
            except Exception:
                return self.json(503,{"error":"El módulo de aireación todavía no está instalado en la base de datos."})
            for item in equipment:
                if item["oxigeno"] is None:item["condicion"]="Sin lectura"
                elif float(item["oxigeno"]) < float(item["umbral_enc"]):item["condicion"]="Oxígeno bajo"
                elif float(item["oxigeno"]) >= float(item["umbral_apa"]):item["condicion"]="Normal"
                else:item["condicion"]="En recuperación"
            return self.json(200,{"aireadores":equipment,"eventos":events,"piscinas":pools})
        if path=="/api/calidad":
            if not self.require("calidad_agua.ver"): return
            try:
                with db() as c:
                    ranges=[dict(row) for row in c.execute(
                        "SELECT id,parametro,unidad,minimo,maximo,activo FROM rangos_calidad_agua ORDER BY id"
                    ).fetchall()]
                    rows=[dict(row) for row in c.execute("""SELECT q.id,q.piscina_id,q.resp_id,q.fecha,q.oxigeno,q.temp,q.ph,q.salinidad,q.notas,
                        COALESCE(v.codigo_productivo,p.codigo) piscina,c.nombre responsable,u.nombre registrado_por
                        FROM mediciones_calidad_agua q
                        JOIN piscinas p ON p.id=q.piscina_id
                        LEFT JOIN vista_piscinas_ciclo_actual v ON v.piscina_id=p.id
                        JOIN colaboradores c ON c.id=q.resp_id
                        JOIN usuarios u ON u.id=q.usuario_id
                        ORDER BY q.fecha DESC,q.id DESC LIMIT 300""").fetchall()]
                    pools=[dict(row) for row in c.execute("""SELECT p.id,COALESCE(v.codigo_productivo,p.codigo) codigo
                        FROM piscinas p LEFT JOIN vista_piscinas_ciclo_actual v ON v.piscina_id=p.id
                        WHERE p.estado=1 ORDER BY codigo""").fetchall()]
                    staff=[dict(row) for row in c.execute(
                        "SELECT id,codigo_empleado,nombre,puesto FROM colaboradores WHERE estado=1 ORDER BY nombre"
                    ).fetchall()]
            except Exception:
                return self.json(503,{"error":"El módulo de calidad del agua todavía no está instalado en la base de datos."})
            limits={str(row["parametro"]).lower():row for row in ranges if row["activo"]}
            fields=(("oxigeno","oxígeno"),("temp","temperatura"),("ph","ph"),("salinidad","salinidad"))
            for row in rows:
                outside=[]
                for field,key in fields:
                    limit=next((value for name,value in limits.items() if key in name),None)
                    if limit and not (float(limit["minimo"]) <= float(row[field]) <= float(limit["maximo"])):
                        outside.append(limit["parametro"])
                row["estado"]="Fuera de rango" if outside else "Normal"
                row["fuera_rango"]=outside
            return self.json(200,{"mediciones":rows,"rangos":ranges,"piscinas":pools,"responsables":staff})
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
                    "sql":"SELECT a.descripcion actividad,c.nombre responsable,COALESCE(v.codigo_productivo,p.codigo,'Trabajos varios') piscina,a.fecha_inicio inicio,COALESCE(a.fecha_fin,a.fecha_limite) fin,a.estado FROM actividades a JOIN colaboradores c ON c.id=a.colaborador_id LEFT JOIN piscinas p ON p.id=a.piscina_id LEFT JOIN vista_piscinas_ciclo_actual v ON v.piscina_id=p.id",
                    "fecha":"DATE(COALESCE(a.fecha_inicio,a.fecha_limite))"},
                "inventario":{
                    "titulo":"Movimientos de inventario",
                    "columnas":[("fecha","Fecha"),("tipo","Movimiento"),("producto","Producto"),("cantidad","Cantidad"),("unidad","Unidad"),("lote","Lote"),("piscina","Piscina"),("responsable","Responsable")],
                    "sql":"SELECT mi.creado_en fecha,mi.tipo,pa.nombre producto,mi.cantidad,pa.unidad,mi.lote,COALESCE(v.codigo_productivo,p.codigo,'—') piscina,COALESCE(c.nombre,'—') responsable FROM movimientos_inventario mi JOIN productos_alimento pa ON pa.id=mi.producto_id LEFT JOIN piscinas p ON p.id=mi.piscina_id LEFT JOIN vista_piscinas_ciclo_actual v ON v.piscina_id=p.id LEFT JOIN colaboradores c ON c.id=mi.responsable_id",
                    "fecha":"DATE(mi.creado_en)"},
                "calidad":{
                    "titulo":"Mediciones de calidad del agua",
                    "columnas":[("fecha","Fecha"),("piscina","Piscina"),("responsable","Responsable"),("oxigeno","Oxígeno mg/L"),("temp","Temperatura °C"),("ph","pH"),("salinidad","Salinidad ppt"),("notas","Observaciones")],
                    "sql":"SELECT q.fecha,COALESCE(v.codigo_productivo,p.codigo) piscina,c.nombre responsable,q.oxigeno,q.temp,q.ph,q.salinidad,COALESCE(q.notas,'—') notas FROM mediciones_calidad_agua q JOIN piscinas p ON p.id=q.piscina_id LEFT JOIN vista_piscinas_ciclo_actual v ON v.piscina_id=p.id JOIN colaboradores c ON c.id=q.resp_id",
                    "fecha":"DATE(q.fecha)"},
                "aireacion":{
                    "titulo":"Historial de control de aireación",
                    "columnas":[("fecha","Fecha"),("aireador","Aireador"),("piscina","Piscina"),("accion","Acción"),("origen","Origen"),("oxigeno","Oxígeno mg/L"),("usuario","Usuario"),("detalle","Detalle")],
                    "sql":"SELECT e.creado fecha,a.codigo aireador,COALESCE(v.codigo_productivo,p.codigo) piscina,e.accion,e.origen,e.oxigeno,u.nombre usuario,COALESCE(e.detalle,'—') detalle FROM eventos_aireacion e JOIN aireadores a ON a.id=e.aireador_id JOIN piscinas p ON p.id=a.piscina_id LEFT JOIN vista_piscinas_ciclo_actual v ON v.piscina_id=p.id JOIN usuarios u ON u.id=e.usuario_id",
                    "fecha":"DATE(e.creado)"},
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
                    LEFT JOIN piscinas p ON p.id=a.piscina_id LEFT JOIN modulos m ON m.id=p.modulo_id LEFT JOIN fincas f ON f.id=m.finca_id"""+where+" GROUP BY a.estado ORDER BY valor DESC",args).fetchall()
                where,args=conditions("DATE(mi.creado_en)")
                movements=c.execute("""SELECT mi.tipo etiqueta,COALESCE(SUM(mi.cantidad),0) valor FROM movimientos_inventario mi
                    LEFT JOIN piscinas p ON p.id=mi.piscina_id LEFT JOIN modulos m ON m.id=p.modulo_id LEFT JOIN fincas f ON f.id=m.finca_id"""+where+" GROUP BY mi.tipo ORDER BY mi.tipo",args).fetchall()
                where,args=conditions("DATE(q.fecha)")
                quality=c.execute("""SELECT CASE WHEN
                    q.oxigeno NOT BETWEEN (SELECT minimo FROM rangos_calidad_agua WHERE activo=1 ORDER BY id LIMIT 1) AND (SELECT maximo FROM rangos_calidad_agua WHERE activo=1 ORDER BY id LIMIT 1)
                    OR q.temp NOT BETWEEN (SELECT minimo FROM rangos_calidad_agua WHERE parametro='Temperatura' AND activo=1 LIMIT 1) AND (SELECT maximo FROM rangos_calidad_agua WHERE parametro='Temperatura' AND activo=1 LIMIT 1)
                    OR q.ph NOT BETWEEN (SELECT minimo FROM rangos_calidad_agua WHERE parametro='pH' AND activo=1 LIMIT 1) AND (SELECT maximo FROM rangos_calidad_agua WHERE parametro='pH' AND activo=1 LIMIT 1)
                    OR q.salinidad NOT BETWEEN (SELECT minimo FROM rangos_calidad_agua WHERE parametro='Salinidad' AND activo=1 LIMIT 1) AND (SELECT maximo FROM rangos_calidad_agua WHERE parametro='Salinidad' AND activo=1 LIMIT 1)
                    THEN 'Fuera de rango' ELSE 'Normal' END etiqueta,COUNT(*) valor
                    FROM mediciones_calidad_agua q JOIN piscinas p ON p.id=q.piscina_id
                    JOIN modulos m ON m.id=p.modulo_id JOIN fincas f ON f.id=m.finca_id"""+where+" GROUP BY etiqueta ORDER BY etiqueta",args).fetchall()
                where,args=conditions()
                aeration=c.execute("""SELECT IF(a.encendido=1,'Encendidos','Apagados') etiqueta,COUNT(*) valor
                    FROM aireadores a JOIN piscinas p ON p.id=a.piscina_id
                    JOIN modulos m ON m.id=p.modulo_id JOIN fincas f ON f.id=m.finca_id"""+where+" GROUP BY a.encendido ORDER BY a.encendido DESC",args).fetchall()
                alert_where,alert_args=conditions("DATE(a.generada_en)",False)
                alert_rows=[]
                if alerts_table_ready(c):
                    sync_alerts(c)
                    alert_rows=c.execute("SELECT a.estado etiqueta,COUNT(*) valor FROM alertas a"+alert_where+" GROUP BY a.estado ORDER BY valor DESC",alert_args).fetchall()
                metrics={
                    "piscinas":int(pool["total"] or 0),"disponibles":int(pool["disponibles"] or 0),"sembradas":int(pool["sembradas"] or 0),"cosechadas":int(pool["cosechadas"] or 0),
                    "colaboradores":c.execute("SELECT COUNT(*) total FROM colaboradores WHERE estado=1").fetchone()["total"],
                    "stock_bajo":c.execute("SELECT COUNT(*) total FROM productos_alimento WHERE estado=1 AND stock_actual<=stock_minimo").fetchone()["total"],
                    "alertas":sum(int(row["valor"]) for row in alert_rows if row["etiqueta"]=="Pendiente"),
                    "calidad_fuera":sum(int(row["valor"]) for row in quality if row["etiqueta"]=="Fuera de rango"),
                    "aireadores_enc":sum(int(row["valor"]) for row in aeration if row["etiqueta"]=="Encendidos")}
            return self.json(200,{"dashboard":{"metricas":metrics,"ciclos":[dict(row) for row in cycles],"actividades":[dict(row) for row in activities],"movimientos":[dict(row) for row in movements],"calidad":[dict(row) for row in quality],"aireacion":[dict(row) for row in aeration],"alertas":[dict(row) for row in alert_rows],"fincas":farms,"modulos":modules,"desde":start,"hasta":end}})
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
                rows=c.execute("SELECT a.*,c.nombre colaborador,COALESCE(v.codigo_productivo,p.codigo,'Trabajos varios') piscina,u.nombre asignado_por FROM actividades a JOIN colaboradores c ON c.id=a.colaborador_id LEFT JOIN piscinas p ON p.id=a.piscina_id LEFT JOIN vista_piscinas_ciclo_actual v ON v.piscina_id=p.id JOIN usuarios u ON u.id=a.usuario_asigna ORDER BY COALESCE(a.fecha_inicio,a.fecha_limite) DESC").fetchall()
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
                cookie=f"session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800{SECURE_COOKIE}"
                return self.json(200,{"usuario":user_payload(c,row["id"])},cookie)
        if path=="/api/logout":
            cookie=SimpleCookie(self.headers.get("Cookie")); morsel=cookie.get("session")
            if morsel:
                with db() as c: c.execute("UPDATE sesiones SET fecha_fin=? WHERE token_hash=?",(iso(),hashlib.sha256(morsel.value.encode()).hexdigest()))
            return self.json(200,{"ok":True},f"session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0{SECURE_COOKIE}")
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
                colaborador=int(data.get("colaborador_id")); piscina=int(data["piscina_id"]) if data.get("piscina_id") else None
                inicio_dt=datetime.fromisoformat(inicio); fin_dt=datetime.fromisoformat(fin)
            except (TypeError,ValueError): return self.json(400,{"error":"Complete colaborador, inicio y finalización válidos."})
            if not descripcion: return self.json(400,{"error":"La descripción debe contener entre 5 y 300 caracteres."})
            if inicio_dt.date()!=fin_dt.date(): return self.json(400,{"error":"La actividad debe iniciar y finalizar el mismo día."})
            if fin_dt<=inicio_dt: return self.json(400,{"error":"La hora de finalización debe ser posterior a la hora de inicio."})
            with db() as c:
                valid=c.execute("""SELECT 1 FROM colaboradores c
                    WHERE c.id=? AND c.estado=1
                    AND (UPPER(TRIM(c.puesto)) LIKE 'AUXILIAR%%' OR UPPER(TRIM(c.puesto)) LIKE 'SUPERVISOR%%')""",(colaborador,)).fetchone()
                if not valid:return self.json(400,{"error":"Solo puede asignar actividades a auxiliares o supervisores activos."})
                if piscina and not c.execute("SELECT 1 FROM piscinas WHERE id=? AND estado=1",(piscina,)).fetchone():
                    return self.json(400,{"error":"La piscina seleccionada no está habilitada."})
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
        if path=="/api/aireacion":
            user=self.require("aireacion.operar")
            if not user:return
            codigo=clean_text(data,"codigo",2,30)
            try:
                piscina=int(data.get("piscina_id")); enc=float(data.get("umbral_enc")); apa=float(data.get("umbral_apa"))
            except (TypeError,ValueError):
                return self.json(400,{"error":"Complete la piscina, el código y los umbrales."})
            if not codigo or enc<0 or apa<=enc:
                return self.json(400,{"error":"El umbral de apagado debe ser mayor que el de encendido."})
            try:
                with db() as c:
                    if not c.execute("SELECT 1 FROM piscinas WHERE id=? AND estado=1",(piscina,)).fetchone():
                        return self.json(400,{"error":"La piscina seleccionada no está activa."})
                    c.execute("INSERT INTO aireadores(piscina_id,codigo,umbral_enc,umbral_apa) VALUES(?,?,?,?)",(piscina,codigo.upper(),enc,apa))
                return self.json(201,{"ok":True})
            except INTEGRITY_ERRORS:return self.json(409,{"error":"Ya existe un aireador con ese código."})
        if path in ("/api/aireacion/lectura","/api/aireacion/operar","/api/aireacion/modo"):
            user=self.require("aireacion.operar")
            if not user:return
            try:air_id=int(data.get("aireador_id"))
            except (TypeError,ValueError):return self.json(400,{"error":"Seleccione un aireador válido."})
            with db() as c:
                item=c.execute("SELECT * FROM aireadores WHERE id=? AND activo=1 FOR UPDATE",(air_id,)).fetchone()
                if not item:return self.json(404,{"error":"El aireador no existe o está inactivo."})
                if path.endswith("/lectura"):
                    oxygen=nonnegative_number(data.get("oxigeno"))
                    if oxygen is None:return self.json(400,{"error":"Ingrese una lectura de oxígeno válida."})
                    previous=bool(item["encendido"]); current=previous; detail="Lectura registrada."
                    if item["modo"]=="Automático":
                        if oxygen<float(item["umbral_enc"]):current=True
                        elif oxygen>=float(item["umbral_apa"]):current=False
                        detail="Control automático aplicado según los umbrales configurados."
                    c.execute("UPDATE aireadores SET oxigeno=?,encendido=? WHERE id=?",(oxygen,current,air_id))
                    c.execute("INSERT INTO eventos_aireacion(aireador_id,usuario_id,accion,origen,oxigeno,detalle) VALUES(?,?,?,?,?,?)",(air_id,user["id"],"Lectura",item["modo"],oxygen,detail))
                    if current!=previous:
                        action="Encendido" if current else "Apagado"
                        c.execute("INSERT INTO eventos_aireacion(aireador_id,usuario_id,accion,origen,oxigeno,detalle) VALUES(?,?,?,?,?,?)",(air_id,user["id"],action,"Automático",oxygen,"Cambio automático por nivel de oxígeno."))
                elif path.endswith("/operar"):
                    if item["modo"]!="Manual":return self.json(409,{"error":"Cambie el aireador a modo Manual antes de operarlo directamente."})
                    current=not bool(item["encendido"])
                    c.execute("UPDATE aireadores SET encendido=? WHERE id=?",(current,air_id))
                    c.execute("INSERT INTO eventos_aireacion(aireador_id,usuario_id,accion,origen,oxigeno,detalle) VALUES(?,?,?,?,?,?)",(air_id,user["id"],"Encendido" if current else "Apagado","Manual",item["oxigeno"],"Acción ejecutada por el usuario."))
                else:
                    mode=data.get("modo")
                    if mode not in ("Manual","Automático"):return self.json(400,{"error":"Seleccione un modo válido."})
                    c.execute("UPDATE aireadores SET modo=? WHERE id=?",(mode,air_id))
                    c.execute("INSERT INTO eventos_aireacion(aireador_id,usuario_id,accion,origen,oxigeno,detalle) VALUES(?,?,?,?,?,?)",(air_id,user["id"],"Modo","Manual",item["oxigeno"],f"Modo cambiado a {mode}."))
            return self.json(200,{"ok":True})
        if path=="/api/calidad":
            user=self.require("calidad_agua.registrar")
            if not user:return
            try:
                piscina=int(data.get("piscina_id")); responsable=int(data.get("resp_id"))
                oxigeno=float(data.get("oxigeno")); temp=float(data.get("temp"))
                ph=float(data.get("ph")); salinidad=float(data.get("salinidad"))
                fecha=datetime.fromisoformat(str(data.get("fecha","")).replace("T"," "))
            except (TypeError,ValueError):
                return self.json(400,{"error":"Complete todos los datos de la medición con valores válidos."})
            if oxigeno<0 or temp<0 or not 0<=ph<=14 or salinidad<0:
                return self.json(400,{"error":"Revise los valores: no pueden ser negativos y el pH debe estar entre 0 y 14."})
            notas=clean_text(data,"notas",0,300) or None
            with db() as c:
                if not c.execute("SELECT 1 FROM piscinas WHERE id=? AND estado=1",(piscina,)).fetchone():
                    return self.json(400,{"error":"La piscina seleccionada no está activa."})
                if not c.execute("SELECT 1 FROM colaboradores WHERE id=? AND estado=1",(responsable,)).fetchone():
                    return self.json(400,{"error":"El responsable seleccionado no está activo."})
                c.execute("""INSERT INTO mediciones_calidad_agua(
                    piscina_id,resp_id,usuario_id,fecha,oxigeno,temp,ph,salinidad,notas
                    ) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (piscina,responsable,user["id"],fecha.strftime("%Y-%m-%d %H:%M:%S"),oxigeno,temp,ph,salinidad,notas))
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
        if resource=="calidad":
            if not self.require("calidad_agua.registrar"):return
            with db() as c:
                if not c.execute("SELECT 1 FROM mediciones_calidad_agua WHERE id=?",(record_id,)).fetchone():return self.json(404,{"error":"La medición no existe."})
                c.execute("DELETE FROM alertas WHERE clave='calidad_fuera_rango' AND referencia_id=?",(record_id,))
                c.execute("DELETE FROM mediciones_calidad_agua WHERE id=?",(record_id,))
            return self.json(200,{"ok":True})
        if resource=="aireacion":
            if not self.require("aireacion.operar"):return
            with db() as c:
                if not c.execute("SELECT 1 FROM aireadores WHERE id=?",(record_id,)).fetchone():return self.json(404,{"error":"El aireador no existe."})
                if c.execute("SELECT 1 FROM eventos_aireacion WHERE aireador_id=? LIMIT 1",(record_id,)).fetchone():
                    return self.json(409,{"error":"El aireador tiene historial y no puede eliminarse. Puede desactivarlo."})
                c.execute("DELETE FROM alertas WHERE clave='oxigeno_bajo' AND referencia_id=?",(record_id,))
                c.execute("DELETE FROM aireadores WHERE id=?",(record_id,))
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
        if resource=="calidad":
            if not self.require("calidad_agua.registrar"):return
            try:
                measurement_id=int(parts[2]); piscina=int(data.get("piscina_id")); responsable=int(data.get("resp_id"))
                oxigeno=float(data.get("oxigeno")); temp=float(data.get("temp")); ph=float(data.get("ph")); salinidad=float(data.get("salinidad"))
                fecha=datetime.fromisoformat(str(data.get("fecha","")).replace("T"," "))
            except (TypeError,ValueError):return self.json(400,{"error":"Complete todos los datos con valores válidos."})
            if oxigeno<0 or temp<0 or not 0<=ph<=14 or salinidad<0:return self.json(400,{"error":"Revise los valores registrados."})
            with db() as c:
                if not c.execute("SELECT 1 FROM mediciones_calidad_agua WHERE id=?",(measurement_id,)).fetchone():return self.json(404,{"error":"La medición no existe."})
                if not c.execute("SELECT 1 FROM piscinas WHERE id=? AND estado=1",(piscina,)).fetchone():return self.json(400,{"error":"La piscina no está activa."})
                if not c.execute("SELECT 1 FROM colaboradores WHERE id=? AND estado=1",(responsable,)).fetchone():return self.json(400,{"error":"El responsable no está activo."})
                c.execute("""UPDATE mediciones_calidad_agua SET piscina_id=?,resp_id=?,fecha=?,oxigeno=?,temp=?,ph=?,salinidad=?,notas=? WHERE id=?""",
                    (piscina,responsable,fecha.strftime("%Y-%m-%d %H:%M:%S"),oxigeno,temp,ph,salinidad,clean_text(data,"notas",0,300) or None,measurement_id))
            return self.json(200,{"ok":True})
        if resource=="rangos-calidad":
            if not self.require("calidad_agua.atender_alertas"):return
            try:range_id=int(parts[2]); minimum=float(data.get("minimo")); maximum=float(data.get("maximo"))
            except (TypeError,ValueError):return self.json(400,{"error":"Ingrese límites válidos."})
            if minimum<0 or maximum<=minimum:return self.json(400,{"error":"El máximo debe ser mayor que el mínimo."})
            with db() as c:
                if not c.execute("SELECT 1 FROM rangos_calidad_agua WHERE id=?",(range_id,)).fetchone():return self.json(404,{"error":"El rango no existe."})
                c.execute("UPDATE rangos_calidad_agua SET minimo=?,maximo=? WHERE id=?",(minimum,maximum,range_id))
            return self.json(200,{"ok":True})
        if resource=="aireacion":
            user=self.require("aireacion.operar")
            if not user:return
            try:air_id=int(parts[2])
            except ValueError:return self.json(400,{"error":"Aireador no válido."})
            with db() as c:
                item=c.execute("SELECT * FROM aireadores WHERE id=? FOR UPDATE",(air_id,)).fetchone()
                if not item:return self.json(404,{"error":"El aireador no existe."})
                if set(data)=={"activo"}:
                    active=bool(data["activo"])
                    c.execute("UPDATE aireadores SET activo=?,encendido=IF(?=0,0,encendido) WHERE id=?",(active,active,air_id))
                    detail="Aireador activado." if active else "Aireador desactivado y apagado."
                else:
                    codigo=clean_text(data,"codigo",2,30)
                    try:piscina=int(data.get("piscina_id")); enc=float(data.get("umbral_enc")); apa=float(data.get("umbral_apa"))
                    except (TypeError,ValueError):return self.json(400,{"error":"Complete la configuración del aireador."})
                    if not codigo or enc<0 or apa<=enc:return self.json(400,{"error":"El umbral de apagado debe superar al de encendido."})
                    if not c.execute("SELECT 1 FROM piscinas WHERE id=? AND estado=1",(piscina,)).fetchone():return self.json(400,{"error":"La piscina no está activa."})
                    if c.execute("SELECT 1 FROM aireadores WHERE codigo=? AND id<>?",(codigo.upper(),air_id)).fetchone():return self.json(409,{"error":"Ya existe otro aireador con ese código."})
                    c.execute("UPDATE aireadores SET piscina_id=?,codigo=?,umbral_enc=?,umbral_apa=? WHERE id=?",(piscina,codigo.upper(),enc,apa,air_id))
                    detail="Configuración del aireador actualizada."
                c.execute("INSERT INTO eventos_aireacion(aireador_id,usuario_id,accion,origen,oxigeno,detalle) VALUES(?,?,?,?,?,?)",(air_id,user["id"],"Modo","Manual",item["oxigeno"],detail))
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
    # En Railway se define PORT y HOST=0.0.0.0; en local se conserva 127.0.0.1:8000.
    host=os.getenv("HOST","127.0.0.1"); port=int(os.getenv("PORT","8000"))
    init_db()
    if WHATSAPP_ALERTS_ENABLED:
        threading.Thread(target=whatsapp_alert_worker,daemon=True,name="whatsapp-alerts").start()
    print(f"Sistema disponible en http://{host}:{port}"); ThreadingHTTPServer((host,port),App).serve_forever()
