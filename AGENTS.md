# Guía de continuidad para agentes de IA

## Propósito del proyecto

Este repositorio contiene el sistema web de gestión acuícola de Pacific Gold. Es un
proyecto de graduación y debe mantenerse comprensible, demostrable y documentado.
La primera fase cubrió autenticación, autorización por roles/permisos y usuarios.
La fase actual amplía el sistema con piscinas/ciclos, personal/actividades,
inventario y panel principal.

El usuario desea trabajar paso a paso: primero diseñar y crear tablas, después
validarlas, luego cargar datos y finalmente conectar/probar la interfaz. No cargar
datos ni aplicar migraciones destructivas sin explicar antes el paso.

## Ubicación y ejecución

- Raíz: `sistema-camaronera/`
- Backend: `server.py`
- Frontend estático: `public/`
- SQL y migraciones: `database/`
- Documentación: `docs/`
- Pruebas: `tests/`
- URL local: `http://localhost:8000`

Documento formal de opciones y requerimientos:
`docs/CATALOGO_OPCIONES_Y_REQUERIMIENTOS.md`.

Preparación y ejecución:

```powershell
cd C:\Users\ELIO_MARROQUIN\Desktop\formulario-agenda\sistema-camaronera
python -m pip install -r requirements.txt
python server.py
```

No abrir `login.html` directamente como archivo: debe servirse por HTTP para que
las rutas `/api/*` y las cookies de sesión funcionen.

## Tecnologías y restricciones vigentes

- Python 3 y servidor HTTP de la biblioteca estándar.
- PyMySQL para MariaDB (`requirements.txt`).
- HTML, CSS y JavaScript sin framework en `public/`.
- MariaDB 12.3 local, administrada con HeidiSQL.
- Base de datos: `pacific_gold`.
- La aplicación usa las variables de `.env`.
- `.env` contiene secretos locales: nunca mostrar, copiar a documentación ni
  confirmar contraseñas en respuestas.
- Las migraciones estructurales se ejecutan con `root@localhost`.
- El usuario de la aplicación es limitado y debe conservarse sin privilegios DDL;
  se usa para SELECT, INSERT, UPDATE y DELETE, no para CREATE/ALTER/DROP.
- No colocar las credenciales de `root` en `.env`.

## Arquitectura del backend

`server.py` sirve los archivos de `public/` y expone una API JSON. Usa MariaDB
cuando `DB_PASSWORD` está configurado; de lo contrario mantiene un fallback
SQLite para demostración. La aplicación real está trabajando con MariaDB.

Funciones de seguridad ya implementadas:

- Hash de contraseñas PBKDF2-SHA256 con sal individual.
- Sesiones mediante token aleatorio; solo se guarda el hash del token.
- Cookie `HttpOnly`, `SameSite=Strict` y duración de ocho horas.
- Cuenta y rol activos requeridos para iniciar sesión.
- Consulta de permisos asociados al rol.
- Login solamente con nombre de usuario, por decisión del usuario.
- Mensaje genérico para credenciales incorrectas.

Rutas principales existentes:

- `GET /api/me`
- `GET /api/roles`
- `GET/POST/PATCH /api/usuarios`
- `GET /api/resumen`
- `GET/POST/PATCH /api/piscinas`
- `GET /api/modulos`
- `GET/POST/PATCH /api/colaboradores`
- `GET/POST/PATCH /api/actividades`
- `GET/POST/PATCH /api/productos`
- `GET/POST /api/movimientos`
- `POST /api/login`
- `POST /api/logout`

La recuperación por correo todavía no debe considerarse terminada. El correo de
soporte está configurado, pero faltan una configuración SMTP real, tokens de
recuperación completos y pruebas del flujo.

## Roles previstos

1. Administrador
2. Jefe de producción
3. Encargado de piscina
4. Técnico de calidad
5. Gerencia

