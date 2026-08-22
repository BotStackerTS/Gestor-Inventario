# repositories/venta_repo.py
from database.connection import DatabaseConnection
from models.entidades import PagoVenta


class VentaRepository:
    """
    Acceso a datos de ventas y sus pagos.

    Los métodos que reciben 'conn' son de bajo nivel: no abren ni cierran
    transacción propia, para que el llamador (ej. SalesService) controle
    todo el commit/rollback de la operación de venta como una unidad atómica.
    Los métodos que NO reciben 'conn' son de solo lectura y manejan su
    propia conexión.
    """

    @staticmethod
    def crear_venta(conn, total: float, caja_sesion_id: int) -> int:
        if caja_sesion_id is None:
            raise ValueError(
                "La venta debe estar asociada a una sesión de caja abierta."
            )
        cursor = conn.execute(
            "INSERT INTO ventas (total, caja_sesion_id) VALUES (?, ?)",
            (float(total), int(caja_sesion_id)),
        )
        return cursor.lastrowid

    @staticmethod
    def agregar_detalle(
        conn, venta_id: int, codigo: str, cantidad: int, subtotal: float
    ) -> None:
        conn.execute(
            """
            INSERT INTO detalle_venta (venta_id, codigo_articulo, cantidad, subtotal)
            VALUES (?, ?, ?, ?)
            """,
            (int(venta_id), str(codigo).strip(), int(cantidad), float(subtotal)),
        )

    @staticmethod
    def actualizar_total_venta(conn, venta_id: int, total: float) -> None:
        conn.execute(
            "UPDATE ventas SET total = ? WHERE id = ?",
            (float(total), int(venta_id)),
        )

    @staticmethod
    def registrar_pago(conn, venta_id: int, medio_pago: str, monto: float) -> None:
        if float(monto) <= 0:
            raise ValueError("El monto de un pago debe ser mayor a 0.")
        conn.execute(
            "INSERT INTO venta_pagos (venta_id, medio_pago, monto) VALUES (?, ?, ?)",
            (int(venta_id), medio_pago, float(monto)),
        )

    # --- Lecturas (conexión propia) ---

    @staticmethod
    def obtener_pagos_de_venta(venta_id: int) -> list[PagoVenta]:
        with DatabaseConnection.conectar() as conn:
            rows = conn.execute(
                "SELECT medio_pago, monto FROM venta_pagos WHERE venta_id = ?",
                (int(venta_id),),
            ).fetchall()
            return [PagoVenta(medio_pago=row[0], monto=float(row[1])) for row in rows]

    @staticmethod
    def obtener_ventas_de_sesion(caja_sesion_id: int) -> list[dict]:
        """Cada venta de la sesión con su total y el detalle de pagos."""
        with DatabaseConnection.conectar() as conn:
            ventas = conn.execute(
                "SELECT id, total, fecha FROM ventas WHERE caja_sesion_id = ? ORDER BY id",
                (int(caja_sesion_id),),
            ).fetchall()

            resultado = []
            for venta_id, total, fecha in ventas:
                pagos = conn.execute(
                    "SELECT medio_pago, monto FROM venta_pagos WHERE venta_id = ?",
                    (venta_id,),
                ).fetchall()
                resultado.append(
                    {
                        "venta_id": venta_id,
                        "total": float(total),
                        "fecha": fecha,
                        "pagos": [
                            PagoVenta(medio_pago=p[0], monto=float(p[1])) for p in pagos
                        ],
                    }
                )
            return resultado
