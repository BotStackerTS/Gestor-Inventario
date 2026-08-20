# main.py
import tkinter as tk
from database.connection import DatabaseConnection
from services.auth_service import AuthService
from views.login_view import LoginView
from views.main_window import MainWindow

def iniciar_app():
    # 1. Inicializar la base de datos y tablas
    DatabaseConnection.inicializar_base_datos()
    
    # 2. Asegurar la creación de usuarios con hashes seguros
    AuthService.inicializar_usuarios_por_defecto()

    # 3. Lanzar la aplicación raíz oculta para el login
    root = tk.Tk()
    root.withdraw() # Oculta la ventana principal temporalmente

    def abrir_sistema(usuario, rol):
        root.destroy() # Destruye el root oculto y abre la ventana principal real
        app = MainWindow(usuario, rol)
        app.mainloop()

    # Mostrar la vista de login
    LoginView(root, abrir_sistema)
    
    root.mainloop()

if __name__ == "__main__":
    iniciar_app()