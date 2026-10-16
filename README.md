# Sistema acuícola Oro del Pacífico — fase 1

Prototipo funcional del **login y módulo de usuarios**, basado en los diagramas del Capítulo II: Usuario → Rol → Permisos → Sesión.

## Ejecutar

Requiere Python 3.10 o superior, sin instalar paquetes adicionales.

```powershell
cd sistema-camaronera
python server.py
```

Abrir `http://localhost:8000`.

Credenciales iniciales (solo desarrollo):

- Usuario: `admin`
- Contraseña: `Admin123!`

## Incluido

- Validación de usuario/correo y contraseña.
- Contraseñas protegidas con PBKDF2-SHA256 y sal individual.
- Sesión de 8 horas en cookie `HttpOnly` y `SameSite=Strict`.
- Consulta del rol y permisos antes de habilitar cada función.
- Crear, editar, activar y desactivar usuarios.
- Roles iniciales: Administrador y Supervisor.
- Diseño adaptable para computadora y teléfono.
- Base SQL local SQLite en `data/sistema.db`, creada al iniciar para demostración.
- Esquema MariaDB listo para importar desde HeidiSQL en `database/mariadb_schema.sql`.
- Cinco roles: Administrador, Jefe de producción, Encargado de piscina, Técnico de calidad y Gerencia.
- Soporte de acceso configurado como `emarroquin@esteromar.gt`.

## Datos necesarios para producción

1. Logo y colores oficiales de Oro del Pacífico, S. A.
2. Nombres definitivos de roles y matriz de permisos.
3. Campos obligatorios del usuario (por ejemplo: teléfono, puesto o colaborador asociado).
4. Datos de conexión del servidor MariaDB.
5. Servidor SMTP y contraseña de aplicación de `emarroquin@esteromar.gt`.
6. Dominio/servidor y certificado HTTPS.

Nunca se debe publicar con la contraseña inicial. En producción, configurar HTTPS, límite de intentos, recuperación de contraseña y secretos mediante variables de entorno.
