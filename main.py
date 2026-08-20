import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
import csv
import threading
from datetime import datetime

# --- Subsistema Inteligente de Precios y Negocio ---
class SubsistemaPrecios:
    @staticmethod
    def calcular_precio_inteligente(precio_base, impuestos_pct=21.0, inflacion_pct=4.0, logistica_fija=50.0):
        factor_impuestos = 1 + (impuestos_pct / 100)
        factor_inflacion = 1 + (inflacion_pct / 100)
        precio_unitario = (precio_base * factor_impuestos * factor_inflacion) + logistica_fija
        return round(precio_unitario, 2)

# --- Backend y Base de Datos (Con Context Managers) ---
class GestorInventarioDB:
    def __init__(self, db_name="inventario_pro.db"):
        self.db_name = db_name
        self.crear_tablas()

    def conectar(self):
        return sqlite3.connect(self.db_name)

    def crear_tablas(self):
        with self.conectar() as conn:
            cursor = conn.cursor()
            cursor.executescript('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    usuario TEXT UNIQUE, 
                    password TEXT, 
                    rol TEXT
                );
                CREATE TABLE IF NOT EXISTS inventario (
                    codigo TEXT PRIMARY KEY, 
                    nombre TEXT, 
                    cantidad INTEGER, 
                    precio_base REAL, 
                    precio_final REAL,
                    stock_minimo INTEGER DEFAULT 5
                );
                CREATE TABLE IF NOT EXISTS ventas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    total REAL, 
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS detalle_venta (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    venta_id INTEGER, 
                    codigo_articulo TEXT, 
                    cantidad INTEGER, 
                    subtotal REAL
                );
            ''')
            conn.commit()
            
            # Crear usuarios iniciales (Admin y Cajero de prueba)
            try:
                cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, password, rol) VALUES ('admin', 'admin123', 'admin')")
                cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, password, rol) VALUES ('cajero', 'caja123', 'cajero')")
                conn.commit()
            except:
                pass

    def verificar_login(self, usuario, password):
        with self.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT rol FROM usuarios WHERE usuario = ? AND password = ?", (usuario, password))
            row = cursor.fetchone()
            return row[0] if row else None

    def cargar_articulo(self, codigo, nombre, cantidad, precio_base, stock_minimo=5):
        precio_final = SubsistemaPrecios.calcular_precio_inteligente(precio_base)
        try:
            with self.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO inventario VALUES (?, ?, ?, ?, ?, ?)", 
                               (codigo, nombre, cantidad, precio_base, precio_final, stock_minimo))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def modificar_o_eliminar(self, codigo, nombre=None, cantidad=None, precio_base=None, stock_minimo=None, eliminar=False):
        with self.conectar() as conn:
            cursor = conn.cursor()
            if eliminar:
                cursor.execute("DELETE FROM inventario WHERE codigo = ?", (codigo,))
            else:
                campos, valores = [], []
                if nombre: 
                    campos.append("nombre = ?"); valores.append(nombre)
                if cantidad is not None: 
                    campos.append("cantidad = ?"); valores.append(cantidad)
                if precio_base is not None: 
                    campos.append("precio_base = ?"); valores.append(precio_base)
                    campos.append("precio_final = ?"); valores.append(SubsistemaPrecios.calcular_precio_inteligente(precio_base))
                if stock_minimo is not None:
                    campos.append("stock_minimo = ?"); valores.append(stock_minimo)
                
                if not campos: return
                valores.append(codigo)
                cursor.execute(f"UPDATE inventario SET {', '.join(campos)} WHERE codigo = ?", valores)
            conn.commit()

    def procesar_venta(self, carrito):
        with self.conectar() as conn:
            cursor = conn.cursor()
            total_venta = 0
            cursor.execute("INSERT INTO ventas (total) VALUES (0)")
            venta_id = cursor.lastrowid
            
            alertas_stock = []
            for codigo, cant_vendida in carrito:
                cursor.execute("SELECT cantidad, precio_final, nombre, stock_minimo FROM inventario WHERE codigo = ?", (codigo,))
                row = cursor.fetchone()
                if row and row[0] >= cant_vendida:
                    stock_actual, precio_final, nombre_art, stock_min = row
                    subtotal = cant_vendida * precio_final
                    total_venta += subtotal
                    nuevo_stock = stock_actual - cant_vendida
                    
                    cursor.execute("UPDATE inventario SET cantidad = ? WHERE codigo = ?", (nuevo_stock, codigo))
                    cursor.execute("INSERT INTO detalle_venta (venta_id, codigo_articulo, cantidad, subtotal) VALUES (?, ?, ?, ?)", 
                                   (venta_id, codigo, cant_vendida, subtotal))
                    
                    if nuevo_stock <= stock_min:
                        alertas_stock.append(f"⚠️ Alerta: '{nombre_art}' tiene stock bajo ({nuevo_stock} un.).")
                else:
                    raise Exception(f"Stock insuficiente o artículo inexistente para código: {codigo}")
            
            cursor.execute("UPDATE ventas SET total = ? WHERE id = ?", (total_venta, venta_id))
            conn.commit()
            return venta_id, total_venta, alertas_stock

    def exportar_stock_excel(self, nombre_archivo="inventario_negocio.csv"):
        try:
            with self.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT codigo, nombre, cantidad, precio_base, precio_final, stock_minimo FROM inventario")
                filas = cursor.fetchall()
            
            with open(nombre_archivo, mode="w", newline="", encoding="utf-8-sig") as archivo:
                writer = csv.writer(archivo)
                writer.writerow(["Código", "Nombre", "Cantidad", "Precio Base", "Precio Final Inteligente", "Stock Mínimo"])
                writer.writerows(filas)
            return True
        except Exception:
            return False

# --- Chatbot Inteligente ---
class ChatbotAsistente:
    def __init__(self, db_manager): 
        self.db = db_manager

    def responder_consulta(self, mensaje_cliente):
        mensaje = mensaje_cliente.lower()
        if "stock" in mensaje or "materiales" in mensaje:
            with self.db.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT codigo, nombre, cantidad, precio_final FROM inventario")
                articulos = cursor.fetchall()
            if not articulos:
                return "📦 No hay artículos registrados actualmente."
            reporte = "📦 **Informe de Stock Actual (Negocio):**\n"
            for art in articulos:
                reporte += f"- [{art[0]}] {art[1]} | Stock: {art[2]} un. | Precio: ${art[3]}\n"
            return reporte
        elif "noticias" in mensaje or "ofertas" in mensaje:
            return "📰 **Novedades:** Promociones vigentes y reposición semanal de mercadería disponible."
        else:
            return "Hola, soy tu asistente virtual comercial. Consúltame por 'stock' o 'noticias'."

    def generar_reporte_archivo(self, contenido, formato="txt"):
        nombre_archivo = f"reporte_comercial.{formato.lower()}"
        with open(nombre_archivo, "w", encoding="utf-8") as f:
            f.write(f"--- REPORTE COMERCIAL ---\n{contenido}")
        return nombre_archivo

    def enviar_por_canal(self, destino, mensaje, canal="whatsapp"):
        print(f"[{canal.upper()}] Transmisión a {destino}:\n{mensaje}")
        return True

# --- Interfaz Gráfica Profesional (Tkinter) ---
class AppPro(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestor Comercial Pro - Control de Inventario y Ventas")
        self.geometry("850x650")
        self.db = GestorInventarioDB()
        self.chatbot = ChatbotAsistente(self.db)
        self.rol_actual = None
        self.login_frame()

    def limpiar_ventana(self):
        for widget in self.winfo_children():
            widget.destroy()

    def login_frame(self):
        self.limpiar_ventana()
        marco = tk.Frame(self, padx=20, pady=20, relief="raised", bd=2)
        marco.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(marco, text="💼 Sistema de Gestión Comercial", font=("Segoe UI", 16, "bold")).pack(pady=10)
        tk.Label(marco, text="Usuario:", font=("Segoe UI", 10)).pack(anchor="w")
        self.u = tk.Entry(marco, width=30, font=("Segoe UI", 10))
        self.u.pack(pady=5)
        
        tk.Label(marco, text="Contraseña:", font=("Segoe UI", 10)).pack(anchor="w")
        self.p = tk.Entry(marco, show="*", width=30, font=("Segoe UI", 10))
        self.p.pack(pady=5)
        
        tk.Button(marco, text="Iniciar Sesión", bg="#2E7D32", fg="white", font=("Segoe UI", 10, "bold"), 
                  width=20, command=self.validar).pack(pady=15)
        
        tk.Label(marco, text="Credenciales de prueba:\nAdmin: admin / admin123\nCajero: cajero / cajero123", fg="gray", font=("Segoe UI", 8)).pack()

    def validar(self):
        rol = self.db.verificar_login(self.u.get(), self.p.get())
        if rol:
            self.rol_actual = rol
            self.menu_principal()
        else: 
            messagebox.showerror("Error de Acceso", "Usuario o contraseña incorrectos.")

    def menu_principal(self):
        self.limpiar_ventana()
        self.geometry("900x680")
        
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        f_venta = ttk.Frame(nb)
        f_stock = ttk.Frame(nb)
        f_carga = ttk.Frame(nb)
        f_historial = ttk.Frame(nb)
        f_chat = ttk.Frame(nb)

        nb.add(f_venta, text="🛒 Caja / Ventas")
        nb.add(f_stock, text="📦 Inventario y Alertas")
        nb.add(f_carga, text="➕ Cargar Stock")
        nb.add(f_historial, text="📊 Historial de Ventas")
        nb.add(f_chat, text="🤖 Chatbot y Reportes")

        # --- 1. PESTAÑA VENTAS ---
        tk.Label(f_venta, text="Caja Registradora", font=("Segoe UI", 14, "bold")).pack(pady=10)
        
        f_form_v = tk.LabelFrame(f_venta, text="Datos del Ticket", padx=15, pady=15)
        f_form_v.pack(fill="x", padx=20, pady=10)

        tk.Label(f_form_v, text="Código del Artículo:").grid(row=0, column=0, sticky="w", pady=5)
        e_v_cod = tk.Entry(f_form_v, width=20); e_v_cod.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(f_form_v, text="Cantidad a Vender:").grid(row=1, column=0, sticky="w", pady=5)
        e_v_cant = tk.Entry(f_form_v, width=20); e_v_cant.grid(row=1, column=1, padx=10, pady=5)

        def procesar_venta_hilo():
            try:
                carrito = [(e_v_cod.get(), int(e_v_cant.get()))]
                v_id, total, alertas = self.db.procesar_venta(carrito)
                
                mensaje_ticket = f"Ticket N°: {v_id}\nTotal a Pagar: ${total:.2f}\n\n¡Venta registrada y stock actualizado!"
                if alertas:
                    mensaje_ticket += "\n\n" + "\n".join(alertas)
                
                messagebox.showinfo("Ticket Emitido 🎫", mensaje_ticket)
                e_v_cod.delete(0, tk.END); e_v_cant.delete(0, tk.END)
            except Exception as ex:
                messagebox.showerror("Error en Venta", str(ex))

        tk.Button(f_venta, text="Imprimir Ticket y Descontar Stock", bg="#2E7D32", fg="white", 
                  font=("Segoe UI", 10, "bold"), command=lambda: threading.Thread(target=procesar_venta_hilo).start()).pack(pady=20)

        # --- 2. PESTAÑA INVENTARIO ---
        tk.Label(f_stock, text="Control General de Inventario", font=("Segoe UI", 14, "bold")).pack(pady=10)
        
        columns = ("Codigo", "Nombre", "Cantidad", "Base", "Final", "Mínimo")
        tree = ttk.Treeview(f_stock, columns=columns, show="headings", height=8)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=110, anchor="center")
        tree.pack(pady=5)

        def actualizar_tabla():
            for row in tree.get_children(): tree.delete(row)
            with self.db.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM inventario")
                for row in cursor.fetchall():
                    tree.insert("", tk.END, values=row)

        f_btn_s = tk.Frame(f_stock); f_btn_s.pack(pady=5)
        tk.Button(f_btn_s, text="Actualizar Vista", command=actualizar_tabla, bg="#546E7A", fg="white").pack(side="left", padx=5)
        
        def exportar_excel_seguro():
            if self.rol_actual != "admin":
                messagebox.showwarning("Acceso Denegado", "Solo los administradores pueden exportar datos.")
                return
            if self.db.exportar_stock_excel():
                messagebox.showinfo("Éxito", "Archivo 'inventario_negocio.csv' generado correctamente para Excel.")
            else:
                messagebox.showerror("Error", "No se pudo exportar.")

        tk.Button(f_btn_s, text="📊 Exportar a Excel (CSV)", command=exportar_excel_seguro, bg="#0288D1", fg="white").pack(side="left", padx=5)
        actualizar_tabla()

        # Opciones de modificación (Restringidas por rol)
        f_mod = tk.LabelFrame(f_stock, text="Modificar o Eliminar Artículo (Solo Admin)", padx=10, pady=5)
        f_mod.pack(fill="x", padx=20, pady=5)

        tk.Label(f_mod, text="Código:").grid(row=0, column=0, sticky="w")
        e_m_cod = tk.Entry(f_mod, width=15); e_m_cod.grid(row=0, column=1, padx=5, pady=2)
        tk.Label(f_mod, text="Nuevo Nombre:").grid(row=0, column=2, sticky="w")
        e_m_nom = tk.Entry(f_mod, width=15); e_m_nom.grid(row=0, column=3, padx=5, pady=2)
        tk.Label(f_mod, text="Nueva Cantidad:").grid(row=1, column=0, sticky="w")
        e_m_cant = tk.Entry(f_mod, width=15); e_m_cant.grid(row=1, column=1, padx=5, pady=2)
        tk.Label(f_mod, text="Nuevo Precio Base:").grid(row=1, column=2, sticky="w")
        e_m_prec = tk.Entry(f_mod, width=15); e_m_prec.grid(row=1, column=3, padx=5, pady=2)

        def ejecutar_mod():
            if self.rol_actual != "admin":
                messagebox.showwarning("Permisos Insuficientes", "Acción reservada para administradores.")
                return
            try:
                cant = int(e_m_cant.get()) if e_m_cant.get() else None
                prec = float(e_m_prec.get()) if e_m_prec.get() else None
                self.db.modificar_o_eliminar(e_m_cod.get(), nombre=e_m_nom.get() or None, cantidad=cant, precio_base=prec)
                messagebox.showinfo("Éxito", "Modificación aplicada con éxito.")
                actualizar_tabla()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        def ejecutar_del():
            if self.rol_actual != "admin":
                messagebox.showwarning("Permisos Insuficientes", "Acción reservada para administradores.")
                return
            if messagebox.askyesno("Confirmar", "¿Eliminar artículo permanentemente?"):
                self.db.modificar_o_eliminar(e_m_cod.get(), eliminar=True)
                actualizar_tabla()

        tk.Button(f_mod, text="Modificar", bg="#F57C00", fg="white", command=ejecutar_mod).grid(row=2, column=0, pady=5)
        tk.Button(f_mod, text="Eliminar", bg="#D32F2F", fg="white", command=ejecutar_del).grid(row=2, column=1, pady=5)

        # --- 3. PESTAÑA CARGAR STOCK ---
        tk.Label(f_carga, text="Carga de Nuevo Material (Subsistema Inteligente)", font=("Segoe UI", 14, "bold")).pack(pady=10)
        
        f_form_c = tk.LabelFrame(f_carga, text="Detalles del Producto", padx=20, pady=20)
        f_form_c.pack(padx=20, pady=10)

        tk.Label(f_form_c, text="Código:").grid(row=0, column=0, sticky="w", pady=5)
        e_c_cod = tk.Entry(f_form_c, width=25); e_c_cod.grid(row=0, column=1, padx=10, pady=5)
        tk.Label(f_form_c, text="Nombre:").grid(row=1, column=0, sticky="w", pady=5)
        e_c_nom = tk.Entry(f_form_c, width=25); e_c_nom.grid(row=1, column=1, padx=10, pady=5)
        tk.Label(f_form_c, text="Cantidad Inicial:").grid(row=2, column=0, sticky="w", pady=5)
        e_c_cant = tk.Entry(f_form_c, width=25); e_c_cant.grid(row=2, column=1, padx=10, pady=5)
        tk.Label(f_form_c, text="Precio Base Unitario:").grid(row=3, column=0, sticky="w", pady=5)
        e_c_prec = tk.Entry(f_form_c, width=25); e_c_prec.grid(row=3, column=1, padx=10, pady=5)
        tk.Label(f_form_c, text="Stock Mínimo de Alerta:").grid(row=4, column=0, sticky="w", pady=5)
        e_c_min = tk.Entry(f_form_c, width=25); e_c_min.insert(0, "5"); e_c_min.grid(row=4, column=1, padx=10, pady=5)

        def guardar_nuevo():
            if self.rol_actual != "admin":
                messagebox.showwarning("Acceso Denegado", "Solo el administrador puede cargar stock nuevo.")
                return
            try:
                exito = self.db.cargar_articulo(e_c_cod.get(), e_c_nom.get(), int(e_c_cant.get()), 
                                                float(e_c_prec.get()), int(e_c_min.get()))
                if exito:
                    messagebox.showinfo("Éxito", "Artículo cargado y precio inteligente aplicado.")
                    e_c_cod.delete(0, tk.END); e_c_nom.delete(0, tk.END); e_c_cant.delete(0, tk.END); e_c_prec.delete(0, tk.END)
                    actualizar_tabla()
                else:
                    messagebox.showerror("Error", "El código ya existe o faltan datos válidos.")
            except ValueError:
                messagebox.showerror("Error", "Verifique que los campos numéricos sean correctos.")

        tk.Button(f_carga, text="Guardar Artículo en Sistema", bg="#0288D1", fg="white", 
                  font=("Segoe UI", 10, "bold"), command=guardar_nuevo).pack(pady=15)

        # --- 4. PESTAÑA HISTORIAL DE VENTAS ---
        tk.Label(f_historial, text="Auditoría de Ventas Realizadas", font=("Segoe UI", 14, "bold")).pack(pady=10)
        
        columns_h = ("ID Venta", "Fecha y Hora", "Total Recaudado")
        tree_h = ttk.Treeview(f_historial, columns=columns_h, show="headings", height=12)
        for col in columns_h:
            tree_h.heading(col, text=col)
            tree_h.column(col, width=200, anchor="center")
        tree_h.pack(pady=5)

        def actualizar_historial():
            for row in tree_h.get_children(): tree_h.delete(row)
            with self.db.conectar() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, fecha, total FROM ventas ORDER BY id DESC")
                for row in cursor.fetchall():
                    tree_h.insert("", tk.END, values=(row[0], row[1], f"${row[2]:.2f}"))

        tk.Button(f_historial, text="Actualizar Historial", command=actualizar_historial, bg="#546E7A", fg="white").pack(pady=5)
        actualizar_historial()

        # --- 5. PESTAÑA CHATBOT Y REPORTES ---
        tk.Label(f_chat, text="Asistente Virtual Automatizado", font=("Segoe UI", 14, "bold")).pack(pady=10)
        
        tk.Label(f_chat, text="Escriba su consulta (ej. 'Ver stock', 'Noticias'):").pack()
        e_chat = tk.Entry(f_chat, width=50); e_chat.pack(pady=5)

        txt_res = tk.Text(f_chat, height=10, width=75)
        txt_res.pack(pady=5)

        def consultar_bot():
            resp = self.chatbot.responder_consulta(e_chat.get())
            txt_res.delete("1.0", tk.END)
            txt_res.insert(tk.END, resp)

        tk.Button(f_chat, text="Consultar al Asistente", bg="#7B1FA2", fg="white", command=consultar_bot).pack(pady=5)

        f_env = tk.Frame(f_chat); f_env.pack(pady=10)
        def enviar_reporte(formato, canal):
            contenido = txt_res.get("1.0", tk.END)
            archivo = self.chatbot.generar_reporte_archivo(contenido, formato=formato)
            self.chatbot.enviar_por_canal("cliente@email.com", f"Reporte adjunto:\n{archivo}", canal=canal)
            messagebox.showinfo("Enviado", f"Reporte generado en {formato.upper()} y transmitido vía {canal.capitalize()}.")

        tk.Button(f_env, text="Enviar TXT por Gmail", bg="#00897B", fg="white", command=lambda: enviar_reporte("txt", "gmail")).pack(side="left", padx=5)
        tk.Button(f_env, text="Enviar PDF por WhatsApp", bg="#43A047", fg="white", command=lambda: enviar_reporte("pdf", "whatsapp")).pack(side="left", padx=5)

if __name__ == "__main__":
    app = AppPro()
    app.mainloop()