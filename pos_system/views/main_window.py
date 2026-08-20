# views/main_window.py
import tkinter as tk
from tkinter import ttk, messagebox
from services.sales_service import SalesService
from services.pricing_service import PricingService
from repositories.inventario_repo import InventarioRepository
from repositories.venta_repo import VentaRepository
from models.entidades import Articulo
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import config

class MainWindow(tk.Tk):
    def __init__(self, usuario: str, rol: str):
        super().__init__()
        self.usuario = usuario
        self.rol = rol
        self.title(f"POS Pro - Comercial | Usuario: {usuario} ({rol.upper()})")
        self.geometry("1000x720")
        
        self.crear_interfaz()

    def crear_interfaz(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        f_venta = ttk.Frame(nb)
        f_inventario = ttk.Frame(nb)
        f_carga = ttk.Frame(nb)
        f_historial = ttk.Frame(nb)
        f_config = ttk.Frame(nb)

        nb.add(f_venta, text="🛒 Caja Rápida")
        nb.add(f_inventario, text="📦 Gestión de Stock")
        nb.add(f_carga, text="➕ Nuevo Artículo")
        nb.add(f_historial, text="📊 Historial y Tendencias")
        
        if self.rol == "admin":
            nb.add(f_config, text="⚙️ Configuración Comercial")

        self.construir_pestana_venta(f_venta)
        self.construir_pestana_inventario(f_inventario)
        self.construir_pestana_carga(f_carga)
        self.construir_pestana_historial(f_historial)
        if self.rol == "admin":
            self.construir_pestana_config(f_config)

    def construir_pestana_venta(self, parent):
        tk.Label(parent, text="Terminal de Caja", font=("Segoe UI", 16, "bold")).pack(pady=15)
        
        f_form = tk.LabelFrame(parent, text="Cobro Ágil", font=("Segoe UI", 11, "bold"), padx=20, pady=20)
        f_form.pack(padx=20, pady=10, fill="x")

        tk.Label(f_form, text="Código del Artículo:", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", pady=8)
        e_cod = tk.Entry(f_form, width=25, font=("Segoe UI", 10)); e_cod.grid(row=0, column=1, padx=10, pady=8)

        tk.Label(f_form, text="Cantidad:", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", pady=8)
        e_cant = tk.Entry(f_form, width=25, font=("Segoe UI", 10)); e_cant.insert(0, "1"); e_cant.grid(row=1, column=1, padx=10, pady=8)

        def procesar():
            try:
                cantidad = int(e_cant.get())
                carrito = [(e_cod.get(), cantidad)]
                resultado = SalesService.procesar_venta(carrito)
                
                msg = f"🎫 TICKET N°: {resultado.venta_id}\n💰 Total a Pagar: ${resultado.total:.2f}\n\n¡Venta registrada con éxito!"
                if resultado.alertas_stock:
                    msg += "\n\n" + "\n".join(resultado.alertas_stock)
                
                messagebox.showinfo("Cobro Exitoso", msg)
                e_cod.delete(0, tk.END); e_cant.delete(0, tk.END); e_cant.insert(0, "1")
            except Exception as ex:
                messagebox.showerror("Error en Venta", str(ex))

        tk.Button(parent, text="💳 Cobrar e Imprimir Ticket", bg="#2E7D32", fg="white", 
                  font=("Segoe UI", 11, "bold"), padx=15, pady=8, command=procesar).pack(pady=25)

    def construir_pestana_inventario(self, parent):
        tk.Label(parent, text="Inventario y Edición de Stock", font=("Segoe UI", 16, "bold")).pack(pady=15)
        
        columns = ("Código", "Nombre", "Cantidad", "Precio Base", "Precio Final", "Mínimo")
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=10)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=130, anchor="center")
        tree.pack(pady=5, padx=10, fill="x")

        def actualizar():
            for row in tree.get_children(): tree.delete(row)
            for art in InventarioRepository.obtener_todos():
                tree.insert("", tk.END, values=(art.codigo, art.nombre, art.cantidad, f"${art.precio_base}", f"${art.precio_final}", art.stock_minimo))

        f_acciones = tk.LabelFrame(parent, text="Acciones de Modificación", font=("Segoe UI", 10, "bold"), padx=15, pady=15)
        f_acciones.pack(fill="x", padx=20, pady=15)

        tk.Label(f_acciones, text="Código a Editar:").grid(row=0, column=0, sticky="w", pady=5)
        e_m_cod = tk.Entry(f_acciones, width=15); e_m_cod.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(f_acciones, text="Nueva Cantidad Stock:").grid(row=0, column=2, sticky="w", pady=5)
        e_m_cant = tk.Entry(f_acciones, width=15); e_m_cant.grid(row=0, column=3, padx=5, pady=5)

        tk.Label(f_acciones, text="Nuevo Precio Base:").grid(row=1, column=0, sticky="w", pady=5)
        e_m_base = tk.Entry(f_acciones, width=15); e_m_base.grid(row=1, column=1, padx=5, pady=5)

        def ejecutar_edicion():
            try:
                codigo = e_m_cod.get()
                if not codigo:
                    messagebox.showerror("Error", "Debe especificar el código del artículo.")
                    return
                
                campos = {}
                if e_m_cant.get():
                    campos["cantidad"] = int(e_m_cant.get())
                if e_m_base.get():
                    nuevo_base = float(e_m_base.get())
                    campos["precio_base"] = nuevo_base
                    campos["precio_final"] = PricingService.calcular_precio_inteligente(nuevo_base)

                if not campos:
                    messagebox.showwarning("Atención", "No hay campos para modificar.")
                    return

                InventarioRepository.actualizar(codigo, campos)
                messagebox.showinfo("Éxito", "Artículo modificado correctamente.")
                actualizar()
            except Exception as ex:
                messagebox.showerror("Error", str(ex))

        def ejecutar_eliminacion():
            if self.rol != "admin":
                messagebox.showwarning("Acceso Denegado", "Solo el administrador puede eliminar artículos.")
                return
            codigo = e_m_cod.get()
            if codigo and messagebox.askyesno("Confirmar", f"¿Eliminar el artículo {codigo}?"):
                InventarioRepository.eliminar(codigo)
                actualizar()
                messagebox.showinfo("Eliminado", "Artículo borrado del inventario.")

        tk.Button(f_acciones, text="💾 Guardar Cambios", bg="#0288D1", fg="white", font=("Segoe UI", 9, "bold"), command=ejecutar_edicion).grid(row=2, column=1, pady=10)
        if self.rol == "admin":
            tk.Button(f_acciones, text="🗑️ Eliminar Artículo", bg="#D32F2F", fg="white", font=("Segoe UI", 9, "bold"), command=ejecutar_eliminacion).grid(row=2, column=2, pady=10)

        tk.Button(parent, text="🔄 Actualizar Tabla", command=actualizar, bg="#546E7A", fg="white").pack(pady=5)
        actualizar()

    def construir_pestana_carga(self, parent):
        tk.Label(parent, text="Alta de Nuevo Artículo", font=("Segoe UI", 16, "bold")).pack(pady=15)
        
        f_form = tk.LabelFrame(parent, text="Información del Producto", font=("Segoe UI", 11, "bold"), padx=20, pady=20)
        f_form.pack(padx=20, pady=10)

        tk.Label(f_form, text="Código Único:").grid(row=0, column=0, sticky="w", pady=8)
        e_cod = tk.Entry(f_form, width=25); e_cod.grid(row=0, column=1, padx=10, pady=8)
        tk.Label(f_form, text="Nombre del Producto:").grid(row=1, column=0, sticky="w", pady=8)
        e_nom = tk.Entry(f_form, width=25); e_nom.grid(row=1, column=1, padx=10, pady=8)
        tk.Label(f_form, text="Cantidad Inicial:").grid(row=2, column=0, sticky="w", pady=8)
        e_cant = tk.Entry(f_form, width=25); e_cant.grid(row=2, column=1, padx=10, pady=8)
        tk.Label(f_form, text="Precio Base (Costo):").grid(row=3, column=0, sticky="w", pady=8)
        e_prec = tk.Entry(f_form, width=25); e_prec.grid(row=3, column=1, padx=10, pady=8)
        tk.Label(f_form, text="Stock Mínimo de Alerta:").grid(row=4, column=0, sticky="w", pady=8)
        e_min = tk.Entry(f_form, width=25); e_min.insert(0, "5"); e_min.grid(row=4, column=1, padx=10, pady=8)

        def guardar():
            if self.rol != "admin":
                messagebox.showwarning("Acceso Denegado", "Solo el administrador puede dar de alta nuevos productos.")
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
                messagebox.showinfo("Éxito", f"Producto registrado. Precio Inteligente Aplicado: ${p_final}")
                e_cod.delete(0, tk.END); e_nom.delete(0, tk.END); e_cant.delete(0, tk.END); e_prec.delete(0, tk.END)
            except Exception as ex:
                messagebox.showerror("Error", f"No se pudo guardar: {ex}")

        tk.Button(parent, text="➕ Registrar en Inventario", bg="#0288D1", fg="white", 
                  font=("Segoe UI", 11, "bold"), padx=10, pady=8, command=guardar).pack(pady=20)

    def construir_pestana_historial(self, parent):
        tk.Label(parent, text="Historial de Ventas y Tendencias de Compra", font=("Segoe UI", 16, "bold")).pack(pady=10)

        f_split = tk.Frame(parent)
        f_split.pack(fill="both", expand=True, padx=10, pady=5)

        f_left = tk.Frame(f_split)
        f_left.pack(side="left", fill="both", expand=True, padx=5)

        columns = ("ID", "Fecha", "Total")
        tree_h = ttk.Treeview(f_left, columns=columns, show="headings", height=12)
        for col in columns:
            tree_h.heading(col, text=col)
            tree_h.column(col, width=100, anchor="center")
        tree_h.pack(pady=5)

        def actualizar_todo():
            for row in tree_h.get_children(): tree_h.delete(row)
            for row in VentaRepository.obtener_historial():
                tree_h.insert("", tk.END, values=(row[0], row[1], f"${row[2]:.2f}"))
            actualizar_grafico()

        tk.Button(f_left, text="🔄 Actualizar Datos", command=actualizar_todo, bg="#546E7A", fg="white").pack(pady=5)

        f_right = tk.LabelFrame(f_split, text="📈 Tendencia: Productos Más Vendidos", font=("Segoe UI", 10, "bold"))
        f_right.pack(side="right", fill="both", expand=True, padx=5)

        fig, ax = plt.subplots(figsize=(4, 3), dpi=100)

        def actualizar_grafico():
            ax.clear()
            datos = VentaRepository.obtener_tendencias_productos()
            if datos:
                productos = [d[0] for d in datos]
                cantidades = [d[1] for d in datos]
                ax.bar(productos, cantidades, color="#2E7D32")
                ax.set_title("Top Artículos Vendidos", fontsize=10)
                ax.tick_params(axis='x', rotation=25, labelsize=8)
            else:
                ax.text(0.5, 0.5, "Sin ventas registradas", horizontalalignment='center', verticalalignment='center')
            fig.tight_layout()
            canvas.draw()

        canvas = FigureCanvasTkAgg(fig, master=f_right)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        actualizar_todo()

    def construir_pestana_config(self, parent):
        tk.Label(parent, text="Configuración Comercial Global (Ubicación / Impuestos)", font=("Segoe UI", 16, "bold")).pack(pady=15)
        
        f_form = tk.LabelFrame(parent, text="Parámetros del Subsistema de Precios", font=("Segoe UI", 11, "bold"), padx=20, pady=20)
        f_form.pack(padx=20, pady=10)

        tk.Label(f_form, text="Impuestos (%):").grid(row=0, column=0, sticky="w", pady=8)
        e_imp = tk.Entry(f_form, width=20); e_imp.insert(0, str(config.IMPUESTOS_PCT)); e_imp.grid(row=0, column=1, padx=10, pady=8)

        tk.Label(f_form, text="Inflación Proyectada (%):").grid(row=1, column=0, sticky="w", pady=8)
        e_inf = tk.Entry(f_form, width=20); e_inf.insert(0, str(config.INFLACION_PCT)); e_inf.grid(row=1, column=1, padx=10, pady=8)

        tk.Label(f_form, text="Logística Fija ($):").grid(row=2, column=0, sticky="w", pady=8)
        e_log = tk.Entry(f_form, width=20); e_log.insert(0, str(config.LOGISTICA_FIJA)); e_log.grid(row=2, column=1, padx=10, pady=8)

        def guardar_config():
            try:
                config.IMPUESTOS_PCT = float(e_imp.get())
                config.INFLACION_PCT = float(e_inf.get())
                config.LOGISTICA_FIJA = float(e_log.get())
                messagebox.showinfo("Configuración Actualizada", "Parámetros comerciales modificados para futuras altas de precios.")
            except ValueError:
                messagebox.showerror("Error", "Ingrese valores numéricos válidos.")

        tk.Button(parent, text="💾 Guardar Cambios de Ubicación", bg="#2E7D32", fg="white", 
                  font=("Segoe UI", 11, "bold"), padx=15, pady=8, command=guardar_config).pack(pady=20)