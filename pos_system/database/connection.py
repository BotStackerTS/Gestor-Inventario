# database/connection.py
import sqlite3
from config import DB_NAME


class DatabaseConnection:
    """Gestiona conexiones SQLite y garantiza el esquema mínimo del POS."""

    @staticmethod
    def conectar() -> sqlite3.Connection:
        conn = sqlite3.connect(DB_NAME, timeout=10)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 10000")
        return conn

    @staticmethod
    def inicializar_base_datos() -> None:
        with DatabaseConnection.conectar() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    rol TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS inventario (
                    codigo TEXT PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    cantidad INTEGER NOT NULL DEFAULT 0,
                    precio_base REAL NOT NULL,
                    precio_final REAL NOT NULL,
                    stock_minimo INTEGER NOT NULL DEFAULT 5
                );

                CREATE TABLE IF NOT EXISTS etiquetas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE NOT NULL
                );

                CREATE TABLE IF NOT EXISTS producto_etiqueta (
                    codigo_articulo TEXT NOT NULL,
                    etiqueta_id INTEGER NOT NULL,
                    FOREIGN KEY (codigo_articulo)
                        REFERENCES inventario(codigo) ON DELETE CASCADE,
                    FOREIGN KEY (etiqueta_id)
                        REFERENCES etiquetas(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS promociones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    codigo_articulo TEXT,
                    etiqueta_id INTEGER,
                    tipo TEXT NOT NULL,
                    valor REAL NOT NULL,
                    FOREIGN KEY (codigo_articulo)
                        REFERENCES inventario(codigo) ON DELETE CASCADE,
                    FOREIGN KEY (etiqueta_id)
                        REFERENCES etiquetas(id) ON DELETE CASCADE
                );

                -- Sesión de caja: se abre con un fondo inicial y se cierra con arqueo.
                CREATE TABLE IF NOT EXISTS caja_sesiones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fondo_inicial REAL NOT NULL,
                    fecha_apertura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fecha_cierre TIMESTAMP,
                    usuario_apertura TEXT NOT NULL,
                    usuario_cierre TEXT,
                    estado TEXT NOT NULL DEFAULT 'ABIERTA'
                        CHECK (estado IN ('ABIERTA', 'CERRADA')),
                    observaciones TEXT
                );

                -- Detalle del arqueo de cierre: un renglón por medio de pago.
                CREATE TABLE IF NOT EXISTS caja_arqueo_detalle (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    caja_sesion_id INTEGER NOT NULL,
                    medio_pago TEXT NOT NULL,
                    monto_sistema REAL NOT NULL DEFAULT 0,
                    monto_contado REAL,
                    diferencia REAL,
                    FOREIGN KEY (caja_sesion_id)
                        REFERENCES caja_sesiones(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS ventas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total REAL NOT NULL,
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    caja_sesion_id INTEGER,
                    FOREIGN KEY (caja_sesion_id)
                        REFERENCES caja_sesiones(id) ON DELETE RESTRICT
                );

                CREATE TABLE IF NOT EXISTS detalle_venta (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    venta_id INTEGER NOT NULL,
                    codigo_articulo TEXT NOT NULL,
                    cantidad INTEGER NOT NULL,
                    subtotal REAL NOT NULL,
                    FOREIGN KEY (venta_id)
                        REFERENCES ventas(id) ON DELETE CASCADE,
                    FOREIGN KEY (codigo_articulo)
                        REFERENCES inventario(codigo)
                );

                -- Pagos mixtos: una venta puede tener 1..N renglones de pago.
                CREATE TABLE IF NOT EXISTS venta_pagos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    venta_id INTEGER NOT NULL,
                    medio_pago TEXT NOT NULL,
                    monto REAL NOT NULL CHECK (monto > 0),
                    FOREIGN KEY (venta_id)
                        REFERENCES ventas(id) ON DELETE CASCADE
                );
                """
            )
            DatabaseConnection._migrar_esquema(conn)
            conn.commit()

    @staticmethod
    def _migrar_esquema(conn: sqlite3.Connection) -> None:
        """Corrige instalaciones antiguas sin borrar los datos existentes."""
        columnas = {
            row[1]
            for row in conn.execute("PRAGMA table_info(promociones)").fetchall()
        }

        if "nombre" not in columnas and "nombre_promo" in columnas:
            conn.execute(
                "ALTER TABLE promociones RENAME COLUMN nombre_promo TO nombre"
            )
        elif "nombre" not in columnas:
            conn.execute(
                "ALTER TABLE promociones ADD COLUMN nombre TEXT NOT NULL DEFAULT ''"
            )

        if "etiqueta_id" not in columnas:
            try:
                conn.execute("ALTER TABLE promociones ADD COLUMN etiqueta_id INTEGER")
            except sqlite3.OperationalError:
                pass

        columnas_inventario = {
            row[1]
            for row in conn.execute("PRAGMA table_info(inventario)").fetchall()
        }
        if "stock_minimo" not in columnas_inventario:
            conn.execute(
                "ALTER TABLE inventario ADD COLUMN stock_minimo INTEGER NOT NULL DEFAULT 5"
            )

        # Instalaciones existentes de "ventas" no tienen caja_sesion_id.
        columnas_ventas = {
            row[1] for row in conn.execute("PRAGMA table_info(ventas)").fetchall()
        }
        if "caja_sesion_id" not in columnas_ventas:
            conn.execute(
                "ALTER TABLE ventas ADD COLUMN caja_sesion_id INTEGER "
                "REFERENCES caja_sesiones(id)"
            )

        try:
            conn.execute(
                """
                DELETE FROM producto_etiqueta
                WHERE rowid NOT IN (
                    SELECT MIN(rowid)
                    FROM producto_etiqueta
                    GROUP BY codigo_articulo, etiqueta_id
                )
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ux_producto_etiqueta
                ON producto_etiqueta(codigo_articulo, etiqueta_id)
                """
            )
        except sqlite3.OperationalError:
            pass

        conn.commit()
