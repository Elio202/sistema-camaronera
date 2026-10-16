-- PASO 4: Cargar colaboradores desde el CSV real.
-- Ejecutar en HeidiSQL conectado como root@localhost.
-- Requiere local_infile = ON.
-- No importa Estado Civil porque no es necesario para la operación.

USE pacific_gold;

DROP TEMPORARY TABLE IF EXISTS carga_colaboradores_csv;

CREATE TEMPORARY TABLE carga_colaboradores_csv (
    codigo VARCHAR(30) NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    fecha_ingreso_texto VARCHAR(20) NOT NULL,
    puesto VARCHAR(100) NOT NULL,
    estado_civil_texto VARCHAR(30) NULL,
    estado_texto VARCHAR(20) NOT NULL
) ENGINE = InnoDB;

LOAD DATA LOCAL INFILE
    'C:/Users/ELIO_MARROQUIN/Desktop/Archivos CSV/PROYECTO/Personal Finca.csv'
INTO TABLE carga_colaboradores_csv
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ';'
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(
    @codigo,
    @nombre,
    @fecha_ingreso,
    @puesto,
    @estado_civil,
    @estado
)
SET
    codigo = TRIM(@codigo),
    nombre = UPPER(REGEXP_REPLACE(TRIM(@nombre), '[[:space:]]+', ' ')),
    fecha_ingreso_texto = TRIM(@fecha_ingreso),
    puesto = UPPER(REGEXP_REPLACE(TRIM(@puesto), '[[:space:]]+', ' ')),
    estado_civil_texto = TRIM(@estado_civil),
    estado_texto = UPPER(TRIM(TRAILING '\r' FROM TRIM(@estado)));

START TRANSACTION;

INSERT INTO colaboradores (
    codigo_empleado,
    nombre,
    puesto,
    fecha_ingreso,
    fecha_baja,
    celular,
    estado
)
SELECT
    codigo,
    nombre,
    puesto,
    STR_TO_DATE(fecha_ingreso_texto, '%Y-%m-%d'),
    NULL,
    NULL,
    CASE WHEN estado_texto = 'ACTIVO' THEN TRUE ELSE FALSE END
FROM carga_colaboradores_csv
WHERE codigo <> ''
  AND nombre <> ''
  AND puesto <> ''
  AND STR_TO_DATE(fecha_ingreso_texto, '%Y-%m-%d') IS NOT NULL
ON DUPLICATE KEY UPDATE
    nombre = VALUES(nombre),
    puesto = VALUES(puesto),
    fecha_ingreso = VALUES(fecha_ingreso),
    estado = VALUES(estado);

COMMIT;

-- Verificación: el archivo contiene 45 filas válidas.
SELECT
    COUNT(*) AS filas_csv,
    COUNT(DISTINCT codigo) AS codigos_unicos,
    SUM(
        CASE
            WHEN codigo <> ''
             AND nombre <> ''
             AND puesto <> ''
             AND STR_TO_DATE(fecha_ingreso_texto, '%Y-%m-%d') IS NOT NULL
            THEN 1 ELSE 0
        END
    ) AS filas_validas
FROM carga_colaboradores_csv;

SELECT
    COUNT(*) AS colaboradores_del_archivo_cargados
FROM colaboradores AS c
INNER JOIN carga_colaboradores_csv AS carga
    ON carga.codigo = c.codigo_empleado;

-- Muestra limitada sin incluir información sensible innecesaria.
SELECT
    codigo_empleado,
    nombre,
    puesto,
    fecha_ingreso,
    estado
FROM colaboradores
ORDER BY nombre
LIMIT 15;

