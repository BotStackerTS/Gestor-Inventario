# database/connection.py
import sqlite3
from config import DB_NAME

class DatabaseConnection:
    @staticmethod
    def conectar():
        conn = sqlite3.connect(DB_NAME)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    @staticmethod
    def inicializar_base_datos():
        with DatabaseConnection.conectar() as conn:
            cursor = conn.cursor()
            cursor.executescript('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    usuario TEXT UNIQUE NOT NULL, 
                    password_hash TEXT NOT NULL, 
                    rol TEXT NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS inventario (
                    codigo TEXT PRIMARY KEY, 
                    nombre TEXT NOT NULL, 
                    cantidad INTEGER NOT NULL, 
                    precio_base REAL NOT NULL, 
                    precio_final REAL NOT NULL,
                    stock_minimo INTEGER DEFAULT 5
                );

                CREATE TABLE IF NOT EXISTS etiquetas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE NOT NULL
                );

                CREATE TABLE IF NOT EXISTS producto_etiqueta (
                    codigo_articulo TEXT,
                    etiqueta_id INTEGER,
                    PRIMARY KEY (codigo_articulo, etiqueta_id),
                    FOREIGN KEY (codigo_articulo) REFERENCES inventario(codigo) ON DELETE CASCADE,
                    FOREIGN KEY (etiqueta_id) REFERENCES etiquetas(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS promociones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo_articulo TEXT NOT NULL,
                    tipo TEXT NOT NULL, -- Ej: '2X1', 'DESCUENTO_PCT'
                    valor REAL NOT NULL, -- Ej: 50.0 para 50% o 2 para 2x1
                    FOREIGN KEY (codigo_articulo) REFERENCES inventario(codigo) ON DELETE CASCADE
                );
                
                CREATE TABLE IF NOT EXISTS ventas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    total REAL NOT NULL, 
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS detalle_venta (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    venta_id INTEGER NOT NULL, 
                    codigo_articulo TEXT NOT NULL, 
                    cantidad INTEGER NOT NULL, 
                    subtotal REAL NOT NULL,
                    FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE,
                    FOREIGN KEY (codigo_articulo) REFERENCES inventario(codigo)
                );
            ''')
            conn.commit()