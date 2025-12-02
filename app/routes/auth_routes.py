"""
Rotas de Autenticação
Login, logout e gerenciamento de sessão
"""
from flask import render_template, request, redirect, url_for, flash, session, send_from_directory, jsonify
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from config import Config
from app.services.auth_service import AuthService
from app.services.two_fa_service import TwoFAService
from app.services.email_service import EmailService
from app.utils.auth_decorators import login_required, master_required


def init_auth_routes(app):
    """Inicializa as rotas de autenticação"""
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Página de login"""
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            senha = request.form.get('senha', '')
            next_url = request.args.get('next') or request.form.get('next')
            
            if not username or not senha:
                flash('Por favor, preencha todos os campos.', 'error')
                return render_template('auth/login.html')
            
            usuario = AuthService.verificar_login(username, senha)
            
            if usuario:
                # Gerar código 2FA
                codigo_2fa = TwoFAService.gerar_codigo()
                data_geracao = datetime.now().isoformat()
                
                # Salvar dados temporários na sessão (antes de completar login)
                session['pending_user_id'] = usuario['id']
                session['pending_username'] = usuario['username']
                session['pending_nome_completo'] = usuario['nome_completo']
                session['pending_email'] = usuario['email']
                session['pending_role'] = usuario['role']
                session['two_fa_code'] = codigo_2fa
                session['two_fa_generated_at'] = data_geracao
                session['next_url'] = next_url
                
                # Enviar código por e-mail
                EmailService.enviar_codigo_2fa(
                    email_destino=usuario['email'],
                    codigo=codigo_2fa,
                    nome_usuario=usuario['nome_completo']
                )
                
                flash('Código de verificação enviado para seu e-mail!', 'info')
                return redirect(url_for('verificar_2fa'))
            else:
                flash('Usuário ou senha incorretos.', 'error')
        
        # Se já estiver logado e com 2FA verificado, redirecionar
        if 'user_id' in session and session.get('two_fa_verified'):
            return redirect(url_for('entregadores'))
        
        return render_template('auth/login.html')
    
    @app.route('/verificar-2fa', methods=['GET', 'POST'])
    def verificar_2fa():
        """Página de verificação 2FA"""
        # Verificar se há dados pendentes na sessão
        if 'pending_user_id' not in session:
            flash('Sessão expirada. Faça login novamente.', 'warning')
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            codigo_inserido = request.form.get('codigo', '').strip()
            
            if not codigo_inserido:
                flash('Por favor, insira o código de verificação.', 'error')
                return render_template('auth/verificar_2fa.html')
            
            codigo_esperado = session.get('two_fa_code')
            data_geracao = session.get('two_fa_generated_at')
            
            # Verificar se o código expirou
            if TwoFAService.codigo_expirado(data_geracao):
                session.clear()
                flash('Código expirado. Faça login novamente.', 'error')
                return redirect(url_for('login'))
            
            # Validar código
            if TwoFAService.validar_codigo(codigo_inserido, codigo_esperado):
                # Login completo - criar sessão final
                session['user_id'] = session['pending_user_id']
                session['username'] = session['pending_username']
                session['nome_completo'] = session['pending_nome_completo']
                session['email'] = session['pending_email']
                session['user_role'] = session['pending_role']
                session['two_fa_verified'] = True
                session['last_activity'] = datetime.now().isoformat()
                session.permanent = True
                
                # Buscar foto de perfil se existir
                usuario_completo = AuthService.buscar_usuario_por_id(session['user_id'])
                if usuario_completo and usuario_completo.get('foto_perfil'):
                    session['foto_perfil'] = usuario_completo['foto_perfil']
                
                # Limpar dados temporários
                session.pop('pending_user_id', None)
                session.pop('pending_username', None)
                session.pop('pending_nome_completo', None)
                session.pop('pending_email', None)
                session.pop('pending_role', None)
                session.pop('two_fa_code', None)
                session.pop('two_fa_generated_at', None)
                
                next_url = session.pop('next_url', None)
                
                flash(f'Bem-vindo, {session["nome_completo"]}!', 'success')
                
                # Redirecionar para a URL original ou página padrão
                if next_url and next_url.startswith('/'):
                    return redirect(next_url)
                return redirect(url_for('entregadores'))
            else:
                flash('Código de verificação incorreto. Tente novamente.', 'error')
        
        return render_template('auth/verificar_2fa.html')
    
    @app.route('/reenviar-codigo-2fa', methods=['POST'])
    def reenviar_codigo_2fa():
        """Reenvia o código 2FA"""
        if 'pending_user_id' not in session:
            flash('Sessão expirada. Faça login novamente.', 'warning')
            return redirect(url_for('login'))
        
        # Gerar novo código
        codigo_2fa = TwoFAService.gerar_codigo()
        data_geracao = datetime.now().isoformat()
        
        session['two_fa_code'] = codigo_2fa
        session['two_fa_generated_at'] = data_geracao
        
        # Enviar novo código
        EmailService.enviar_codigo_2fa(
            email_destino=session['pending_email'],
            codigo=codigo_2fa,
            nome_usuario=session['pending_nome_completo']
        )
        
        flash('Novo código de verificação enviado!', 'success')
        return redirect(url_for('verificar_2fa'))
    
    @app.route('/logout')
    def logout():
        """Fazer logout"""
        nome = session.get('nome_completo', 'Usuário')
        timeout = request.args.get('timeout')
        session.clear()
        if timeout:
            flash('Sua sessão expirou por inatividade. Faça login novamente.', 'warning')
        else:
            flash(f'Até logo, {nome}!', 'info')
        return redirect(url_for('login'))
    
    @app.route('/check-session')
    @login_required
    def check_session():
        """Endpoint para verificar se a sessão ainda é válida (usado pelo JavaScript)"""
        return jsonify({'status': 'ok', 'user_id': session.get('user_id')})
    
    @app.route('/perfil')
    @login_required
    def perfil():
        """Página de perfil do usuário"""
        user_id = session.get('user_id')
        usuario = AuthService.buscar_usuario_por_id(user_id)
        
        if not usuario:
            flash('Usuário não encontrado.', 'error')
            session.clear()
            return redirect(url_for('login'))
        
        # Formatar data de cadastro
        if usuario.get('data_criacao'):
            try:
                data_criacao = usuario['data_criacao']
                
                # Se for datetime object (PostgreSQL), converter diretamente
                if isinstance(data_criacao, datetime):
                    usuario['data_criacao_formatada'] = data_criacao.strftime('%d/%m/%Y')
                else:
                    # Se for string (SQLite), parsear e formatar
                    data_str = str(data_criacao)
                    # Remover timezone se existir
                    if 'T' in data_str:
                        data_str = data_str.split('T')[0]
                    # Tentar parsear
                    data_obj = datetime.strptime(data_str, '%Y-%m-%d')
                    usuario['data_criacao_formatada'] = data_obj.strftime('%d/%m/%Y')
            except Exception as e:
                # Fallback: tentar pegar primeiros 10 caracteres se for string
                if isinstance(usuario['data_criacao'], str):
                    usuario['data_criacao_formatada'] = usuario['data_criacao'][:10]
                else:
                    usuario['data_criacao_formatada'] = '—'
        else:
            usuario['data_criacao_formatada'] = '—'
        
        return render_template('auth/perfil.html', usuario=usuario)
    
    @app.route('/perfil/atualizar', methods=['POST'])
    @login_required
    def atualizar_perfil():
        """Atualiza os dados do perfil do usuário"""
        user_id = session.get('user_id')
        nome_completo = request.form.get('nome_completo', '').strip()
        
        if not nome_completo:
            flash('O nome completo é obrigatório.', 'error')
            return redirect(url_for('perfil'))
        
        try:
            AuthService.atualizar_usuario(
                user_id,
                nome_completo=nome_completo
            )
            # Atualizar na sessão também
            session['nome_completo'] = nome_completo
            flash('Perfil atualizado com sucesso!', 'success')
        except Exception as e:
            flash(f'Erro ao atualizar perfil: {str(e)}', 'error')
        
        return redirect(url_for('perfil'))
    
    @app.route('/perfil/upload-foto', methods=['POST'])
    @login_required
    def upload_foto_perfil():
        """Faz upload da foto de perfil do usuário"""
        user_id = session.get('user_id')
        
        if 'foto' not in request.files:
            flash('Nenhuma imagem selecionada.', 'error')
            return redirect(url_for('perfil'))
        
        file = request.files['foto']
        
        if file.filename == '':
            flash('Nenhuma imagem selecionada.', 'error')
            return redirect(url_for('perfil'))
        
        # Verificar extensão
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        if '.' in file.filename:
            ext = file.filename.rsplit('.', 1)[1].lower()
            if ext not in allowed_extensions:
                flash('Formato de imagem não permitido. Use: PNG, JPG, JPEG, GIF ou WEBP.', 'error')
                return redirect(url_for('perfil'))
        
        try:
            # Criar pasta se não existir
            os.makedirs(Config.PROFILE_PHOTOS_FOLDER, exist_ok=True)
            
            # Nome do arquivo: user_{id}.{ext}
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
            filename = f"user_{user_id}.{ext}"
            filepath = os.path.join(Config.PROFILE_PHOTOS_FOLDER, filename)
            
            # Salvar arquivo
            file.save(filepath)
            
            # Atualizar no banco
            foto_url = f"img/profiles/{filename}"
            AuthService.atualizar_usuario(user_id, foto_perfil=foto_url)
            
            # Atualizar na sessão
            session['foto_perfil'] = foto_url
            
            flash('Foto de perfil atualizada com sucesso!', 'success')
        except Exception as e:
            flash(f'Erro ao fazer upload da foto: {str(e)}', 'error')
        
        return redirect(url_for('perfil'))
    
    @app.route('/img/profiles/<filename>')
    def profile_photo(filename):
        """Serve as fotos de perfil"""
        return send_from_directory(Config.PROFILE_PHOTOS_FOLDER, filename)
    
    @app.route('/perfil/alterar-senha', methods=['POST'])
    @login_required
    def alterar_senha():
        """Altera a senha do usuário logado"""
        user_id = session.get('user_id')
        senha_atual = request.form.get('senha_atual', '')
        nova_senha = request.form.get('nova_senha', '')
        confirmar_senha = request.form.get('confirmar_senha', '')
        
        if not senha_atual or not nova_senha or not confirmar_senha:
            flash('Por favor, preencha todos os campos.', 'error')
            return redirect(url_for('perfil'))
        
        if nova_senha != confirmar_senha:
            flash('As novas senhas não coincidem.', 'error')
            return redirect(url_for('perfil'))
        
        if len(nova_senha) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'error')
            return redirect(url_for('perfil'))
        
        if AuthService.alterar_senha(user_id, senha_atual, nova_senha):
            flash('Senha alterada com sucesso!', 'success')
        else:
            flash('Senha atual incorreta.', 'error')
        
        return redirect(url_for('perfil'))
    
    @app.route('/admin/usuarios')
    @master_required
    def admin_usuarios():
        """Lista de usuários (apenas Master)"""
        usuarios = AuthService.listar_usuarios()
        return render_template('auth/admin_usuarios.html', usuarios=usuarios)
    
    @app.route('/admin/usuarios/criar', methods=['POST'])
    @master_required
    def criar_usuario():
        """Cria um novo usuário (apenas Master)"""
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '')
        nome_completo = request.form.get('nome_completo', '').strip()
        role = request.form.get('role', 'Operacional')
        
        # Debug: log dos dados recebidos
        print(f"🔍 [Criar Usuário] Dados recebidos:")
        print(f"  - username: {username}")
        print(f"  - email: {email}")
        print(f"  - senha: {'*' * len(senha) if senha else '(vazia)'}")
        print(f"  - nome_completo: {nome_completo}")
        print(f"  - role: {role}")
        
        if not all([username, email, senha, nome_completo]):
            flash('Por favor, preencha todos os campos.', 'error')
            return redirect(url_for('admin_usuarios'))
        
        if len(senha) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'error')
            return redirect(url_for('admin_usuarios'))
        
        try:
            AuthService.criar_usuario(username, email, senha, nome_completo, role)
            flash(f'Usuário {nome_completo} criado com sucesso!', 'success')
        except ValueError as e:
            print(f"❌ [Criar Usuário] ValueError: {e}")
            flash(str(e), 'error')
        except Exception as e:
            print(f"❌ [Criar Usuário] Erro: {e}")
            import traceback
            traceback.print_exc()
            flash(f'Erro ao criar usuário: {str(e)}', 'error')
        
        return redirect(url_for('admin_usuarios'))
    
    @app.route('/admin/usuarios/<int:user_id>/editar', methods=['POST'])
    @master_required
    def editar_usuario(user_id):
        """Edita um usuário (apenas Master)"""
        nome_completo = request.form.get('nome_completo', '').strip()
        email = request.form.get('email', '').strip()
        role = request.form.get('role')
        ativo = request.form.get('ativo') == 'on'
        nova_senha = request.form.get('nova_senha', '').strip()
        
        try:
            # Atualizar dados básicos
            AuthService.atualizar_usuario(
                user_id,
                nome_completo=nome_completo if nome_completo else None,
                email=email if email else None,
                role=role if role else None,
                ativo=ativo
            )
            
            # Se forneceu nova senha, resetar
            if nova_senha and len(nova_senha) >= 6:
                AuthService.resetar_senha(user_id, nova_senha)
                flash('Usuário atualizado e senha resetada com sucesso!', 'success')
            else:
                flash('Usuário atualizado com sucesso!', 'success')
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'Erro ao atualizar usuário: {str(e)}', 'error')
        
        return redirect(url_for('admin_usuarios'))
    
    @app.route('/admin/usuarios/<int:user_id>/resetar-senha', methods=['POST'])
    @master_required
    def resetar_senha_usuario(user_id):
        """Reseta a senha de um usuário (apenas Master)"""
        nova_senha = request.form.get('nova_senha', '')
        
        if not nova_senha or len(nova_senha) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'error')
            return redirect(url_for('admin_usuarios'))
        
        try:
            AuthService.resetar_senha(user_id, nova_senha)
            flash('Senha resetada com sucesso!', 'success')
        except Exception as e:
            flash(f'Erro ao resetar senha: {str(e)}', 'error')
        
        return redirect(url_for('admin_usuarios'))

