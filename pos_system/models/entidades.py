# models/entidades.py
from dataclasses import dataclass

@dataclass
class Articulo:
    codigo: str
    nombre: str
    cantidad: int
    precio_base: float
    precio_final: float
    stock_minimo: int

@dataclass
class VentaResultado:
    venta_id: int
    total: float
    alertas_stock: list[str]