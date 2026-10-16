# Depuración de la tabla de empleados

## Resultado del análisis

- Registros analizados: **324**.
- Columnas originales: **35**.
- `CodigoEtalent`: 324 valores únicos; se utilizará como código externo del colaborador.
- `Codigo`: solo 109 valores distintos; no es adecuado como clave primaria del empleado.
- `DPI`: es único, pero se excluye por ser información personal sensible innecesaria para el seguimiento operativo.
- Diez campos contienen únicamente el texto `NULL`.
- El archivo no contiene el puesto laboral; se agregó `puesto` vacío para completarlo con información autorizada.

## Campos conservados

| Campo depurado | Origen | Justificación |
|---|---|---|
| `codigo_empleado` | `CodigoEtalent` | Identificador empresarial único |
| `primer_nombre` | `PrimerNombre` | Identificación operacional |
| `segundo_nombre` | `SegundoNombre` | Nombre completo; puede ser nulo |
| `tercer_nombre` | `TercerNombre` | Nombre completo; puede ser nulo |
| `primer_apellido` | `PrimerApellido` | Identificación operacional |
| `segundo_apellido` | `SegundoApellido` | Nombre completo; puede ser nulo |
| `apellido_casada` | `ApellidoCasada` | Nombre utilizado por algunas colaboradoras; puede ser nulo |
| `celular` | `Celular` | Contacto para actividades y alertas; debe validarse |
| `fecha_ingreso` | `FechaIngreso` | Control del estado operativo |
| `fecha_baja` | `FechaBaja` | Se convierte `NULL` a valor vacío/nulo |
| `estado` | `Estado` | Permite impedir asignaciones a personal inactivo |
| `puesto` | Nuevo | Necesario para el módulo; debe completarse |

## Campos eliminados

| Grupo | Campos | Motivo |
|---|---|---|
| Identificación sensible | `DPI`, `PaisDPI`, `DepartamentoDPI`, `MunicipioDPI`, `VencimientoDPI`, `NIT`, `SeguroSocial` | El proyecto no administra expedientes laborales ni nómina |
| Información personal no operativa | `FechaNacimiento`, `Sexo`, `EstadoCivil`, `NumeroHijos`, `Etnia`, `TipoSangre`, `Beneficiario` | No es necesaria para asignar o seguir actividades |
| Lugar de nacimiento | `PaisNacimiento`, `DepartamentoNacimiento`, `MunicipioNacimiento`, `Nacionalidad` | No interviene en los procesos definidos |
| Documentación laboral | `PermisoTrabajo`, `TituloPersonal`, `NivelAcademico`, `Profesion` | Fuera del alcance actual; profesión no equivale a puesto |
| Contacto sin datos | `Telefono` | Contiene únicamente `NULL`; se conserva `Celular` |
| Código no único | `Codigo` | Presenta 215 repeticiones; se reemplaza por `CodigoEtalent` |

## Modelo recomendado

La tabla final de MariaDB se denominará `colaboradores`. Su clave primaria será un identificador interno autoincremental y `codigo_empleado` tendrá una restricción única. La relación opcional con `usuarios` permitirá que un colaborador tenga una cuenta sin obligar a que todo empleado pueda iniciar sesión.

El archivo original permanece intacto. `empleados_depurado.csv` es una copia de trabajo y continúa conteniendo datos personales básicos, por lo que no debe publicarse en repositorios ni adjuntarse al documento académico.
