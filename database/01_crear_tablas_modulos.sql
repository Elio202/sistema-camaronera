-- PASO 1: Crear únicamente la estructura de los módulos.
-- Ejecutar en HeidiSQL conectado como root@localhost.

USE pacific_gold;

CREATE TABLE IF NOT EXISTS fincas (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(80) NOT NULL,
    estado BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_finca_nombre UNIQUE (nombre)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS modulos (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    finca_id INT UNSIGNED NOT NULL,
    codigo VARCHAR(20) NOT NULL,
    estado BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_modulo_codigo UNIQUE (codigo),
    CONSTRAINT fk_modulo_finca
        FOREIGN KEY (finca_id) REFERENCES fincas(id)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS piscinas (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    modulo_id INT UNSIGNED NOT NULL,
    codigo VARCHAR(20) NOT NULL,
    tipo ENUM('Engorde', 'Precría') NOT NULL,
    area_m2 DECIMAL(10, 2) NOT NULL,
    estado BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_piscina_codigo UNIQUE (codigo),
    CONSTRAINT chk_piscina_area CHECK (area_m2 > 0),
    CONSTRAINT fk_piscina_modulo
        FOREIGN KEY (modulo_id) REFERENCES modulos(id),
    INDEX ix_piscina_modulo (modulo_id)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS ciclos_piscina (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    piscina_id INT UNSIGNED NOT NULL,
    numero_ciclo INT UNSIGNED NOT NULL,
    estado ENUM('Planificado', 'Sembrado', 'Cosechado', 'Cancelado')
        NOT NULL DEFAULT 'Planificado',
    fecha_siembra DATE NULL,
    fecha_cosecha DATE NULL,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_ciclo_piscina_numero UNIQUE (piscina_id, numero_ciclo),
    CONSTRAINT fk_ciclo_piscina
        FOREIGN KEY (piscina_id) REFERENCES piscinas(id),
    CONSTRAINT chk_ciclo_numero CHECK (numero_ciclo >= 1),
    CONSTRAINT chk_ciclo_fechas CHECK (
        fecha_cosecha IS NULL
        OR fecha_siembra IS NULL
        OR fecha_cosecha >= fecha_siembra
    ),
    INDEX ix_ciclo_estado (estado)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS colaboradores (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    codigo_empleado VARCHAR(30) NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    puesto VARCHAR(100) NOT NULL,
    fecha_ingreso DATE NULL,
    fecha_baja DATE NULL,
    celular VARCHAR(20) NULL,
    estado BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_colaborador_codigo UNIQUE (codigo_empleado)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS actividades (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    colaborador_id INT UNSIGNED NOT NULL,
    piscina_id INT UNSIGNED NOT NULL,
    descripcion VARCHAR(300) NOT NULL,
    fecha_limite DATETIME NOT NULL,
    estado ENUM('Pendiente', 'Realizada', 'Vencida') NOT NULL DEFAULT 'Pendiente',
    usuario_asigna INT UNSIGNED NOT NULL,
    realizada_en DATETIME NULL,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_actividad_colaborador
        FOREIGN KEY (colaborador_id) REFERENCES colaboradores(id),
    CONSTRAINT fk_actividad_piscina
        FOREIGN KEY (piscina_id) REFERENCES piscinas(id),
    CONSTRAINT fk_actividad_usuario
        FOREIGN KEY (usuario_asigna) REFERENCES usuarios(id),
    INDEX ix_actividad_estado_fecha (estado, fecha_limite)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS productos_alimento (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(30) NOT NULL,
    nombre VARCHAR(120) NOT NULL,
    marca VARCHAR(80) NOT NULL,
    unidad VARCHAR(20) NOT NULL DEFAULT 'kg',
    stock_actual DECIMAL(12, 2) NOT NULL DEFAULT 0,
    stock_minimo DECIMAL(12, 2) NOT NULL DEFAULT 0,
    estado BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_producto_codigo UNIQUE (codigo),
    CONSTRAINT chk_producto_stock CHECK (stock_actual >= 0),
    CONSTRAINT chk_producto_minimo CHECK (stock_minimo >= 0)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS movimientos_inventario (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    producto_id INT UNSIGNED NOT NULL,
    tipo ENUM('Entrada', 'Salida') NOT NULL,
    cantidad DECIMAL(12, 2) NOT NULL,
    piscina_id INT UNSIGNED NULL,
    lote VARCHAR(50) NULL,
    fecha_vencimiento DATE NULL,
    responsable_id INT UNSIGNED NULL,
    usuario_id INT UNSIGNED NOT NULL,
    observacion VARCHAR(255) NULL,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_movimiento_producto
        FOREIGN KEY (producto_id) REFERENCES productos_alimento(id),
    CONSTRAINT fk_movimiento_piscina
        FOREIGN KEY (piscina_id) REFERENCES piscinas(id),
    CONSTRAINT fk_movimiento_responsable
        FOREIGN KEY (responsable_id) REFERENCES colaboradores(id),
    CONSTRAINT fk_movimiento_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    CONSTRAINT chk_movimiento_cantidad CHECK (cantidad > 0),
    INDEX ix_movimiento_producto_fecha (producto_id, creado_en),
    INDEX ix_movimiento_piscina (piscina_id)
) ENGINE = InnoDB;

-- Verificación del paso 1.
SELECT TABLE_NAME
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'pacific_gold'
  AND TABLE_NAME IN (
      'piscinas',
      'fincas',
      'modulos',
      'ciclos_piscina',
      'colaboradores',
      'actividades',
      'productos_alimento',
      'movimientos_inventario'
  )
ORDER BY TABLE_NAME;
