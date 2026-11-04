# Guía para la presentación final

## 1. Presentación breve del proyecto

> Pacific Gold es una aplicación web para centralizar el control operativo del cultivo de camarón. Integra piscinas y ciclos, personal y actividades, inventario de alimento, calidad del agua, aireación, alertas, monitoreo ambiental, usuarios, permisos y reportes gerenciales.

El problema que resuelve es la dispersión de información operativa. Los registros quedan centralizados, relacionados con piscinas y responsables, y disponibles para seguimiento y toma de decisiones.

## 2. Arquitectura que debes explicar

- **Tipo de aplicación:** aplicación web Full-Stack.
- **Arquitectura:** cliente-servidor organizada por módulos.
- **Frontend:** HTML, CSS y JavaScript.
- **Backend:** Python con una API HTTP tipo REST.
- **Base de datos:** MariaDB en desarrollo y MySQL en Railway.
- **Seguridad:** contraseñas cifradas, sesiones mediante cookies, roles y permisos.
- **Despliegue:** GitHub para el código y Railway para aplicación y base de datos.

No confundas arquitectura con metodología. Cascada o Scrum describen cómo se organiza el desarrollo; cliente-servidor describe cómo está construido el software.

## 3. Orden recomendado de la demostración

### 1. Inicio de sesión

- Explica que las contraseñas no se almacenan como texto visible.
- Ingresa con un usuario autorizado.
- Señala el nombre y rol mostrado en la parte superior.

### 2. Panel principal

- Piscinas disponibles y piscinas sembradas.
- Colaboradores activos.
- Actividades pendientes y vencidas.
- Productos con stock bajo.
- Alertas y lectura del sensor ambiental.

### 3. Piscinas y ciclos

- Muestra el catálogo de piscinas.
- Explica finca, módulo, tipo y área.
- Enseña el código productivo: piscina más número de ciclo.
- Muestra cómo iniciar, cosechar, cancelar y reutilizar correctamente un ciclo cancelado.

### 4. Personal y actividades

- Muestra los colaboradores cargados.
- Asigna una actividad con inicio y finalización.
- Explica que puede relacionarse con una piscina o registrarse como trabajo variado.
- Muestra los estados Pendiente, Realizada y Vencida.

### 5. Inventario

- Explica productos, existencia y mínimo.
- Registra una entrada o salida de demostración.
- Muestra lote, vencimiento, responsable, piscina y observación.
- Explica que el sistema impide una salida mayor a la existencia.

### 6. Calidad del agua

- Registra oxígeno, temperatura, pH y salinidad.
- Muestra los rangos configurados.
- Explica cómo el sistema identifica automáticamente valores fuera de rango.

### 7. Aireación

- Crea o selecciona un aireador.
- Explica el modo Manual y el modo Automático.
- En modo automático registra oxígeno menor de 4.00 mg/L: debe encenderse.
- Registra oxígeno igual o mayor de 5.50 mg/L: debe apagarse.
- Enseña el historial de acciones.

Aclara que el prototipo valida la lógica de control. La conexión física con aireadores requiere el controlador y sensores definitivos de la empresa.

### 8. Alertas

- Muestra alertas por stock bajo o actividades vencidas.
- Explica los estados Pendiente, Atendida y Resuelta automáticamente.

### 9. Reportes

- Abre el dashboard interactivo.
- Aplica filtros por fecha, finca o módulo.
- Muestra gráficas de ciclos, actividades, inventario, calidad y aireación.
- Enseña un reporte detallado y la exportación CSV o impresión en PDF.

### 10. Usuarios, roles y permisos

- Muestra que cada rol tiene funciones autorizadas.
- Explica que ocultar una opción no es la única seguridad: la API también valida el permiso.

## 4. Preguntas probables y respuestas

### ¿Por qué es una aplicación web?

Porque permite acceder desde un navegador sin instalar el sistema en cada computadora, centraliza las actualizaciones y facilita su uso desde diferentes ubicaciones.

### ¿Qué patrón de arquitectura utiliza?

Cliente-servidor. El navegador presenta la interfaz y consume una API; el servidor aplica las reglas de negocio y accede a la base de datos.

### ¿Cómo protege las contraseñas?

Se almacenan mediante PBKDF2 con sal y múltiples iteraciones. El sistema compara el resultado cifrado y nunca necesita recuperar la contraseña original.

### ¿Cómo se controlan los accesos?

Cada usuario posee un rol y cada rol tiene permisos por módulo y acción. El servidor verifica esos permisos antes de ejecutar las operaciones.

### ¿Qué sucede si no hay Internet?

La versión publicada requiere conexión al servidor. La arquitectura también permite una instalación dentro de la red local de la empresa si se necesita operación interna.

### ¿El sistema ya controla equipos físicos?

El módulo de aireación implementa y demuestra la lógica de control mediante umbrales e historial. La integración física final depende de los sensores, controlador y protocolo definidos por la empresa.

### ¿Dónde se encuentra la base de datos?

Durante el desarrollo se utiliza MariaDB local. La aplicación publicada utiliza una base MySQL alojada en Railway.

### ¿Cómo se evita perder información?

La base utiliza relaciones, restricciones y transacciones. Para producción también se requieren respaldos periódicos y pruebas de restauración.

## 5. Lista de preparación antes de presentar

- Confirmar que la aplicación de Railway abre.
- Confirmar que la base de Railway contiene las migraciones finales.
- Preparar un usuario administrador y otro usuario con permisos limitados.
- Tener datos suficientes para que las gráficas no aparezcan vacías.
- Cerrar pestañas y programas que no se usarán.
- Aumentar el zoom del navegador si el proyector lo requiere.
- Tener una copia local funcional por si falla Internet.
- Tener el código, SQL y documentación en una memoria USB.
- No mostrar archivos `.env`, claves, tokens ni contraseñas.

## 6. Cierre sugerido

> El prototipo demuestra que los procesos principales pueden centralizarse en una sola plataforma, con trazabilidad, permisos y reportes. La siguiente etapa consiste en validar los rangos operativos con Pacific Gold, conectar los equipos físicos definitivos y ejecutar una prueba piloto en producción.
