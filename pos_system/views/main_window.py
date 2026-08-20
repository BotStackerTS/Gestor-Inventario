# views/main_window.py
import tkinter as tk
from tkinter import ttk, messagebox

from database.connection import DatabaseConnection
from services.sales_service import SalesService
from services.pricing_service import PricingService
from repositories.inventario_repo import InventarioRepository
from models.entidades import Articulo
import config


class MainWindow(tk.Tk):
    """Ventana principal del POS optimizada para cajeros, lectores y diseño minimalista."""

    REFRESH_MS = 750

    BG_COLOR = "#F8F9FA"
    CARD_BG = "#FFFFFF"
    PRIMARY = "#1A1A1A"
    ACCENT = "#2563EB"
    SUCCESS = "#16A34A"
    DANGER = "#DC2626"
    TEXT_MAIN = "#1F2937"
    TEXT_MUTED = "#6B7280"
    BORDER_COLOR = "#E5E7EB"

    def __init__(self, usuario: str, rol: str):
        super().__init__()
        self.usuario = usuario
        self.rol = rol
        self.title(f"POS Pro — {usuario.capitalize()} ({rol.upper()})")
        self.geometry("1200x800")
        self.minsize(950, 700)
        self.configure(bg=self.BG_COLOR)

        self._refresh_inventory_view = None
        self._refresh_faltantes_view = None
        self._refresh_promos_view = None

        self._configurar_estilos()
        self.crear_interfaz()
        self.after(self.REFRESH_MS, self._sincronizar_vistas)

    def _configurar_estilos(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TNotebook", background=self.BG_COLOR, borderwidth=0)
        style.configure(
            "TNotebook.Tab", 
            background="#E9ECEF", 
            foreground=self.TEXT_MAIN,
            padding=(16, 10),
            font=("Segoe UI", 10, "bold")
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.CARD_BG)],
            foreground=[("selected", self.ACCENT)]
        )

        style.configure("TFrame", background=self.BG_COLOR)
        style.configure("TLabelframe", background=self.CARD_BG, bordercolor=self.BORDER_COLOR, relief="solid")
        style.configure("TLabelframe.Label", background=self.CARD_BG, foreground=self.TEXT_MAIN, font=("Segoe UI", 10, "bold"))
        
        style.configure(
            "Treeview",
            background=self.CARD_BG,
            foreground=self.TEXT_MAIN,
            fieldbackground=self.CARD_BG,
            rowheight=26,
            font=("Segoe UI", 9)
        )
        style.configure(
            "Treeview.Heading",
            background="#F1F3F5",
            foreground=self.TEXT_MAIN,
            font=("Segoe UI", 9, "bold")
        )

    def crear_interfaz(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=16, pady=16)

        f_caja = ttk.Frame(nb)
        nb.add(f_caja, text="  🛒  Caja Rápida  ")
        self._construir_seguro(self.construir_pestana_caja, f_caja, "Caja")

        if self.rol == "admin":
            vistas_admin = [
                ("  📦  Inventario  ", self.construir_pestana_inventario),
                ("  🏷️  Promociones  ", self.construir_pestana_promociones),
                ("  ⚙️  Configuración  ", self.construir_pestana_config),
                ("  🔖  Etiquetas  ", self.construir_pestana_etiquetas),
            ]
            for titulo, constructor in vistas_admin:
                frame = ttk.Frame(nb)
                nb.add(frame, text=titulo)
                self._construir_seguro(constructor, frame, titulo.strip())

        f_faltantes = ttk.Frame(nb)
        nb.add(f_faltantes, text="  ⚠️  Faltantes  ")
        self._construir_seguro(self.construir_pestana_faltantes, f_faltantes, "Faltantes")

        f_chatbot = ttk.Frame(nb)
        nb.add(f_chatbot, text="  🤖  Reportes & IA  ")
        self._construir_seguro(self.construir_pestana_chatbot, f_chatbot, "Asistente Virtual")

    def _construir_seguro(self, constructor, parent, nombre):
        try:
            constructor(parent)
        except Exception as exc:
            for widget in parent.winfo_children():
                widget.destroy()
            ttk.Label(
                parent,
                text=f"No se pudo cargar {nombre}.\n{exc}",
                justify="center",
            ).pack(expand=True, padx=20, pady=20)

    def _sincronizar_vistas(self):
        try:
            if callable(self._refresh_inventory_view):
                self._refresh_inventory_view(silencioso=True)
            if callable(self._refresh_faltantes_view):
                self._refresh_faltantes_view(silencioso=True)
            if callable(self._refresh_promos_view):
                self._refresh_promos_view(silencioso=True)
        except tk.TclError:
            return
        except Exception:
            pass
        finally:
            try:
                if self.winfo_exists():
                    self.after(self.REFRESH_MS, self._sincronizar_vistas)
            except tk.TclError:
                pass

    def construir_pestana_caja(self, parent):
        tk.Label(
            parent,
            text="Terminal de Cobro (Optimizado para Lector de Barras)",
            font=("Segoe UI", 16, "bold"),
            bg=self.BG_COLOR,
            fg=self.PRIMARY
        ).pack(pady=16)

        f_form = ttk.LabelFrame(parent, text=" Escaneo y Cobro ", padding=20)
        f_form.pack(padx=20, pady=10, fill="x")

        ttk.Label(f_form, text="Código Artículo / Escáner:").grid(row=0, column=0, sticky="w", pady=8)
        e_cod = ttk.Entry(f_form, width=30, font=("Segoe UI", 11))
        e_cod.grid(row=0, column=1, padx=12, pady=8)
        e_cod.focus()

        ttk.Label(f_form, text="Cantidad:").grid(row=1, column=0, sticky="w", pady=8)
        e_cant = ttk.Entry(f_form, width=15, font=("Segoe UI", 11))
        e_cant.insert(0, "1")
        e_cant.grid(row=1, column=1, sticky="w", padx=12, pady=8)

        def cobrar(event=None):
            try:
                codigo = e_cod.get().strip()
                cantidad_str = e_cant.get().strip()
                if not codigo:
                    return
                cantidad = int(cantidad_str) if cantidad_str else 1
                if cantidad <= 0:
                    raise ValueError("La cantidad debe ser mayor a cero.")

                art = InventarioRepository.obtener_por_codigo(codigo)
                if not art:
                    messagebox.showerror("Error", f"Artículo con código '{codigo}' no encontrado.")
                    e_cod.delete(0, tk.END)
                    return
                if cantidad > art.cantidad:
                    messagebox.showerror("Stock insuficiente", f"Stock disponible: {art.cantidad}")
                    return

                promo = InventarioRepository.verificar_promocion_activa(codigo)
                cantidad_cobrar = cantidad
                monto_total = art.precio_final * cantidad
                promo_txt = "Ninguna"

                if promo:
                    tipo_p, valor_p = promo
                    if tipo_p == "2X1":
                        gratis = cantidad // 2
                        cantidad_cobrar = cantidad - gratis
                        monto_total = art.precio_final * cantidad_cobrar
                        promo_txt = f"Promoción 2x1 Aplicada (-{gratis} sin cargo)"
                    elif tipo_p == "PORCENTAJE":
                        descuento = monto_total * (float(valor_p) / 100)
                        monto_total -= descuento
                        promo_txt = f"Descuento de {valor_p}% aplicado"

                resultado = SalesService.procesar_venta([(codigo, cantidad_cobrar)])
                
                detalle_txt = (
                    f"🎫 TICKET DE VENTA #{resultado.venta_id}\n"
                    "----------------------------------------\n"
                    f"Producto: {art.nombre}\n"
                    f"Cantidad: {cantidad}\n"
                    f"Promoción: {promo_txt}\n"
                    "----------------------------------------\n"
                    f"💰 TOTAL PAGADO: ${monto_total:.2f}"
                )
                messagebox.showinfo("Ticket Exitoso", detalle_txt)
                e_cod.delete(0, tk.END)
                e_cant.delete(0, tk.END)
                e_cant.insert(0, "1")
                e_cod.focus()
            except ValueError as exc:
                messagebox.showerror("Error", str(exc))
            except Exception as exc:
                messagebox.showerror("Error al procesar la venta", str(exc))

        e_cod.bind("<Return>", cobrar)

        tk.Button(
            parent,
            text="💳 Procesar Venta / Cobrar (Enter)",
            bg=self.SUCCESS,
            fg="white",
            relief="flat",
            padx=16,
            pady=10,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
            command=cobrar,
        ).pack(pady=20)

    def construir_pestana_inventario(self, parent):
        tk.Label(
            parent,
            text="Gestión Integral de Inventario",
            font=("Segoe UI", 15, "bold"),
            bg=self.BG_COLOR,
            fg=self.PRIMARY
        ).pack(pady=10)

        f_nuevo = ttk.LabelFrame(parent, text=" ➕ Registrar Nuevo Producto ", padding=12)
        f_nuevo.pack(fill="x", padx=16, pady=6)

        ttk.Label(f_nuevo, text="Código:").grid(row=0, column=0, sticky="w", padx=4)
        e_n_cod = ttk.Entry(f_nuevo, width=12)
        e_n_cod.grid(row=0, column=1, padx=4)
        
        ttk.Label(f_nuevo, text="Nombre:").grid(row=0, column=2, sticky="w", padx=4)
        e_n_nom = ttk.Entry(f_nuevo, width=16)
        e_n_nom.grid(row=0, column=3, padx=4)
        
        ttk.Label(f_nuevo, text="Cantidad:").grid(row=0, column=4, sticky="w", padx=4)
        e_n_cant = ttk.Entry(f_nuevo, width=8)
        e_n_cant.grid(row=0, column=5, padx=4)
        
        ttk.Label(f_nuevo, text="Precio ($):").grid(row=0, column=6, sticky="w", padx=4)
        e_n_precio = ttk.Entry(f_nuevo, width=10)
        e_n_precio.grid(row=0, column=7, padx=4)

        def registrar_nuevo_producto():
            try:
                codigo = e_n_cod.get().strip()
                nombre = e_n_nom.get().strip()
                cantidad = int(e_n_cant.get())
                precio_base = float(e_n_precio.get())
                if not codigo or not nombre:
                    messagebox.showwarning("Aviso", "Código y Nombre son obligatorios.")
                    return
                if cantidad < 0 or precio_base < 0:
                    raise ValueError("Cantidad y precio no pueden ser negativos.")

                precio_final, _ = PricingService.calcular_detallado(precio_base)
                nuevo_art = Articulo(
                    codigo=codigo,
                    nombre=nombre,
                    cantidad=cantidad,
                    precio_base=precio_base,
                    precio_final=precio_final,
                    stock_minimo=5,
                )
                InventarioRepository.insertar(nuevo_art)
                self._refresh_inventory_view()
                self._refresh_faltantes_view()
                messagebox.showinfo("Éxito", f"Producto '{nombre}' agregado correctamente.")
                for entry in (e_n_cod, e_n_nom, e_n_cant, e_n_precio):
                    entry.delete(0, tk.END)
            except ValueError as exc:
                messagebox.showerror("Error", str(exc))
            except Exception as exc:
                messagebox.showerror("Error al guardar", str(exc))

        tk.Button(
            f_nuevo,
            text="Guardar",
            bg=self.SUCCESS,
            fg="white",
            relief="flat",
            padx=12,
            pady=4,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            command=registrar_nuevo_producto,
        ).grid(row=0, column=8, padx=12)

        f_filtro = ttk.Frame(parent)
        f_filtro.pack(fill="x", padx=16, pady=6)
        ttk.Label(f_filtro, text="Filtrar por Etiqueta:").pack(side="left", padx=4)
        combo_filtro = ttk.Combobox(f_filtro, state="readonly", width=22)
        combo_filtro.pack(side="left", padx=4)

        columns = ("Código", "Nombre", "Stock Disponible", "Base", "Final", "Mínimo")
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=5)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120, anchor="center")
        tree.pack(pady=4, padx=16, fill="x")

        lbl_sel = tk.Label(
            parent,
            text="Producto seleccionado: Ninguno",
            font=("Segoe UI", 9, "bold"),
            bg=self.BG_COLOR,
            fg=self.ACCENT
        )
        lbl_sel.pack(anchor="w", padx=16, pady=2)

        f_inferior = ttk.Frame(parent)
        f_inferior.pack(fill="x", padx=16, pady=4)

        f_stock = ttk.LabelFrame(f_inferior, text=" Ajuste Rápido de Stock ", padding=10)
        f_stock.pack(side="left", fill="both", expand=True, padx=(0, 8))

        ttk.Label(f_stock, text="Cantidad:").grid(row=0, column=0, sticky="w", pady=4)
        e_cant_stock = ttk.Entry(f_stock, width=12)
        e_cant_stock.grid(row=0, column=1, padx=6, pady=4)

        def actualizar_tabla(etiqueta=None, silencioso=False, codigo_seleccionado=None):
            etiqueta = etiqueta if etiqueta is not None else combo_filtro.get() or "Todas"
            if not tree.winfo_exists():
                return
            if codigo_seleccionado is None:
                sel = tree.selection()
                if sel:
                    codigo_seleccionado = str(tree.item(sel[0], "values")[0])

            try:
                articulos = InventarioRepository.obtener_todos(etiqueta)
                for row in tree.get_children():
                    tree.delete(row)
                nuevo_item = None
                for art in articulos:
                    item = tree.insert(
                        "",
                        tk.END,
                        values=(
                            art.codigo,
                            art.nombre,
                            art.cantidad,
                            f"${art.precio_base:.2f}",
                            f"${art.precio_final:.2f}",
                            art.stock_minimo,
                        ),
                    )
                    if art.codigo == codigo_seleccionado:
                        nuevo_item = item
                if nuevo_item:
                    tree.selection_set(nuevo_item)
                    tree.focus(nuevo_item)
                    seleccionar_item(None)
                else:
                    lbl_sel.config(text="Producto seleccionado: Ninguno")
                
                actualizar_histograma(articulos)
            except Exception as exc:
                if not silencioso:
                    messagebox.showerror("Error", f"No se pudo actualizar inventario: {exc}")

        f_histo = ttk.LabelFrame(f_inferior, text=" 📊 Histograma de Tendencia de Stock ", padding=10)
        f_histo.pack(side="right", fill="both", expand=True, padx=(8, 0))
        
        canvas_histo = tk.Canvas(f_histo, height=110, bg=self.CARD_BG, highlightthickness=0)
        canvas_histo.pack(fill="both", expand=True)

        def actualizar_histograma(articulos):
            canvas_histo.delete("all")
            if not articulos:
                canvas_histo.create_text(150, 55, text="Sin datos de stock disponibles", fill=self.TEXT_MUTED)
                return
            
            MUESTRA = articulos[:7]
            max_stock = max((a.cantidad for a in MUESTRA), default=10)
            if max_stock == 0:
                max_stock = 1

            canvas_width = 380
            ancho_barra = max(18, (canvas_width - 30) // len(MUESTRA))
            
            for i, art in enumerate(MUESTRA):
                x0 = 20 + i * (ancho_barra + 8)
                altura_relativa = (art.cantidad / max_stock) * 70
                y0 = 85 - altura_relativa
                x1 = x0 + ancho_barra
                y1 = 85
                
                color = self.DANGER if art.cantidad <= art.stock_minimo else self.SUCCESS
                
                canvas_histo.create_rectangle(x0, y0, x1, y1, fill=color, outline="")
                canvas_histo.create_text(x0 + ancho_barra/2, 97, text=art.nombre[:5], font=("Segoe UI", 8), fill=self.TEXT_MAIN)
                canvas_histo.create_text(x0 + ancho_barra/2, y0 - 8, text=str(art.cantidad), font=("Segoe UI", 8, "bold"), fill=self.TEXT_MAIN)

        def actualizar_etiquetas_combo(silencioso=False):
            try:
                etiquetas = InventarioRepository.obtener_etiquetas()
                valores = ["Todas"] + etiquetas
                actual = combo_filtro.get()
                combo_filtro["values"] = valores
                combo_filtro.set(actual if actual in valores else "Todas")
            except Exception as exc:
                combo_filtro["values"] = ["Todas"]
                combo_filtro.set("Todas")
                if not silencioso:
                    messagebox.showerror("Error", f"No se pudieron cargar las etiquetas: {exc}")

        def seleccionar_item(_event):
            sel = tree.selection()
            if sel:
                vals = tree.item(sel[0], "values")
                lbl_sel.config(
                    text=f"Seleccionado: [{vals[0]}] {vals[1]} | Stock actual: {vals[2]}"
                )
            else:
                lbl_sel.config(text="Producto seleccionado: Ninguno")

        combo_filtro.bind("<<ComboboxSelected>>", lambda _e: actualizar_tabla(combo_filtro.get()))
        tree.bind("<<TreeviewSelect>>", seleccionar_item)

        def operacion_stock(tipo):
            try:
                sel = tree.selection()
                if not sel:
                    messagebox.showwarning("Aviso", "Seleccione un producto de la tabla.")
                    return
                val = int(e_cant_stock.get())
                if val < 0:
                    raise ValueError("La cantidad no puede ser negativa.")
                codigo = str(tree.item(sel[0], "values")[0]).strip()
                art = InventarioRepository.obtener_por_codigo(codigo)
                if not art:
                    raise ValueError("El producto seleccionado ya no existe.")

                if tipo == "agregar":
                    nuevo_total = art.cantidad + val
                elif tipo == "eliminar":
                    nuevo_total = max(0, art.cantidad - val)
                else:
                    nuevo_total = val

                InventarioRepository.actualizar(codigo, {"cantidad": nuevo_total})
                actualizar_tabla(combo_filtro.get(), codigo_seleccionado=codigo)
                self._refresh_faltantes_view()
                e_cant_stock.delete(0, tk.END)
                messagebox.showinfo("Éxito", f"Stock actualizado a: {nuevo_total}")
            except ValueError as exc:
                messagebox.showerror("Error", str(exc))
            except Exception as exc:
                messagebox.showerror("Error de stock", str(exc))

        f_btns = ttk.Frame(f_stock)
        f_btns.grid(row=1, column=0, columnspan=2, pady=8)
        
        tk.Button(f_btns, text="➕ Agregar", bg=self.SUCCESS, fg="white", relief="flat", padx=8, font=("Segoe UI", 8, "bold"), command=lambda: operacion_stock("agregar")).pack(side="left", padx=2)
        tk.Button(f_btns, text="➖ Quitar", bg=self.DANGER, fg="white", relief="flat", padx=8, font=("Segoe UI", 8, "bold"), command=lambda: operacion_stock("eliminar")).pack(side="left", padx=2)
        tk.Button(f_btns, text="✏️ Modificar", bg="#D97706", fg="white", relief="flat", padx=8, font=("Segoe UI", 8, "bold"), command=lambda: operacion_stock("modificar")).pack(side="left", padx=2)

        def refresh_inventory(silencioso=False):
            actualizar_etiquetas_combo(silencioso=silencioso)
            actualizar_tabla(combo_filtro.get() or "Todas", silencioso=silencioso)

        self._refresh_inventory_view = refresh_inventory
        actualizar_etiquetas_combo()
        actualizar_tabla("Todas")

    def construir_pestana_promociones(self, parent):
        tk.Label(parent, text="Promociones", font=("Segoe UI", 16, "bold"), bg=self.BG_COLOR, fg=self.PRIMARY).pack(pady=10)

        f_crear = ttk.LabelFrame(parent, text=" Crear Promoción ", padding=12)
        f_crear.pack(fill="x", padx=16, pady=6)
        
        ttk.Label(f_crear, text="Nombre:").grid(row=0, column=0, sticky="w", pady=4)
        e_nom_promo = ttk.Entry(f_crear, width=18)
        e_nom_promo.grid(row=0, column=1, padx=6, pady=4)
        
        ttk.Label(f_crear, text="Código Artículo:").grid(row=0, column=2, sticky="w", pady=4)
        e_cod_art = ttk.Entry(f_crear, width=15)
        e_cod_art.grid(row=0, column=3, padx=6, pady=4)
        
        ttk.Label(f_crear, text="O Etiqueta:").grid(row=1, column=0, sticky="w", pady=4)
        combo_eti_promo = ttk.Combobox(f_crear, state="readonly", width=15)
        combo_eti_promo.grid(row=1, column=1, padx=6, pady=4)
        
        ttk.Label(f_crear, text="Tipo:").grid(row=1, column=2, sticky="w", pady=4)
        e_tipo = ttk.Combobox(f_crear, values=["2X1", "PORCENTAJE"], state="readonly", width=12)
        e_tipo.grid(row=1, column=3, padx=6, pady=4)
        e_tipo.set("2X1")
        
        ttk.Label(f_crear, text="Valor (%):").grid(row=2, column=0, sticky="w", pady=4)
        e_val = ttk.Entry(f_crear, width=15)
        e_val.insert(0, "0")
        e_val.grid(row=2, column=1, padx=6, pady=4)

        columns_p = ("ID", "Nombre Promo", "Aplica A", "Tipo", "Valor")
        tree_promo = ttk.Treeview(parent, columns=columns_p, show="headings", height=7)
        for col in columns_p:
            tree_promo.heading(col, text=col)
            tree_promo.column(col, width=140, anchor="center")
        tree_promo.pack(pady=6, padx=16, fill="x")

        def cargar_promos(silencioso=False):
            try:
                rows = InventarioRepository.obtener_promociones()
                for row in tree_promo.get_children():
                    tree_promo.delete(row)
                for row in rows:
                    tree_promo.insert("", tk.END, values=row)
            except Exception as exc:
                if not silencioso:
                    messagebox.showerror("Error", f"No se pudieron cargar las promociones: {exc}")

        def actualizar_combos_promo(silencioso=False):
            try:
                valores = ["Ninguna"] + InventarioRepository.obtener_etiquetas()
                combo_eti_promo["values"] = valores
                if combo_eti_promo.get() not in valores:
                    combo_eti_promo.set("Ninguna")
            except Exception as exc:
                combo_eti_promo["values"] = ["Ninguna"]
                combo_eti_promo.set("Ninguna")
                if not silencioso:
                    messagebox.showerror("Error", f"No se pudieron cargar las etiquetas: {exc}")

        def registrar_promo():
            try:
                nombre = e_nom_promo.get().strip()
                codigo = e_cod_art.get().strip()
                etiqueta = combo_eti_promo.get()
                tipo = e_tipo.get()
                valor = float(e_val.get())
                
                val_codigo = codigo if codigo else None
                val_etiqueta = etiqueta if etiqueta and etiqueta != "Ninguna" else None

                InventarioRepository.guardar_promocion(nombre, tipo, valor, val_codigo, val_etiqueta)
                messagebox.showinfo("Éxito", "Promoción creada correctamente.")
                e_nom_promo.delete(0, tk.END)
                e_cod_art.delete(0, tk.END)
                combo_eti_promo.set("Ninguna")
                cargar_promos()
            except (ValueError, TypeError) as exc:
                messagebox.showerror("Error", str(exc))
            except Exception as exc:
                messagebox.showerror("Error", str(exc))

        tk.Button(
            f_crear,
            text="➕ Crear Promoción",
            bg=self.SUCCESS,
            fg="white",
            relief="flat",
            padx=12,
            font=("Segoe UI", 9, "bold"),
            command=registrar_promo,
        ).grid(row=2, column=2, columnspan=2, pady=6)

        def eliminar_promo_seleccionada():
            sel = tree_promo.selection()
            if not sel:
                messagebox.showwarning("Aviso", "Seleccione una promoción para eliminar.")
                return
            promo_id = int(tree_promo.item(sel[0], "values")[0])
            if messagebox.askyesno("Confirmar", "¿Eliminar esta promoción?"):
                try:
                    InventarioRepository.eliminar_promocion(promo_id)
                    cargar_promos()
                except Exception as exc:
                    messagebox.showerror("Error", str(exc))

        tk.Button(
            parent,
            text="🗑️ Eliminar Promoción Seleccionada",
            bg=self.DANGER,
            fg="white",
            relief="flat",
            padx=12,
            pady=6,
            font=("Segoe UI", 9, "bold"),
            command=eliminar_promo_seleccionada,
        ).pack(pady=6)

        self._refresh_promos_view = lambda silencioso=False: (
            actualizar_combos_promo(silencioso), cargar_promos(silencioso)
        )
        actualizar_combos_promo()
        cargar_promos()

    def construir_pestana_config(self, parent):
        tk.Label(parent, text="Configuración Avanzada", font=("Segoe UI", 16, "bold"), bg=self.BG_COLOR, fg=self.PRIMARY).pack(pady=15)
        f_form = ttk.LabelFrame(parent, text=" Parámetros Comerciales ", padding=20)
        f_form.pack(padx=20, pady=10)

        campos = [
            ("Impuesto (%):", "IMPUESTOS_PCT"),
            ("Comisión (%):", "COMISION_PCT"),
            ("Logística Fija:", "LOGISTICA_FIJA"),
            ("Margen de Ganancia (%):", "MARGEN_PCT"),
        ]
        entries = {}
        for row, (texto, atributo) in enumerate(campos):
            ttk.Label(f_form, text=texto).grid(row=row, column=0, sticky="w", pady=6)
            entry = ttk.Entry(f_form, width=18)
            entry.insert(0, str(getattr(config, atributo, 0)))
            entry.grid(row=row, column=1, padx=10, pady=6)
            entries[atributo] = entry

        def guardar_config():
            try:
                valores = {k: float(v.get()) for k, v in entries.items()}
                if any(v < 0 for v in valores.values()):
                    raise ValueError("Los parámetros no pueden ser negativos.")
                for atributo, valor in valores.items():
                    setattr(config, atributo, valor)
                messagebox.showinfo("Éxito", "Parámetros guardados correctamente.")
            except ValueError as exc:
                messagebox.showerror("Error", str(exc))
            except Exception as exc:
                messagebox.showerror("Error", f"No se pudo guardar la configuración: {exc}")

        tk.Button(
            f_form,
            text="💾 Guardar Configuración",
            bg=self.ACCENT,
            fg="white",
            relief="flat",
            padx=14,
            pady=8,
            font=("Segoe UI", 9, "bold"),
            command=guardar_config,
        ).grid(row=4, column=0, columnspan=2, pady=15)

    def construir_pestana_etiquetas(self, parent):
        tk.Label(parent, text="Gestión de Etiquetas", font=("Segoe UI", 16, "bold"), bg=self.BG_COLOR, fg=self.PRIMARY).pack(pady=10)
        
        f_form = ttk.LabelFrame(parent, text=" Nueva Etiqueta ", padding=15)
        f_form.pack(padx=20, pady=6, fill="x")
        ttk.Label(f_form, text="Nombre:").grid(row=0, column=0, sticky="w", pady=4)
        e_eti = ttk.Entry(f_form, width=22)
        e_eti.grid(row=0, column=1, padx=10, pady=4)

        f_asig = ttk.LabelFrame(parent, text=" Vincular a Producto ", padding=15)
        f_asig.pack(padx=20, pady=6, fill="x")
        ttk.Label(f_asig, text="Código Producto:").grid(row=0, column=0, sticky="w")
        e_cod_prod = ttk.Entry(f_asig, width=15)
        e_cod_prod.grid(row=0, column=1, padx=8)
        ttk.Label(f_asig, text="Etiqueta:").grid(row=0, column=2, sticky="w")
        combo_asig_eti = ttk.Combobox(f_asig, state="readonly", width=15)
        combo_asig_eti.grid(row=0, column=3, padx=8)

        tree_eti = ttk.Treeview(parent, columns=("Etiqueta",), show="headings", height=6)
        tree_eti.heading("Etiqueta", text="Nombre de Etiqueta")
        tree_eti.pack(pady=6, padx=20, fill="x")

        def cargar_lista_etiquetas(silencioso=False):
            try:
                etiquetas = InventarioRepository.obtener_etiquetas()
                combo_asig_eti["values"] = etiquetas
                if etiquetas:
                    combo_asig_eti.set(etiquetas[0])
                else:
                    combo_asig_eti.set("")
                for row in tree_eti.get_children():
                    tree_eti.delete(row)
                for eti in etiquetas:
                    tree_eti.insert("", tk.END, values=(eti,))
            except Exception as exc:
                if not silencioso:
                    messagebox.showerror("Error", f"No se pudieron cargar las etiquetas: {exc}")

        def crear_eti():
            nombre = e_eti.get().strip()
            if not nombre:
                messagebox.showwarning("Aviso", "El nombre no puede estar vacío.")
                return
            try:
                with DatabaseConnection.conectar() as conn:
                    conn.execute("INSERT INTO etiquetas (nombre) VALUES (?)", (nombre,))
                e_eti.delete(0, tk.END)
                cargar_lista_etiquetas()
                if callable(self._refresh_inventory_view):
                    self._refresh_inventory_view(silencioso=True)
                if callable(self._refresh_promos_view):
                    self._refresh_promos_view(silencioso=True)
                messagebox.showinfo("Éxito", f"Etiqueta '{nombre}' creada correctamente.")
            except Exception as exc:
                messagebox.showerror("Error", f"No se pudo crear la etiqueta: {exc}")

        def asociar_producto():
            cod = e_cod_prod.get().strip()
            eti = combo_asig_eti.get()
            if not cod or not eti:
                messagebox.showwarning("Aviso", "Indique producto y etiqueta.")
                return
            try:
                InventarioRepository.asociar_etiqueta_a_producto(cod, eti)
                e_cod_prod.delete(0, tk.END)
                messagebox.showinfo("Éxito", f"Producto {cod} vinculado a '{eti}'.")
                if callable(self._refresh_inventory_view):
                    self._refresh_inventory_view(silencioso=True)
            except Exception as exc:
                messagebox.showerror("Error", str(exc))

        def eliminar_etiqueta():
            sel = tree_eti.selection()
            if not sel:
                messagebox.showwarning("Aviso", "Seleccione una etiqueta.")
                return
            nombre = tree_eti.item(sel[0], "values")[0]
            if not messagebox.askyesno("Confirmar", f"¿Eliminar la etiqueta '{nombre}'?"):
                return
            try:
                with DatabaseConnection.conectar() as conn:
                    conn.execute("DELETE FROM etiquetas WHERE nombre = ?", (nombre,))
                cargar_lista_etiquetas()
                if callable(self._refresh_inventory_view):
                    self._refresh_inventory_view(silencioso=True)
                if callable(self._refresh_promos_view):
                    self._refresh_promos_view(silencioso=True)
            except Exception as exc:
                messagebox.showerror("Error", f"No se pudo eliminar la etiqueta: {exc}")

        tk.Button(f_form, text="➕ Agregar Etiqueta", bg=self.SUCCESS, fg="white", relief="flat", padx=10, command=crear_eti).grid(row=0, column=2, padx=10)
        tk.Button(f_asig, text="🔗 Vincular", bg=self.ACCENT, fg="white", relief="flat", padx=10, command=asociar_producto).grid(row=0, column=4, padx=10)
        tk.Button(parent, text="🗑️ Eliminar Etiqueta Seleccionada", bg=self.DANGER, fg="white", relief="flat", padx=12, pady=6, command=eliminar_etiqueta).pack(pady=6)
        cargar_lista_etiquetas()

    def construir_pestana_faltantes(self, parent):
        tk.Label(parent, text="Productos Faltantes (Stock Crítico)", font=("Segoe UI", 16, "bold"), bg=self.BG_COLOR, fg=self.PRIMARY).pack(pady=15)
        columns = ("Código", "Nombre", "Cantidad", "Mínimo")
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=10)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=140, anchor="center")
        tree.pack(pady=6, padx=16, fill="x")

        def cargar_faltantes(silencioso=False):
            try:
                for row in tree.get_children():
                    tree.delete(row)
                for art in InventarioRepository.obtener_faltantes():
                    tree.insert("", tk.END, values=(art.codigo, art.nombre, art.cantidad, art.stock_minimo))
            except Exception as exc:
                if not silencioso:
                    messagebox.showerror("Error", f"No se pudo cargar Faltantes: {exc}")

        self._refresh_faltantes_view = cargar_faltantes
        tk.Button(parent, text="🔄 Actualizar Lista", command=cargar_faltantes, bg=self.ACCENT, fg="white", relief="flat", padx=12, pady=6, font=("Segoe UI", 9, "bold")).pack(pady=10)
        cargar_faltantes()

    def construir_pestana_chatbot(self, parent):
        tk.Label(parent, text="Reportes y Exportaciones", font=("Segoe UI", 16, "bold"), bg=self.BG_COLOR, fg=self.PRIMARY).pack(pady=15)
        f_opts = ttk.LabelFrame(parent, text=" Centro de Reportes ", padding=20)
        f_opts.pack(padx=20, pady=10, fill="x")

        def exportar(formato, tipo_dato):
            try:
                if tipo_dato == "stock":
                    arts = InventarioRepository.obtener_todos()
                    contenido = "REPORTE DE STOCK:\n" + "\n".join(
                        f"- {a.nombre} (Stock: {a.cantidad})" for a in arts
                    )
                else:
                    promos = InventarioRepository.obtener_promociones()
                    contenido = "REPORTE DE PROMOCIONES:\n" + "\n".join(
                        f"- {p[1]} | {p[2]} [Tipo: {p[3]}]" for p in promos
                    )
                messagebox.showinfo(
                    f"Exportar a {formato}",
                    f"Archivo de {tipo_dato} preparado para {formato}.\n\n{contenido}",
                )
            except Exception as exc:
                messagebox.showerror("Error", f"No se pudo generar el reporte: {exc}")

        tk.Button(f_opts, text="📦 Exportar Stock a PDF", bg=self.DANGER, fg="white", relief="flat", width=35, pady=6, command=lambda: exportar("PDF", "stock")).pack(pady=6)
        tk.Button(f_opts, text="📦 Exportar Stock a Excel", bg=self.SUCCESS, fg="white", relief="flat", width=35, pady=6, command=lambda: exportar("Excel", "stock")).pack(pady=6)
        tk.Button(f_opts, text="🏷️ Exportar Promociones a PDF", bg="#7C3AED", fg="white", relief="flat", width=35, pady=6, command=lambda: exportar("PDF", "promos")).pack(pady=6)
        tk.Button(f_opts, text="🏷️ Exportar Promociones a Excel", bg=self.ACCENT, fg="white", relief="flat", width=35, pady=6, command=lambda: exportar("Excel", "promos")).pack(pady=6)