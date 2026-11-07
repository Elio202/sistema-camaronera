# Guía para la presentación final

## Sistema de gestión acuícola Pacific Gold

**Versión:** 4.0
**Fecha:** 7 de noviembre de 2026
**Aplicación:** https://web-production-5dd5b.up.railway.app

## 1. Presentación breve del proyecto

> Pacific Gold es una aplicación web que centraliza el control operativo del cultivo de camarón. Integra piscinas y ciclos, personal y actividades, alimento, calidad del agua, aireación, alertas, monitoreo ambiental, seguridad y reportes.

El problema atendido es la dispersión de información. El sistema relaciona los registros con piscinas, ciclos y responsables para facilitar seguimiento, trazabilidad y toma de decisiones.

## 2. Arquitectura que debes explicar

- **Tipo:** aplicación web Full-Stack.
- **Patrón:** cliente-servidor.
- **Frontend:** HTML, CSS y JavaScript.
- **Backend:** Python con API HTTP y respuestas JSON.
- **Organización:** rutas, controladores, servicios, repositorios y base de datos bajo `app/`.
- **Datos:** MariaDB local y MySQL 8 en Railway.
- **Seguridad:** PBKDF2, sesiones con cookies, roles y permisos.
- **Despliegue:** GitHub y Railway.

No confundas arquitectura con metodología. Cliente-servidor indica cómo está construido el software; Cascada o Scrum describen cómo se organiza el desarrollo.

## 3. Estructura que puedes mostrar en VS Code

```text
app/
  routes/          Catálogo y ensamblaje de rutas
  controllers/     GET, POST, PATCH, DELETE y seguridad base
  services/        Alertas e integración del sensor
  repositories/    Acceso reutilizable a datos
  database/        Conexión e inicialización
public/            Interfaz HTML, CSS y JavaScript
database/          Esquema y migraciones
tests/             Pruebas automatizadas
server.py          Punto de entrada
```

Explica que es un monolito modular: se publica como un servicio, pero sus responsabilidades están separadas en el código.

## 4. Orden recomendado de la demostración

### 1. Inicio de sesión

- Ingresa con un usuario administrador.
- Señala nombre y rol.
- Explica que las contraseñas no se guardan como texto visible.

### 2. Panel principal

- Piscinas disponibles y sembradas.
- Colaboradores activos y actividades.
- Stock bajo, alertas, calidad, aireadores y sensor ambiental.

### 3. Piscinas y ciclos

- Muestra finca, módulo, tipo, área y estado administrativo.
- Filtra ciclos por Sembrado o Cosechado.
- Explica el código productivo: piscina más número de ciclo.
- Enseña iniciar, cosechar y cancelar. Un ciclo cancelado puede iniciarse otra vez con el mismo número.

### 4. Personal y actividades

- Muestra los 45 colaboradores cargados.
- Explica que solo auxiliares y supervisores reciben actividades.
- Abre **Asignar actividad** y señala las piscinas sembradas y disponibles.
- Muestra **Trabajos varios (sin piscina)** y el horario de inicio y finalización.
- Explica que no se permiten horarios superpuestos.

### 5. Inventario

- Muestra los 12 productos activos.
- Señala el resaltado de stock bajo.
- Registra o explica entradas y salidas, lote, vencimiento y observación.
- Indica que una salida requiere piscina y responsable y no puede superar el stock.

### 6. Calidad del agua

- Registra o muestra oxígeno, temperatura, pH y salinidad.
- Compara la lectura con los rangos configurados.
- Explica la generación de alertas fuera de rango.

### 7. Aireación

- Explica modos Manual y Automático.
- Con oxígeno menor al umbral de encendido, el aireador se activa.
- Con oxígeno igual o mayor al umbral de apagado, se desactiva.
- Muestra el historial y el esquema circular de la piscina.
- Arrastra un aireador para explicar el almacenamiento de su ubicación.

Aclara que el prototipo valida la lógica; el accionamiento físico requiere hardware definitivo.

### 8. Monitoreo y alertas

- Muestra temperatura, humedad, batería, conexión y última lectura.
- Si el proveedor está desconectado, explica que el panel permanece visible y conserva el último dato conocido.
- Muestra los filtros y estados Pendiente, Atendida y Resuelta del centro de alertas.