No asumir que la matriz actual es definitiva. Antes de cerrar cada módulo, revisar
`permisos`, `rol_permisos`, la función `require()` y los enlaces visibles en el
frontend. En particular, verificar que existan y estén asignados los permisos del
módulo `piscinas`; `init_mariadb()` aún debe armonizarse con las migraciones.

## Estado de MariaDB

Tablas originales de autenticación/autorización:

- `roles`
- `permisos`
- `rol_permisos`
- `usuarios`
- `sesiones`
- `recuperaciones_password`

Tablas creadas para los módulos:

- `fincas`
- `modulos`
- `piscinas`
- `ciclos_piscina`
- `colaboradores`
- `actividades`
- `productos_alimento`
- `movimientos_inventario`

También existe la vista `vista_piscinas_ciclo_actual`.

Estado real verificado el 3 de septiembre de 2026 mediante las credenciales de la
aplicación:

- 2 fincas.
- 16 módulos.
- 104 piscinas.
- 104 ciclos de referencia cargados.
- Ejemplos válidos: `EM00-PC1-3`, `EM00-PC2-3`, `EM00-PC3-4` y `EM00-PC4-5`.

El archivo `database/verificar_piscinas.py` comprueba esos conteos sin imprimir
credenciales.

## Decisión de dominio: piscinas y ciclos

La identificación física y el ciclo se guardan separados:

- Código estable de piscina: `EM00-PC1`.
- Número de ciclo: `5`.
- Código productivo presentado en la aplicación: `EM00-PC1-5`.

Nunca sobrescribir el código estable de la piscina cuando comienza una nueva
siembra. Registrar un nuevo renglón en `ciclos_piscina`. La combinación
`(piscina_id, numero_ciclo)` es única.

Interpretación confirmada de códigos:

- `E` = Engorde.
- `P` = Precría.
- `PC` = Precría.

La columna `nombre` fue eliminada manualmente de `piscinas` porque repetía el
código. Esta decisión ya fue aplicada a:

- `database/01_crear_tablas_modulos.sql`
- `database/02_cargar_piscinas_reales.sql`
- consultas de piscinas, actividades y movimientos en `server.py`
- `public/piscinas.html`
- `public/piscinas.js`

No volver a introducir `piscinas.nombre`. Los campos `nombre` de fincas,
colaboradores y productos sí son válidos.

## Archivos SQL y orden de uso

- `database/mariadb_schema.sql`: esquema base de autenticación. Ya se utilizó en
  esta instalación; no ejecutarlo a ciegas porque usa CREATE sin IF NOT EXISTS en
  varias tablas.
- `database/01_crear_tablas_modulos.sql`: esquema consolidado para una instalación
  nueva.
- `database/01b_ajustar_piscinas_y_ciclos.sql`: migración aplicada a esta base ya
  existente; agregó fincas, módulos, ciclos, `modulo_id` y la vista concatenada.
- `database/02_cargar_piscinas_reales.sql`: carga idempotente del CSV real.
- `database/02_cargar_datos_demo.sql`: datos demostrativos antiguos.
- `database/migracion_modulos_demo.sql`: migración demostrativa antigua.

No ejecutar los dos archivos de demostración sobre la base real salvo petición
explícita y después de revisar sus efectos. La fuente real de piscinas está fuera
del repositorio, en:

`C:\Users\ELIO_MARROQUIN\Desktop\Archivos CSV\PROYECTO\piscinas.csv`

El CSV tiene 104 filas, delimitador `;`, áreas con separador de millares y columna
`Ultimo ciclo`. La carga usa `LOAD DATA LOCAL INFILE`; `local_infile` fue confirmado
como `ON`.

## Estado del frontend

Pantallas existentes:

- `login.html`: inicio de sesión.
- `app.html`: mantenimiento de usuarios.
- `roles.html`: pantalla de roles/permisos o marcador funcional según su estado.
- `dashboard.html`: panel principal.
- `piscinas.html`: catálogo de piscinas.
- `personal.html`: colaboradores y actividades.
- `inventario.html`: productos y movimientos.

