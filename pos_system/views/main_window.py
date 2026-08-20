# views/main_window.py
import tkinter as tk
from tkinter import ttk, messagebox
from services.sales_service import SalesService
from services.pricing_service import PricingService
from services.report_service import ReportService
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
        self.geometry("1100x750")
        
        self.crear_interfaz()

    def crear_interfaz(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        f_venta = ttk.Frame(nb)
        f_inventario = ttk.Frame(nb)
        f_carga = ttk.Frame(nb)
        f_historial = ttk.Frame(nb)
        f_promo = ttk.Frame(nb)
        f_chatbot = ttk.Frame(nb)
        f_config = ttk.Frame(nb)

        nb.add(f_venta, text="🛒 Caja Rápida")
        nb.add(f_inventario, text="📦 Inventario y Filtros")
        nb.add(f_carga, text="➕ Altas & Etiquetas")
        nb.add(f_historial, text="📊 Historial & Reportes")
        nb.add(f_promo, text="🏷️ Promociones (2x1)")
        nb.add(f_chatbot, text="🤖 Asistente Chatbot")
        
        if self.rol == "admin":
            nb.add(f_config, text="⚙️ Configuración")

        self.construir_pestana_venta(f_venta)
        self.construir_pestana_inventario(f_inventario)
        self.construir_pestana_carga(f_carga)
        self.construir_pestana_historial(f_historial)
        self.construir_pestana_promo(f_promo)
        self.construir_pestana_chatbot(f_chatbot)
        if self.rol == "admin":
            self.construir_pestana_config(f_config)

    def construir_pestana_venta(self, parent):
        tk.Label(parent, text="Terminal de Caja Inteligente", font=("Segoe UI", 16, "bold")).pack(pady=15)
        
        f_form = tk.LabelFrame(parent, text="Cobro Ágil (Aplica Promociones Automáticas)", font=("Segoe UI", 11, "bold"), padx=20, pady=20)
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
        tk.Label(parent, text="Inventario, Filtros y Edición por Clic", font=("Segoe UI", 16, "bold")).pack(pady=10)
        
        # Barra de Filtros y Búsqueda
        f_filtros = tk.Frame(parent)
        f_filtros.pack(fill="x", padx=10, pady=5)
        
        tk.Label(f_filtros, text="Buscar:").pack(side="left", padx=5)
        e_buscar = tk.Entry(f_filtros, width=20); e_buscar.pack(side="left", padx=5)
        
        tk.Label(f_filtros, text="Ordenar por:").pack(side="left", padx=5)
        cb_orden = ttk.Combobox(f_filtros, values=["Nombre (A-Z)", "Precio (Mayor a Menor)", "Precio (Menor a Mayor)", "Stock Disponible"], state="readonly", width=22)
        cb_orden.pack(side="left", padx=5)
        cb_orden.current(0)

        columns = ("Código", "Nombre", "Cantidad", "Precio Base", "Precio Final", "Mínimo")
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=10)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=130, anchor="center")
        tree.pack(pady=5, padx=10, fill="x")

        e_m_cod = tk.Entry(parent, width=15) # Oculto o referenciado para autocompletar al hacer clic

        f_acciones = tk.LabelFrame(parent, text="Edición de Producto Seleccionado", font=("Segoe UI", 10, "bold"), padx=15, pady=10)
        f_acciones.pack(fill="x", padx=20, pady=10)

        tk.Label(f_acciones, text="Código:").grid(row=0, column=0, sticky="w")
        lbl_sel_cod = tk.Label(f_acciones, text="---", font=("Segoe UI", 9, "bold")); lbl_sel_cod.grid(row=0, column=1, sticky="w", padx=5)

        tk.Label(f_acciones, text="Nueva Cantidad:").grid(row=0, column=2, sticky="w", padx=5)
        e_m_cant = tk.Entry(f_acciones, width=12); e_m_cant.grid(row=0, column=3, padx=5)

        tk.Label(f_acciones, text="Nuevo Precio Base:").grid(row=0, column=4, sticky="w", padx=5)
        e_m_base = tk.Entry(f_acciones, width=12); e_m_base.grid(row=0, column=5, padx=5)

        def al_seleccionar_fila(event):
            selected_item = tree.selection()
            if selected_item:
                valores = tree.item(selected_item, "values")
                lbl_sel_cod.config(text=valores[0])
                e_m_cant.delete(0, tk.END); e_m_cant.insert(0, valores[2])
                e_m_base.delete(0, tk.END); e_m_base.insert(0, valores[3].replace("$", ""))

        tree.bind("<<TreeviewSelect>>", al_seleccionar_fila)

        def actualizar():
            for row in tree.get_children(): tree.delete(row)
            articulos = InventarioRepository.obtener_todos()
            
            # Aplicar filtro de búsqueda
            texto_busqueda = e_buscar.get().lower()
            if texto_busqueda:
                articulos = [a for a in articulos if texto_busqueda in a.nombre.lower() or texto_busqueda in a.codigo.lower()]
            
            # Aplicar ordenamiento
            criterio = cb_orden.get()
            if criterio == "Nombre (A-Z)":
                articulos.sort(key=lambda x: x.nombre)
            elif criterio == "Precio (Mayor a Menor)":
                articulos.sort(key=lambda x: x.precio_final, reverse=True)
            elif criterio == "Precio (Menor a Mayor)":
                articulos.sort(key=lambda x: x.precio_final)
            elif criterio == "Stock Disponible":
                articulos.sort(key=lambda x: x.cantidad, reverse=True)

            for art in articulos:
                tree.insert("", tk.END, values=(art.codigo, art.nombre, art.cantidad, f"${art.precio_base}", f"${art.precio_final}", art.stock_minimo))

        def ejecutar_edicion():
            try:
                codigo = lbl_sel_cod.cget("text")
                if codigo == "---":
                    messagebox.showerror("Error", "Seleccione un producto de la tabla haciendo clic.")
                    return
                campos = {"cantidad": int(e_m_cant.get())}
                nuevo_base = float(e_m_base.get())
                campos["precio_base"] = nuevo_base
                campos["precio_final"] = PricingService.calcular_precio_inteligente(nuevo_base)

                InventarioRepository.actualizar(codigo, campos)
                messagebox.showinfo("Éxito", "Producto actualizado correctamente.")
                actualizar()
            except Exception as ex:
                messagebox.showerror("Error", str(ex))

        def ejecutar_eliminacion():
            if self.rol != "admin":
                messagebox.showwarning("Denegado", "Solo admin puede eliminar.")
                return
            codigo = lbl_sel_cod.cget("text")
            if codigo != "---" and messagebox.askyesno("Confirmar", f"¿Eliminar {codigo}?"):
                InventarioRepository.eliminar(codigo)
                actualizar()
                messagebox.showinfo("Éxito", "Artículo eliminado.")

        tk.Button(f_acciones, text="💾 Guardar Cambios", bg="#0288D1", fg="white", command=ejecutar_edicion).grid(row=0, column=6, padx=10)
        if self.rol == "admin":
            tk.Button(f_acciones, text="🗑️ Eliminar", bg="#D32F2F", fg="white", command=ejecutar_eliminacion).grid(row=0, column=7, padx=5)

        tk.Button(parent, text="🔍 Aplicar Filtros / Buscar", command=actualizar, bg="#546E7A", fg="white").pack(pady=5)
        actualizar()

    def construir_pestana_carga(self, parent):
        tk.Label(parent, text="Alta de Productos y Gestión de Etiquetas", font=("Segoe UI", 16, "bold")).pack(pady=10)
        
        f_form = tk.LabelFrame(parent, text="Nuevo Producto", font=("Segoe UI", 10, "bold"), padx=15, pady=10)
        f_form.pack(padx=20, pady=5, fill="x")

        tk.Label(f_form, text="Código:").grid(row=0, column=0, sticky="w"); e_cod = tk.Entry(f_form, width=20); e_cod.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(f_form, text="Nombre:").grid(row=0, column=2, sticky="w"); e_nom = tk.Entry(f_form, width=20); e_nom.grid(row=0, column=3, padx=5, pady=5)
        tk.Label(f_form, text="Cantidad:").grid(row=1, column=0, sticky="w"); e_cant = tk.Entry(f_form, width=20); e_cant.grid(row=1, column=1, padx=5, pady=5)
        tk.Label(f_form, text="Precio Base:").grid(row=1, column=2, sticky="w"); e_prec = tk.Entry(f_form, width=20); e_prec.grid(row=1, column=3, padx=5, pady=5)

        def guardar():
            try:
                p_base = float(e_prec.get())
                p_final = PricingService.calcular_precio_inteligente(p_base)
                art = Articulo(codigo=e_cod.get(), nombre=e_nom.get(), cantidad=int(e_cant.get()), precio_base=p_base, precio_final=p_final, stock_minimo=5)
                InventarioRepository.insertar(art)
                messagebox.showinfo("Éxito", f"Registrado con precio final: ${p_final}")
            except Exception as ex:
                messagebox.showerror("Error", str(ex))

        tk.Button(f_form, text="Registrar Producto", bg="#0288D1", fg="white", command=guardar).grid(row=2, column=1, columnspan=2, pady=10)

        # Sección de Etiquetas
        f_etq = tk.LabelFrame(parent, text="Gestión de Etiquetas (#harinas, #limpieza, etc.)", font=("Segoe UI", 10, "bold"), padx=15, pady=10)
        f_etq.pack(padx=20, pady=10, fill="x")

        tk.Label(f_etq, text="Nueva Etiqueta:").grid(row=0, column=0, sticky="w")
        e_etq_nombre = tk.Entry(f_etq, width=15); e_etq_nombre.grid(row=0, column=1, padx=5)

        def crear_etiqueta():
            if self.rol != "admin": return messagebox.showwarning("Denegado", "Solo admin.")
            InventarioRepository.gestionar_etiqueta(e_etq_nombre.get())
            messagebox.showinfo("Éxito", "Etiqueta creada.")
            actualizar_combos_etiquetas()

        tk.Button(f_etq, text="Crear Etiqueta", bg="#2E7D32", fg="white", command=crear_etiqueta).grid(row=0, column=2, padx=5)

        tk.Label(f_etq, text="Código Art.:").grid(row=1, column=0, sticky="w", pady=10)
        e_etq_prod = tk.Entry(f_etq, width=15); e_etq_prod.grid(row=1, column=1, padx=5)
        
        tk.Label(f_etq, text="Seleccionar Etiqueta:").grid(row=1, column=2, sticky="w")
        cb_etiquetas = ttk.Combobox(f_etq, state="readonly", width=15)
        cb_etiquetas.grid(row=1, column=3, padx=5)

        def actualizar_combos_etiquetas():
            etq = InventarioRepository.obtener_etiquetas()
            cb_etiquetas['values'] = [f"{e[0]}: {e[1]}" for e in etq]

        def asociar():
            try:
                sel = cb_etiquetas.get()
                etq_id = int(sel.split(":")[0])
                InventarioRepository.asignar_etiqueta_a_producto(e_etq_prod.get(), etq_id)
                messagebox.showinfo("Éxito", "Etiqueta asociada al producto.")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        tk.Button(f_etq, text="Asociar a Producto", bg="#546E7A", fg="white", command=asociar).grid(row=1, column=4, padx=5)
        actualizar_combos_etiquetas()

    def construir_pestana_historial(self, parent):
        tk.Label(parent, text="Historial, Tendencias y Exportación", font=("Segoe UI", 16, "bold")).pack(pady=10)

        f_split = tk.Frame(parent)
        f_split.pack(fill="both", expand=True, padx=10, pady=5)

        f_left = tk.Frame(f_split)
        f_left.pack(side="left", fill="both", expand=True, padx=5)

        columns = ("ID", "Fecha", "Total")
        tree_h = ttk.Treeview(f_left, columns=columns, show="headings", height=10)
        for col in columns:
            tree_h.heading(col, text=col)
            tree_h.column(col, width=90, anchor="center")
        tree_h.pack(pady=5)

        # Botones de Exportación
        f_exp = tk.LabelFrame(f_left, text="Exportar & Enviar Reportes", padx=10, pady=10)
        f_exp.pack(fill="x", pady=5)

        def exp_excel():
            f = ReportService.exportar_excel()
            messagebox.showinfo("Exportado", f"Excel guardado en {f}")

        def exp_pdf():
            f = ReportService.exportar_pdf()
            messagebox.showinfo("Exportado", f"PDF guardado en {f}")

        def enviar_correo():
            f = ReportService.exportar_pdf()
            ok = ReportService.enviar_correo_gmail("destinatario@gmail.com", "Reporte Inventario POS Pro", "Adjunto reporte actualizado.", f)
            if ok: messagebox.showinfo("Correo", "Enviado con éxito a Gmail.")
            else: messagebox.showerror("Error", "No se pudo enviar. Revisa credenciales SMTP.")

        tk.Button(f_exp, text="📊 Excel", bg="#1B5E20", fg="white", command=exp_excel).pack(side="left", padx=2)
        tk.Button(f_exp, text="📄 PDF", bg="#B71C1C", fg="white", command=exp_pdf).pack(side="left", padx=2)
        tk.Button(f_exp, text="📧 Enviar Gmail", bg="#0D47A1", fg="white", command=enviar_correo).pack(side="left", padx=2)

        f_right = tk.LabelFrame(f_split, text="📈 Tendencia Top Ventas")
        f_right.pack(side="right", fill="both", expand=True, padx=5)

        fig, ax = plt.subplots(figsize=(4, 3), dpi=100)
        def actualizar_todo():
            for row in tree_h.get_children(): tree_h.delete(row)
            for row in VentaRepository.obtener_historial():
                tree_h.insert("", tk.END, values=(row[0], row[1], f"${row[2]:.2f}"))
            ax.clear()
            datos = VentaRepository.obtener_tendencias_productos()
            if datos:
                ax.bar([d[0] for d in datos], [d[1] for d in datos], color="#2E7D32")
                ax.tick_params(axis='x', rotation=25, labelsize=8)
            fig.tight_layout()
            canvas.draw()

        canvas = FigureCanvasTkAgg(fig, master=f_right)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        actualizar_todo()

    def construir_pestana_promo(self, parent):
        tk.Label(parent, text="Módulo de Promociones (Ej: 2x1 en Harinas)", font=("Segoe UI", 16, "bold")).pack(pady=15)
        
        f_form = tk.LabelFrame(parent, text="Crear Promoción", padx=20, pady=20)
        f_form.pack(padx=20, pady=10)

        tk.Label(f_form, text="Código Artículo:").grid(row=0, column=0, sticky="w", pady=5)
        e_cod = tk.Entry(f_form, width=20); e_cod.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(f_form, text="Tipo de Promoción:").grid(row=1, column=0, sticky="w", pady=5)
        cb_tipo = ttk.Combobox(f_form, values=["2X1"], state="readonly", width=18)
        cb_tipo.current(0); cb_tipo.grid(row=1, column=1, padx=10, pady=5)

        def guardar_promo():
            try:
                InventarioRepository.guardar_promocion(e_cod.get(), cb_tipo.get(), 0.0)
                messagebox.showinfo("Éxito", "Promoción aplicada correctamente al artículo.")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        tk.Button(parent, text="💾 Activar Promoción", bg="#2E7D32", fg="white", command=guardar_promo).pack(pady=20)

    def construir_pestana_chatbot(self, parent):
        tk.Label(parent, text="🤖 Asistente Virtual POS Pro", font=("Segoe UI", 16, "bold")).pack(pady=15)
        
        f_chat = tk.LabelFrame(parent, text="Consulta al Sistema", padx=15, pady=15)
        f_chat.pack(padx=20, pady=10, fill="both", expand=True)

        txt_chat = tk.Text(f_chat, height=12, state="disabled", font=("Segoe UI", 10))
        txt_chat.pack(fill="both", expand=True, pady=5)

        f_input = tk.Frame(parent)
        f_input.pack(fill="x", padx=20, pady=10)

        e_pregunta = tk.Entry(f_input, width=60, font=("Segoe UI", 10))
        e_pregunta.pack(side="left", padx=5)

        def responder():
            pregunta = e_pregunta.get().lower()
            txt_chat.config(state="normal")
            txt_chat.insert(tk.END, f"Tú: {e_pregunta.get()}\n")
            
            respuesta = "No entiendo tu consulta. Prueba preguntando por 'stock', 'precio' o 'ventas'."
            if "stock" in pregunta or "cuanto hay" in pregunta:
                total_arts = len(InventarioRepository.obtener_todos())
                respuesta = f"Asistente: Actualmente tienes {total_arts} productos registrados en inventario."
            elif "ventas" in pregunta or "recaudado" in pregunta:
                hist = VentaRepository.obtener_historial()
                total_recaudado = sum([h[2] for h in hist])
                respuesta = f"Asistente: Se han registrado {len(hist)} ventas con una recaudación total de ${total_recaudado:.2f}."
            elif "ayuda" in pregunta:
                respuesta = "Asistente: Puedo informarte sobre el estado del stock, total de ventas y control general."

            txt_chat.insert(tk.END, f"{respuesta}\n\n")
            txt_chat.config(state="disabled")
            e_pregunta.delete(0, tk.END)

        tk.Button(f_input, text="Preguntar", bg="#0288D1", fg="white", command=responder).pack(side="left", padx=5)

    def construir_pestana_config(self, parent):
        tk.Label(parent, text="Configuración Comercial Global", font=("Segoe UI", 16, "bold")).pack(pady=15)
        f_form = tk.LabelFrame(parent, text="Parámetros de Ubicación", padx=20, pady=20)
        f_form.pack(padx=20, pady=10)

        tk.Label(f_form, text="Impuestos (%):").grid(row=0, column=0, sticky="w", pady=8)
        e_imp = tk.Entry(f_form, width=20); e_imp.insert(0, str(config.IMPUESTOS_PCT)); e_imp.grid(row=0, column=1, padx=10, pady=8)

        def guardar_config():
            try:
                config.IMPUESTOS_PCT = float(e_imp.get())
                messagebox.showinfo("Guardado", "Parámetros actualizados.")
            except ValueError:
                messagebox.showerror("Error", "Valor numérico inválido.")

        tk.Button(parent, text="💾 Guardar", bg="#2E7D32", fg="white", command=guardar_config).pack(pady=20)