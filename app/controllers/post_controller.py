"""Post de solicitudes HTTP."""

from app.core import *  # noqa: F401,F403


class PostController:
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
            try:
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
            except INTEGRITY_ERRORS:
                return self.json(409,{"error":"No fue posible guardar la actividad. Verifique el colaborador y el lugar seleccionados."})
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
