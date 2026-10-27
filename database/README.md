# Base de datos

La carpeta está dividida según la función de cada archivo:

- `schema/schema.sql`: estructura completa para instalaciones nuevas.
- `migrations/`: cambios incrementales aplicados durante el desarrollo.
- `tools/`: utilidad para aplicar el esquema de forma controlada.

Las cargas con información real se conservan únicamente como respaldo local y
no forman parte del repositorio. Antes de ejecutar una migración en producción
se debe crear un respaldo y comprobar su compatibilidad con MySQL 8.
