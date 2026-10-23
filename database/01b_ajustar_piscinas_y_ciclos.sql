-- PASO 1B: Ajustar la estructura de piscinas para fincas, módulos y ciclos.
-- Ejecutar en HeidiSQL conectado como root@localhost.
-- Esta migración no elimina las tablas ni los datos existentes.

USE pacific_gold;

CREATE TABLE IF NOT EXISTS fincas (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(80) NOT NULL,
    estado BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_finca_nombre UNIQUE (nombre)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS modulos (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    finca_id INT UNSIGNED NOT NULL,
    codigo VARCHAR(20) NOT NULL,
    estado BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_modulo_codigo UNIQUE (codigo),
    CONSTRAINT fk_modulo_finca
        FOREIGN KEY (finca_id) REFERENCES fincas(id)
) ENGINE = InnoDB;

-- El procedimiento permite ejecutar nuevamente el archivo sin duplicar
-- la columna modulo_id cuando ya exista.
DELIMITER //

DROP PROCEDURE IF EXISTS agregar_modulo_a_piscinas//
CREATE PROCEDURE agregar_modulo_a_piscinas()
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = 'pacific_gold'
          AND TABLE_NAME = 'piscinas'
          AND COLUMN_NAME = 'modulo_id'
    ) THEN
        ALTER TABLE piscinas
            ADD COLUMN modulo_id INT UNSIGNED NULL AFTER id,
            ADD INDEX ix_piscina_modulo (modulo_id),
            ADD CONSTRAINT fk_piscina_modulo
                FOREIGN KEY (modulo_id) REFERENCES modulos(id);
    END IF;
END//

CALL agregar_modulo_a_piscinas()//
DROP PROCEDURE agregar_modulo_a_piscinas//

DELIMITER ;

CREATE TABLE IF NOT EXISTS ciclos_piscina (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    piscina_id INT UNSIGNED NOT NULL,
    numero_ciclo INT UNSIGNED NOT NULL,
    estado ENUM('Planificado', 'Sembrado', 'Cosechado', 'Cancelado')
        NOT NULL DEFAULT 'Planificado',
    fecha_siembra DATE NULL,
    fecha_cosecha DATE NULL,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_ciclo_piscina_numero UNIQUE (piscina_id, numero_ciclo),
    CONSTRAINT fk_ciclo_piscina
        FOREIGN KEY (piscina_id) REFERENCES piscinas(id),
    CONSTRAINT chk_ciclo_numero CHECK (numero_ciclo >= 1),
    CONSTRAINT chk_ciclo_fechas CHECK (
        fecha_cosecha IS NULL
        OR fecha_siembra IS NULL
        OR fecha_cosecha >= fecha_siembra
    ),
    INDEX ix_ciclo_estado (estado)
) ENGINE = InnoDB;

CREATE OR REPLACE VIEW vista_piscinas_ciclo_actual AS
SELECT
    p.id AS piscina_id,
    f.nombre AS finca,
    m.codigo AS modulo,
    p.codigo AS piscina,
    p.tipo,
    p.area_m2,
    p.estado AS piscina_activa,
    c.id AS ciclo_id,
    c.numero_ciclo,
    c.estado AS estado_ciclo,
    CASE
        WHEN c.numero_ciclo IS NULL THEN p.codigo
        ELSE CONCAT(p.codigo, '-', c.numero_ciclo)
    END AS codigo_productivo
FROM piscinas AS p
LEFT JOIN modulos AS m
    ON m.id = p.modulo_id
LEFT JOIN fincas AS f
    ON f.id = m.finca_id
LEFT JOIN ciclos_piscina AS c
    ON c.piscina_id = p.id
   AND c.numero_ciclo = (
       SELECT MAX(c2.numero_ciclo)
       FROM ciclos_piscina AS c2
       WHERE c2.piscina_id = p.id
   );

-- Verificación del paso 1B.
SELECT TABLE_NAME
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'pacific_gold'
  AND TABLE_NAME IN ('fincas', 'modulos', 'piscinas', 'ciclos_piscina')
ORDER BY TABLE_NAME;

