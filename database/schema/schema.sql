-- ESQUEMA COMPLETO PARA UNA INSTALACIÓN NUEVA (Railway / MySQL 8 o MariaDB).
-- Consolida mariadb_schema.sql, 01, 01b (vista), 03, 05, 06, 09, 10 y 11 en un solo paso.
-- Se ejecuta sobre la base ya seleccionada (no usa USE ni CREATE DATABASE).
-- No carga piscinas, colaboradores ni datos demo.

CREATE TABLE IF NOT EXISTS roles (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(60) NOT NULL UNIQUE,
  descripcion VARCHAR(255),
  estado BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS permisos (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  modulo VARCHAR(60) NOT NULL,
  funcion VARCHAR(60) NOT NULL,
  UNIQUE KEY uq_permiso (modulo, funcion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS rol_permisos (
  rol_id INT UNSIGNED NOT NULL,
  permiso_id INT UNSIGNED NOT NULL,
  PRIMARY KEY (rol_id, permiso_id),
  CONSTRAINT fk_rp_rol FOREIGN KEY (rol_id) REFERENCES roles(id),
  CONSTRAINT fk_rp_permiso FOREIGN KEY (permiso_id) REFERENCES permisos(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS usuarios (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  nombre_usuario VARCHAR(50) NOT NULL UNIQUE,
  nombre VARCHAR(120) NOT NULL,
  correo VARCHAR(150) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  rol_id INT UNSIGNED NOT NULL,
  estado BOOLEAN NOT NULL DEFAULT TRUE,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_usuario_rol FOREIGN KEY (rol_id) REFERENCES roles(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sesiones (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  token_hash CHAR(64) NOT NULL UNIQUE,
  usuario_id INT UNSIGNED NOT NULL,
  fecha_inicio DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_fin DATETIME NULL,
  expira_en DATETIME NOT NULL,
  CONSTRAINT fk_sesion_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
  INDEX ix_sesion_expira (expira_en)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recuperaciones_password (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  usuario_id INT UNSIGNED NOT NULL,
  token_hash CHAR(64) NOT NULL UNIQUE,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expira_en DATETIME NOT NULL,
  utilizado_en DATETIME NULL,
  CONSTRAINT fk_recuperacion_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
  INDEX ix_recuperacion_expira (expira_en)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS fincas (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(80) NOT NULL,
  estado BOOLEAN NOT NULL DEFAULT TRUE,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_finca_nombre UNIQUE (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS modulos (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  finca_id INT UNSIGNED NOT NULL,
  codigo VARCHAR(20) NOT NULL,
  estado BOOLEAN NOT NULL DEFAULT TRUE,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_modulo_codigo UNIQUE (codigo),
  CONSTRAINT fk_modulo_finca FOREIGN KEY (finca_id) REFERENCES fincas(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
  CONSTRAINT fk_piscina_modulo FOREIGN KEY (modulo_id) REFERENCES modulos(id),
  INDEX ix_piscina_modulo (modulo_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ciclos_piscina (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  piscina_id INT UNSIGNED NOT NULL,
  numero_ciclo INT UNSIGNED NOT NULL,
  estado ENUM('Planificado', 'Sembrado', 'Cosechado', 'Cancelado') NOT NULL DEFAULT 'Planificado',
  fecha_siembra DATE NULL,
  fecha_cosecha DATE NULL,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT uq_ciclo_piscina_numero UNIQUE (piscina_id, numero_ciclo),
  CONSTRAINT fk_ciclo_piscina FOREIGN KEY (piscina_id) REFERENCES piscinas(id),
  CONSTRAINT chk_ciclo_numero CHECK (numero_ciclo >= 1),
  CONSTRAINT chk_ciclo_fechas CHECK (fecha_cosecha IS NULL OR fecha_siembra IS NULL OR fecha_cosecha >= fecha_siembra),
  INDEX ix_ciclo_estado (estado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Incluye fecha_ingreso y fecha_baja (paso 03).
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Incluye horario de inicio/fin y los estados ampliados (paso 06).
CREATE TABLE IF NOT EXISTS actividades (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  colaborador_id INT UNSIGNED NOT NULL,
  piscina_id INT UNSIGNED NULL,
  descripcion VARCHAR(300) NOT NULL,
  fecha_inicio DATETIME NULL,
  fecha_fin DATETIME NULL,
  fecha_limite DATETIME NOT NULL,
  estado ENUM('Pendiente', 'En proceso', 'Realizada', 'Vencida', 'Cancelada') NOT NULL DEFAULT 'Pendiente',
  usuario_asigna INT UNSIGNED NOT NULL,
  realizada_en DATETIME NULL,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_actividad_colaborador FOREIGN KEY (colaborador_id) REFERENCES colaboradores(id),
  CONSTRAINT fk_actividad_piscina FOREIGN KEY (piscina_id) REFERENCES piscinas(id),
  CONSTRAINT fk_actividad_usuario FOREIGN KEY (usuario_asigna) REFERENCES usuarios(id),
  INDEX ix_actividad_estado_fecha (estado, fecha_limite)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
  CONSTRAINT fk_movimiento_producto FOREIGN KEY (producto_id) REFERENCES productos_alimento(id),
  CONSTRAINT fk_movimiento_piscina FOREIGN KEY (piscina_id) REFERENCES piscinas(id),
  CONSTRAINT fk_movimiento_responsable FOREIGN KEY (responsable_id) REFERENCES colaboradores(id),
  CONSTRAINT fk_movimiento_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
  CONSTRAINT chk_movimiento_cantidad CHECK (cantidad > 0),
  INDEX ix_movimiento_producto_fecha (producto_id, creado_en),
  INDEX ix_movimiento_piscina (piscina_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Alertas centralizadas (paso 09).
CREATE TABLE IF NOT EXISTS alertas (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  modulo VARCHAR(40) NOT NULL,
  referencia_id BIGINT UNSIGNED NOT NULL,
  clave VARCHAR(50) NOT NULL,
  titulo VARCHAR(150) NOT NULL,
  descripcion VARCHAR(300) NOT NULL,
  nivel ENUM('Informativa', 'Advertencia', 'Crítica') NOT NULL DEFAULT 'Advertencia',
  estado ENUM('Pendiente', 'Atendida', 'Resuelta') NOT NULL DEFAULT 'Pendiente',
  generada_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atendida_en DATETIME NULL,
  atendida_por INT UNSIGNED NULL,
  resuelta_en DATETIME NULL,
  CONSTRAINT fk_alerta_usuario FOREIGN KEY (atendida_por) REFERENCES usuarios(id),
  INDEX ix_alerta_estado_fecha (estado, generada_en),
  INDEX ix_alerta_origen (modulo, clave, referencia_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Calidad del agua (paso 10).
CREATE TABLE IF NOT EXISTS rangos_calidad_agua (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  parametro VARCHAR(40) NOT NULL,
  unidad VARCHAR(20) NOT NULL,
  minimo DECIMAL(10, 2) NOT NULL,
  maximo DECIMAL(10, 2) NOT NULL,
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  actualizado DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT uq_rango_calidad_parametro UNIQUE (parametro),
  CONSTRAINT chk_rango_calidad_valores CHECK (minimo <= maximo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS mediciones_calidad_agua (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  piscina_id INT UNSIGNED NOT NULL,
  resp_id INT UNSIGNED NOT NULL,
  usuario_id INT UNSIGNED NOT NULL,
  fecha DATETIME NOT NULL,
  oxigeno DECIMAL(6, 2) NOT NULL,
  temp DECIMAL(6, 2) NOT NULL,
  ph DECIMAL(4, 2) NOT NULL,
  salinidad DECIMAL(6, 2) NOT NULL,
  notas VARCHAR(300) NULL,
  creado DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_medicion_calidad_piscina FOREIGN KEY (piscina_id) REFERENCES piscinas(id),
  CONSTRAINT fk_medicion_calidad_responsable FOREIGN KEY (resp_id) REFERENCES colaboradores(id),
  CONSTRAINT fk_medicion_calidad_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
  CONSTRAINT chk_medicion_oxigeno CHECK (oxigeno >= 0),
  CONSTRAINT chk_medicion_temperatura CHECK (temp >= 0),
  CONSTRAINT chk_medicion_ph CHECK (ph BETWEEN 0 AND 14),
  CONSTRAINT chk_medicion_salinidad CHECK (salinidad >= 0),
  INDEX ix_medicion_calidad_piscina_fecha (piscina_id, fecha),
  INDEX ix_medicion_calidad_fecha (fecha),
  INDEX ix_medicion_calidad_responsable (resp_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO rangos_calidad_agua (parametro, unidad, minimo, maximo, activo) VALUES
  ('Oxígeno disuelto', 'mg/L', 4.00, 8.00, TRUE),
  ('Temperatura', '°C', 26.00, 32.00, TRUE),
  ('pH', 'pH', 7.50, 8.50, TRUE),
  ('Salinidad', 'ppt', 10.00, 35.00, TRUE)
ON DUPLICATE KEY UPDATE unidad = VALUES(unidad);

CREATE OR REPLACE VIEW vista_piscinas_ciclo_actual AS
SELECT
  p.id AS piscina_id,
  f.nombre AS finca,
  m.codigo AS modulo,
  p.codigo AS piscina,
  p.tipo,
  p.area_m2,
  p.estado AS piscina_activa,
  c.id AS ciclo_id,
  c.numero_ciclo,
  c.estado AS estado_ciclo,
  CASE WHEN c.numero_ciclo IS NULL THEN p.codigo ELSE CONCAT(p.codigo, '-', c.numero_ciclo) END AS codigo_productivo
FROM piscinas AS p
LEFT JOIN modulos AS m ON m.id = p.modulo_id
LEFT JOIN fincas AS f ON f.id = m.finca_id
LEFT JOIN ciclos_piscina AS c
  ON c.piscina_id = p.id
 AND c.numero_ciclo = (SELECT MAX(c2.numero_ciclo) FROM ciclos_piscina AS c2 WHERE c2.piscina_id = p.id);

-- Roles base (los mismos id 1-5 que usa init_mariadb() en server.py).
INSERT IGNORE INTO roles (id, nombre, descripcion) VALUES
  (1, 'Administrador', 'Configuración y acceso total'),
  (2, 'Jefe de producción', 'Supervisión integral de la operación'),
  (3, 'Encargado de piscina', 'Operación de piscinas asignadas'),
  (4, 'Técnico de calidad', 'Control de parámetros del agua'),
  (5, 'Gerencia', 'Consulta de indicadores y reportes');

-- Permisos de los módulos reales (paso 05).
INSERT IGNORE INTO permisos (modulo, funcion) VALUES
  ('piscinas', 'ver'), ('piscinas', 'crear'), ('piscinas', 'editar'), ('piscinas', 'cambiar_estado'),
  ('personal', 'ver'), ('personal', 'crear'), ('personal', 'editar'), ('personal', 'cambiar_estado'),
  ('personal', 'asignar'), ('personal', 'confirmar'),
  ('inventario', 'ver'), ('inventario', 'registrar');

INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id FROM roles AS r JOIN permisos AS p
  ON p.modulo = 'piscinas'
  OR (p.modulo = 'personal' AND p.funcion IN ('ver', 'asignar', 'confirmar'))
  OR (p.modulo = 'inventario' AND p.funcion = 'ver')
WHERE r.nombre = 'Jefe de producción';

INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id FROM roles AS r JOIN permisos AS p
  ON (p.modulo = 'piscinas' AND p.funcion = 'ver')
  OR (p.modulo = 'personal' AND p.funcion IN ('ver', 'confirmar'))
  OR p.modulo = 'inventario'
WHERE r.nombre = 'Encargado de piscina';

INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id FROM roles AS r JOIN permisos AS p
  ON p.modulo = 'piscinas' AND p.funcion = 'ver'
WHERE r.nombre = 'Técnico de calidad';

INSERT IGNORE INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id FROM roles AS r JOIN permisos AS p
  ON p.modulo IN ('piscinas', 'personal', 'inventario') AND p.funcion = 'ver'
WHERE r.nombre = 'Gerencia';
-- El rol 6 (Encargado de Bodega), los permisos de alertas y todos los del Administrador
-- los crea init_mariadb() al iniciar el servidor.
