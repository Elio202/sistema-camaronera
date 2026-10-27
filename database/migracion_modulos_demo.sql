-- ARCHIVO REEMPLAZADO.
-- Para evitar ejecuciones parciales, utilizar en este orden:
--   1. 01_crear_tablas_modulos.sql
--   2. 02_cargar_datos_demo.sql

USE pacific_gold;

CREATE TABLE IF NOT EXISTS piscinas (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  codigo VARCHAR(20) NOT NULL UNIQUE,
  nombre VARCHAR(80) NOT NULL,
  tipo ENUM('Engorde','Precría') NOT NULL,
  area_m2 DECIMAL(10,2) NOT NULL,
  estado BOOLEAN NOT NULL DEFAULT TRUE,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS colaboradores (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  codigo_empleado VARCHAR(30) NOT NULL UNIQUE,
  nombre VARCHAR(150) NOT NULL,
  puesto VARCHAR(100) NOT NULL,
  celular VARCHAR(20),
  estado BOOLEAN NOT NULL DEFAULT TRUE,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS actividades (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  colaborador_id INT UNSIGNED NOT NULL,
  piscina_id INT UNSIGNED NULL,
  descripcion VARCHAR(300) NOT NULL,
  fecha_limite DATETIME NOT NULL,
  estado ENUM('Pendiente','Realizada','Vencida') NOT NULL DEFAULT 'Pendiente',
  usuario_asigna INT UNSIGNED NOT NULL,
  realizada_en DATETIME NULL,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_actividad_colaborador FOREIGN KEY (colaborador_id) REFERENCES colaboradores(id),
  CONSTRAINT fk_actividad_piscina FOREIGN KEY (piscina_id) REFERENCES piscinas(id),
  CONSTRAINT fk_actividad_usuario FOREIGN KEY (usuario_asigna) REFERENCES usuarios(id),
  INDEX ix_actividad_estado_fecha (estado, fecha_limite)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS productos_alimento (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  codigo VARCHAR(30) NOT NULL UNIQUE,
  nombre VARCHAR(120) NOT NULL,
  marca VARCHAR(80) NOT NULL,
  unidad VARCHAR(20) NOT NULL DEFAULT 'kg',
  stock_actual DECIMAL(12,2) NOT NULL DEFAULT 0,
  stock_minimo DECIMAL(12,2) NOT NULL DEFAULT 0,
  estado BOOLEAN NOT NULL DEFAULT TRUE,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS movimientos_inventario (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  producto_id INT UNSIGNED NOT NULL,
  tipo ENUM('Entrada','Salida') NOT NULL,
  cantidad DECIMAL(12,2) NOT NULL,
  piscina_id INT UNSIGNED NULL,
  lote VARCHAR(50) NULL,
  fecha_vencimiento DATE NULL,
  responsable_id INT UNSIGNED NULL,
  usuario_id INT UNSIGNED NOT NULL,
  observacion VARCHAR(255) NULL,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_mov_producto FOREIGN KEY (producto_id) REFERENCES productos_alimento(id),
  CONSTRAINT fk_mov_piscina FOREIGN KEY (piscina_id) REFERENCES piscinas(id),
  CONSTRAINT fk_mov_responsable FOREIGN KEY (responsable_id) REFERENCES colaboradores(id),
  CONSTRAINT fk_mov_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
  INDEX ix_mov_producto_fecha (producto_id, creado_en)
) ENGINE=InnoDB;

INSERT IGNORE INTO permisos(modulo,funcion) VALUES
('piscinas','ver'),('piscinas','crear'),('piscinas','editar'),('piscinas','cambiar_estado'),
('personal','crear'),('personal','editar'),('personal','cambiar_estado');

INSERT IGNORE INTO rol_permisos
SELECT 1,id FROM permisos WHERE modulo IN ('piscinas','personal','inventario');

INSERT IGNORE INTO rol_permisos
SELECT 2,id FROM permisos WHERE modulo='piscinas' OR (modulo='personal' AND funcion IN ('ver','asignar','confirmar')) OR (modulo='inventario' AND funcion='ver');

INSERT IGNORE INTO rol_permisos
SELECT 3,id FROM permisos WHERE modulo='piscinas' AND funcion='ver' OR modulo='personal' AND funcion IN ('ver','confirmar') OR modulo='inventario';

INSERT IGNORE INTO rol_permisos
SELECT 4,id FROM permisos WHERE modulo='piscinas' AND funcion='ver';

INSERT IGNORE INTO rol_permisos
SELECT 5,id FROM permisos WHERE funcion='ver' AND modulo IN ('piscinas','personal','inventario');

INSERT IGNORE INTO piscinas(codigo,nombre,tipo,area_m2) VALUES
('ENG-01','Piscina Engorde Norte','Engorde',350.00),
('ENG-02','Piscina Engorde Sur','Engorde',320.00),
('PRE-01','Piscina Precría Uno','Precría',180.00);

INSERT IGNORE INTO colaboradores(codigo_empleado,nombre,puesto,celular) VALUES
('DEM-001','Carlos Méndez','Encargado de piscina','5550-1001'),
('DEM-002','Ana López','Técnico de calidad','5550-1002'),
('DEM-003','José Ramírez','Auxiliar de producción','5550-1003'),
('DEM-004','María González','Encargada de bodega','5550-1004');

INSERT IGNORE INTO productos_alimento(codigo,nombre,marca,unidad,stock_actual,stock_minimo) VALUES
('ALI-001','Alimento iniciador 35%','DemoMar','kg',500,100),
('ALI-002','Alimento crecimiento 30%','DemoMar','kg',800,150),
('ALI-003','Alimento engorde 28%','AquaDemo','kg',1000,200);
