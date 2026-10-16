# Manual de pruebas del login y módulo de usuarios

**Proyecto:** Prototipo de sistema automatizado para el monitoreo y control de procesos en cultivos de camarón  
**Empresa:** Pacific Gold / Oro del Pacífico, S. A.  
**Módulo evaluado:** Autenticación y mantenimiento de usuarios  
**Base de datos:** MariaDB — `pacific_gold`  
**Responsable:** Elio Danilo Marroquín Álvarez  
**Versión:** 1.0  
**Fecha de ejecución:** ____________________

---

## 1. Objetivo

Comprobar que el sistema valide correctamente las credenciales, consulte el rol del usuario, obtenga los permisos asociados, habilite únicamente las funciones autorizadas y permita acceder al panel correspondiente, conforme al diagrama de actividad definido para el proyecto.

## 2. Flujo que debe validarse

1. El usuario ingresa su nombre de usuario y contraseña.
2. Las credenciales son enviadas al sistema.
3. El sistema verifica si las credenciales son válidas.
4. Si no son válidas, muestra un error de acceso y permite intentarlo nuevamente.
5. Si son válidas, consulta el rol del usuario.
6. Obtiene los permisos asociados con el rol.
7. Habilita únicamente los módulos y funciones autorizados.
8. Muestra el panel principal.

## 3. Alcance

Este manual cubre:

- Inicio y cierre de sesión.
- Validación de credenciales.
- Restricción del acceso a cuentas inactivas.
- Validación de sesiones.
- Consulta de roles y permisos.
- Creación, modificación, activación y desactivación de usuarios.
- Validación de nombres de usuario, correos y contraseñas.
- Verificación de datos en MariaDB.

No cubre todavía los módulos de aireación, inventario, personal, calidad del agua ni reportes, debido a que corresponden a fases posteriores.

## 4. Requisitos previos

Antes de comenzar, verificar:

- El servicio local `MariaDB` está iniciado.
- La base `pacific_gold` existe.
- La aplicación está ejecutándose con `python server.py`.
- El navegador puede acceder a `http://localhost:8000/login.html`.
- HeidiSQL puede conectarse a MariaDB.
- Existe el usuario administrador inicial.

Credenciales temporales de desarrollo:

```text
Usuario: admin
Contraseña: Admin123!
```

> Estas credenciales son exclusivamente para desarrollo y deben cambiarse antes de publicar el sistema.

## 5. Criterios de evaluación

- **Aprobado:** el resultado obtenido coincide completamente con el resultado esperado.
- **No aprobado:** el sistema permite una operación inválida, bloquea una operación válida o presenta un error inesperado.
- **No ejecutado:** la prueba no pudo realizarse por falta de datos, permisos o disponibilidad del sistema.

## 6. Datos de prueba

| Usuario | Nombre | Correo | Rol | Contraseña |
|---|---|---|---|---|
| `jefe.prueba` | Jefe de Producción Prueba | jefe.prueba@example.com | Jefe de producción | `Prueba123` |
| `piscina.prueba` | Encargado de Piscina Prueba | piscina.prueba@example.com | Encargado de piscina | `Prueba123` |
| `calidad.prueba` | Técnico de Calidad Prueba | calidad.prueba@example.com | Técnico de calidad | `Prueba123` |
| `gerencia.prueba` | Gerente de Prueba | gerencia.prueba@example.com | Gerencia | `Prueba123` |

No utilizar información ni contraseñas reales de empleados.

---

## 7. Casos de prueba

### CP-LOGIN-001 — Inicio de sesión correcto

**Objetivo:** comprobar que un usuario activo con credenciales válidas pueda ingresar.

**Pasos:**

1. Abrir `http://localhost:8000/login.html`.
2. Escribir `admin` en Usuario.
3. Escribir `Admin123!` en Contraseña.
4. Presionar **Ingresar al sistema**.

**Resultado esperado:** el sistema valida las credenciales, consulta el rol Administrador, carga sus permisos y muestra el módulo de usuarios.

**Resultado obtenido:** ________________________________________________  
**Estado:** ☐ Aprobado ☐ No aprobado ☐ No ejecutado  
**Evidencia:** ______________________________

### CP-LOGIN-002 — Contraseña incorrecta

**Pasos:**

1. Escribir `admin` como usuario.
2. Escribir `Incorrecta123` como contraseña.
3. Presionar **Ingresar al sistema**.

**Resultado esperado:** se muestra `Usuario o contraseña incorrectos.` y no se crea una sesión.

**Resultado obtenido:** ________________________________________________  
**Estado:** ☐ Aprobado ☐ No aprobado ☐ No ejecutado  
**Evidencia:** ______________________________

### CP-LOGIN-003 — Usuario inexistente

