"""Patch de solicitudes HTTP."""

from app.core import *  # noqa: F401,F403


class PatchController:
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
                elif set(data)=={"pos_x","pos_y"}:
                    try:x=float(data["pos_x"]);y=float(data["pos_y"])
                    except (TypeError,ValueError):return self.json(400,{"error":"La ubicación del aireador no es válida."})
                    if not 4<=x<=96 or not 4<=y<=96 or ((x-50)**2+(y-50)**2)**0.5>44:
                        return self.json(400,{"error":"El aireador debe quedar dentro del área de la piscina."})
                    c.execute("UPDATE aireadores SET pos_x=?,pos_y=? WHERE id=?",(round(x,2),round(y,2),air_id))
                    return self.json(200,{"ok":True})
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
