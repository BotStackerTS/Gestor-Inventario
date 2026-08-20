# repositories/usuario_repo.py
from database.connection import DatabaseConnection

class UsuarioRepository:
    @staticmethod
    def obtener_usuario_por_nombre(usuario: str):
        with DatabaseConnection.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, usuario, password_hash, rol FROM usuarios WHERE usuario = ?", (usuario,))
            return cursor.fetchone()

    @staticmethod
    def crear_usuario_inicial(usuario: str, password_hash: str, rol: str):
        with DatabaseConnection.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO usuarios (usuario, password_hash, rol) 
                VALUES (?, ?, ?)
            """, (usuario, password_hash, rol))
            conn.commit()