-- PASO 5: Consolidar permisos de módulos reales sin insertar datos demo.
-- Ejecutar en HeidiSQL conectado como root@localhost.

USE pacific_gold;

INSERT IGNORE INTO permisos (modulo, funcion) VALUES
    ('piscinas', 'ver'),
    ('piscinas', 'crear'),
    ('piscinas', 'editar'),
    ('piscinas', 'cambiar_estado'),
    ('personal', 'ver'),
    ('personal', 'crear'),
    ('personal', 'editar'),
    ('personal', 'cambiar_estado'),
    ('personal', 'asignar'),
    ('personal', 'confirmar'),
    ('inventario', 'ver'),
    ('inventario', 'registrar');

-- Administrador: todos los permisos existentes.
INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles AS r
CROSS JOIN permisos AS p
WHERE r.nombre = 'Administrador';

-- Jefe de producción: piscinas, seguimiento de personal e inventario de consulta.
INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles AS r
JOIN permisos AS p
  ON p.modulo = 'piscinas'
  OR (p.modulo = 'personal' AND p.funcion IN ('ver', 'asignar', 'confirmar'))
  OR (p.modulo = 'inventario' AND p.funcion = 'ver')
WHERE r.nombre = 'Jefe de producción';

-- Encargado de piscina: consulta y confirmación de actividades.
INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles AS r
JOIN permisos AS p
  ON (p.modulo = 'piscinas' AND p.funcion = 'ver')
  OR (p.modulo = 'personal' AND p.funcion IN ('ver', 'confirmar'))
  OR p.modulo = 'inventario'
WHERE r.nombre = 'Encargado de piscina';

-- Técnico de calidad: consulta de piscinas.
INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles AS r
JOIN permisos AS p
  ON p.modulo = 'piscinas' AND p.funcion = 'ver'
WHERE r.nombre = 'Técnico de calidad';

-- Gerencia: consulta de los módulos operativos.
INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles AS r
JOIN permisos AS p
  ON p.modulo IN ('piscinas', 'personal', 'inventario')
 AND p.funcion = 'ver'
WHERE r.nombre = 'Gerencia';

SELECT
    r.nombre AS rol,
    p.modulo,
    p.funcion
FROM roles AS r
JOIN rol_permisos AS rp ON rp.rol_id = r.id
JOIN permisos AS p ON p.id = rp.permiso_id
WHERE p.modulo IN ('piscinas', 'personal', 'inventario')
ORDER BY r.nombre, p.modulo, p.funcion;

