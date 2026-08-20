# repositories/inventario_repo.py
from database.connection import DatabaseConnection
from models.entidades import Articulo

class InventarioRepository:
    @staticmethod
    def insertar(articulo: Articulo):
        with DatabaseConnection.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO inventario (codigo, nombre, cantidad, precio_base, precio_final, stock_minimo) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (articulo.codigo, articulo.nombre, articulo.cantidad, articulo.precio_base, articulo.precio_final, articulo.stock_minimo))
            conn.commit()

    @staticmethod
    def obtener_por_codigo(codigo: str) -> Articulo | None:
        with DatabaseConnection.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT codigo, nombre, cantidad, precio_base, precio_final, stock_minimo 
                FROM inventario WHERE codigo = ?
            """, (codigo,))
            row = cursor.fetchone()
            if row:
                return Articulo(codigo=row[0], nombre=row[1], cantidad=row[2], precio_base=row[3], precio_final=row[4], stock_minimo=row[5])
            return None

    @staticmethod
    def obtener_todos() -> list[Articulo]:
        with DatabaseConnection.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT codigo, nombre, cantidad, precio_base, precio_final, stock_minimo FROM inventario")
            rows = cursor.fetchall()
            return [Articulo(codigo=r[0], nombre=r[1], cantidad=r[2], precio_base=r[3], precio_final=r[4], stock_minimo=r[5]) for r in rows]

    @staticmethod
    def actualizar(codigo: str, campos: dict):
        if not campos:
            return
        columnas = ", ".join([f"{k} = ?" for k in campos.keys()])
        valores = list(campos.values()) + [codigo]
        with DatabaseConnection.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE inventario SET {columnas} WHERE codigo = ?", valores)
            conn.commit()

    @staticmethod
    def eliminar(codigo: str):
        with DatabaseConnection.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM inventario WHERE codigo = ?", (codigo,))
            conn.commit()

    @staticmethod
    def gestionar_etiqueta(nombre_etiqueta: str):
        nombre_etiqueta = nombre_etiqueta.strip().lower()
        if not nombre_etiqueta.startswith("#"):
            nombre_etiqueta = "#" + nombre_etiqueta
        with DatabaseConnection.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO etiquetas (nombre) VALUES (?)", (nombre_etiqueta,))
            conn.commit()

    @staticmethod
    def obtener_etiquetas():
        with DatabaseConnection.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombre FROM etiquetas")
            return cursor.fetchall()

    @staticmethod
    def asignar_etiqueta_a_producto(codigo_articulo: str, etiqueta_id: int):
        with DatabaseConnection.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO producto_etiqueta (codigo_articulo, etiqueta_id) VALUES (?, ?)", (codigo_articulo, etiqueta_id))
            conn.commit()

    @staticmethod
    def obtener_etiquetas_de_producto(codigo_articulo: str):
        with DatabaseConnection.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.nombre FROM etiquetas e
                JOIN producto_etiqueta pe ON e.id = pe.etiqueta_id
                WHERE pe.codigo_articulo = ?
            """, (codigo_articulo,))
            return [r[0] for r in cursor.fetchall()]

    @staticmethod
    def guardar_promocion(codigo_articulo: str, tipo: str, valor: float):
        with DatabaseConnection.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO promociones (codigo_articulo, tipo, valor) VALUES (?, ?, ?)", (codigo_articulo, tipo, valor))
            conn.commit()

    @staticmethod
    def obtener_promociones():
        with DatabaseConnection.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT p.id, i.nombre, p.tipo, p.valor, p.codigo_articulo FROM promociones p JOIN inventario i ON p.codigo_articulo = i.codigo")
            return cursor.fetchall()