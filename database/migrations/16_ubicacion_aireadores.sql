-- PASO 16: Guardar la ubicación visual de los aireadores dentro de la piscina.
-- Las coordenadas son porcentajes relativos al plano circular (0 a 100).

USE pacific_gold;

ALTER TABLE aireadores
    ADD COLUMN IF NOT EXISTS pos_x DECIMAL(5,2) NULL AFTER umbral_apa,
    ADD COLUMN IF NOT EXISTS pos_y DECIMAL(5,2) NULL AFTER pos_x;

SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'aireadores'
  AND COLUMN_NAME IN ('pos_x', 'pos_y')
ORDER BY ORDINAL_POSITION;
