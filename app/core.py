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

ROOT = Path(__file__).resolve().parents[1]
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
