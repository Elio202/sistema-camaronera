-- PASO 14: Registrar el estado de las alertas del sensor enviadas por WhatsApp.
-- Permite repetir avisos cada dos horas sin enviar mensajes duplicados.

CREATE TABLE IF NOT EXISTS avisos_sensor (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    sensor VARCHAR(100) NOT NULL,
    tipo ENUM('Temperatura', 'Conexion', 'Bateria') NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    valor VARCHAR(50) NULL,
    ult_env DATETIME NULL,
    creado DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_aviso_sensor_tipo UNIQUE (sensor, tipo),
    INDEX ix_aviso_sensor_activo (activo, ult_env)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'avisos_sensor'
ORDER BY ORDINAL_POSITION;