### 9. Reportes

- Abre el dashboard interactivo.
- Filtra por fechas, finca y módulo.
- Muestra gráficas de operación, calidad y aireación.
- Enseña CSV e impresión/PDF.

### 10. Usuarios, roles y permisos

- Explica que el usuario recibe un rol y el rol contiene permisos.
- Muestra que la interfaz oculta opciones no autorizadas.
- Aclara que la API vuelve a validar cada permiso; la seguridad no depende solo del menú.

### 11. Código y despliegue

- Muestra `server.py`, `app/`, `database/`, `public/` y `tests/`.
- Explica que GitHub versiona el código.
- Señala que Railway aloja el servicio web y MySQL en red privada.
- Menciona que existen 17 pruebas automatizadas aprobadas.

## 5. Preguntas probables y respuestas

### ¿Por qué es una aplicación web?

Permite ingresar desde un navegador, centraliza datos y actualizaciones y evita instalar el programa en cada equipo.

### ¿Qué arquitectura utiliza?

Cliente-servidor, implementada como monolito modular. El navegador consume una API y el servidor aplica reglas y accede a MySQL.

### ¿Dónde están las rutas y controladores?

Las rutas se catalogan y ensamblan en `app/routes/`. Las solicitudes se atienden en `app/controllers/`, separadas en GET, POST, PATCH y DELETE.

### ¿Cómo protege las contraseñas?

Utiliza PBKDF2-SHA256 con sal aleatoria y 310,000 iteraciones. No almacena ni recupera la contraseña original.

### ¿Cómo controla el acceso?

Cada usuario tiene un rol; cada rol posee permisos por módulo y función. El backend valida esos permisos en cada endpoint.

### ¿Cómo evita inyección SQL?

Utiliza consultas parametrizadas y valida tipos, cantidades, fechas y relaciones antes de guardar.

### ¿Dónde está la base de datos?

En desarrollo se usa MariaDB local. La aplicación publicada usa MySQL 8 en Railway, conectada internamente al servicio web.

### ¿Qué sucede si falla el sensor?

La aplicación informa la desconexión sin ocultar el dashboard. El navegador puede conservar la última lectura conocida.

### ¿El sistema controla equipos físicos?

Demuestra la lógica de control e historial de aireadores. La actuación física final depende de sensores, controlador y protocolo de la empresa.

### ¿Cómo evita perder información?

Usa claves foráneas, restricciones, transacciones y respaldos previos a migraciones. Git conserva el historial del código.

### ¿Qué sucede si no hay Internet?

La versión Railway requiere conexión. Existe una instalación local para desarrollo y contingencia; una implementación empresarial también podría alojarse en la red interna.

### ¿Qué pruebas se realizaron?

Hay 17 pruebas automatizadas de autenticación, seguridad, permisos y sensor, además de pruebas manuales y comprobaciones HTTP locales y productivas.

## 6. Datos que debes recordar

- 2 fincas.
- 16 módulos productivos.
- 104 piscinas.
- 105 ciclos registrados.
- 45 colaboradores.
- 12 productos de alimento activos.
- 17 pruebas automatizadas aprobadas.
- Backend Python; frontend HTML, CSS y JavaScript.
- MariaDB local; MySQL 8 y aplicación en Railway.

## 7. Lista antes de presentar

- Confirmar que abre la URL de Railway.
- Probar el usuario de demostración sin proyectar la contraseña.
- Confirmar que el sensor y los gráficos tengan un estado comprensible, incluso desconectados.
- Tener algunos datos preparados para no crear registros improvisados.
- Cerrar correo, mensajería, `.env`, tokens y ventanas privadas.
- Usar Chrome y ajustar el zoom para el proyector.
- Mantener el servidor local funcional como respaldo.
- Llevar el ZIP, documento, SQL, manuales y código en USB.
- No modificar permisos, ciclos o stock real durante la exposición salvo que sea parte de la demostración.

## 8. Cierre sugerido

> El sistema demuestra que los procesos principales de Pacific Gold pueden centralizarse en una plataforma web segura, con trazabilidad, alertas y reportes. La siguiente etapa consiste en validar el prototipo mediante una prueba piloto e integrar gradualmente los equipos físicos definitivos.