**Datos:** usuario `usuario_no_existe`, contraseña `Prueba123`.

**Resultado esperado:** se muestra el mismo mensaje genérico de credenciales incorrectas. El sistema no revela cuál dato falló.

**Resultado obtenido:** ________________________________________________  
**Estado:** ☐ Aprobado ☐ No aprobado ☐ No ejecutado

### CP-LOGIN-004 — Campos obligatorios

**Pasos:** probar usuario vacío, contraseña vacía y ambos campos vacíos.

**Resultado esperado:** el navegador solicita completar los campos y no envía el formulario.

**Resultado obtenido:** ________________________________________________  
**Estado:** ☐ Aprobado ☐ No aprobado ☐ No ejecutado

### CP-LOGIN-005 — Acceso únicamente mediante usuario

**Datos:** escribir `emarroquin@esteromar.gt` en el campo Usuario y usar la contraseña del administrador.

**Resultado esperado:** acceso rechazado, debido a que el sistema solo admite nombre de usuario.

**Resultado obtenido:** ________________________________________________  
**Estado:** ☐ Aprobado ☐ No aprobado ☐ No ejecutado

### CP-LOGIN-006 — Mostrar y ocultar contraseña

**Pasos:** escribir una contraseña, pulsar **Ver** y volver a pulsarlo.

**Resultado esperado:** la contraseña cambia de oculta a visible y después vuelve a ocultarse.

**Resultado obtenido:** ________________________________________________  
**Estado:** ☐ Aprobado ☐ No aprobado ☐ No ejecutado

### CP-LOGIN-007 — Cuenta inactiva

**Precondición:** crear `gerencia.prueba` y desactivarlo desde el administrador.

**Pasos:** cerrar sesión e intentar entrar como `gerencia.prueba`.

**Resultado esperado:** el acceso se rechaza con el mensaje genérico de credenciales incorrectas.

**Resultado obtenido:** ________________________________________________  
**Estado:** ☐ Aprobado ☐ No aprobado ☐ No ejecutado

### CP-LOGIN-008 — Acceso sin sesión

**Pasos:** abrir una ventana de incógnito e ingresar a `http://localhost:8000/app.html`.

**Resultado esperado:** no se muestra información protegida y el usuario es enviado al login.

**Resultado obtenido:** ________________________________________________  
**Estado:** ☐ Aprobado ☐ No aprobado ☐ No ejecutado

### CP-LOGIN-009 — Cierre de sesión

**Pasos:** iniciar sesión, pulsar **Salir** y usar el botón Atrás del navegador.

**Resultado esperado:** la sesión queda invalidada y no vuelve a mostrarse información protegida.

**Resultado obtenido:** ________________________________________________  
**Estado:** ☐ Aprobado ☐ No aprobado ☐ No ejecutado

### CP-USR-001 — Crear usuario válido

**Pasos:**

1. Ingresar como Administrador.
2. Pulsar **Nuevo usuario**.
3. Registrar los datos de `jefe.prueba` indicados en la sección 6.
4. Guardar.

**Resultado esperado:** el usuario aparece en la tabla con rol Jefe de producción y estado Activo.

**Resultado obtenido:** ________________________________________________  
**Estado:** ☐ Aprobado ☐ No aprobado ☐ No ejecutado  
**Evidencia:** ______________________________

### CP-USR-002 — Contraseña débil

**Datos que deben probarse:** `abcdefgh`, `prueba123`, `PRUEBA123` y `PruebaABC`.

**Resultado esperado:** todas son rechazadas. La contraseña debe tener ocho o más caracteres, mayúscula, minúscula y número.

**Resultado obtenido:** ________________________________________________  
**Estado:** ☐ Aprobado ☐ No aprobado ☐ No ejecutado

### CP-USR-003 — Nombre de usuario inválido

**Datos que deben probarse:** `mi usuario`, `usuario@` y `ab`.

**Resultado esperado:** se rechazan. Solo se permiten letras, números, punto, guion y guion bajo, con longitud de 3 a 50 caracteres.

**Resultado obtenido:** ________________________________________________  
**Estado:** ☐ Aprobado ☐ No aprobado ☐ No ejecutado

### CP-USR-004 — Correo inválido

**Datos que deben probarse:** `prueba`, `prueba@` y `prueba@correo`.

**Resultado esperado:** el formulario no se guarda y solicita un correo válido.

**Resultado obtenido:** ________________________________________________  
**Estado:** ☐ Aprobado ☐ No aprobado ☐ No ejecutado

### CP-USR-005 — Usuario duplicado

**Pasos:** intentar registrar nuevamente un nombre de usuario existente.

**Resultado esperado:** se informa que el usuario o correo ya existe y no se duplica el registro.

