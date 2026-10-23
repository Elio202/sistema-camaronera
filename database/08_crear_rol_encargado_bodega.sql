-- PASO 8: Crear el rol Encargado de Bodega y limitarlo al inventario.
-- Ejecutar en HeidiSQL conectado como root@localhost.
-- La migración es idempotente y puede ejecutarse nuevamente sin duplicar datos.

USE pacific_gold;

START TRANSACTION;

INSERT INTO roles (id, nombre, descripcion, estado)
VALUES (
    6,
    'Encargado de Bodega',
    'Control de entradas y salidas de alimento',
    TRUE
)
ON DUPLICATE KEY UPDATE
    nombre = VALUES(nombre),
    descripcion = VALUES(descripcion),
    estado = TRUE;

INSERT IGNORE INTO permisos (modulo, funcion) VALUES
    ('inventario', 'ver'),
    ('inventario', 'registrar');

-- El rol queda únicamente con los permisos definidos para inventario.
DELETE FROM rol_permisos
WHERE rol_id = 6;

INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT 6, id
FROM permisos
WHERE (modulo = 'inventario' AND funcion IN ('ver', 'registrar'));

COMMIT;

-- Verificación: deben aparecer exactamente dos permisos.
SELECT
    r.id,
    r.nombre AS rol,
    p.modulo,
    p.funcion
FROM roles AS r
JOIN rol_permisos AS rp ON rp.rol_id = r.id
JOIN permisos AS p ON p.id = rp.permiso_id
WHERE r.id = 6
ORDER BY p.modulo, p.funcion;
