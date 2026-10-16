# Opciones y requerimientos del sistema

## Sistema de gestión acuícola Pacific Gold

**Versión:** 2.0 resumida  
**Fecha:** 5 de septiembre de 2026

## 1. Objetivo

Centralizar el monitoreo y control de los procesos acuícolas de Pacific Gold,
incluyendo aireación, alimento, personal, calidad del agua, seguridad y reportes.

## 2. Usuarios previstos

- Administrador.
- Jefe de producción.
- Encargado de piscina.
- Técnico de calidad.
- Gerencia.

Cada usuario tendrá acceso únicamente a las opciones autorizadas para su rol.

## 3. Opciones del sistema

| Módulo | Opciones principales | Estado actual |
|---|---|---|
| Acceso | Iniciar sesión, cerrar sesión y recuperar contraseña | Login funcional; recuperación pendiente |
| Panel principal | Ver indicadores, alertas y accesos rápidos | En validación |
| Usuarios y permisos | Crear, editar, activar usuarios y asignar roles/permisos | Usuarios funcional; matriz de permisos parcial |
| Piscinas y ciclos | Administrar fincas, módulos, piscinas y ciclos productivos | Datos cargados; gestión de ciclos pendiente |
| Aireación | Leer oxígeno, controlar aireadores, consultar historial y alertas | Pendiente |
| Inventario | Administrar alimentos, entradas, salidas, existencias y mínimos | En validación |
| Personal | Administrar colaboradores y asignar actividades | En validación |
| Calidad del agua | Registrar oxígeno, temperatura, pH y salinidad; validar rangos | Pendiente |
| Alertas | Consultar y atender alertas de operación | Pendiente |
| Reportes | Consultar, filtrar y exportar información en PDF | Pendiente |

### Opciones destacadas

- Mostrar códigos productivos concatenados, por ejemplo `EM00-PC1-5`.
- Conservar por separado la piscina y su número de ciclo.
- Clasificar piscinas como Engorde o Precría.
- Asignar actividades a un colaborador y una piscina.
- Clasificar actividades como pendientes, realizadas o vencidas.
- Registrar entradas y salidas de alimento sin permitir existencias negativas.
- Clasificar las salidas de alimento según la piscina de destino.
- Encender o apagar aireadores según límites de oxígeno configurados.
- Alertar sobre parámetros críticos, actividades vencidas e inventario bajo.
- Generar reportes operativos y administrativos.

## 4. Requerimientos funcionales

| Código | Requerimiento | Estado |
|---|---|---|
| RF-01 | El sistema deberá permitir iniciar y cerrar sesión mediante credenciales válidas. | Implementado |
| RF-02 | El sistema deberá habilitar módulos y acciones según el rol y los permisos del usuario. | Implementado parcialmente |
| RF-03 | El administrador deberá gestionar usuarios, roles y permisos. | Usuarios implementado; permisos parcial |
| RF-04 | El sistema deberá mostrar en el panel los principales indicadores y alertas. | En validación |
| RF-05 | El usuario autorizado deberá administrar fincas, módulos, piscinas y sus ciclos productivos. | Implementado parcialmente |
| RF-06 | El sistema deberá mostrar el código de piscina y ciclo concatenado, conservando ambos datos separados. | Implementado |
| RF-07 | El sistema deberá recibir el oxígeno del sensor y controlar automáticamente los aireadores según límites configurados. | Pendiente |
| RF-08 | El usuario autorizado deberá registrar productos, entradas y salidas de alimento, actualizando automáticamente las existencias. | En validación |
| RF-09 | El sistema deberá impedir salidas superiores al inventario disponible y advertir cuando se alcance el mínimo. | En validación |
| RF-10 | El usuario autorizado deberá administrar colaboradores y asignarles actividades relacionadas con piscinas. | En validación |
| RF-11 | El sistema deberá clasificar las actividades como pendientes, realizadas o vencidas y generar alertas por incumplimiento. | En validación |
| RF-12 | El sistema deberá registrar y validar oxígeno, temperatura, pH y salinidad según rangos configurados. | Pendiente |
| RF-13 | El sistema deberá centralizar y permitir atender alertas de aireación, calidad, personal e inventario. | Pendiente |
| RF-14 | El sistema deberá generar reportes operativos y administrativos con filtros y exportación en PDF. | Pendiente |
| RF-15 | El sistema deberá permitir recuperar la contraseña mediante un enlace seguro enviado por correo. | Pendiente |

## 5. Reglas de negocio

- Los nombres de usuario y correos no podrán repetirse.
- Solo las cuentas y roles activos podrán ingresar.
- Cada operación dependerá de los permisos del rol.
- El código estable de una piscina no cambiará al comenzar otro ciclo.
- Una piscina no podrá repetir un número de ciclo.
- `E` significa Engorde; `P` y `PC` significan Precría.
- Solo piscinas y colaboradores activos podrán recibir actividades nuevas.
- Una actividad pendiente fuera de plazo se marcará como vencida.
- Toda salida de alimento requerirá piscina y responsable.
- Una salida no podrá superar la existencia disponible.

## 6. Requerimientos no funcionales

| Código | Requerimiento |
|---|---|
| RNF-01 | Las contraseñas y sesiones deberán almacenarse de forma segura. |
| RNF-02 | La aplicación deberá utilizar roles, permisos y un usuario limitado de MariaDB. |
| RNF-03 | La información personal almacenada deberá limitarse a los datos necesarios para la operación. |
| RNF-04 | La interfaz deberá ser clara, consistente y adaptable a computadora, tableta y teléfono. |
| RNF-05 | Las consultas normales deberán responder en un máximo objetivo de dos segundos en la red local. |
| RNF-06 | La base deberá proteger la integridad mediante claves, relaciones y validaciones. |
| RNF-07 | El sistema deberá registrar las operaciones críticas para mantener trazabilidad. |
| RNF-08 | Deberán existir procedimientos comprobados de respaldo y restauración. |
| RNF-09 | Las fallas de sensores o comunicación deberán registrarse y manejarse de forma segura. |
| RNF-10 | La instalación productiva deberá utilizar HTTPS y secretos fuera del código fuente. |

## 7. Alcance oficial

La propuesta comprende seis módulos:

1. Monitoreo y control de aireación.
2. Inventario de alimento.
3. Control y seguimiento de personal.
4. Parámetros y calidad del agua.
5. Usuarios, roles y permisos.
6. Reportes de procesos.

El panel, las piscinas, los ciclos y las alertas funcionan como componentes que
integran esos módulos.

## 8. Fuera del alcance

- Cálculo automático de raciones de alimento.
- Nómina y salarios.
- Expedientes laborales completos.
- Inventarios separados para Engorde y Precría; se utilizará un inventario general.

## 9. Prioridad inmediata de desarrollo

Para completar primero cuatro módulos funcionales se priorizarán:

1. Usuarios, roles y permisos.
2. Piscinas y ciclos.
3. Personal y actividades.
4. Inventario de alimento.

Después se integrarán aireación, calidad del agua y reportes para completar el
alcance oficial.

