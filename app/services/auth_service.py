"""
Serviço de Autenticação e Autorização
Gerencia login, logout e verificação de permissões por role
"""
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from app.models.database import get_db_connection, is_postgresql_connection


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
        is_postgresql = is_postgresql_connection(conn)
        placeholder = "%s" if is_postgresql else "?"
        
        try:
            senha_hash = generate_password_hash(senha)
            placeholders = ", ".join([placeholder] * 5)
            cursor.execute(f"""
                INSERT INTO usuarios (username, email, senha_hash, nome_completo, role, ativo)
                VALUES ({placeholders}, 1)
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
        is_postgresql = is_postgresql_connection(conn)
        
        if is_postgresql:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        placeholder = "%s" if is_postgresql else "?"
        
        cursor.execute(f"""
            SELECT id, username, email, senha_hash, nome_completo, role, ativo
            FROM usuarios
            WHERE username = {placeholder} AND ativo = 1
        """, (username,))
        
        usuario = cursor.fetchone()
        conn.close()
        
        if not usuario:
            return None
        
        # Para SQLite, converter para dict se necessário
        # Para PostgreSQL com RealDictCursor, já é dict
        if not isinstance(usuario, dict):
            if hasattr(usuario, 'keys'):
                usuario = dict(usuario)
            else:
                # Se for tupla (não deveria acontecer, mas por segurança)
                return None
        
        if check_password_hash(usuario['senha_hash'], senha):
            # Atualizar último acesso
            conn = get_db_connection()
            cursor = conn.cursor()
            is_postgresql = is_postgresql_connection(conn)
            placeholder = "%s" if is_postgresql else "?"
            cursor.execute(f"""
                UPDATE usuarios
                SET ultimo_acesso = {placeholder}
                WHERE id = {placeholder}
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
        is_postgresql = is_postgresql_connection(conn)
        
        if is_postgresql:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        placeholder = "%s" if is_postgresql else "?"
        
        cursor.execute(f"""
            SELECT id, username, email, nome_completo, role, ativo, data_criacao, ultimo_acesso, foto_perfil
            FROM usuarios
            WHERE id = {placeholder} AND ativo = 1
        """, (user_id,))
        
        usuario = cursor.fetchone()
        conn.close()
        
        if usuario:
            if not isinstance(usuario, dict):
                if hasattr(usuario, 'keys'):
                    usuario_dict = dict(usuario)
                else:
                    return None
            else:
                usuario_dict = dict(usuario)
            
            # Converter datetime para string se necessário (PostgreSQL retorna datetime objects)
            if 'ultimo_acesso' in usuario_dict and usuario_dict['ultimo_acesso']:
                if not isinstance(usuario_dict['ultimo_acesso'], str):
                    usuario_dict['ultimo_acesso'] = usuario_dict['ultimo_acesso'].strftime('%Y-%m-%d %H:%M:%S')
            
            if 'data_criacao' in usuario_dict and usuario_dict['data_criacao']:
                if not isinstance(usuario_dict['data_criacao'], str):
                    usuario_dict['data_criacao'] = usuario_dict['data_criacao'].strftime('%Y-%m-%d %H:%M:%S')
            
            return usuario_dict
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
        is_postgresql = is_postgresql_connection(conn)
        
        if is_postgresql:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
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
        
        usuarios = cursor.fetchall()
        conn.close()
        
        # Converter para lista de dicionários e formatar datetimes
        result = []
        for row in usuarios:
            if isinstance(row, dict):
                usuario_dict = dict(row)
            elif hasattr(row, 'keys'):
                usuario_dict = dict(row)
            else:
                # Se for tupla, não deveria acontecer, mas por segurança
                continue
            
            # Converter datetime para string se necessário (PostgreSQL retorna datetime objects)
            if 'ultimo_acesso' in usuario_dict and usuario_dict['ultimo_acesso']:
                if not isinstance(usuario_dict['ultimo_acesso'], str):
                    usuario_dict['ultimo_acesso'] = usuario_dict['ultimo_acesso'].strftime('%Y-%m-%d %H:%M:%S')
            
            if 'data_criacao' in usuario_dict and usuario_dict['data_criacao']:
                if not isinstance(usuario_dict['data_criacao'], str):
                    usuario_dict['data_criacao'] = usuario_dict['data_criacao'].strftime('%Y-%m-%d %H:%M:%S')
            
            result.append(usuario_dict)
        
        return result
    
    @staticmethod
    def atualizar_usuario(user_id, nome_completo=None, email=None, role=None, ativo=None, foto_perfil=None):
        """Atualiza dados do usuário"""
        conn = get_db_connection()
        cursor = conn.cursor()
        is_postgresql = is_postgresql_connection(conn)
        placeholder = "%s" if is_postgresql else "?"
        
        updates = []
        params = []
        
        if nome_completo is not None:
            updates.append(f"nome_completo = {placeholder}")
            params.append(nome_completo)
        
        if email is not None:
            updates.append(f"email = {placeholder}")
            params.append(email)
        
        if role is not None:
            if role not in AuthService.ROLES:
                raise ValueError(f"Role inválida. Use: {', '.join(AuthService.ROLES.keys())}")
            updates.append(f"role = {placeholder}")
            params.append(role)
        
        if ativo is not None:
            updates.append(f"ativo = {placeholder}")
            params.append(1 if ativo else 0)
        
        if foto_perfil is not None:
            updates.append(f"foto_perfil = {placeholder}")
            params.append(foto_perfil)
        
        if not updates:
            conn.close()
            return False
        
        params.append(user_id)
        cursor.execute(f"""
            UPDATE usuarios
            SET {', '.join(updates)}
            WHERE id = {placeholder}
        """, params)
        
        conn.commit()
        conn.close()
        return True
    
    @staticmethod
    def alterar_senha(user_id, senha_atual, nova_senha):
        """Altera a senha do usuário"""
        conn = get_db_connection()
        cursor = conn.cursor()
        is_postgresql = is_postgresql_connection(conn)
        placeholder = "%s" if is_postgresql else "?"
        
        cursor.execute(f"SELECT senha_hash FROM usuarios WHERE id = {placeholder}", (user_id,))
        usuario = cursor.fetchone()
        
        if not usuario or not check_password_hash(usuario['senha_hash'], senha_atual):
            conn.close()
            return False
        
        nova_senha_hash = generate_password_hash(nova_senha)
        cursor.execute(f"""
            UPDATE usuarios
            SET senha_hash = {placeholder}
            WHERE id = {placeholder}
        """, (nova_senha_hash, user_id))
        
        conn.commit()
        conn.close()
        return True
    
    @staticmethod
    def resetar_senha(user_id, nova_senha):
        """Reseta a senha do usuário (apenas Master pode fazer isso)"""
        conn = get_db_connection()
        cursor = conn.cursor()
        is_postgresql = is_postgresql_connection(conn)
        placeholder = "%s" if is_postgresql else "?"
        
        nova_senha_hash = generate_password_hash(nova_senha)
        cursor.execute(f"""
            UPDATE usuarios
            SET senha_hash = {placeholder}
            WHERE id = {placeholder}
        """, (nova_senha_hash, user_id))
        
        conn.commit()
        conn.close()
        return True

