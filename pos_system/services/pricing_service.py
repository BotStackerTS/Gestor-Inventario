# services/pricing_service.py
from config import IMPUESTOS_PCT, INFLACION_PCT, LOGISTICA_FIJA

class PricingService:
    @staticmethod
    def calcular_precio_inteligente(precio_base: float, impuestos: float = IMPUESTOS_PCT, inflacion: float = INFLACION_PCT, logistica: float = LOGISTICA_FIJA) -> float:
        factor_impuestos = 1 + (impuestos / 100)
        factor_inflacion = 1 + (inflacion / 100)
        precio_unitario = (precio_base * factor_impuestos * factor_inflacion) + logistica
        return round(precio_unitario, 2)