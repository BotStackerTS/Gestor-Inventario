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
            cursor.execute("""
                SELECT codigo, nombre, cantidad, precio_base, precio_final, stock_minimo 
                FROM inventario
            """)
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