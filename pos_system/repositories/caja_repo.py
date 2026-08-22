# repositories/caja_repo.py
from typing import Optional

from database.connection import DatabaseConnection
from models.entidades import SesionCaja, DetalleArqueo, ResultadoCierreCaja


class CajaRepository:
    """Apertura, cierre y arqueo de caja."""

    MEDIOS_PAGO_VALIDOS = {
        "EFECTIVO",
        "TARJETA_DEBITO",
        "TARJETA_CREDITO",
        "TRANSFERENCIA",
        "QR",
        "OTRO",
    }

    @staticmethod
    def _sesion(row) -> SesionCaja:
        return SesionCaja(
            id=row[0],
            fondo_inicial=float(row[1]),
            fecha_apertura=row[2],
            fecha_cierre=row[3],
            usuario_apertura=row[4],
            usuario_cierre=row[5],
            estado=row[6],
            observaciones=row[7],
        )

    _SELECT_SESION = """
        SELECT id, fondo_inicial, fecha_apertura, fecha_cierre,
               usuario_apertura, usuario_cierre, estado, observaciones
        FROM caja_sesiones
    """

    @staticmethod
    def abrir_caja(usuario: str, fondo_inicial: float) -> SesionCaja:
        usuario = (usuario or "").strip()
        if not usuario:
            raise ValueError("Debe indicar el usuario que abre la caja.")
        if float(fondo_inicial) < 0:
            raise ValueError("El fondo inicial no puede ser negativo.")

        with DatabaseConnection.conectar() as conn:
            activa = conn.execute(
                "SELECT id FROM caja_sesiones WHERE estado = 'ABIERTA' LIMIT 1"
            ).fetchone()
            if activa:
                raise ValueError(
                    f"Ya existe una caja abierta (sesión #{activa[0]}). "
                    "Debe cerrarla antes de abrir una nueva."
                )

            cursor = conn.execute(
                """
                INSERT INTO caja_sesiones (fondo_inicial, usuario_apertura, estado)
                VALUES (?, ?, 'ABIERTA')
                """,
                (float(fondo_inicial), usuario),
            )
            nueva_id = cursor.lastrowid
            row = conn.execute(
                CajaRepository._SELECT_SESION + " WHERE id = ?", (nueva_id,)
            ).fetchone()
            return CajaRepository._sesion(row)

    @staticmethod
    def obtener_sesion_activa() -> Optional[SesionCaja]:
        with DatabaseConnection.conectar() as conn:
            row = conn.execute(
                CajaRepository._SELECT_SESION
                + " WHERE estado = 'ABIERTA' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return CajaRepository._sesion(row) if row else None

    @staticmethod
    def obtener_por_id(caja_sesion_id: int) -> Optional[SesionCaja]:
        with DatabaseConnection.conectar() as conn:
            row = conn.execute(
                CajaRepository._SELECT_SESION + " WHERE id = ?",
                (int(caja_sesion_id),),
            ).fetchone()
            return CajaRepository._sesion(row) if row else None

    @staticmethod
    def obtener_historial(limite: int = 30) -> list[SesionCaja]:
        with DatabaseConnection.conectar() as conn:
            rows = conn.execute(
                CajaRepository._SELECT_SESION + " ORDER BY id DESC LIMIT ?",
                (int(limite),),
            ).fetchall()
            return [CajaRepository._sesion(row) for row in rows]

    @staticmethod
    def calcular_totales_por_medio_pago(caja_sesion_id: int) -> dict[str, float]:
        """Suma, por medio de pago, lo que el sistema registró en ventas de esta sesión."""
        with DatabaseConnection.conectar() as conn:
            rows = conn.execute(
                """
                SELECT vp.medio_pago, SUM(vp.monto)
                FROM venta_pagos vp
                JOIN ventas v ON vp.venta_id = v.id
                WHERE v.caja_sesion_id = ?
                GROUP BY vp.medio_pago
                """,
                (int(caja_sesion_id),),
            ).fetchall()
            return {row[0]: float(row[1]) for row in rows}

    @staticmethod
    def obtener_detalle_arqueo(caja_sesion_id: int) -> list[DetalleArqueo]:
        with DatabaseConnection.conectar() as conn:
            rows = conn.execute(
                """
                SELECT medio_pago, monto_sistema, monto_contado, diferencia
                FROM caja_arqueo_detalle
                WHERE caja_sesion_id = ?
                ORDER BY medio_pago
                """,
                (int(caja_sesion_id),),
            ).fetchall()
            return [
                DetalleArqueo(
                    medio_pago=row[0],
                    monto_sistema=float(row[1]),
                    monto_contado=(float(row[2]) if row[2] is not None else None),
                    diferencia=(float(row[3]) if row[3] is not None else None),
                )
                for row in rows
            ]

    @staticmethod
    def cerrar_caja(
        usuario: str,
        caja_sesion_id: int,
        montos_contados: dict[str, float],
        observaciones: Optional[str] = None,
    ) -> ResultadoCierreCaja:
        """
        montos_contados: ej. {"EFECTIVO": 15300.0, "TRANSFERENCIA": 8900.0}
        Solo hace falta contar manualmente el efectivo; los medios electrónicos
        se pueden omitir y su monto_contado queda en None (se asume = sistema).
        """
        usuario = (usuario or "").strip()
        if not usuario:
            raise ValueError("Debe indicar el usuario que cierra la caja.")

        for medio in montos_contados:
            if medio not in CajaRepository.MEDIOS_PAGO_VALIDOS:
                raise ValueError(f"Medio de pago no válido: '{medio}'.")

        with DatabaseConnection.conectar() as conn:
            sesion_row = conn.execute(
                CajaRepository._SELECT_SESION + " WHERE id = ?",
                (int(caja_sesion_id),),
            ).fetchone()
            if not sesion_row:
                raise ValueError(f"No existe la sesión de caja #{caja_sesion_id}.")
            if sesion_row[6] != "ABIERTA":
                raise ValueError("Esa sesión de caja ya está cerrada.")

            fondo_inicial = float(sesion_row[1])

            totales_row = conn.execute(
                """
                SELECT vp.medio_pago, SUM(vp.monto)
                FROM venta_pagos vp
                JOIN ventas v ON vp.venta_id = v.id
                WHERE v.caja_sesion_id = ?
                GROUP BY vp.medio_pago
                """,
                (int(caja_sesion_id),),
            ).fetchall()
            totales_sistema = {row[0]: float(row[1]) for row in totales_row}
            # El efectivo esperado en caja incluye el fondo inicial con el que se abrió.
            totales_sistema["EFECTIVO"] = totales_sistema.get("EFECTIVO", 0.0) + fondo_inicial

            medios = set(totales_sistema) | set(montos_contados)
            detalles: list[DetalleArqueo] = []
            diferencia_total = 0.0

            for medio in sorted(medios):
                monto_sistema = totales_sistema.get(medio, 0.0)
                monto_contado = montos_contados.get(medio)
                diferencia = (
                    round(monto_contado - monto_sistema, 2)
                    if monto_contado is not None
                    else None
                )
                if diferencia is not None:
                    diferencia_total += diferencia

                conn.execute(
                    """
                    INSERT INTO caja_arqueo_detalle
                        (caja_sesion_id, medio_pago, monto_sistema, monto_contado, diferencia)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (int(caja_sesion_id), medio, monto_sistema, monto_contado, diferencia),
                )
                detalles.append(
                    DetalleArqueo(medio, monto_sistema, monto_contado, diferencia)
                )

            conn.execute(
                """
                UPDATE caja_sesiones
                SET estado = 'CERRADA',
                    fecha_cierre = CURRENT_TIMESTAMP,
                    usuario_cierre = ?,
                    observaciones = ?
                WHERE id = ?
                """,
                (usuario, observaciones, int(caja_sesion_id)),
            )

            sesion_final = conn.execute(
                CajaRepository._SELECT_SESION + " WHERE id = ?",
                (int(caja_sesion_id),),
            ).fetchone()

            return ResultadoCierreCaja(
                sesion=CajaRepository._sesion(sesion_final),
                detalles=detalles,
                diferencia_total=round(diferencia_total, 2),
            )
