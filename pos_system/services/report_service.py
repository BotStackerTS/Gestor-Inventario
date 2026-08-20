# services/report_service.py
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from repositories.inventario_repo import InventarioRepository
import smtplib
from email.message import EmailMessage

class ReportService:
    @staticmethod
    def exportar_excel(filename="inventario_reporte.xlsx"):
        articulos = InventarioRepository.obtener_todos()
        data = [{
            "Código": a.codigo,
            "Nombre": a.nombre,
            "Cantidad": a.cantidad,
            "Precio Base": a.precio_base,
            "Precio Final": a.precio_final,
            "Stock Mínimo": a.stock_minimo
        } for a in articulos]
        df = pd.DataFrame(data)
        df.to_excel(filename, index=False)
        return filename

    @staticmethod
    def exportar_pdf(filename="inventario_reporte.pdf"):
        articulos = InventarioRepository.obtener_todos()
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter
        
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, "Reporte General de Inventario - POS Pro")
        
        c.setFont("Helvetica", 10)
        y = height - 90
        c.drawString(50, y, "Código")
        c.drawString(130, y, "Nombre")
        c.drawString(280, y, "Cant")
        c.drawString(340, y, "Precio Final")
        y -= 20
        c.line(50, y+15, 550, y+15)

        for a in articulos:
            if y < 50:
                c.showPage()
                y = height - 50
            c.drawString(50, y, str(a.codigo))
            c.drawString(130, y, str(a.nombre))
            c.drawString(280, y, str(a.cantidad))
            c.drawString(340, y, f"${a.precio_final:.2f}")
            y -= 20
            
        c.save()
        return filename

    @staticmethod
    def enviar_correo_gmail(destinatario: str, asunto: str, cuerpo: str, archivo_adjunto: str = None):
        # Nota: Configura aquí tu cuenta o usa variables de entorno para producción
        remitente = "tutuapp.soporte@gmail.com" 
        password_app = "tu_password_de_aplicacion" # Contraseña de aplicación de Gmail

        msg = EmailMessage()
        msg["Subject"] = asunto
        msg["From"] = remitente
        msg["To"] = destinatario
        msg.set_content(cuerpo)

        if archivo_adjunto:
            with open(archivo_adjunto, "rb") as f:
                file_data = f.read()
                file_name = archivo_adjunto.split("/")[-1]
            msg.add_attachment(file_data, maintype="application", subtype="octet-stream", filename=file_name)

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(remitente, password_app)
                smtp.send_message(msg)
            return True
        except Exception as e:
            print(f"Error al enviar correo: {e}")
            return False