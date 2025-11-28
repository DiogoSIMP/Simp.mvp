"""
Decoradores para proteção de rotas baseado em roles
"""
from functools import wraps
from flask import session, redirect, url_for, flash, request


def login_required(f):
    """Decorador que exige que o usuário esteja logado e com 2FA verificado"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar se está logado
        if 'user_id' not in session:
            flash('Você precisa estar logado para acessar esta página.', 'warning')
            return redirect(url_for('login', next=request.url))
        
        # Verificar se 2FA foi verificado
        if not session.get('two_fa_verified'):
            # Se tem dados pendentes, redirecionar para verificação 2FA
            if 'pending_user_id' in session:
                return redirect(url_for('verificar_2fa'))
            # Caso contrário, fazer login novamente
            session.clear()
            flash('Sessão expirada. Faça login novamente.', 'warning')
            return redirect(url_for('login', next=request.url))
        
        return f(*args, **kwargs)
    return decorated_function


def role_required(*allowed_roles):
    """
    Decorador que exige que o usuário tenha um dos roles especificados
    
    Uso:
        @role_required('Master', 'Adm')
        def minha_rota():
            ...
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            user_role = session.get('user_role')
            
            if not user_role:
                flash('Acesso negado. Faça login novamente.', 'error')
                return redirect(url_for('login'))
            
            # Verificar hierarquia de roles
            from app.services.auth_service import AuthService
            
            # Se Master, tem acesso a tudo
            if user_role == 'Master':
                return f(*args, **kwargs)
            
            # Verificar se o role do usuário tem permissão suficiente
            for role in allowed_roles:
                if AuthService.verificar_permissao(user_role, role):
                    return f(*args, **kwargs)
            
            flash('Você não tem permissão para acessar esta página.', 'error')
            return redirect(url_for('entregadores'))  # Redireciona para página padrão
        
        return decorated_function
    return decorator


def master_required(f):
    """Decorador que exige role Master"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if session.get('user_role') != 'Master':
            flash('Acesso restrito. Apenas usuários Master podem acessar esta página.', 'error')
            return redirect(url_for('entregadores'))
        return f(*args, **kwargs)
    return decorated_function


def adm_or_master_required(f):
    """Decorador que exige role Adm ou Master"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        user_role = session.get('user_role')
        if user_role not in ['Master', 'Adm']:
            flash('Acesso restrito. Apenas Administradores podem acessar esta página.', 'error')
            return redirect(url_for('entregadores'))
        return f(*args, **kwargs)
    return decorated_function

