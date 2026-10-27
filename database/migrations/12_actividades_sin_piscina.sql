-- PASO 12: Permitir actividades de trabajos varios sin piscina asociada.
-- Ejecutar en HeidiSQL sobre cada base existente antes de publicar este cambio.
-- Seleccione primero la base correspondiente (pacific_gold en local o la base
-- configurada en el servidor). No requiere eliminar ni recrear registros.

ALTER TABLE actividades
    MODIFY COLUMN piscina_id INT UNSIGNED NULL;

-- Verificación: IS_NULLABLE debe mostrar YES.
SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'actividades'
  AND COLUMN_NAME = 'piscina_id';
