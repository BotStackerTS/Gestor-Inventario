# repositories/inventario_repo.py
from typing import Optional

from database.connection import DatabaseConnection
from models.entidades import Articulo


class InventarioRepository:
    """Acceso a datos de inventario, etiquetas y promociones."""

    @staticmethod
    def _articulo(row) -> Articulo:
        return Articulo(
            codigo=row[0],
            nombre=row[1],
            cantidad=int(row[2]),
            precio_base=float(row[3]),
            precio_final=float(row[4]),
            stock_minimo=int(row[5]),
        )

    @staticmethod
    def insertar(articulo: Articulo) -> None:
        with DatabaseConnection.conectar() as conn:
            conn.execute(
                """
                INSERT INTO inventario
                    (codigo, nombre, cantidad, precio_base, precio_final, stock_minimo)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(codigo) DO UPDATE SET
                    nombre = excluded.nombre,
                    cantidad = excluded.cantidad,
                    precio_base = excluded.precio_base,
                    precio_final = excluded.precio_final,
                    stock_minimo = excluded.stock_minimo
                """,
                (
                    articulo.codigo,
                    articulo.nombre,
                    articulo.cantidad,
                    articulo.precio_base,
                    articulo.precio_final,
                    articulo.stock_minimo,
                ),
            )

    @staticmethod
    def obtener_por_codigo(codigo: str) -> Optional[Articulo]:
        with DatabaseConnection.conectar() as conn:
            row = conn.execute(
                """
                SELECT codigo, nombre, cantidad, precio_base,
                       precio_final, stock_minimo
                FROM inventario
                WHERE codigo = ?
                """,
                (str(codigo).strip(),),
            ).fetchone()
            return InventarioRepository._articulo(row) if row else None

    @staticmethod
    def obtener_todos(etiqueta: Optional[str] = None) -> list[Articulo]:
        with DatabaseConnection.conectar() as conn:
            if etiqueta and etiqueta != "Todas":
                rows = conn.execute(
                    """
                    SELECT DISTINCT i.codigo, i.nombre, i.cantidad,
                           i.precio_base, i.precio_final, i.stock_minimo
                    FROM inventario i
                    JOIN producto_etiqueta pe
                        ON i.codigo = pe.codigo_articulo
                    JOIN etiquetas e
                        ON pe.etiqueta_id = e.id
                    WHERE e.nombre = ?
                    ORDER BY i.nombre COLLATE NOCASE
                    """,
                    (etiqueta,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT codigo, nombre, cantidad, precio_base,
                           precio_final, stock_minimo
                    FROM inventario
                    ORDER BY nombre COLLATE NOCASE
                    """
                ).fetchall()
            return [InventarioRepository._articulo(row) for row in rows]

    @staticmethod
    def obtener_faltantes() -> list[Articulo]:
        with DatabaseConnection.conectar() as conn:
            rows = conn.execute(
                """
                SELECT codigo, nombre, cantidad, precio_base,
                       precio_final, stock_minimo
                FROM inventario
                WHERE cantidad <= 0
                ORDER BY nombre COLLATE NOCASE
                """
            ).fetchall()
            return [InventarioRepository._articulo(row) for row in rows]

    @staticmethod
    def actualizar(codigo: str, campos: dict) -> None:
        if not campos:
            return

        permitidas = {
            "nombre",
            "cantidad",
            "precio_base",
            "precio_final",
            "stock_minimo",
        }
        desconocidas = set(campos) - permitidas
        if desconocidas:
            raise ValueError(
                "Campos de inventario no permitidos: "
                + ", ".join(sorted(desconocidas))
            )

        columnas = ", ".join(f"{campo} = ?" for campo in campos)
        valores = list(campos.values()) + [str(codigo).strip()]

        with DatabaseConnection.conectar() as conn:
            cursor = conn.execute(
                f"UPDATE inventario SET {columnas} WHERE codigo = ?", valores
            )
            if cursor.rowcount == 0:
                raise ValueError(f"No existe el artículo con código '{codigo}'.")

    @staticmethod
    def eliminar(codigo: str) -> None:
        with DatabaseConnection.conectar() as conn:
            cursor = conn.execute(
                "DELETE FROM inventario WHERE codigo = ?", (str(codigo).strip(),)
            )
            if cursor.rowcount == 0:
                raise ValueError(f"No existe el artículo con código '{codigo}'.")

    @staticmethod
    def guardar_promocion(
        nombre: str,
        tipo: str,
        valor: float,
        codigo_articulo: Optional[str] = None,
        etiqueta_nombre: Optional[str] = None,
    ) -> None:
        nombre = nombre.strip()
        tipo = tipo.strip().upper()
        codigo_articulo = codigo_articulo.strip() if codigo_articulo else None
        etiqueta_nombre = (
            etiqueta_nombre.strip()
            if etiqueta_nombre and etiqueta_nombre != "Ninguna"
            else None
        )

        if not nombre:
            raise ValueError("El nombre de la promoción es obligatorio.")
        if tipo not in {"2X1", "PORCENTAJE"}:
            raise ValueError("Tipo de promoción no válido.")
        if tipo == "PORCENTAJE" and not 0 <= float(valor) <= 100:
            raise ValueError("El descuento debe estar entre 0 y 100%.")
        
        if codigo_articulo and etiqueta_nombre:
            raise ValueError(
                "Una promoción debe aplicarse a un producto o a una etiqueta, pero no a ambos a la vez."
            )
        if not codigo_articulo and not etiqueta_nombre:
            raise ValueError("Debe indicar obligatoriamente un producto o una etiqueta.")

        with DatabaseConnection.conectar() as conn:
            etiqueta_id = None
            if etiqueta_nombre:
                row = conn.execute(
                    "SELECT id FROM etiquetas WHERE nombre = ?", (etiqueta_nombre,)
                ).fetchone()
                if not row:
                    raise ValueError(f"No existe la etiqueta '{etiqueta_nombre}'.")
                etiqueta_id = row[0]

            if codigo_articulo:
                if not conn.execute(
                    "SELECT 1 FROM inventario WHERE codigo = ?", (codigo_articulo,)
                ).fetchone():
                    raise ValueError(
                        f"No existe el producto con código '{codigo_articulo}'."
                    )

            conn.execute(
                """
                INSERT INTO promociones
                    (nombre, codigo_articulo, etiqueta_id, tipo, valor)
                VALUES (?, ?, ?, ?, ?)
                """,
                (nombre, codigo_articulo, etiqueta_id, tipo, float(valor)),
            )

    @staticmethod
    def obtener_promociones() -> list[tuple]:
        with DatabaseConnection.conectar() as conn:
            return conn.execute(
                """
                SELECT p.id, p.nombre,
                       COALESCE(i.nombre, 'Etiqueta: ' || e.nombre) AS destino,
                       p.tipo, p.valor
                FROM promociones p
                LEFT JOIN inventario i ON p.codigo_articulo = i.codigo
                LEFT JOIN etiquetas e ON p.etiqueta_id = e.id
                ORDER BY p.id DESC
                """
            ).fetchall()

    @staticmethod
    def eliminar_promocion(promo_id: int) -> None:
        with DatabaseConnection.conectar() as conn:
            cursor = conn.execute(
                "DELETE FROM promociones WHERE id = ?", (int(promo_id),)
            )
            if cursor.rowcount == 0:
                raise ValueError("La promoción seleccionada ya no existe.")

    @staticmethod
    def verificar_promocion_activa(codigo_articulo: str):
        with DatabaseConnection.conectar() as conn:
            row = conn.execute(
                """
                SELECT tipo, valor
                FROM promociones
                WHERE codigo_articulo = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (str(codigo_articulo).strip(),),
            ).fetchone()
            if row:
                return row

            return conn.execute(
                """
                SELECT p.tipo, p.valor
                FROM promociones p
                JOIN producto_etiqueta pe
                    ON p.etiqueta_id = pe.etiqueta_id
                WHERE pe.codigo_articulo = ?
                ORDER BY p.id DESC
                LIMIT 1
                """,
                (str(codigo_articulo).strip(),),
            ).fetchone()

    @staticmethod
    def obtener_etiquetas() -> list[str]:
        with DatabaseConnection.conectar() as conn:
            rows = conn.execute(
                "SELECT nombre FROM etiquetas ORDER BY nombre COLLATE NOCASE"
            ).fetchall()
            return [row[0] for row in rows]

    @staticmethod
    def asociar_etiqueta_a_producto(
        codigo_articulo: str, nombre_etiqueta: str
    ) -> None:
        with DatabaseConnection.conectar() as conn:
            if not conn.execute(
                "SELECT 1 FROM inventario WHERE codigo = ?", (str(codigo_articulo).strip(),)
            ).fetchone():
                raise ValueError(f"No existe el producto '{codigo_articulo}'.")

            row = conn.execute(
                "SELECT id FROM etiquetas WHERE nombre = ?", (nombre_etiqueta,)
            ).fetchone()
            if not row:
                raise ValueError(f"No existe la etiqueta '{nombre_etiqueta}'.")

            conn.execute(
                """
                INSERT OR IGNORE INTO producto_etiqueta
                    (codigo_articulo, etiqueta_id)
                VALUES (?, ?)
                """,
                (str(codigo_articulo).strip(), row[0]),
            )