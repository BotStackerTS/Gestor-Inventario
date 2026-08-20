# views/main_window.py
import tkinter as tk
from tkinter import ttk, messagebox
from services.sales_service import SalesService
from services.pricing_service import PricingService
from repositories.inventario_repo import InventarioRepository
from repositories.venta_repo import VentaRepository
from models.entidades import Articulo

class MainWindow(tk.Tk):
    def __init__(self, usuario: str, rol: str):
        super().__init__()
        self.usuario = usuario
        self.rol = rol
        self.title(f"POS Pro - Comercial | Usuario: {usuario} ({rol.upper()})")
        self.geometry("900x680")
        
        self.crear_interfaz()

    def crear_interfaz(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        # Crear pestañas
        f_venta = ttk.Frame(nb)
        f_inventario = ttk.Frame(nb)
        f_carga = ttk.Frame(nb)
        f_historial = ttk.Frame(nb)

        nb.add(f_venta, text="🛒 Caja / Ventas")
        nb.add(f_inventario, text="📦 Inventario")
        nb.add(f_carga, text="➕ Cargar Stock")
        nb.add(f_historial, text="📊 Historial de Ventas")

        self.construir_pestana_venta(f_venta)
        self.construir_pestana_inventario(f_inventario)
        self.construir_pestana_carga(f_carga)
        self.construir_pestana_historial(f_historial)

    def construir_pestana_venta(self, parent):
        tk.Label(parent, text="Caja Registradora", font=("Segoe UI", 14, "bold")).pack(pady=10)
        
        f_form = tk.LabelFrame(parent, text="Detalle de Venta", padx=15, pady=15)
        f_form.pack(fill="x", padx=20, pady=10)

        tk.Label(f_form, text="Código del Artículo:").grid(row=0, column=0, sticky="w", pady=5)
        e_cod = tk.Entry(f_form, width=20); e_cod.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(f_form, text="Cantidad a Vender:").grid(row=1, column=0, sticky="w", pady=5)
        e_cant = tk.Entry(f_form, width=20); e_cant.grid(row=1, column=1, padx=10, pady=5)

        def procesar():
            try:
                cantidad = int(e_cant.get())
                carrito = [(e_cod.get(), cantidad)]
                resultado = SalesService.procesar_venta(carrito)
                
                msg = f"Ticket N°: {resultado.venta_id}\nTotal a Pagar: ${resultado.total:.2f}\n\n¡Venta exitosa!"
                if resultado.alertas_stock:
                    msg += "\n\n" + "\n".join(resultado.alertas_stock)
                
                messagebox.showinfo("Ticket Emitido 🎫", msg)
                e_cod.delete(0, tk.END); e_cant.delete(0, tk.END)
            except Exception as ex:
                messagebox.showerror("Error en Venta", str(ex))

        tk.Button(parent, text="Cobrar y Emitir Ticket", bg="#2E7D32", fg="white", 
                  font=("Segoe UI", 10, "bold"), command=procesar).pack(pady=20)

    def construir_pestana_inventario(self, parent):
        tk.Label(parent, text="Control General de Inventario", font=("Segoe UI", 14, "bold")).pack(pady=10)
        
        columns = ("Código", "Nombre", "Cantidad", "Precio Base", "Precio Final", "Mínimo")
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=12)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=110, anchor="center")
        tree.pack(pady=5)

        def actualizar():
            for row in tree.get_children(): tree.delete(row)
            for art in InventarioRepository.obtener_todos():
                tree.insert("", tk.END, values=(art.codigo, art.nombre, art.cantidad, f"${art.precio_base}", f"${art.precio_final}", art.stock_minimo))

        tk.Button(parent, text="Actualizar Vista", command=actualizar, bg="#546E7A", fg="white").pack(pady=5)
        actualizar()

    def construir_pestana_carga(self, parent):
        tk.Label(parent, text="Carga de Nuevo Material", font=("Segoe UI", 14, "bold")).pack(pady=10)
        
        f_form = tk.LabelFrame(parent, text="Datos del Producto", padx=20, pady=20)
        f_form.pack(padx=20, pady=10)

        tk.Label(f_form, text="Código:").grid(row=0, column=0, sticky="w", pady=5)
        e_cod = tk.Entry(f_form, width=25); e_cod.grid(row=0, column=1, padx=10, pady=5)
        tk.Label(f_form, text="Nombre:").grid(row=1, column=0, sticky="w", pady=5)
        e_nom = tk.Entry(f_form, width=25); e_nom.grid(row=1, column=1, padx=10, pady=5)
        tk.Label(f_form, text="Cantidad Inicial:").grid(row=2, column=0, sticky="w", pady=5)
        e_cant = tk.Entry(f_form, width=25); e_cant.grid(row=2, column=1, padx=10, pady=5)
        tk.Label(f_form, text="Precio Base Unitario:").grid(row=3, column=0, sticky="w", pady=5)
        e_prec = tk.Entry(f_form, width=25); e_prec.grid(row=3, column=1, padx=10, pady=5)
        tk.Label(f_form, text="Stock Mínimo:").grid(row=4, column=0, sticky="w", pady=5)
        e_min = tk.Entry(f_form, width=25); e_min.insert(0, "5"); e_min.grid(row=4, column=1, padx=10, pady=5)

        def guardar():
            if self.rol != "admin":
                messagebox.showwarning("Acceso Denegado", "Solo los administradores pueden registrar nuevos artículos.")
                return
            try:
                p_base = float(e_prec.get())
                p_final = PricingService.calcular_precio_inteligente(p_base)
                
                art = Articulo(
                    codigo=e_cod.get(),
                    nombre=e_nom.get(),
                    cantidad=int(e_cant.get()),
                    precio_base=p_base,
                    precio_final=p_final,
                    stock_minimo=int(e_min.get())
                )
                InventarioRepository.insertar(art)
                messagebox.showinfo("Éxito", f"Artículo guardado. Precio inteligente calculado: ${p_final}")
                e_cod.delete(0, tk.END); e_nom.delete(0, tk.END); e_cant.delete(0, tk.END); e_prec.delete(0, tk.END)
            except Exception as ex:
                messagebox.showerror("Error", f"No se pudo guardar el artículo: {ex}")

        tk.Button(parent, text="Guardar Artículo", bg="#0288D1", fg="white", 
                  font=("Segoe UI", 10, "bold"), command=guardar).pack(pady=15)

    def construir_pestana_historial(self, parent):
        tk.Label(parent, text="Auditoría de Ventas Realizadas", font=("Segoe UI", 14, "bold")).pack(pady=10)
        
        columns = ("ID Venta", "Fecha y Hora", "Total Recaudado")
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=12)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=200, anchor="center")
        tree.pack(pady=5)

        def actualizar():
            for row in tree.get_children(): tree.delete(row)
            for row in VentaRepository.obtener_historial():
                tree.insert("", tk.END, values=(row[0], row[1], f"${row[2]:.2f}"))

        tk.Button(parent, text="Actualizar Historial", command=actualizar, bg="#546E7A", fg="white").pack(pady=5)
        actualizar()