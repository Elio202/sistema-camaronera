-- PASO 15: Crear el módulo de monitoreo y control de aireación.
-- Ejecutar en HeidiSQL sobre la base pacific_gold.

USE pacific_gold;

CREATE TABLE IF NOT EXISTS aireadores (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    piscina_id INT UNSIGNED NOT NULL,
    codigo VARCHAR(30) NOT NULL,
    modo ENUM('Manual','Automático') NOT NULL DEFAULT 'Manual',
    encendido BOOLEAN NOT NULL DEFAULT FALSE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    oxigeno DECIMAL(6,2) NULL,
    umbral_enc DECIMAL(6,2) NOT NULL DEFAULT 4.00,
    umbral_apa DECIMAL(6,2) NOT NULL DEFAULT 5.50,
    actualizado DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_aireador_codigo UNIQUE (codigo),
    CONSTRAINT fk_aireador_piscina FOREIGN KEY (piscina_id) REFERENCES piscinas(id),
    CONSTRAINT chk_aireador_umbrales CHECK (umbral_enc >= 0 AND umbral_apa > umbral_enc),
    INDEX ix_aireador_piscina (piscina_id, activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS eventos_aireacion (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    aireador_id INT UNSIGNED NOT NULL,
    usuario_id INT UNSIGNED NOT NULL,
    accion ENUM('Encendido','Apagado','Lectura','Modo') NOT NULL,
    origen ENUM('Manual','Automático') NOT NULL,
    oxigeno DECIMAL(6,2) NULL,
    detalle VARCHAR(200) NULL,
    creado DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_evento_aireador FOREIGN KEY (aireador_id) REFERENCES aireadores(id),
    CONSTRAINT fk_evento_aireacion_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    INDEX ix_evento_aireador_fecha (aireador_id, creado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SELECT TABLE_NAME FROM information_schema.TABLES
WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME IN ('aireadores','eventos_aireacion')
ORDER BY TABLE_NAME;
