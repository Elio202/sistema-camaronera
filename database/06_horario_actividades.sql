-- PASO 6: Agregar horario de inicio y finalización a las actividades.
-- Conserva fecha_limite para compatibilidad con los registros anteriores.
-- Ejecutar una sola vez en HeidiSQL conectado como root@localhost.

USE pacific_gold;

ALTER TABLE actividades
    ADD COLUMN IF NOT EXISTS fecha_inicio DATETIME NULL AFTER descripcion,
    ADD COLUMN IF NOT EXISTS fecha_fin DATETIME NULL AFTER fecha_inicio;

-- Las actividades anteriores conservan su fecha límite como finalización.
UPDATE actividades
SET fecha_fin = fecha_limite
WHERE fecha_fin IS NULL;

ALTER TABLE actividades
    MODIFY COLUMN estado ENUM(
        'Pendiente',
        'En proceso',
        'Realizada',
        'Vencida',
        'Cancelada'
    ) NOT NULL DEFAULT 'Pendiente';

SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'pacific_gold'
  AND TABLE_NAME = 'actividades'
  AND COLUMN_NAME IN ('fecha_inicio', 'fecha_fin', 'fecha_limite', 'estado')
ORDER BY ORDINAL_POSITION;
