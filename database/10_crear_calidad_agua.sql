-- PASO 10: Crear la estructura del módulo Calidad del agua.
-- Ejecutar en HeidiSQL conectado como root@localhost.
-- No elimina ni modifica los datos existentes.

USE pacific_gold;

CREATE TABLE IF NOT EXISTS rangos_calidad_agua (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    parametro VARCHAR(40) NOT NULL,
    unidad VARCHAR(20) NOT NULL,
    minimo DECIMAL(10, 2) NOT NULL,
    maximo DECIMAL(10, 2) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    actualizado DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_rango_calidad_parametro UNIQUE (parametro),
    CONSTRAINT chk_rango_calidad_valores CHECK (
        minimo <= maximo
    )
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS mediciones_calidad_agua (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    piscina_id INT UNSIGNED NOT NULL,
    resp_id INT UNSIGNED NOT NULL,
    usuario_id INT UNSIGNED NOT NULL,
    fecha DATETIME NOT NULL,
    oxigeno DECIMAL(6, 2) NOT NULL,
    temp DECIMAL(6, 2) NOT NULL,
    ph DECIMAL(4, 2) NOT NULL,
    salinidad DECIMAL(6, 2) NOT NULL,
    notas VARCHAR(300) NULL,
    creado DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_medicion_calidad_piscina
        FOREIGN KEY (piscina_id) REFERENCES piscinas(id),
    CONSTRAINT fk_medicion_calidad_responsable
        FOREIGN KEY (resp_id) REFERENCES colaboradores(id),
    CONSTRAINT fk_medicion_calidad_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    CONSTRAINT chk_medicion_oxigeno CHECK (oxigeno >= 0),
    CONSTRAINT chk_medicion_temperatura CHECK (temp >= 0),
    CONSTRAINT chk_medicion_ph CHECK (ph BETWEEN 0 AND 14),
    CONSTRAINT chk_medicion_salinidad CHECK (salinidad >= 0),
    INDEX ix_medicion_calidad_piscina_fecha (piscina_id, fecha),
    INDEX ix_medicion_calidad_fecha (fecha),
    INDEX ix_medicion_calidad_responsable (resp_id)
) ENGINE = InnoDB;

-- Rangos iniciales configurables. Podrán ajustarse cuando Pacific Gold
-- confirme sus límites operativos oficiales.
INSERT INTO rangos_calidad_agua (
    parametro,
    unidad,
    minimo,
    maximo,
    activo
)
VALUES
    ('Oxígeno disuelto', 'mg/L', 4.00, 8.00, TRUE),
    ('Temperatura', '°C', 26.00, 32.00, TRUE),
    ('pH', 'pH', 7.50, 8.50, TRUE),
    ('Salinidad', 'ppt', 10.00, 35.00, TRUE)
ON DUPLICATE KEY UPDATE
    unidad = VALUES(unidad);

-- Verificación: deben aparecer las dos tablas.
SELECT TABLE_NAME
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'pacific_gold'
  AND TABLE_NAME IN (
      'rangos_calidad_agua',
      'mediciones_calidad_agua'
  )
ORDER BY TABLE_NAME;

-- Verificación: deben aparecer cuatro parámetros configurados.
SELECT
    parametro,
    unidad,
    minimo,
    maximo,
    activo
FROM rangos_calidad_agua
ORDER BY id;
