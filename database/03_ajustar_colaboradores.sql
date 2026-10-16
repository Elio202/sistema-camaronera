-- PASO 3: Agregar fechas laborales al catálogo de colaboradores.
-- Ejecutar en HeidiSQL conectado como root@localhost.
-- No carga empleados y no elimina datos existentes.

USE pacific_gold;

DELIMITER //

DROP PROCEDURE IF EXISTS ajustar_fechas_colaboradores//
CREATE PROCEDURE ajustar_fechas_colaboradores()
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = 'pacific_gold'
          AND TABLE_NAME = 'colaboradores'
          AND COLUMN_NAME = 'fecha_ingreso'
    ) THEN
        ALTER TABLE colaboradores
            ADD COLUMN fecha_ingreso DATE NULL AFTER puesto;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = 'pacific_gold'
          AND TABLE_NAME = 'colaboradores'
          AND COLUMN_NAME = 'fecha_baja'
    ) THEN
        ALTER TABLE colaboradores
            ADD COLUMN fecha_baja DATE NULL AFTER fecha_ingreso;
    END IF;
END//

CALL ajustar_fechas_colaboradores()//
DROP PROCEDURE ajustar_fechas_colaboradores//

DELIMITER ;

-- Verificación del paso 3: deben aparecer fecha_ingreso y fecha_baja.
SELECT
    COLUMN_NAME,
    COLUMN_TYPE,
    IS_NULLABLE
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'pacific_gold'
  AND TABLE_NAME = 'colaboradores'
  AND COLUMN_NAME IN ('fecha_ingreso', 'fecha_baja')
ORDER BY ORDINAL_POSITION;