**Resultado obtenido:** ________________________________________________  
**Estado:** ☐ Aprobado ☐ No aprobado ☐ No ejecutado

### CP-USR-006 — Correo duplicado

**Pasos:** utilizar un usuario nuevo con el correo de otro usuario existente.

**Resultado esperado:** se rechaza la operación y no se duplica el registro.

**Resultado obtenido:** ________________________________________________  
**Estado:** ☐ Aprobado ☐ No aprobado ☐ No ejecutado

### CP-USR-007 — Editar usuario

**Pasos:** editar `jefe.prueba`, cambiar su nombre y asignarle Técnico de calidad sin escribir una contraseña nueva.

**Resultado esperado:** nombre y rol se actualizan, pero conserva su contraseña anterior.

**Resultado obtenido:** ________________________________________________  
**Estado:** ☐ Aprobado ☐ No aprobado ☐ No ejecutado

### CP-USR-008 — Desactivar y reactivar usuario

**Pasos:** desactivar `jefe.prueba`, comprobar que no pueda ingresar, reactivarlo y comprobar nuevamente.

**Resultado esperado:** la cuenta inactiva no ingresa; después de reactivarla, sus credenciales vuelven a ser aceptadas.

**Resultado obtenido:** ________________________________________________  
**Estado:** ☐ Aprobado ☐ No aprobado ☐ No ejecutado

### CP-ROL-001 — Consulta del rol

**Pasos:** iniciar sesión con cada usuario de la sección 6.

**Resultado esperado:** el sistema identifica el rol asignado a cada cuenta.

**Resultado obtenido:** ________________________________________________  
**Estado:** ☐ Aprobado ☐ No aprobado ☐ No ejecutado

### CP-ROL-002 — Restricción del módulo de usuarios

**Pasos:** iniciar sesión con Gerencia, Jefe de producción, Encargado de piscina y Técnico de calidad e intentar acceder al mantenimiento de usuarios.

**Resultado esperado:** ninguno puede consultar ni modificar usuarios. Solo Administrador tiene acceso.

**Resultado obtenido:** ________________________________________________  
**Estado:** ☐ Aprobado ☐ No aprobado ☐ No ejecutado

### CP-DB-001 — Contraseña protegida en MariaDB

**Pasos:** abrir HeidiSQL, seleccionar `pacific_gold → usuarios → Datos` y localizar un usuario de prueba.

**Resultado esperado:** `password_hash` contiene un valor cifrado y nunca muestra `Prueba123`.

**Resultado obtenido:** ________________________________________________  
**Estado:** ☐ Aprobado ☐ No aprobado ☐ No ejecutado  
**Evidencia:** ocultar cualquier información sensible.

### CP-DB-002 — Registro de sesión

**Pasos:** iniciar y cerrar sesión; luego revisar `pacific_gold → sesiones → Datos`.

**Resultado esperado:** existe una sesión con fecha de inicio y, después de salir, una fecha de finalización.

**Resultado obtenido:** ________________________________________________  
**Estado:** ☐ Aprobado ☐ No aprobado ☐ No ejecutado

---

## 8. Resumen de ejecución

| Código | Prueba | Estado | Evidencia/observación |
|---|---|---|---|
| CP-LOGIN-001 | Inicio correcto | | |
| CP-LOGIN-002 | Contraseña incorrecta | | |
| CP-LOGIN-003 | Usuario inexistente | | |
| CP-LOGIN-004 | Campos obligatorios | | |
| CP-LOGIN-005 | Acceso solo por usuario | | |
| CP-LOGIN-006 | Mostrar contraseña | | |
| CP-LOGIN-007 | Cuenta inactiva | | |
| CP-LOGIN-008 | Acceso sin sesión | | |
| CP-LOGIN-009 | Cierre de sesión | | |
| CP-USR-001 | Crear usuario | | |
| CP-USR-002 | Contraseña débil | | |
| CP-USR-003 | Usuario inválido | | |
| CP-USR-004 | Correo inválido | | |
| CP-USR-005 | Usuario duplicado | | |
| CP-USR-006 | Correo duplicado | | |
| CP-USR-007 | Editar usuario | | |
| CP-USR-008 | Activar/desactivar | | |
| CP-ROL-001 | Consulta del rol | | |
| CP-ROL-002 | Restricción por rol | | |
| CP-DB-001 | Contraseña protegida | | |
| CP-DB-002 | Registro de sesión | | |

## 9. Resultado final

**Total de pruebas:** 21  
**Aprobadas:** ______  
**No aprobadas:** ______  
**No ejecutadas:** ______  

**Conclusión:**

________________________________________________________________________

________________________________________________________________________

________________________________________________________________________

**Nombre y firma del responsable:** ____________________________________

