-- PASO 2: Cargar fincas, módulos, piscinas y últimos ciclos desde el CSV real.
-- Ejecutar en HeidiSQL conectado como root@localhost.
-- Requiere local_infile = ON.

USE pacific_gold;

DROP TEMPORARY TABLE IF EXISTS carga_piscinas_csv;

CREATE TEMPORARY TABLE carga_piscinas_csv (
    finca VARCHAR(80) NOT NULL,
    modulo VARCHAR(20) NOT NULL,
    piscina VARCHAR(20) NOT NULL,
    area_texto VARCHAR(30) NOT NULL,
    estado_texto VARCHAR(30) NOT NULL,
    ultimo_ciclo_texto VARCHAR(10) NOT NULL
) ENGINE = InnoDB;

LOAD DATA LOCAL INFILE
    'C:/Users/ELIO_MARROQUIN/Desktop/Archivos CSV/PROYECTO/piscinas.csv'
INTO TABLE carga_piscinas_csv
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ';'
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(
    finca,
    modulo,
    piscina,
    area_texto,
    estado_texto,
    ultimo_ciclo_texto
);

-- Quitar espacios y retornos de carro provenientes del archivo CSV.
UPDATE carga_piscinas_csv
SET
    finca = UPPER(TRIM(finca)),
    modulo = UPPER(TRIM(modulo)),
    piscina = UPPER(TRIM(piscina)),
    area_texto = TRIM(area_texto),
    estado_texto = UPPER(TRIM(estado_texto)),
    ultimo_ciclo_texto = TRIM(TRAILING '\r' FROM TRIM(ultimo_ciclo_texto));

START TRANSACTION;

INSERT INTO fincas (nombre, estado)
SELECT DISTINCT finca, TRUE
FROM carga_piscinas_csv
WHERE finca <> ''
ON DUPLICATE KEY UPDATE
    estado = VALUES(estado);

INSERT INTO modulos (finca_id, codigo, estado)
SELECT DISTINCT f.id, c.modulo, TRUE
FROM carga_piscinas_csv AS c
INNER JOIN fincas AS f
    ON f.nombre = c.finca
WHERE c.modulo <> ''
ON DUPLICATE KEY UPDATE
    finca_id = VALUES(finca_id),
    estado = VALUES(estado);

INSERT INTO piscinas (
    modulo_id,
    codigo,
    tipo,
    area_m2,
    estado
)
SELECT
    m.id,
    c.piscina,
    CASE
        WHEN c.piscina REGEXP '-E[0-9]+$' THEN 'Engorde'
        WHEN c.piscina REGEXP '-(P|PC)[0-9]+$' THEN 'Precría'
        ELSE 'Precría'
    END,
    CAST(REPLACE(REPLACE(c.area_texto, ',', ''), ' ', '') AS DECIMAL(10, 2)),
    TRUE
FROM carga_piscinas_csv AS c
INNER JOIN modulos AS m
    ON m.codigo = c.modulo
WHERE c.piscina <> ''
ON DUPLICATE KEY UPDATE
    modulo_id = VALUES(modulo_id),
    tipo = VALUES(tipo),
    area_m2 = VALUES(area_m2),
    estado = VALUES(estado);

INSERT INTO ciclos_piscina (
    piscina_id,
    numero_ciclo,
    estado
)
SELECT
    p.id,
    CAST(c.ultimo_ciclo_texto AS UNSIGNED),
    CASE
        WHEN c.estado_texto IN ('COSECHADA', 'COSECHADAS') THEN 'Cosechado'
        ELSE 'Sembrado'
    END
FROM carga_piscinas_csv AS c
INNER JOIN piscinas AS p
    ON p.codigo = c.piscina
WHERE CAST(c.ultimo_ciclo_texto AS UNSIGNED) >= 1
ON DUPLICATE KEY UPDATE
    estado = VALUES(estado);

COMMIT;

-- modulo_id puede quedar obligatorio una vez que todas las piscinas se cargaron.
DELIMITER //

DROP PROCEDURE IF EXISTS asegurar_modulo_piscina//
CREATE PROCEDURE asegurar_modulo_piscina()
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM piscinas
        WHERE modulo_id IS NULL
    ) THEN
        ALTER TABLE piscinas
            MODIFY COLUMN modulo_id INT UNSIGNED NOT NULL;
    END IF;
END//

CALL asegurar_modulo_piscina()//
DROP PROCEDURE asegurar_modulo_piscina//

DELIMITER ;

-- Verificación general: se esperan 2 fincas, 16 módulos y 104 piscinas/ciclos.
SELECT 'Fincas' AS concepto, COUNT(*) AS total FROM fincas
UNION ALL
SELECT 'Módulos', COUNT(*) FROM modulos
UNION ALL
SELECT 'Piscinas', COUNT(*) FROM piscinas
UNION ALL
SELECT 'Ciclos cargados', COUNT(*) FROM ciclos_piscina;

-- Muestra de los códigos que utilizará la aplicación.
SELECT
    finca,
    modulo,
    piscina,
    numero_ciclo,
    codigo_productivo,
    tipo,
    area_m2,
    estado_ciclo
FROM vista_piscinas_ciclo_actual
ORDER BY finca, modulo, piscina
LIMIT 20;
