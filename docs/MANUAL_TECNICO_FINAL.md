# Manual técnico

## Sistema de gestión acuícola Pacific Gold

**Versión:** 4.0
**Fecha:** 7 de noviembre de 2026
**Producción:** https://web-production-5dd5b.up.railway.app

## 1. Arquitectura

Aplicación web Full-Stack con patrón cliente-servidor:

- Frontend en HTML, CSS y JavaScript bajo `public/`.
- Backend y API HTTP en Python bajo `app/`.
- `server.py` como punto de entrada compatible con desarrollo y Railway.
- MariaDB para desarrollo local y MySQL 8 en producción.
- Comunicación cliente-servidor mediante endpoints JSON bajo `/api/`.
- GitHub para control de versiones y Railway para aplicación y base productiva.

Es una arquitectura monolítica modular: se despliega como un servicio, pero el código está separado por rutas, controladores, servicios, repositorios y acceso a datos.

## 2. Organización del proyecto

```text
app/
  application.py       Composición y arranque del backend
  core.py              Configuración y funciones compartidas
  routes/
    api_routes.py      Catálogo de recursos de la API
    http_routes.py     Ensamblaje del manejador HTTP
  controllers/
    base_controller.py Sesión, permisos y respuesta JSON
    get_controller.py  Consultas
    post_controller.py Creación y acciones
    patch_controller.py Actualizaciones
    delete_controller.py Eliminaciones
  services/
    alerts_service.py  Reglas de alertas
    sensor_service.py  Integración del sensor ambiental
  repositories/
    base_repository.py Consultas reutilizables
  database/
    connection.py      Conexión e inicialización
database/
  schema/              Esquema completo
  migrations/          Cambios incrementales
docs/                  Manuales y documentación
public/                HTML, CSS, JavaScript e imágenes
tests/                 Pruebas automatizadas
tools/                 Utilidades administrativas
server.py              Punto de entrada
requirements.txt       Dependencias
railway.json           Configuración de despliegue vigente
```

## 3. Requisitos

- Python 3.12 o compatible.
- MariaDB 10.6 o MySQL 8.
- Navegador moderno.
- Dependencias de `requirements.txt`: PyMySQL y cryptography.

## 4. Configuración local

1. Copiar `.env.example` como `.env`.
2. Configurar `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASSWORD`.
3. Mantener `COOKIE_SECURE=false` solo en desarrollo.
4. Instalar dependencias:

```powershell
python -m pip install -r requirements.txt
```

5. Preparar la base con `database/schema/schema.sql` y las migraciones requeridas.
6. Iniciar con `python server.py`.
7. Abrir `http://127.0.0.1:8000/login.html`.

## 5. Base de datos

Entidades principales: roles, permisos, usuarios, sesiones, fincas, módulos, piscinas, ciclos, colaboradores, actividades, productos, movimientos, alertas, rangos y mediciones de calidad, aireadores y eventos de aireación.

La migración más reciente es `16_ubicacion_aireadores.sql`. Para permitir trabajos varios, `12_actividades_sin_piscina.sql` debe dejar `actividades.piscina_id` como `NULL`.

El usuario de la aplicación necesita lectura y escritura. Las migraciones deben ejecutarse con un usuario administrativo después de generar respaldo.

## 6. Seguridad

- Contraseñas con PBKDF2-SHA256, sal aleatoria y 310,000 iteraciones.
- Tokens de sesión aleatorios; solo su hash se guarda en la base.
- Cookies `HttpOnly`, `SameSite=Strict` y `Secure` en producción.
- Validación de permisos por endpoint.
- Consultas parametrizadas contra inyección SQL.
- Validación de fechas, cantidades, roles y reglas de negocio.
- Secretos únicamente en variables de entorno; `.env` y respaldos están excluidos de Git.
- MySQL productivo utiliza red privada y credenciales referenciadas por Railway.

## 7. API y controladores

Las rutas se agrupan en `app/routes/api_routes.py`. `http_routes.py` compone el manejador con:

- `GetController`: consultas y reportes.
- `PostController`: login, altas y operaciones.
- `PatchController`: ediciones y cambios de estado.
- `DeleteController`: eliminaciones autorizadas.
- `BaseController`: JSON, sesiones y permisos.

Recursos principales:

- `/api/login`, `/api/logout`, `/api/me`.
- `/api/usuarios` y configuración de roles.
- `/api/piscinas`, ciclos e historial.
- `/api/colaboradores`, `/api/actividades` y opciones auxiliares.
- `/api/productos`, `/api/movimientos` e inventario.
- `/api/calidad`, `/api/aireacion`, `/api/alertas`.
- `/api/reportes`, dashboard y `/api/monitoreo`.

Las respuestas son JSON y utilizan códigos HTTP 200/201, 400, 401, 403, 404, 409 y 5xx según el resultado.

## 8. Servicios externos

El sensor se configura mediante `SENSOR_API_URL` y `SENSOR_EXPORT_KEY`. El backend consulta al proveedor y nunca expone la clave al navegador. Ante indisponibilidad devuelve un error controlado; el frontend conserva el panel y el último valor local.

La integración WhatsApp/Evolution permanece deshabilitada en producción mediante `WHATSAPP_ALERTS_ENABLED=false` y no forma parte del alcance final.

## 9. Despliegue en Railway

1. Confirmar cambios y subir `main` a GitHub.
2. Aplicar migraciones productivas con respaldo previo.
3. Configurar referencias de conexión desde MySQL.
4. Configurar `HOST=0.0.0.0`, `COOKIE_SECURE=true` y secretos del sensor.
5. Desplegar `web`, revisar registros y probar módulos críticos.

Proyecto actual: `sistema-camaronera-elio`. La configuración `railway.json` debe migrarse al formato Infrastructure as Code antes del 1 de diciembre de 2026.

## 10. Pruebas

```powershell
python -m compileall -q app server.py
python -m unittest discover -s tests -v
```

La versión 4.0 tiene 17 pruebas automatizadas aprobadas. También deben probarse manualmente login, permisos, ciclos, actividades, inventario, alertas, calidad, aireación, monitoreo y reportes.

## 11. Respaldo y restauración

- Crear un respaldo SQL antes de migraciones o importaciones.
- Guardarlo cifrado fuera del repositorio.
- Excluir sesiones antiguas al trasladar una base cuando no sean necesarias.
- Probar periódicamente la restauración en un entorno separado.

## 12. Mantenimiento

- Revisar alertas y registros de Railway.
- Desactivar cuentas sin autorización vigente.
- Mantener sincronizados GitHub, Railway y el esquema SQL.
- Actualizar dependencias solo después de pruebas locales.
- Documentar toda migración y conservar el historial de Git.

## 13. Limitaciones conocidas

- La aireación demuestra lógica y trazabilidad; el accionamiento físico requiere hardware definitivo.
- El monitoreo ambiental depende de un proveedor externo.
- La recuperación automática de contraseña no forma parte de la entrega final.
- La disponibilidad depende de Railway, MySQL, internet y servicios externos.
