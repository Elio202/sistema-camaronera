"""Delete de solicitudes HTTP."""

from app.core import *  # noqa: F401,F403


class DeleteController:
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
