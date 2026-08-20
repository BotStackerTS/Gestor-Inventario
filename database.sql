-- Creación de tablas principales
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    rol TEXT DEFAULT 'admin'
);

CREATE TABLE IF NOT EXISTS inventario (
    codigo TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    cantidad INTEGER NOT NULL,
    precio_base REAL NOT NULL,
    precio_final REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS detalle_venta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id INTEGER,
    codigo_articulo TEXT,
    cantidad INTEGER,
    subtotal REAL,
    FOREIGN KEY(venta_id) REFERENCES ventas(id),
    FOREIGN KEY(codigo_articulo) REFERENCES inventario(codigo)
);