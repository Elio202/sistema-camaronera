# Manual técnico

## Sistema de gestión acuícola Pacific Gold

**Versión:** 3.0
**Fecha:** 4 de noviembre de 2026

## 1. Arquitectura

Aplicación web Full-Stack con patrón cliente-servidor:

- Frontend en HTML, CSS y JavaScript bajo `public/`.
- Backend y API HTTP en Python mediante `server.py`.
- MariaDB para desarrollo local y MySQL en producción.
- Código fuente versionado con Git y GitHub.
- Aplicación y base productiva alojadas en Railway.

## 2. Organización del proyecto

```text
database/
  schema/          Esquema completo de instalación
  migrations/      Cambios incrementales de la base
  tools/           Utilidad para aplicar el esquema
docs/              Manuales y documentación
public/
  assets/css/      Estilos
  assets/images/   Imágenes utilizadas por la interfaz
  assets/js/       Lógica de cada pantalla
  *.html           Vistas del sistema
tests/             Pruebas automatizadas
tools/database/    Verificaciones administrativas
server.py          Servidor web, API y reglas de negocio
requirements.txt   Dependencias de Python
railway.json       Configuración de despliegue
```

## 3. Requisitos

- Python 3.12 o compatible.
- MariaDB 10.6 o MySQL 8.
- Navegador web moderno.
- Paquetes de `requirements.txt`.

## 4. Configuración local

1. Copiar `.env.example` como `.env`.
2. Configurar `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASSWORD`.
3. Mantener `COOKIE_SECURE=false` únicamente en desarrollo local.
4. Instalar dependencias:

```powershell
python -m pip install -r requirements.txt
```

5. Preparar la base con `database/schema/schema.sql` o aplicar las migraciones en orden.
6. Iniciar:

```powershell
python server.py
```

7. Abrir `http://127.0.0.1:8000`.

## 5. Base de datos

Las entidades principales son usuarios, roles, permisos, sesiones, fincas, módulos, piscinas, ciclos, colaboradores, actividades, productos, movimientos, alertas, mediciones de calidad, aireadores y eventos de aireación.

Las migraciones deben ejecutarse en orden. La migración más reciente es `15_crear_aireacion.sql`. El usuario utilizado por la aplicación debe tener permisos de lectura y escritura, pero no necesita permisos para crear o eliminar tablas.

## 6. Seguridad

- Contraseñas protegidas con PBKDF2-SHA256, sal aleatoria y múltiples iteraciones.
- Sesiones identificadas por tokens aleatorios; en la base solo se guarda su hash.
- Cookies `HttpOnly`, `SameSite=Strict` y `Secure` en producción.
- Validación de rol y permiso en cada endpoint protegido.
- Consultas parametrizadas para evitar inyección SQL.
- Validaciones de formato, fechas, cantidades y reglas de negocio.
- Secretos almacenados en variables de entorno, nunca en Git.

## 7. API

La API utiliza rutas bajo `/api/`. Los grupos principales son:

- `/api/login`, `/api/logout`, `/api/me`.
- `/api/usuarios`, `/api/roles-config`.
- `/api/piscinas`, `/api/ciclos`, `/api/modulos`.
- `/api/colaboradores`, `/api/actividades`.
- `/api/productos`, `/api/movimientos`.
- `/api/calidad`.
- `/api/aireacion` y sus acciones.
- `/api/alertas`.
- `/api/reportes`, `/api/reportes-dashboard`.
- `/api/monitoreo`.

Las respuestas se entregan como JSON y utilizan códigos HTTP para indicar éxito, validación, falta de autorización o fallas externas.

## 8. Despliegue en Railway

1. Confirmar los cambios en Git y subir la rama principal a GitHub.
2. Aplicar primero las migraciones faltantes en la base productiva.
3. Configurar las variables de base de datos y `COOKIE_SECURE=true`.
4. Desplegar el servicio web.
5. Revisar registros y probar login, dashboard y módulos críticos.

No se debe publicar `.env`, tokens, claves del sensor ni contraseñas.

## 9. Pruebas

Ejecutar:

```powershell
python -m py_compile server.py
python -m unittest discover -s tests -v
```

También se debe realizar una prueba manual de cada módulo con un usuario administrador y otro con permisos limitados.

## 10. Respaldo y restauración

- Generar periódicamente un respaldo SQL de estructura y datos.
- Guardarlo cifrado y fuera del servidor principal.
- Verificar la restauración en una base de prueba.
- Antes de cada migración productiva, realizar un respaldo.

## 11. Mantenimiento

- Revisar alertas y registros del servidor.
- Desactivar cuentas que ya no deban ingresar.
- Actualizar dependencias después de probarlas localmente.
- Mantener sincronizados GitHub, Railway y el esquema SQL.
- Documentar toda migración nueva.

## 12. Limitaciones conocidas

- El control de aireación demuestra la lógica y trazabilidad; la actuación física requiere integrar hardware.
- El monitoreo ambiental depende de un servicio externo.
- La recuperación automática de contraseña no forma parte de la versión final.
- La disponibilidad depende del servidor y la conexión de red.
