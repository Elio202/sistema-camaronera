-- PASO 7: Cargar el catálogo activo de alimentos de OROPSA 2026.
-- Fuente: CONCENTRADO OROPSA 2026.xlsx.
-- Se importan únicamente los 12 productos marcados como Activo.
-- La carga no modifica el archivo original ni altera el stock existente.
-- Ejecutar en HeidiSQL conectado a la base pacific_gold.

USE pacific_gold;

START TRANSACTION;

INSERT INTO productos_alimento (
    codigo,
    nombre,
    marca,
    unidad,
    stock_actual,
    stock_minimo,
    estado
)
VALUES
    ('PLR00001', 'Zeigler Raceway 40% 600-850', 'ZEIGLER', 'lb', 0, 0, TRUE),
    ('ARE00005', 'Areca Nutrimax 35% 1.2 pellet', 'ARECA', 'lb', 0, 0, TRUE),
    ('ARE00013', 'ARECA 40% 500 - 1200', 'ARECA', 'lb', 0, 0, TRUE),
    ('INT00009', 'Areca Intriago 25% 1.8 pellet', 'ARECA', 'lb', 0, 0, TRUE),
    ('LOR00008', 'Lorica #2 35% 1.2 pellet', 'SKRETTING', 'lb', 0, 0, TRUE),
    ('NIC00005', 'Nicovita Terap 0.8 35%', 'NICOVITA', 'lb', 0, 0, TRUE),
    ('NIC00008', 'Nicovita 45% 0.3 pellet', 'NICOVITA', 'lb', 0, 0, TRUE),
    ('NUT00003', 'Areca Nutrimax 35% 1.8 pellet', 'ARECA', 'lb', 0, 0, TRUE),
    ('OPT00010', 'Skretting Optiline 35% 1.8 pellet', 'SKRETTING', 'lb', 0, 0, TRUE),
    ('XTR00004', 'XtruDix 42% 0.8 mm', 'VIMIFOS', 'lb', 0, 0, TRUE),
    ('LOR00011', 'Lorica #2 42% 900-1200 pellet', 'SKRETTING', 'lb', 0, 0, TRUE),
    ('ARE00026', 'Areca Nutrimax 40% 1.2 x 1.2 mm Extruido', 'ARECA', 'lb', 0, 0, TRUE)
ON DUPLICATE KEY UPDATE
    nombre = VALUES(nombre),
    marca = VALUES(marca),
    unidad = VALUES(unidad),
    estado = TRUE;

COMMIT;

-- Verificación: deben aparecer 12 productos del catálogo activo.
SELECT
    codigo,
    nombre,
    marca,
    unidad,
    stock_actual,
    stock_minimo,
    estado
FROM productos_alimento
WHERE codigo IN (
    'PLR00001', 'ARE00005', 'ARE00013', 'INT00009',
    'LOR00008', 'NIC00005', 'NIC00008', 'NUT00003',
    'OPT00010', 'XTR00004', 'LOR00011', 'ARE00026'
)
ORDER BY marca, nombre;

SELECT COUNT(*) AS productos_activos_importados
FROM productos_alimento
WHERE estado = TRUE
  AND codigo IN (
      'PLR00001', 'ARE00005', 'ARE00013', 'INT00009',
      'LOR00008', 'NIC00005', 'NIC00008', 'NUT00003',
      'OPT00010', 'XTR00004', 'LOR00011', 'ARE00026'
  );
