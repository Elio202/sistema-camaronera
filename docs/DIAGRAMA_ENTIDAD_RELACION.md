# Diagrama Entidad–Relación — Pacific Gold

**Versión:** 1.0 — estructura actual del sistema  
**Base de datos:** `pacific_gold` (MariaDB)

> Este diagrama representa las entidades implementadas actualmente. Debido a que
> el proyecto se desarrolla de forma incremental, deberá actualizarse cuando se
> incorporen nuevas entidades o relaciones.

```mermaid
erDiagram
    ROLES ||--o{ USUARIOS : asigna
    ROLES ||--o{ ROL_PERMISOS : contiene
    PERMISOS ||--o{ ROL_PERMISOS : habilita
    USUARIOS ||--o{ SESIONES : inicia
    USUARIOS ||--o{ RECUPERACIONES_PASSWORD : solicita

    FINCAS ||--o{ MODULOS : contiene
    MODULOS ||--o{ PISCINAS : agrupa
    PISCINAS ||--o{ CICLOS_PISCINA : registra

    COLABORADORES ||--o{ ACTIVIDADES : recibe
    PISCINAS ||--o{ ACTIVIDADES : requiere
    USUARIOS ||--o{ ACTIVIDADES : asigna

    PRODUCTOS_ALIMENTO ||--o{ MOVIMIENTOS_INVENTARIO : registra
    PISCINAS o|--o{ MOVIMIENTOS_INVENTARIO : consume
    COLABORADORES o|--o{ MOVIMIENTOS_INVENTARIO : responsabiliza
    USUARIOS ||--o{ MOVIMIENTOS_INVENTARIO : autoriza

    ROLES {
        int id PK
        varchar nombre UK
        varchar descripcion
        boolean estado
    }

    PERMISOS {
        int id PK
        varchar modulo UK
        varchar funcion UK
    }

    ROL_PERMISOS {
        int rol_id PK,FK
        int permiso_id PK,FK
    }

    USUARIOS {
        int id PK
        varchar nombre_usuario UK
        varchar nombre
        varchar correo UK
        varchar password_hash
        int rol_id FK
        boolean estado
        datetime creado_en
        datetime actualizado_en
    }

    SESIONES {
        bigint id PK
        char token_hash UK
        int usuario_id FK
        datetime fecha_inicio
        datetime fecha_fin
        datetime expira_en
    }

    RECUPERACIONES_PASSWORD {
        bigint id PK
        int usuario_id FK
        char token_hash UK
        datetime creado_en
        datetime expira_en
        datetime utilizado_en
    }

    FINCAS {
        int id PK
        varchar nombre UK
        boolean estado
        datetime creado_en
    }

    MODULOS {
        int id PK
        int finca_id FK
        varchar codigo UK
        boolean estado
        datetime creado_en
    }

    PISCINAS {
        int id PK
        int modulo_id FK
        varchar codigo UK
        enum tipo
        decimal area_m2
        boolean estado
        datetime creado_en
    }

    CICLOS_PISCINA {
        bigint id PK
        int piscina_id FK
        int numero_ciclo UK
        enum estado
        date fecha_siembra
        date fecha_cosecha
    }

    COLABORADORES {
        int id PK
        varchar codigo_empleado UK
        varchar nombre
        varchar puesto
        date fecha_ingreso
        date fecha_baja
        varchar celular
        boolean estado
    }

    ACTIVIDADES {
        int id PK
        int colaborador_id FK
        int piscina_id FK
        int usuario_asigna FK
        varchar descripcion
        datetime fecha_limite
        enum estado
        datetime realizada_en
    }

    PRODUCTOS_ALIMENTO {
        int id PK
        varchar codigo UK
        varchar nombre
        varchar marca
        varchar unidad
        decimal stock_actual
        decimal stock_minimo
        boolean estado
    }

    MOVIMIENTOS_INVENTARIO {
        bigint id PK
        int producto_id FK
        int piscina_id FK
        int responsable_id FK
        int usuario_id FK
        enum tipo
        decimal cantidad
        varchar lote
        date fecha_vencimiento
        varchar observacion
    }
```

## Leyenda

- **PK:** clave primaria que identifica cada registro.
- **FK:** clave foránea que relaciona una tabla con otra.
- **UK:** campo o combinación de campos con valor único.
- `||--o{`: relación de uno a muchos.
- `o|--o{`: relación opcional de uno a muchos.

## Organización del modelo

1. **Seguridad:** roles, permisos, usuarios, sesiones y recuperaciones.
2. **Producción:** fincas, módulos, piscinas y ciclos de piscina.
3. **Personal:** colaboradores y actividades.
4. **Inventario:** productos de alimento y movimientos de inventario.

El código productivo como `EM00-PC1-5` no se almacena en una columna duplicada:
la aplicación lo presenta concatenando el código de la piscina y el número del
ciclo correspondiente.
