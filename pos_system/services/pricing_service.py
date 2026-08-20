# services/pricing_service.py
import config

class PricingService:
    @staticmethod
    def calcular_detallado(precio_base: float):
        impuesto = precio_base * (config.IMPUESTOS_PCT / 100)
        comision = precio_base * (config.COMISION_PCT / 100)
        margen = precio_base * (config.MARGEN_PCT / 100)
        logistica = float(config.LOGISTICA_FIJA)
        
        final = precio_base + impuesto + comision + margen + logistica
        return round(final, 2), {
            "Impuesto": round(impuesto, 2), 
            "Comisión": round(comision, 2), 
            "Margen": round(margen, 2), 
            "Logística": round(logistica, 2)
        }

    @staticmethod
    def calcular_precio_inteligente(precio_base: float) -> float:
        final, _ = PricingService.calcular_detallado(precio_base)
        return final