Los recursos compartidos están en `styles.css` y `module-common.js`.

La pantalla de piscinas fue ajustada para mostrar:

- código productivo concatenado;
- finca;
- módulo;
- tipo;
- área;
- estado.

El formulario de piscina usa un selector de módulos obtenido desde `/api/modulos`.
Estos cambios se compilaron sintácticamente en Python, pero deben probarse en el
navegador después de reiniciar el servidor. Node.js no está instalado, por lo que
no hay validación automática de sintaxis JavaScript con `node --check`.

## Próxima función prioritaria de piscinas

Implementar la administración vertical de ciclos. Requisitos acordados:

- Mostrar una lista vertical de las 104 piscinas.
- Mostrar el código productivo concatenado, no sus partes en la vista normal.
- Permitir seleccionar/asignar ciclo con números inicialmente del 1 al 30, pero
  diseñar sin un límite rígido para el futuro.
- Al iniciar una siembra, proponer automáticamente `último ciclo + 1`.
- Permitir corrección manual solo a usuarios autorizados.
- No duplicar un ciclo para la misma piscina.
- Conservar historial y estados: Planificado, Sembrado, Cosechado o Cancelado.
- Definir antes de implementar si cambiar el selector crea un ciclo inmediatamente
  o si requiere un botón explícito “Iniciar nuevo ciclo”. Es preferible el botón y
  una confirmación para evitar cambios accidentales.

Crear endpoints específicos de ciclos en lugar de actualizar directamente el
último número de la piscina. Añadir pruebas de permisos, duplicación, incremento y
formación del código concatenado.

## Datos de empleados y privacidad

El CSV anterior está en:

`C:\Users\ELIO_MARROQUIN\Desktop\Archivos CSV\empleados.csv`

Fue analizado, pero no cargado. Contiene 324 personas activas y datos sensibles.
Hallazgos:

- `CodigoEtalent` está completo y sin duplicados.
- Todos tienen fecha de ingreso.
- 287 no tienen celular.
- No contiene un campo confiable de puesto laboral.
- `Profesion` no debe asumirse como puesto.

No importar DPI, NIT, afiliación, fecha/lugar de nacimiento, etnia, estado civil,
beneficiario u otros datos personales que no necesite la operación. Campos
propuestos para colaboradores:

- `CodigoEtalent` → `codigo_empleado`.
- nombres y apellidos concatenados → `nombre`.
- puesto laboral real (pendiente en un nuevo Excel).
- celular opcional.
- estado.
- fecha de ingreso.
- fecha de baja opcional.

El usuario indicó que enviará un Excel nuevo con puesto. Esperar ese archivo,
analizar duplicados/incompletos y presentar la depuración antes de crear INSERT o
cargar registros. No modificar la fuente original.

Actualización del 4 de septiembre de 2026: se recibió `Personal Finca.csv` con 45
empleados, sin códigos/nombres duplicados ni campos operativos vacíos. Incluye
código, nombre, fecha de ingreso, puesto y estado; todos aparecen activos. El
estado civil se excluye por no ser necesario y el celular quedará vacío. Por
decisión del usuario, los colaboradores no se relacionarán todavía con una finca.
La relación podrá agregarse después mediante una migración.

Se creó `database/03_ajustar_colaboradores.sql` para añadir `fecha_ingreso` y
`fecha_baja`; el usuario confirmó su ejecución correcta. Se creó
`database/04_cargar_colaboradores_reales.sql` para importar los 45 colaboradores
de manera idempotente. Al retomar, confirmar si el paso 4 ya fue ejecutado antes
de repetirlo (repetirlo no duplica códigos, pero actualiza los datos coincidentes).

