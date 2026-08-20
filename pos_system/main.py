# main.py
import tkinter as tk
from database.connection import DatabaseConnection
from repositories.inventario_repo import InventarioRepository
from models.entidades import Articulo
from views.login_view import LoginView
from views.main_window import MainWindow

def inicializar_sistema():
    DatabaseConnection.inicializar_base_datos()
    try:
        with DatabaseConnection.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM usuarios")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO usuarios (usuario, password_hash, rol) VALUES (?, ?, ?)", 
                               ("admin", "1234", "admin"))
                cursor.execute("INSERT INTO usuarios (usuario, password_hash, rol) VALUES (?, ?, ?)", 
                               ("cajero", "1234", "cajero"))
                conn.commit()

        if not InventarioRepository.obtener_todos():
            articulos_iniciales = [
                Articulo(codigo="A001", nombre="Coca Cola 1.5L", cantidad=20, precio_base=1000.0, precio_final=1500.0, stock_minimo=5),
                Articulo(codigo="A002", nombre="Alfajor Triple", cantidad=0, precio_base=400.0, precio_final=650.0, stock_minimo=10),
                Articulo(codigo="A003", nombre="Pan Lactal 500g", cantidad=15, precio_base=800.0, precio_final=1200.0, stock_minimo=4)
            ]
            for art in articulos_iniciales:
                InventarioRepository.insertar(art)
    except Exception as e:
        print(f"Aviso al inicializar datos: {e}")

def iniciar_app():
    inicializar_sistema()
    root = tk.Tk()
    root.withdraw()
    
    def on_login_success(usuario, rol):
        app = MainWindow(usuario, rol)
        app.mainloop()

    LoginView(root, on_login_success)
    root.mainloop()

if __name__ == "__main__":
    iniciar_app()