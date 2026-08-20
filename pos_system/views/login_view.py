# views/login_view.py
import tkinter as tk
from tkinter import messagebox
from services.auth_service import AuthService

class LoginView(tk.Toplevel):
    def __init__(self, parent, on_login_success):
        super().__init__(parent)
        self.title("Acceso al Sistema - POS Pro")
        self.geometry("400x300")
        self.protocol("WM_DELETE_WINDOW", parent.quit) # Cierra toda la app si cierran el login
        self.on_login_success = on_login_success
        
        self.crear_widgets()

    def crear_widgets(self):
        marco = tk.Frame(self, padx=20, pady=20)
        marco.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(marco, text="🔐 Inicio de Sesión", font=("Segoe UI", 14, "bold")).pack(pady=10)
        
        tk.Label(marco, text="Usuario:", font=("Segoe UI", 10)).pack(anchor="w")
        self.e_usuario = tk.Entry(marco, width=25, font=("Segoe UI", 10))
        self.e_usuario.pack(pady=5)
        
        tk.Label(marco, text="Contraseña:", font=("Segoe UI", 10)).pack(anchor="w")
        self.e_password = tk.Entry(marco, show="*", width=25, font=("Segoe UI", 10))
        self.e_password.pack(pady=5)
        
        tk.Button(marco, text="Ingresar", bg="#2E7D32", fg="white", font=("Segoe UI", 10, "bold"), 
                  width=18, command=self.intentar_login).pack(pady=15)

    def intentar_login(self):
        usuario = self.e_usuario.get()
        password = self.e_password.get()
        
        rol = AuthService.login(usuario, password)
        if rol:
            self.destroy() # Cierra la ventana de login
            self.on_login_success(usuario, rol)
        else:
            messagebox.showerror("Error de Acceso", "Usuario o contraseña incorrectos.")