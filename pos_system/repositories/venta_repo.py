# repositories/venta_repo.py
from database.connection import DatabaseConnection

class VentaRepository:
    @staticmethod
    def crear_venta(conn, total: float) -> int:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO ventas (total) VALUES (?)", (total,))
        return cursor.lastrowid

    @staticmethod
    def agregar_detalle(conn, venta_id: int, codigo_articulo: str, cantidad: int, subtotal: float):
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO detalle_venta (venta_id, codigo_articulo, cantidad, subtotal) 
            VALUES (?, ?, ?, ?)
        """, (venta_id, codigo_articulo, cantidad, subtotal))

    @staticmethod
    def actualizar_total_venta(conn, venta_id: int, total: float):
        cursor = conn.cursor()
        cursor.execute("UPDATE ventas SET total = ? WHERE id = ?", (total, venta_id))
        
    @staticmethod
    def obtener_historial():
        with DatabaseConnection.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, fecha, total FROM ventas ORDER BY id DESC")
            return cursor.fetchall()