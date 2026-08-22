# services/sales_service.py
from database.connection import DatabaseConnection
from repositories.inventario_repo import InventarioRepository
from repositories.venta_repo import VentaRepository
from repositories.caja_repo import CajaRepository
from models.entidades import VentaResultado


class SalesService:
    @staticmethod
    def procesar_venta(
        carrito: list[tuple[str, int]],
        pagos: list[tuple[str, float]],
    ) -> VentaResultado:
        """
        carrito: [(codigo, cantidad), ...]
        pagos:   [(medio_pago, monto), ...]  ej. [("EFECTIVO", 5000.0), ("TRANSFERENCIA", 3200.0)]

        La suma de 'pagos' debe cubrir el total de la venta. Si sobra (vuelto),
        el excedente tiene que poder cubrirse con lo pagado en EFECTIVO, porque
        tarjeta/transferencia no dan vuelto.
        """
        if not carrito:
            raise ValueError("El carrito está vacío.")
        if not pagos:
            raise ValueError("Debe indicar al menos un medio de pago.")

        for medio_pago, monto in pagos:
            if medio_pago not in CajaRepository.MEDIOS_PAGO_VALIDOS:
                raise ValueError(f"Medio de pago no válido: '{medio_pago}'.")
            if float(monto) <= 0:
                raise ValueError("El monto de cada pago debe ser mayor a 0.")

        sesion_activa = CajaRepository.obtener_sesion_activa()
        if not sesion_activa:
            raise ValueError(
                "No hay una caja abierta. Debe abrir caja antes de registrar ventas."
            )

        with DatabaseConnection.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")

            venta_id = VentaRepository.crear_venta(
                conn, total=0.0, caja_sesion_id=sesion_activa.id
            )
            total_venta = 0.0
            alertas_stock = []

            for codigo, cant_vendida in carrito:
                articulo = InventarioRepository.obtener_por_codigo(codigo)
                if not articulo:
                    raise ValueError(f"Artículo con código {codigo} no existe.")

                if articulo.cantidad < cant_vendida:
                    raise ValueError(
                        f"Stock insuficiente para '{articulo.nombre}' "
                        f"(Disponible: {articulo.cantidad})."
                    )

                # Verificar si tiene promociones activas
                cursor.execute(
                    "SELECT tipo, valor FROM promociones WHERE codigo_articulo = ?",
                    (codigo,),
                )
                promo = cursor.fetchone()

                cant_a_cobrar = cant_vendida
                if promo:
                    tipo_promo, valor_promo = promo
                    if tipo_promo == "2X1":
                        # Cada 2 unidades, se paga 1
                        pares = cant_vendida // 2
                        sobrantes = cant_vendida % 2
                        cant_a_cobrar = (pares * 1) + sobrantes

                subtotal = cant_a_cobrar * articulo.precio_final
                total_venta += subtotal
                nuevo_stock = articulo.cantidad - cant_vendida

                cursor.execute(
                    "UPDATE inventario SET cantidad = ? WHERE codigo = ?",
                    (nuevo_stock, codigo),
                )
                VentaRepository.agregar_detalle(
                    conn, venta_id, codigo, cant_vendida, subtotal
                )

                if nuevo_stock <= articulo.stock_minimo:
                    alertas_stock.append(
                        f"⚠️ Alerta: '{articulo.nombre}' stock bajo ({nuevo_stock} un.)."
                    )

            total_venta = round(total_venta, 2)
            SalesService._validar_cobertura_de_pagos(pagos, total_venta)

            VentaRepository.actualizar_total_venta(conn, venta_id, total_venta)
            for medio_pago, monto in pagos:
                VentaRepository.registrar_pago(conn, venta_id, medio_pago, float(monto))

            conn.commit()

            return VentaResultado(
                venta_id=venta_id, total=total_venta, alertas_stock=alertas_stock
            )

    @staticmethod
    def _validar_cobertura_de_pagos(
        pagos: list[tuple[str, float]], total_venta: float
    ) -> None:
        total_pagado = round(sum(float(monto) for _, monto in pagos), 2)

        if total_pagado + 0.01 < total_venta:
            faltante = round(total_venta - total_pagado, 2)
            raise ValueError(
                f"El pago no cubre el total de la venta. "
                f"Total: ${total_venta:.2f} — Pagado: ${total_pagado:.2f} "
                f"(faltan ${faltante:.2f})."
            )

        vuelto = round(total_pagado - total_venta, 2)
        if vuelto > 0.01:
            efectivo_pagado = sum(
                float(monto) for medio, monto in pagos if medio == "EFECTIVO"
            )
            if efectivo_pagado + 0.01 < vuelto:
                raise ValueError(
                    f"El pago excede el total en ${vuelto:.2f}, pero no hay "
                    "suficiente efectivo entre los medios de pago para dar el "
                    "vuelto (tarjeta/transferencia no admiten vuelto)."
                )
