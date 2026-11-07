"""Get de solicitudes HTTP."""

from app.core import *  # noqa: F401,F403


class GetController:
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
            user=self.require()
            if not user:return
            if not module_tables_ready(): return self.json(503,{"error":"Ejecute la migración de módulos en MariaDB."})
            with db() as c:
                refresh_activity_statuses(c)
                alerts_ready=alerts_table_ready(c)
                if alerts_ready: sync_alerts(c)
                all_data={
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
                permissions=set(user["permisos"])
                data={}
                if "piscinas.ver" in permissions:
                    data.update({key:all_data[key] for key in ("piscinas_disponibles","piscinas_activas")})
                if "personal.ver" in permissions:
                    data.update({key:all_data[key] for key in ("colaboradores","pendientes","vencidas")})
                if "inventario.ver" in permissions:data["productos_bajos"]=all_data["productos_bajos"]
                if "alertas.ver" in permissions:data["alertas_pendientes"]=all_data["alertas_pendientes"]
                if "calidad_agua.ver" in permissions:data["calidad_fuera"]=all_data["calidad_fuera"]
                if "aireacion.ver" in permissions:
                    data.update({key:all_data[key] for key in ("aireadores_encendidos","aireacion_baja")})
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
                        a.umbral_enc,a.umbral_apa,a.pos_x,a.pos_y,a.actualizado,COALESCE(v.codigo_productivo,p.codigo) piscina
                        FROM aireadores a JOIN piscinas p ON p.id=a.piscina_id
                        LEFT JOIN vista_piscinas_ciclo_actual v ON v.piscina_id=p.id
                        ORDER BY a.activo DESC,a.codigo""").fetchall()]
                    events=[dict(row) for row in c.execute("""SELECT e.id,e.accion,e.origen,e.oxigeno,e.detalle,e.creado,
                        a.codigo aireador,COALESCE(v.codigo_productivo,p.codigo) piscina,u.nombre usuario
                        FROM eventos_aireacion e JOIN aireadores a ON a.id=e.aireador_id
                        JOIN piscinas p ON p.id=a.piscina_id LEFT JOIN vista_piscinas_ciclo_actual v ON v.piscina_id=p.id
                        JOIN usuarios u ON u.id=e.usuario_id ORDER BY e.id DESC LIMIT 200""").fetchall()]
                    pools=[dict(row) for row in c.execute("""SELECT p.id,COALESCE(v.codigo_productivo,p.codigo) codigo,p.area_m2
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
        if path=="/api/personal-opciones":
            if not self.require("personal.asignar"):return
            with db() as c:
                rows=c.execute("""SELECT piscina_id id,codigo_productivo codigo,estado_ciclo
                    FROM vista_piscinas_ciclo_actual
                    WHERE piscina_activa=1 ORDER BY codigo_productivo""").fetchall()
                return self.json(200,{"piscinas":[dict(row) for row in rows]})
        if path=="/api/inventario-opciones":
            if not self.require("inventario.registrar"):return
            with db() as c:
                pools=c.execute("""SELECT piscina_id id,codigo_productivo codigo,estado_ciclo
                    FROM vista_piscinas_ciclo_actual
                    WHERE piscina_activa=1 ORDER BY codigo_productivo""").fetchall()
                staff=c.execute("SELECT id,nombre FROM colaboradores WHERE estado=1 ORDER BY nombre").fetchall()
                return self.json(200,{"piscinas":[dict(row) for row in pools],"colaboradores":[dict(row) for row in staff]})
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