El usuario confirmó que el paso 4 devolvió 45 filas, 45 códigos únicos, 45 filas
válidas y 45 colaboradores cargados. Existe
`database/verificar_colaboradores.py` para comprobar la lectura con el usuario
limitado de la aplicación.

El módulo Personal fue actualizado para mostrar/buscar los 45 colaboradores,
incluir fecha de ingreso, respetar visualmente los permisos y usar el código
productivo concatenado al asignar actividades. El backend permite crear/editar
fecha de ingreso y registra `fecha_baja` automáticamente al desactivar. Los 12
permisos de piscinas, personal e inventario fueron verificados en MariaDB. El
archivo `database/05_configurar_permisos_modulos.sql` queda como migración
idempotente para otras instalaciones; no es necesario volver a ejecutarlo en la
instalación actual. El servidor se reinició y `personal.html` respondió HTTP 200.

## Pendientes técnicos conocidos

1. Reiniciar el servidor y probar la pantalla real de piscinas de extremo a extremo.
2. Implementar gestión de ciclos y su interfaz vertical.
3. Armonizar permisos de piscinas en `init_mariadb()` y las migraciones.
4. Completar y probar personal/actividades con el nuevo Excel.
5. Recibir catálogo real de alimentos y cargar inventario.
6. Probar entradas/salidas, stock insuficiente, lotes y vencimientos.
7. Revisar el panel principal con datos reales.
8. Actualizar `README.md`, que todavía describe principalmente la fase 1.
9. Actualizar el diagrama ER con fincas, módulos y ciclos.
10. Ampliar el manual y las pruebas automatizadas para los cuatro módulos.
11. Implementar recuperación de contraseña real, limitación de intentos, HTTPS y
    protecciones de producción antes de desplegar.

## Pruebas y verificaciones

Comprobación de la carga de piscinas:

```powershell
python database\verificar_piscinas.py
```

Pruebas existentes del flujo de autenticación:

```powershell
python -m unittest discover -s tests -v
```

Las pruebas actuales pueden conectarse a MariaDB si `.env` está activo y pueden
crear/eliminar usuarios de prueba. Revisar el entorno antes de ejecutarlas. Nunca
usar pruebas destructivas contra una base de producción.

Antes de entregar una modificación:

- ejecutar `python -m py_compile server.py`;
- probar login, permisos y logout;
- probar la API con el usuario limitado de la aplicación;
- revisar consola del navegador y respuestas HTTP;
- comprobar que refrescar el navegador no muestre archivos en caché antiguos;
- documentar cualquier migración y hacerla idempotente cuando sea posible.

## Reglas de trabajo para futuros agentes

- Leer este archivo y revisar el estado actual antes de editar.
- No mostrar ni cambiar `.env` salvo petición expresa; nunca revelar secretos.
- No usar `root` como usuario de la aplicación.
- No borrar ni recrear `pacific_gold` para resolver un error.
- No ejecutar SQL de demostración sobre los datos reales.
- No eliminar datos o tablas sin confirmar alcance y respaldo.
- Mantener el código productivo visible concatenado y los componentes normalizados.
- Mantener los archivos HTML, CSS y JavaScript legibles y ordenados verticalmente.
- Preservar el estilo azul y la identidad visual de Pacific Gold.
- Explicar al usuario un paso verificable a la vez cuando trabaje en HeidiSQL.
- Validar los datos antes de importarlos y reportar conteos esperados.
- Tratar los archivos de empleados como información confidencial.

## Avance del módulo de piscinas (2026-09-05)

- La pantalla separa Gestión de ciclos y Catálogo de piscinas.
- Muestra verticalmente las piscinas y el código productivo concatenado.
- La API permite consultar historial, iniciar, cosechar y cancelar ciclos.
- El siguiente ciclo debe ser el último + 1 y no admite duplicados.
- La lista muestra 1–30 y se amplía automáticamente al superar 30.
- Falta completar las pruebas manuales autenticadas de estas operaciones.
