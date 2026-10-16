-- PASO 2: Ejecutar solamente después de verificar las cinco tablas del paso 1.
USE pacific_gold;

INSERT IGNORE INTO permisos (modulo, funcion) VALUES
    ('piscinas', 'ver'),
    ('piscinas', 'crear'),
    ('piscinas', 'editar'),
    ('piscinas', 'cambiar_estado'),
    ('personal', 'crear'),
    ('personal', 'editar'),
    ('personal', 'cambiar_estado');

INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT 1, id
FROM permisos
WHERE modulo IN ('piscinas', 'personal', 'inventario');

INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT 2, id
FROM permisos
WHERE modulo = 'piscinas'
   OR (modulo = 'personal' AND funcion IN ('ver', 'asignar', 'confirmar'))
   OR (modulo = 'inventario' AND funcion = 'ver');

INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT 3, id
FROM permisos
WHERE (modulo = 'piscinas' AND funcion = 'ver')
   OR (modulo = 'personal' AND funcion IN ('ver', 'confirmar'))
   OR modulo = 'inventario';

INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT 4, id
FROM permisos
WHERE modulo = 'piscinas'
  AND funcion = 'ver';

INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT 5, id
FROM permisos
WHERE modulo IN ('piscinas', 'personal', 'inventario')
  AND funcion = 'ver';

INSERT IGNORE INTO piscinas (codigo, nombre, tipo, area_m2) VALUES
    ('ENG-01', 'Piscina Engorde Norte', 'Engorde', 350.00),
    ('ENG-02', 'Piscina Engorde Sur', 'Engorde', 320.00),
    ('PRE-01', 'Piscina Precría Uno', 'Precría', 180.00);

INSERT IGNORE INTO colaboradores
    (codigo_empleado, nombre, puesto, celular)
VALUES
    ('DEM-001', 'Carlos Méndez', 'Encargado de piscina', '5550-1001'),
    ('DEM-002', 'Ana López', 'Técnico de calidad', '5550-1002'),
    ('DEM-003', 'José Ramírez', 'Auxiliar de producción', '5550-1003'),
    ('DEM-004', 'María González', 'Encargada de bodega', '5550-1004');

INSERT IGNORE INTO productos_alimento
    (codigo, nombre, marca, unidad, stock_actual, stock_minimo)
VALUES
    ('ALI-001', 'Alimento iniciador 35%', 'DemoMar', 'kg', 500.00, 100.00),
    ('ALI-002', 'Alimento crecimiento 30%', 'DemoMar', 'kg', 800.00, 150.00),
    ('ALI-003', 'Alimento engorde 28%', 'AquaDemo', 'kg', 1000.00, 200.00);

-- Verificación del paso 2.
SELECT 'piscinas' AS tabla, COUNT(*) AS registros FROM piscinas
UNION ALL
SELECT 'colaboradores', COUNT(*) FROM colaboradores
UNION ALL
SELECT 'productos_alimento', COUNT(*) FROM productos_alimento;

