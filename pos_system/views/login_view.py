# views/login_view.py
import tkinter as tk
from tkinter import messagebox
from database.connection import DatabaseConnection

class LoginView(tk.Toplevel):
    def __init__(self, master, on_login_success):
        super().__init__(master)
        self.on_login_success = on_login_success
        self.title("POS Pro - Iniciar Sesión")
        self.geometry("350x250")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", master.destroy)
        self.crear_interfaz()

    def crear_interfaz(self):
        tk.Label(self, text="Iniciar Sesión", font=("Segoe UI", 14, "bold")).pack(pady=15)

        f_form = tk.Frame(self)
        f_form.pack(pady=5)

        tk.Label(f_form, text="Usuario:").grid(row=0, column=0, sticky="w", pady=5)
        self.e_usuario = tk.Entry(f_form, width=20)
        self.e_usuario.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(f_form, text="Contraseña:").grid(row=1, column=0, sticky="w", pady=5)
        self.e_pass = tk.Entry(f_form, width=20, show="*")
        self.e_pass.grid(row=1, column=1, padx=10, pady=5)

        tk.Button(self, text="Ingresar", bg="#2E7D32", fg="white", width=15, command=self.intentar_login).pack(pady=15)

    def intentar_login(self):
        usuario = self.e_usuario.get().strip()
        password = self.e_pass.get().strip()

        with DatabaseConnection.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT rol FROM usuarios WHERE usuario = ? AND password_hash = ?", (usuario, password))
            row = cursor.fetchone()

        if row:
            rol = row[0]
            self.destroy()
            self.on_login_success(usuario, rol)
        else:
            messagebox.showerror("Error", "Usuario o contraseña incorrectos")