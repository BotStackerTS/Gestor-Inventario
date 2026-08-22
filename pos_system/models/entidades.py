# models/entidades.py
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Articulo:
    codigo: str
    nombre: str
    cantidad: int
    precio_base: float
    precio_final: float
    stock_minimo: int


@dataclass
class PagoVenta:
    """Un renglón de pago dentro de una venta con pagos mixtos."""
    medio_pago: str
    monto: float


@dataclass
class VentaResultado:
    venta_id: int
    total: float
    alertas_stock: list[str] = field(default_factory=list)


@dataclass
class SesionCaja:
    id: int
    fondo_inicial: float
    fecha_apertura: str
    fecha_cierre: Optional[str]
    usuario_apertura: str
    usuario_cierre: Optional[str]
    estado: str
    observaciones: Optional[str]


@dataclass
class DetalleArqueo:
    """Comparación sistema vs. contado para un medio de pago, al cerrar caja."""
    medio_pago: str
    monto_sistema: float
    monto_contado: Optional[float]
    diferencia: Optional[float]


@dataclass
class ResultadoCierreCaja:
    sesion: SesionCaja
    detalles: list[DetalleArqueo]
    diferencia_total: float
