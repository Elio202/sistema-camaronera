-- PASO 13: Habilitar el permiso de consulta del monitoreo ambiental.
-- No almacena la clave del sensor ni modifica datos operativos.

INSERT IGNORE INTO permisos (modulo, funcion)
VALUES ('monitoreo', 'ver');

INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT id_rol, p.id
FROM (
    SELECT 1 AS id_rol
    UNION ALL SELECT 2
    UNION ALL SELECT 4
    UNION ALL SELECT 5
    UNION ALL SELECT 6
) AS roles_habilitados
INNER JOIN permisos AS p
    ON p.modulo = 'monitoreo'
   AND p.funcion = 'ver';

SELECT r.nombre AS rol, p.modulo, p.funcion
FROM rol_permisos AS rp
INNER JOIN roles AS r ON r.id = rp.rol_id
INNER JOIN permisos AS p ON p.id = rp.permiso_id
WHERE p.modulo = 'monitoreo'
ORDER BY r.id;
