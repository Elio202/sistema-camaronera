# Manual de usuario

## Sistema de gestión acuícola Pacific Gold

**Versión:** 4.0
**Fecha:** 7 de noviembre de 2026
**Aplicación web:** https://web-production-5dd5b.up.railway.app

## 1. Objetivo

Orientar al personal autorizado en el uso de los módulos operativos y administrativos. Las opciones visibles dependen del rol y de los permisos asignados.

## 2. Acceso al sistema

1. Abra la dirección web indicada arriba.
2. Escriba su nombre de usuario y contraseña.
3. Presione **Ingresar al sistema**.
4. Para terminar, presione **Salir**.

No comparta su contraseña. Si no puede ingresar, solicite al administrador que compruebe el usuario, rol y estado de la cuenta.

## 3. Panel principal

El panel presenta piscinas disponibles y sembradas, colaboradores activos, actividades pendientes o vencidas, productos con stock bajo, alertas, calidad del agua, aireadores y monitoreo ambiental. Cada tarjeta abre el módulo relacionado cuando el usuario posee permiso.

## 4. Piscinas y ciclos

### Gestión de ciclos

- Busque por código, finca o módulo y filtre por **Sembrado** o **Cosechado**.
- **Iniciar ciclo:** seleccione el número disponible y registre la siembra.
- **Cosechar:** finaliza correctamente el ciclo productivo.
- **Cancelar ciclo:** anula un inicio incorrecto y permite volver a utilizar el mismo número.
- **Historial:** muestra todos los ciclos registrados para la piscina.

### Catálogo de piscinas

Permite consultar código, finca, módulo, tipo, área entera y estado administrativo. Una piscina inactiva permanece en el historial, pero no recibe operaciones nuevas. Este estado es diferente del estado productivo sembrado o cosechado.

## 5. Personal y actividades

### Colaboradores

Permite crear, editar, activar y desactivar colaboradores. Solo los auxiliares y supervisores activos pueden recibir actividades.

### Asignar una actividad

1. Presione **Asignar actividad**.
2. Seleccione el colaborador.
3. Seleccione una piscina o **Trabajos varios (sin piscina)**.
4. Las piscinas aparecen agrupadas como **Piscinas sembradas** y **Piscinas disponibles**, con su estado junto al código.
5. Escriba la descripción.
6. Defina inicio y finalización durante el mismo día.
7. Presione **Asignar**.

El sistema evita horarios superpuestos para un colaborador. La actividad puede quedar Pendiente, En proceso, Realizada, Vencida o Cancelada.

## 6. Inventario de alimento

### Productos

Muestra código, nombre, marca, existencia, unidad, mínimo y estado. Los productos cuyo stock alcanza o baja del mínimo se resaltan visualmente.

### Movimientos

- **Entrada:** aumenta la existencia; puede incluir lote, vencimiento y observación.
- **Salida:** reduce la existencia y requiere piscina y responsable.
- El historial muestra lote y observación del movimiento.

No se permite una salida superior al stock disponible.

## 7. Calidad del agua

1. Presione **Nueva medición**.
2. Seleccione piscina y responsable.
3. Registre fecha, oxígeno disuelto, temperatura, pH y salinidad.
4. Agregue observaciones cuando corresponda.
5. Presione **Registrar**.

La lectura se compara con los rangos configurados. El sistema identifica valores normales o fuera de rango y genera seguimiento mediante alertas.

## 8. Aireación

### Administración

Cada aireador posee piscina, código, modo, umbral de encendido, umbral de apagado, lectura de oxígeno y estado. Puede editarse, desactivarse o eliminarse según los permisos.

### Operación manual y automática

- En modo **Manual** se habilitan **Encender** y **Apagar**.
- En modo **Automático**, una lectura menor al umbral de encendido activa el equipo.
- Una lectura igual o mayor al umbral de apagado lo desactiva.
- Entre ambos límites se conserva el estado anterior para evitar cambios continuos.

### Esquema de la piscina

Seleccione una piscina para mostrar su área y todos los aireadores asociados dentro de un esquema circular. Cada equipo indica código, oxígeno y estado. Arrástrelo para guardar su ubicación aproximada. El esquema presenta una piscina a la vez.

El prototipo demuestra lógica y trazabilidad. La actuación física requiere el controlador y los sensores definitivos de la empresa.

## 9. Alertas

El centro de alertas permite buscar y filtrar por módulo, estado y nivel. Una alerta pasa de Pendiente a Atendida. Cuando desaparece la condición que la originó, el sistema puede marcarla como Resuelta.

## 10. Monitoreo ambiental

Muestra temperatura, humedad, rango permitido, batería, conexión y hora del último dato. **Actualizar** solicita una lectura al proveedor externo.

Si el sensor está desconectado, el panel permanece visible y muestra **Sin conexión**. Cuando existe una lectura anterior en el navegador, se conserva como último dato conocido.

## 11. Reportes

### Dashboard interactivo

Permite filtrar por fechas, finca y módulo. Presenta indicadores y gráficas de piscinas, ciclos, actividades, inventario, alertas, calidad del agua y aireación.

### Reportes detallados

1. Seleccione el reporte.
2. Defina período y filtros cuando corresponda.
3. Presione **Consultar**.
4. Use **Exportar CSV** o **Imprimir / PDF**.

## 12. Usuarios, roles y permisos

El administrador puede crear usuarios, asignar roles, cambiar contraseñas, activar cuentas y configurar permisos. El mantenimiento de usuarios no sustituye al de roles: el usuario recibe un rol y el rol reúne los permisos. El Administrador conserva acceso completo.

## 13. Solución de problemas

- **Sesión vencida:** ingrese nuevamente.
- **No aparece una opción:** solicite revisar los permisos del rol.
- **No conecta con el servidor:** confirme internet y disponibilidad de Railway.
- **No se pudo completar la operación:** recargue y verifique los datos; si continúa, informe al administrador.
- **Sensor sin conexión:** la interfaz conserva el panel; compruebe el proveedor y el equipo físico.
- **Cambios visuales no aparecen:** actualice con `Ctrl + F5`.

## 14. Buenas prácticas

- Cierre la sesión al terminar.
- Verifique cantidades, piscinas, responsables y horarios antes de guardar.
- No comparta credenciales, tokens ni capturas con información sensible.
- Use Chrome o un navegador moderno para operar y presentar el sistema.
