# Manual de usuario

## Sistema de gestión acuícola Pacific Gold

**Versión:** 3.0
**Fecha:** 4 de noviembre de 2026

## 1. Objetivo

Orientar al personal autorizado en el uso de los módulos operativos y administrativos del sistema. Las opciones visibles dependen del rol y de los permisos asignados.

## 2. Acceso al sistema

1. Abra la dirección proporcionada por el administrador.
2. Escriba su nombre de usuario y contraseña.
3. Presione **Ingresar al sistema**.
4. Para finalizar, presione **Salir** en la esquina superior derecha.

No comparta su contraseña. Si no puede ingresar, solicite al administrador que verifique el estado de su cuenta.

## 3. Panel principal

El panel muestra piscinas disponibles y sembradas, colaboradores activos, actividades pendientes o vencidas, productos con stock bajo, alertas pendientes y monitoreo ambiental. Cada indicador abre el módulo relacionado cuando el usuario posee permiso.

## 4. Piscinas y ciclos

### Gestión de ciclos

- Utilice la búsqueda y el filtro de estado.
- **Iniciar ciclo:** seleccione el siguiente número disponible.
- **Cosechar:** cierra correctamente el ciclo productivo.
- **Cancelar ciclo:** anula un inicio incorrecto y permite reutilizar ese mismo número.
- **Historial:** muestra todos los ciclos de la piscina.

### Catálogo de piscinas

Permite consultar código, finca, módulo, tipo, área y estado. Una piscina inactiva se conserva en el historial, pero no debe recibir operaciones nuevas.

## 5. Personal y actividades

### Colaboradores

Permite crear, editar, activar y desactivar colaboradores. Las actividades se asignan a auxiliares y supervisores activos.

### Actividades

1. Presione **Asignar actividad**.
2. Seleccione colaborador y piscina, o **Trabajos varios**.
3. Escriba la descripción.
4. Defina inicio y finalización durante el mismo día.
5. Presione **Asignar**.

El sistema evita horarios superpuestos para un mismo colaborador. Una actividad puede quedar Pendiente, Realizada o Vencida.

## 6. Inventario de alimento

### Productos

Permite consultar código, producto, marca, existencia, mínimo y estado. Los productos cuyo stock alcanza el mínimo se resaltan visualmente.

### Movimientos

- **Entrada:** aumenta la existencia y puede incluir lote y vencimiento.
- **Salida:** disminuye la existencia y exige piscina y responsable.

El sistema no permite una salida superior al stock disponible. La observación queda registrada en el historial.

## 7. Calidad del agua

1. Presione **Nueva medición**.
2. Seleccione piscina y responsable.
3. Registre fecha, oxígeno, temperatura, pH y salinidad.
4. Agregue observaciones cuando corresponda.
5. Presione **Registrar**.

La medición se compara con los rangos configurados y se identifica como Normal o Fuera de rango.

## 8. Aireación

### Crear un aireador

Seleccione piscina, escriba el código y configure los límites de encendido y apagado.

### Operación manual

Con el modo Manual puede utilizar los botones **Encender** y **Apagar**.

### Operación automática

Cambie el equipo a modo Automático y registre una lectura de oxígeno. Si está debajo del umbral de encendido, el sistema activa el aireador; al alcanzar el umbral de apagado, lo desactiva. Todas las acciones quedan en el historial.

El prototipo demuestra la lógica de control; el accionamiento físico requiere integrar el controlador definitivo.

## 9. Alertas

El centro de alertas permite buscar y filtrar por módulo, estado y nivel. Una alerta puede pasar de Pendiente a Atendida. Cuando desaparece la condición que la originó, el sistema la marca como Resuelta.

## 10. Monitoreo ambiental

Muestra temperatura, humedad, rango permitido, batería, conexión y hora del último dato recibido. **Actualizar** solicita una lectura nueva al servicio externo.

## 11. Reportes

### Dashboard gerencial

Permite filtrar por fechas, finca y módulo. Incluye indicadores y gráficas de ciclos, actividades, inventario, alertas, calidad del agua y aireación.

### Reportes detallados

1. Seleccione el tipo de reporte.
2. Defina el período cuando corresponda.
3. Presione **Consultar**.
4. Utilice **Exportar CSV** o **Imprimir / PDF**.

## 12. Usuarios, roles y permisos

El administrador puede crear usuarios, asignar roles, cambiar contraseñas, activar cuentas y configurar los permisos de cada rol. El rol Administrador conserva acceso completo.

## 13. Solución de problemas

- **Sesión vencida:** vuelva a iniciar sesión.
- **No aparece una opción:** solicite al administrador verificar su permiso.
- **No se conecta con el servidor:** confirme la conexión y que el servicio esté activo.
- **Respuesta inválida:** recargue la página; si continúa, informe al administrador.
- **El sensor no actualiza:** compruebe la conexión del proveedor externo.

## 14. Buenas prácticas

- Cierre la sesión al terminar.
- Registre datos reales y verifique las cantidades antes de confirmar.
- No elimine registros de pruebas sin autorización.
- No comparta credenciales ni capturas que contengan información sensible.
