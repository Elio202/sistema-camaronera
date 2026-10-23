-- PASO 11: Eliminar la columna observaciones de los ciclos de piscina.
-- Ejecutar en HeidiSQL conectado como root@localhost.
-- Esta acción elimina definitivamente los textos guardados en esa columna.

USE pacific_gold;

ALTER TABLE ciclos_piscina
    DROP COLUMN IF EXISTS observaciones;

-- Verificación: el resultado debe ser cero.
SELECT COUNT(*) AS columna_observaciones
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'pacific_gold'
  AND TABLE_NAME = 'ciclos_piscina'
  AND COLUMN_NAME = 'observaciones';
