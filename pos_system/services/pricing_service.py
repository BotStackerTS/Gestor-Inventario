# services/pricing_service.py
from config import IMPUESTOS_PCT, INFLACION_PCT, LOGISTICA_FIJA

class PricingService:
    @staticmethod
    def calcular_precio_inteligente(precio_base: float) -> float:
        factor_impuestos = 1 + (IMPUESTOS_PCT / 100)
        factor_inflacion = 1 + (INFLACION_PCT / 100)
        precio_unitario = (precio_base * factor_impuestos * factor_inflacion) + LOGISTICA_FIJA
        return round(precio_unitario, 2)