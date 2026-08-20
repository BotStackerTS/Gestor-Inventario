# services/sales_service.py
from database.connection import DatabaseConnection
from repositories.inventario_repo import InventarioRepository
from repositories.venta_repo import VentaRepository
from models.entidades import VentaResultado

class SalesService:
    @staticmethod
    def procesar_venta(carrito: list[tuple[str, int]]) -> VentaResultado:
        with DatabaseConnection.conectar() as conn:
            cursor = conn.cursor()
            # Usar BEGIN IMMEDIATE para transacciones concurrentes seguras
            cursor.execute("BEGIN IMMEDIATE;")
            
            venta_id = VentaRepository.crear_venta(conn, total=0.0)
            total_venta = 0.0
            alertas_stock = []

            for codigo, cant_vendida in carrito:
                articulo = InventarioRepository.obtener_por_codigo(codigo)
                if not articulo:
                    raise Exception(f"Artículo con código {codigo} no existe.")
                
                if articulo.cantidad < cant_vendida:
                    raise Exception(f"Stock insuficiente para '{articulo.nombre}' (Disponible: {articulo.cantidad}).")

                subtotal = cant_vendida * articulo.precio_final
                total_venta += subtotal
                nuevo_stock = articulo.cantidad - cant_vendida

                # Actualizar stock de forma atómica
                cursor.execute("UPDATE inventario SET cantidad = ? WHERE codigo = ?", (nuevo_stock, codigo))
                VentaRepository.agregar_detalle(conn, venta_id, codigo, cant_vendida, subtotal)

                if nuevo_stock <= articulo.stock_minimo:
                    alertas_stock.append(f"⚠️ Alerta: '{articulo.nombre}' stock bajo ({nuevo_stock} un.).")

            VentaRepository.actualizar_total_venta(conn, venta_id, total_venta)
            conn.commit()
            
            return VentaResultado(venta_id=venta_id, total=total_venta, alertas_stock=alertas_stock)