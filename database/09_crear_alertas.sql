-- PASO 9: Crear el módulo central de alertas y configurar sus permisos.
-- Ejecutar en HeidiSQL conectado como root@localhost.
-- Es una migración idempotente: no elimina información existente.

USE pacific_gold;

CREATE TABLE IF NOT EXISTS alertas (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    modulo VARCHAR(40) NOT NULL,
    referencia_id BIGINT UNSIGNED NOT NULL,
    clave VARCHAR(50) NOT NULL,
    titulo VARCHAR(150) NOT NULL,
    descripcion VARCHAR(300) NOT NULL,
    nivel ENUM('Informativa', 'Advertencia', 'Crítica') NOT NULL DEFAULT 'Advertencia',
    estado ENUM('Pendiente', 'Atendida', 'Resuelta') NOT NULL DEFAULT 'Pendiente',
    generada_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atendida_en DATETIME NULL,
    atendida_por INT UNSIGNED NULL,
    resuelta_en DATETIME NULL,
    CONSTRAINT fk_alerta_usuario FOREIGN KEY (atendida_por) REFERENCES usuarios(id),
    INDEX ix_alerta_estado_fecha (estado, generada_en),
    INDEX ix_alerta_origen (modulo, clave, referencia_id)
) ENGINE = InnoDB;

INSERT INTO permisos (modulo, funcion) VALUES ('alertas', 'ver'), ('alertas', 'atender')
ON DUPLICATE KEY UPDATE funcion = VALUES(funcion);

INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT 1, id FROM permisos WHERE modulo = 'alertas';
INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT 2, id FROM permisos WHERE modulo = 'alertas' AND funcion IN ('ver', 'atender');
INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT 3, id FROM permisos WHERE modulo = 'alertas' AND funcion = 'ver';
INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT 4, id FROM permisos WHERE modulo = 'alertas' AND funcion IN ('ver', 'atender');
INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id FROM roles AS r INNER JOIN permisos AS p
    ON p.modulo = 'alertas' AND p.funcion = 'ver' WHERE r.id IN (5, 6);

SELECT p.id, p.modulo, p.funcion, COUNT(rp.rol_id) AS roles_asignados
FROM permisos AS p LEFT JOIN rol_permisos AS rp ON rp.permiso_id = p.id
WHERE p.modulo = 'alertas'
GROUP BY p.id, p.modulo, p.funcion ORDER BY p.funcion;
