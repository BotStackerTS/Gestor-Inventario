import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
import csv
from datetime import datetime

# --- Subsistema Inteligente de Precios ---
class SubsistemaPrecios:
    @staticmethod
    def calcular_precio_inteligente(precio_base, impuestos_pct=21.0, inflacion_pct=4.0, logistica_fija=50.0):
        factor_impuestos = 1 + (impuestos_pct / 100)
        factor_inflacion = 1 + (inflacion_pct / 100)
        precio_unitario = (precio_base * factor_impuestos * factor_inflacion) + logistica_fija
        return round(precio_unitario, 2)

    @staticmethod
    def calcular_stock_total(cantidad, precio_unitario):
        return round(cantidad * precio_unitario, 2)

# --- Backend y Base de Datos ---
class GestorInventarioDB:
    def __init__(self, db_name="inventario.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.crear_tablas()

    def crear_tablas(self):
        self.cursor.executescript('''
            CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, password TEXT);
            CREATE TABLE IF NOT EXISTS inventario (codigo TEXT PRIMARY KEY, nombre TEXT, cantidad INTEGER, precio_base REAL, precio_final REAL);
            CREATE TABLE IF NOT EXISTS ventas (id INTEGER PRIMARY KEY AUTOINCREMENT, total REAL, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS detalle_venta (id INTEGER PRIMARY KEY AUTOINCREMENT, venta_id INTEGER, codigo_articulo TEXT, cantidad INTEGER, subtotal REAL);
        ''')
        self.conn.commit()
        try:
            self.cursor.execute("INSERT INTO usuarios (usuario, password) VALUES ('admin', '1234')")
            self.conn.commit()
        except: 
            pass

    def verificar_login(self, usuario, password):
        self.cursor.execute("SELECT * FROM usuarios WHERE usuario = ? AND password = ?", (usuario, password))
        return self.cursor.fetchone() is not None

    def cargar_articulo(self, codigo, nombre, cantidad, precio_base):
        precio_final = SubsistemaPrecios.calcular_precio_inteligente(precio_base)
        try:
            self.cursor.execute("INSERT INTO inventario VALUES (?, ?, ?, ?, ?)", (codigo, nombre, cantidad, precio_base, precio_final))
            self.conn.commit()
            return True
        except: 
            return False

    def modificar_o_eliminar(self, codigo, nombre=None, cantidad=None, precio_base=None, eliminar=False):
        if eliminar:
            self.cursor.execute("DELETE FROM inventario WHERE codigo = ?", (codigo,))
        else:
            campos, valores = [], []
            if nombre: 
                campos.append("nombre = ?")
                valores.append(nombre)
            if cantidad is not None: 
                campos.append("cantidad = ?")
                valores.append(cantidad)
            if precio_base is not None: 
                campos.append("precio_base = ?")
                valores.append(precio_base)
                campos.append("precio_final = ?")
                valores.append(SubsistemaPrecios.calcular_precio_inteligente(precio_base))
            if not campos:
                return
            valores.append(codigo)
            self.cursor.execute(f"UPDATE inventario SET {', '.join(campos)} WHERE codigo = ?", valores)
        self.conn.commit()

    def exportar_stock_excel(self, nombre_archivo="inventario_stock.csv"):
        try:
            self.cursor.execute("SELECT codigo, nombre, cantidad, precio_base, precio_final FROM inventario")
            filas = self.cursor.fetchall()
            
            with open(nombre_archivo, mode="w", newline="", encoding="utf-8-sig") as archivo:
                writer = csv.writer(archivo)
                # Escribir cabeceras compatibles con Excel
                writer.writerow(["Código", "Nombre del Artículo", "Cantidad", "Precio Base", "Precio Final (Inteligente)"])
                # Escribir los datos del inventario
                writer.writerows(filas)
            return True
        except Exception as e:
            print(f"Error al exportar: {e}")
            return False

    def procesar_venta(self, carrito):
        total_venta = 0
        self.cursor.execute("INSERT INTO ventas (total) VALUES (0)")
        venta_id = self.cursor.lastrowid
        for codigo, cant_vendida in carrito:
            self.cursor.execute("SELECT cantidad, precio_final FROM inventario WHERE codigo = ?", (codigo,))
            row = self.cursor.fetchone()
            if row and row[0] >= cant_vendida:
                subtotal = cant_vendida * row[1]
                total_venta += subtotal
                self.cursor.execute("UPDATE inventario SET cantidad = cantidad - ? WHERE codigo = ?", (cant_vendida, codigo))
                self.cursor.execute("INSERT INTO detalle_venta (venta_id, codigo_articulo, cantidad, subtotal) VALUES (?, ?, ?, ?)", (venta_id, codigo, cant_vendida, subtotal))
            else: 
                raise Exception(f"Stock insuficiente o artículo no encontrado para código: {codigo}")
        self.cursor.execute("UPDATE ventas SET total = ? WHERE id = ?", (total_venta, venta_id))
        self.conn.commit()
        return venta_id, total_venta

# --- Chatbot y Reportes ---
class ChatbotAsistente:
    def __init__(self, db_manager): 
        self.db = db_manager

    def responder_consulta(self, mensaje_cliente):
        mensaje = mensaje_cliente.lower()
        if "stock" in mensaje or "materiales" in mensaje:
            self.db.cursor.execute("SELECT codigo, nombre, cantidad, precio_final FROM inventario")
            articulos = self.db.cursor.fetchall()
            if not articulos:
                return "📦 No hay artículos registrados en el inventario actualmente."
            reporte = "📦 **Informe de Stock Actual:**\n"
            for art in articulos:
                reporte += f"- [{art[0]}] {art[1]} | Stock: {art[2]} un. | Precio Final: ${art[3]}\n"
            return reporte
        elif "noticias" in mensaje:
            return "📰 **Noticias:** Nuevos descuentos aplicados y reposición de stock semanal disponible."
        else:
            return "Hola, soy tu asistente virtual. Puedes consultarme por 'stock' o 'noticias'."

    def generar_reporte_archivo(self, contenido, formato="txt"):
        if formato.lower() == "pdf":
            nombre_archivo = "reporte_inventario.pdf"
            with open(nombre_archivo, "w", encoding="utf-8") as f:
                f.write(f"[FORMATO PDF SIMULADO]\n{contenido}")
        else:
            nombre_archivo = "reporte_inventario.txt"
            with open(nombre_archivo, "w", encoding="utf-8") as f:
                f.write(contenido)
        return nombre_archivo

    def enviar_por_canal(self, destino, mensaje, canal="whatsapp"):
        print(f"[{canal.upper()}] Enviando a {destino}:\n{mensaje}")
        return True

# --- Interfaz Gráfica (Tkinter) ---
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestor de Inventario Automatizado")
        self.geometry("750x600")
        self.db = GestorInventarioDB()
        self.chatbot = ChatbotAsistente(self.db)
        self.login_frame()

    def limpiar_ventana(self):
        for widget in self.winfo_children():
            widget.destroy()

    def login_frame(self):
        self.limpiar_ventana()
        marco = tk.Frame(self)
        marco.pack(pady=80)

        tk.Label(marco, text="🔐 Inicio de Sesión", font=("Arial", 16, "bold")).pack(pady=10)
        tk.Label(marco, text="Usuario:").pack()
        self.u = tk.Entry(marco, width=25)
        self.u.pack(pady=5)
        
        tk.Label(marco, text="Contraseña:").pack()
        self.p = tk.Entry(marco, show="*", width=25)
        self.p.pack(pady=5)
        
        tk.Button(marco, text="Ingresar", bg="#4CAF50", fg="white", width=15, command=self.validar).pack(pady=15)

    def validar(self):
        if self.db.verificar_login(self.u.get(), self.p.get()):
            self.menu_principal()
        else: 
            messagebox.showerror("Error", "Usuario o contraseña incorrectos")

    def menu_principal(self):
        self.limpiar_ventana()
        self.geometry("800x630")
        
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        f_carga = ttk.Frame(nb)
        f_stock = ttk.Frame(nb)
        f_venta = ttk.Frame(nb)
        f_chat = ttk.Frame(nb)

        nb.add(f_carga, text="Cargar Stock")
        nb.add(f_stock, text="Inventario / Modificar")
        nb.add(f_venta, text="Caja / Ventas (Tickets)")
        nb.add(f_chat, text="Chatbot & Reportes")

        # --- PESTAÑA 1: CARGAR ---
        tk.Label(f_carga, text="Carga de Nuevo Artículo (con Subsistema Inteligente)", font=("Arial", 12, "bold")).pack(pady=10)
        
        tk.Label(f_carga, text="Código del Artículo:").pack()
        e_cod = tk.Entry(f_carga); e_cod.pack()
        
        tk.Label(f_carga, text="Nombre del Artículo:").pack()
        e_nom = tk.Entry(f_carga); e_nom.pack()
        
        tk.Label(f_carga, text="Cantidad Inicial:").pack()
        e_cant = tk.Entry(f_carga); e_cant.pack()
        
        tk.Label(f_carga, text="Precio Base Unitario:").pack()
        e_prec = tk.Entry(f_carga); e_prec.pack()

        def guardar_art():
            try:
                exito = self.db.cargar_articulo(e_cod.get(), e_nom.get(), int(e_cant.get()), float(e_prec.get()))
                if exito:
                    messagebox.showinfo("Éxito", "Artículo guardado y precio inteligente aplicado correctamente.")
                    e_cod.delete(0, tk.END); e_nom.delete(0, tk.END); e_cant.delete(0, tk.END); e_prec.delete(0, tk.END)
                else:
                    messagebox.showerror("Error", "El código de artículo ya existe o los datos son inválidos.")
            except ValueError:
                messagebox.showerror("Error", "Cantidad y precio deben ser numéricos.")

        tk.Button(f_carga, text="Guardar Artículo", bg="#2196F3", fg="white", command=guardar_art).pack(pady=15)

        # --- PESTAÑA 2: INVENTARIO / MODIFICAR / EXPORTAR ---
        tk.Label(f_stock, text="Listado de Artículos y Gestión de Stock", font=("Arial", 12, "bold")).pack(pady=10)
        
        columns = ("Codigo", "Nombre", "Cantidad", "Base", "Final")
        tree = ttk.Treeview(f_stock, columns=columns, show="headings", height=7)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        tree.pack(pady=5)

        def actualizar_tabla():
            for row in tree.get_children():
                tree.delete(row)
            self.db.cursor.execute("SELECT * FROM inventario")
            for row in self.db.cursor.fetchall():
                tree.insert("", tk.END, values=row)

        f_botones_stock = tk.Frame(f_stock)
        f_botones_stock.pack(pady=5)

        tk.Button(f_botones_stock, text="Actualizar Vista", command=actualizar_tabla, bg="#607D8B", fg="white").pack(side="left", padx=5)

        def exportar_a_excel_click():
            if self.db.exportar_stock_excel("inventario_stock.csv"):
                messagebox.showinfo("Exportado con Éxito", "El archivo 'inventario_stock.csv' se ha guardado en la carpeta del proyecto y se puede abrir directamente en Excel.")
            else:
                messagebox.showerror("Error", "No se pudo exportar el archivo.")

        tk.Button(f_botones_stock, text="📊 Exportar Stock a Excel (CSV)", command=exportar_a_excel_click, bg="#4CAF50", fg="white").pack(side="left", padx=5)
        
        actualizar_tabla()

        # Opciones de modificación
        f_mod = tk.LabelFrame(f_stock, text="Modificar o Eliminar por Código", padx=10, pady=5)
        f_mod.pack(fill="x", padx=20, pady=5)

        tk.Label(f_mod, text="Código a editar:").grid(row=0, column=0, sticky="w")
        e_m_cod = tk.Entry(f_mod); e_m_cod.grid(row=0, column=1, padx=5)

        tk.Label(f_mod, text="Nuevo Nombre:").grid(row=1, column=0, sticky="w")
        e_m_nom = tk.Entry(f_mod); e_m_nom.grid(row=1, column=1, padx=5)

        tk.Label(f_mod, text="Nueva Cantidad:").grid(row=2, column=0, sticky="w")
        e_m_cant = tk.Entry(f_mod); e_m_cant.grid(row=2, column=1, padx=5)

        tk.Label(f_mod, text="Nuevo Precio Base:").grid(row=3, column=0, sticky="w")
        e_m_prec = tk.Entry(f_mod); e_m_prec.grid(row=3, column=1, padx=5)

        def ejecutar_modificacion():
            try:
                cant = int(e_m_cant.get()) if e_m_cant.get() else None
                prec = float(e_m_prec.get()) if e_m_prec.get() else None
                self.db.modificar_o_eliminar(e_m_cod.get(), nombre=e_m_nom.get() or None, cantidad=cant, precio_base=prec)
                messagebox.showinfo("Éxito", "Modificación aplicada.")
                actualizar_tabla()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        def ejecutar_eliminacion():
            if messagebox.askyesno("Confirmar", "¿Seguro que deseas eliminar este artículo?"):
                try:
                    self.db.modificar_o_eliminar(e_m_cod.get(), eliminar=True)
                    messagebox.showinfo("Éxito", "Artículo eliminado.")
                    actualizar_tabla()
                except Exception as e:
                    messagebox.showerror("Error", str(e))

        tk.Button(f_mod, text="Modificar", bg="#FF9800", fg="white", command=ejecutar_modificacion).grid(row=4, column=0, pady=5)
        tk.Button(f_mod, text="Eliminar", bg="#F44336", fg="white", command=ejecutar_eliminacion).grid(row=4, column=1, pady=5)

        # --- PESTAÑA 3: VENTAS Y TICKETS ---
        tk.Label(f_venta, text="Caja Registradora (Emisión de Ticket y Descuento Automático)", font=("Arial", 12, "bold")).pack(pady=10)

        tk.Label(f_venta, text="Código del Artículo:").pack()
        e_v_cod = tk.Entry(f_venta); e_v_cod.pack()

        tk.Label(f_venta, text="Cantidad a Vender:").pack()
        e_v_cant = tk.Entry(f_venta); e_v_cant.pack()

        def procesar_ticket():
            try:
                carrito = [(e_v_cod.get(), int(e_v_cant.get()))]
                v_id, total = self.db.procesar_venta(carrito)
                messagebox.showinfo("Ticket Emitido 🎫", f"Venta ID: {v_id}\nTotal a Pagar: ${total}\n\n¡Stock descontado automáticamente del inventario!")
            except Exception as e:
                messagebox.showerror("Error en Venta", str(e))

        tk.Button(f_venta, text="Imprimir Ticket y Descontar Stock", bg="#4CAF50", fg="white", command=procesar_ticket).pack(pady=20)

        # --- PESTAÑA 4: CHATBOT Y REPORTES ---
        tk.Label(f_chat, text="Asistente Virtual (Chatbot & Envíos de Informes)", font=("Arial", 12, "bold")).pack(pady=10)

        tk.Label(f_chat, text="Escriba su consulta (ej. 'Ver stock', 'Noticias'):").pack()
        e_chat_msg = tk.Entry(f_chat, width=50); e_chat_msg.pack(pady=5)

        txt_chat_res = tk.Text(f_chat, height=10, width=70)
        txt_chat_res.pack(pady=5)

        def consultar_bot():
            respuesta = self.chatbot.responder_consulta(e_chat_msg.get())
            txt_chat_res.delete("1.0", tk.END)
            txt_chat_res.insert(tk.END, respuesta)

        tk.Button(f_chat, text="Consultar al Chatbot", bg="#673AB7", fg="white", command=consultar_bot).pack(pady=5)

        f_envios = tk.Frame(f_chat)
        f_envios.pack(pady=10)

        def enviar_informe_cliente(formato, canal):
            contenido = txt_chat_res.get("1.0", tk.END)
            archivo = self.chatbot.generar_reporte_archivo(contenido, formato=formato)
            self.chatbot.enviar_por_canal("cliente@email.com", f"Adjunto informe en formato {formato.upper()}:\n{archivo}", canal=canal)
            messagebox.showinfo("Enviado con Éxito", f"El informe fue generado como {formato.upper()} y enviado vía {canal.capitalize()}.")

        tk.Button(f_envios, text="Enviar TXT por Gmail", bg="#009688", fg="white", command=lambda: enviar_informe_cliente("txt", "gmail")).pack(side="left", padx=5)
        tk.Button(f_envios, text="Enviar PDF por WhatsApp", bg="#25D366", fg="white", command=lambda: enviar_informe_cliente("pdf", "whatsapp")).pack(side="left", padx=5)

if __name__ == "__main__":
    app = App()
    app.mainloop()