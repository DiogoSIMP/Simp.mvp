"""
Serviço de Autenticação e Autorização
Gerencia login, logout e verificação de permissões por role
"""
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from app.models.database import get_db_connection


class AuthService:
    """Serviço para gerenciar autenticação de usuários internos"""
    
    # Hierarquia de roles (Master > Adm > Operacional)
    ROLES = {
        'Master': 3,
        'Adm': 2,
        'Operacional': 1
    }
    
    @staticmethod
    def criar_usuario(username, email, senha, nome_completo, role='Operacional'):
        """Cria um novo usuário no banco de dados"""
        if role not in AuthService.ROLES:
            raise ValueError(f"Role inválida. Use: {', '.join(AuthService.ROLES.keys())}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            senha_hash = generate_password_hash(senha)
            cursor.execute("""
                INSERT INTO usuarios (username, email, senha_hash, nome_completo, role, ativo)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (username, email, senha_hash, nome_completo, role))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    @staticmethod
    def verificar_login(username, senha):
        """Verifica credenciais e retorna dados do usuário se válido"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, email, senha_hash, nome_completo, role, ativo
            FROM usuarios
            WHERE username = ? AND ativo = 1
        """, (username,))
        
        usuario = cursor.fetchone()
        conn.close()
        
        if not usuario:
            return None
        
        if check_password_hash(usuario['senha_hash'], senha):
            # Atualizar último acesso
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE usuarios
                SET ultimo_acesso = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), usuario['id']))
            conn.commit()
            conn.close()
            
            return {
                'id': usuario['id'],
                'username': usuario['username'],
                'email': usuario['email'],
                'nome_completo': usuario['nome_completo'],
                'role': usuario['role']
            }
        
        return None
    
    @staticmethod
    def buscar_usuario_por_id(user_id):
        """Busca usuário por ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, email, nome_completo, role, ativo, data_criacao, ultimo_acesso, foto_perfil
            FROM usuarios
            WHERE id = ? AND ativo = 1
        """, (user_id,))
        
        usuario = cursor.fetchone()
        conn.close()
        
        if usuario:
            return dict(usuario)
        return None
    
    @staticmethod
    def verificar_permissao(user_role, role_requerida):
        """Verifica se o role do usuário tem permissão suficiente"""
        if user_role not in AuthService.ROLES or role_requerida not in AuthService.ROLES:
            return False
        
        return AuthService.ROLES[user_role] >= AuthService.ROLES[role_requerida]
    
    @staticmethod
    def listar_usuarios():
        """Lista todos os usuários ativos"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, email, nome_completo, role, ativo, data_criacao, ultimo_acesso
            FROM usuarios
            ORDER BY 
                CASE role
                    WHEN 'Master' THEN 1
                    WHEN 'Adm' THEN 2
                    WHEN 'Operacional' THEN 3
                END,
                nome_completo
        """)
        
        usuarios = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return usuarios
    
    @staticmethod
    def atualizar_usuario(user_id, nome_completo=None, email=None, role=None, ativo=None, foto_perfil=None):
        """Atualiza dados do usuário"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if nome_completo is not None:
            updates.append("nome_completo = ?")
            params.append(nome_completo)
        
        if email is not None:
            updates.append("email = ?")
            params.append(email)
        
        if role is not None:
            if role not in AuthService.ROLES:
                raise ValueError(f"Role inválida. Use: {', '.join(AuthService.ROLES.keys())}")
            updates.append("role = ?")
            params.append(role)
        
        if ativo is not None:
            updates.append("ativo = ?")
            params.append(1 if ativo else 0)
        
        if foto_perfil is not None:
            updates.append("foto_perfil = ?")
            params.append(foto_perfil)
        
        if not updates:
            conn.close()
            return False
        
        params.append(user_id)
        cursor.execute(f"""
            UPDATE usuarios
            SET {', '.join(updates)}
            WHERE id = ?
        """, params)
        
        conn.commit()
        conn.close()
        return True
    
    @staticmethod
    def alterar_senha(user_id, senha_atual, nova_senha):
        """Altera a senha do usuário"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT senha_hash FROM usuarios WHERE id = ?", (user_id,))
        usuario = cursor.fetchone()
        
        if not usuario or not check_password_hash(usuario['senha_hash'], senha_atual):
            conn.close()
            return False
        
        nova_senha_hash = generate_password_hash(nova_senha)
        cursor.execute("""
            UPDATE usuarios
            SET senha_hash = ?
            WHERE id = ?
        """, (nova_senha_hash, user_id))
        
        conn.commit()
        conn.close()
        return True
    
    @staticmethod
    def resetar_senha(user_id, nova_senha):
        """Reseta a senha do usuário (apenas Master pode fazer isso)"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        nova_senha_hash = generate_password_hash(nova_senha)
        cursor.execute("""
            UPDATE usuarios
            SET senha_hash = ?
            WHERE id = ?
        """, (nova_senha_hash, user_id))
        
        conn.commit()
        conn.close()
        return True

