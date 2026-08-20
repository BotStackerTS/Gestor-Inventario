# services/auth_service.py
import bcrypt
from repositories.usuario_repo import UsuarioRepository

class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

    @classmethod
    def inicializar_usuarios_por_defecto(cls):
        # Crear usuarios seguros por defecto si no existen
        admin_hash = cls.hash_password("admin123")
        cajero_hash = cls.hash_password("caja123")
        UsuarioRepository.crear_usuario_inicial("admin", admin_hash, "admin")
        UsuarioRepository.crear_usuario_inicial("cajero", cajero_hash, "cajero")

    @classmethod
    def login(cls, usuario: str, password: str) -> str | None:
        user_row = UsuarioRepository.obtener_usuario_por_nombre(usuario)
        if user_row:
            user_id, username, password_hash, rol = user_row
            if cls.verify_password(password, password_hash):
                return rol
        return None