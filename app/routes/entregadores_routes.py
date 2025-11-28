"""
Rotas para gerenciamento de entregadores
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from app.services.entregadores_service import EntregadoresService
from app.utils.auth_decorators import login_required, adm_or_master_required
from app.utils.constants import (
    TEMPLATES_ENTREGADORES,
    MESSAGES,
    PAGINATION_PER_PAGE_ENTREGADORES,
    CAMPOS_OBRIGATORIOS_ENTREGADOR,
    CAMPOS_OBRIGATORIOS_ENTREGADOR_EDICAO,
    DEFAULT_EMISSOR,
    DEFAULT_STATUS
)
from app.utils.route_helpers import (
    paginate_items,
    get_page_from_request,
    extract_form_data,
    validate_required_fields,
    get_flash_message,
    json_response
)


# Mapeamento de campos do formulário
CAMPOS_FORM_ENTREGADOR = [
    'id_da_pessoa_entregadora', 'recebedor', 'cpf', 'email', 'cnpj',
    'subpraca', 'emissor', 'status', 'tipo_de_chave_pix', 'chave_pix'
]

CAMPOS_FORM_ENTREGADOR_EDICAO = [
    'recebedor', 'cpf', 'cnpj', 'email', 'subpraca',
    'emissor', 'status', 'tipo_de_chave_pix', 'chave_pix'
]


def init_entregadores_routes(app):
    """Inicializa as rotas de entregadores"""
    
    @app.route('/')
    def index():
        return redirect(url_for('entregadores'))
    
    @app.route('/entregadores')
    @login_required
    def entregadores():
        """Lista os entregadores com paginação"""
        try:
            page = get_page_from_request()
            entregadores_list = EntregadoresService.listar_entregadores()
            entregadores_paginados, total_pages = paginate_items(
                entregadores_list, page, PAGINATION_PER_PAGE_ENTREGADORES
            )
            
            return render_template(
                TEMPLATES_ENTREGADORES['index'],
                entregadores=entregadores_paginados,
                entregadores_todos=entregadores_list,
                page=page,
                total_pages=total_pages
            )
        except Exception as e:
            flash(
                get_flash_message('entregador', 'erro_carregar', error=str(e)),
                'entregador_error'
            )
            return render_template(TEMPLATES_ENTREGADORES['index'], entregadores=[])
    
    @app.route('/entregador/<string:id_entregador>/detalhes-json', methods=['GET'])
    def detalhes_entregador_json(id_entregador):
        """Retorna os dados de um entregador em JSON para o painel lateral"""
        entregador = EntregadoresService.buscar_entregador_por_id(id_entregador)
        if not entregador:
            return json_response(
                success=False,
                message='Entregador não encontrado',
                status_code=404
            )
        return jsonify(entregador)
    
    @app.route('/entregador/<string:id_entregador>/editar', methods=['POST'])
    @adm_or_master_required
    def editar_entregador_json(id_entregador):
        """Recebe dados via AJAX e atualiza o entregador"""
        if not request.is_json:
            return json_response(
                success=False,
                message='Content-Type deve ser application/json',
                status_code=400
            )
        
        dados = request.json
        if not dados:
            return json_response(
                success=False,
                message='Nenhum dado recebido',
                status_code=400
            )
        
        try:
            EntregadoresService.atualizar_entregador(id_entregador, dados)
            return json_response(
                success=True,
                message=get_flash_message('entregador', 'atualizado')
            )
        except Exception as e:
            import traceback
            print(f"Erro ao atualizar entregador: {str(e)}")
            print(traceback.format_exc())
            return json_response(
                success=False,
                message=str(e),
                status_code=400
            )
    
    @app.route('/api/bancario/dados', methods=['GET'])
    def api_dados_bancarios_por_cpf():
        """Busca dados preenchidos no formulário bancário (historico_pix) pelo CPF"""
        cpf = (request.args.get('cpf') or '').strip()
        if not cpf:
            return json_response(
                success=False,
                message='Informe o CPF para realizar a busca.',
                status_code=400
            )

        try:
            dados = EntregadoresService.buscar_dados_bancarios_por_cpf(cpf)
            if not dados:
                return json_response(
                    success=False,
                    message='Nenhum dado bancário encontrado para este CPF.',
                    status_code=404
                )

            return json_response(success=True, data=dados)
        except Exception as e:
            return json_response(
                success=False,
                message=str(e),
                status_code=500
            )
    
    @app.route('/entregador/<string:id_entregador>/detalhes')
    def detalhes_entregador(id_entregador):
        """Exibe detalhes completos de um entregador"""
        try:
            entregador = EntregadoresService.buscar_entregador_por_id(id_entregador)
            
            if not entregador:
                flash(
                    get_flash_message('entregador', 'nao_encontrado'),
                    'entregador_error'
                )
                return redirect(url_for('entregadores'))
            
            # Se não tiver CNPJ, exibe "Sem CNPJ"
            if not entregador.get('cnpj'):
                entregador['cnpj'] = 'Sem CNPJ'
            
            return render_template(
                TEMPLATES_ENTREGADORES['detalhes'],
                entregador=entregador
            )
        except Exception as e:
            flash(
                get_flash_message('entregador', 'erro_detalhes', error=str(e)),
                'entregador_error'
            )
            return redirect(url_for('entregadores'))
    
    @app.route('/entregador/novo', methods=['GET', 'POST'])
    @adm_or_master_required
    def novo_entregador():
        """Adiciona um novo entregador"""
        if request.method == 'POST':
            dados = extract_form_data(CAMPOS_FORM_ENTREGADOR)
            
            # Aplica valores padrão
            dados['emissor'] = dados.get('emissor') or DEFAULT_EMISSOR
            dados['status'] = dados.get('status') or DEFAULT_STATUS
            
            # Valida campos obrigatórios
            is_valid, missing = validate_required_fields(
                dados, CAMPOS_OBRIGATORIOS_ENTREGADOR
            )
            
            if not is_valid:
                flash(
                    get_flash_message('entregador', 'campos_obrigatorios'),
                    'error'
                )
                return render_template(TEMPLATES_ENTREGADORES['form'])
            
            try:
                EntregadoresService.criar_entregador(dados)
                flash(
                    get_flash_message('entregador', 'criado'),
                    'entregador_success'
                )
                return redirect(url_for('entregadores'))
            except Exception as e:
                flash(str(e), 'entregador_error')
        
        # GET - Pré-preencher com dados da query string se disponível
        dados_preenchidos = type('obj', (object,), {
            'id_da_pessoa_entregadora': request.args.get('id_da_pessoa_entregadora', ''),
            'recebedor': request.args.get('recebedor', '')
        }) if request.method == 'GET' else None
        
        return render_template(
            TEMPLATES_ENTREGADORES['form'],
            dados_preenchidos=dados_preenchidos
        )
    
    @app.route('/entregador/novo-pix', methods=['GET', 'POST'])
    @adm_or_master_required
    def novo_entregador_pix():
        """Adiciona um novo entregador a partir dos dados do PIX"""
        # Obter dados da query string
        cpf = request.args.get('cpf', '')
        nome = request.args.get('nome', '')
        tipo_chave = request.args.get('tipo_chave', '')
        chave_pix = request.args.get('chave_pix', '')
        
        # Mapear tipos de chave do banco para o formulário
        tipo_chave_map = {
            'EMAIL': 'Email',
            'TELEFONE': 'Telefone',
            'CNPJ': 'CNPJ',
            'ALEATORIA': 'Chave Aleatória',
            'AUTO': 'Chave Aleatória'
        }
        tipo_chave_form = tipo_chave_map.get(tipo_chave, tipo_chave)
        
        if request.method == 'POST':
            dados = extract_form_data(CAMPOS_FORM_ENTREGADOR)
            
            # Aplica valores padrão
            dados['emissor'] = dados.get('emissor') or DEFAULT_EMISSOR
            dados['status'] = dados.get('status') or DEFAULT_STATUS
            
            # Valida campos obrigatórios
            is_valid, missing = validate_required_fields(
                dados, CAMPOS_OBRIGATORIOS_ENTREGADOR
            )
            
            if not is_valid:
                flash(
                    get_flash_message('entregador', 'campos_obrigatorios'),
                    'entregador_error'
                )
                # Manter os dados pré-preenchidos
                class EntregadorPreenchido:
                    def __init__(self, recebedor, cpf, tipo_chave_pix, chave_pix):
                        self.recebedor = recebedor
                        self.cpf = cpf
                        self.tipo_de_chave_pix = tipo_chave_pix
                        self.chave_pix = chave_pix
                
                entregador_preenchido = EntregadorPreenchido(
                    nome or dados.get('recebedor', ''),
                    cpf or dados.get('cpf', ''),
                    tipo_chave_form or dados.get('tipo_de_chave_pix', ''),
                    chave_pix or dados.get('chave_pix', '')
                )
                return render_template(
                    TEMPLATES_ENTREGADORES['form'],
                    entregador=entregador_preenchido,
                    is_novo_pix=True
                )
            
            try:
                from app.utils.route_helpers import normalize_cpf
                
                cpf_limpo = normalize_cpf(dados.get('cpf', ''))
                chave_pix = dados.get('chave_pix', '')
                
                # Verificar se entregador já existe pelo CPF
                entregador_existente = EntregadoresService.buscar_entregador_por_cpf(cpf_limpo)
                
                if entregador_existente:
                    # Entregador já existe, apenas atualizar registros PIX pendentes
                    id_ent = entregador_existente['id_da_pessoa_entregadora']
                    EntregadoresService.atualizar_pix_pendentes(id_ent, cpf_limpo, chave_pix)
                    
                    flash(
                        f'Entregador já cadastrado! Registros PIX pendentes foram atualizados.',
                        'entregador_success'
                    )
                else:
                    # Criar novo entregador
                    EntregadoresService.criar_entregador(dados)
                    flash(
                        get_flash_message('entregador', 'criado'),
                        'entregador_success'
                    )
                
                # Redirecionar de volta para a lista de PIX
                return redirect('/admin/bancario')
            except Exception as e:
                flash(str(e), 'entregador_error')
        
        # Pré-preencher dados do PIX usando um objeto simples
        class EntregadorPreenchido:
            def __init__(self, recebedor, cpf, tipo_chave_pix, chave_pix):
                self.recebedor = recebedor
                self.cpf = cpf
                self.tipo_de_chave_pix = tipo_chave_pix
                self.chave_pix = chave_pix
        
        entregador_preenchido = EntregadorPreenchido(nome, cpf, tipo_chave_form, chave_pix)
        
        return render_template(
            TEMPLATES_ENTREGADORES['form'],
            entregador=entregador_preenchido,
            is_novo_pix=True
        )
    
    @app.route('/entregador/editar/<string:id_entregador>', methods=['GET', 'POST'])
    @adm_or_master_required
    def editar_entregador(id_entregador):
        """Edita um entregador existente"""
        if request.method == 'POST':
            dados = extract_form_data(CAMPOS_FORM_ENTREGADOR_EDICAO)
            
            # Aplica valores padrão
            dados['emissor'] = dados.get('emissor') or DEFAULT_EMISSOR
            dados['status'] = dados.get('status') or DEFAULT_STATUS
            
            # Valida campos obrigatórios
            is_valid, missing = validate_required_fields(
                dados, CAMPOS_OBRIGATORIOS_ENTREGADOR_EDICAO
            )
            
            if not is_valid:
                flash(
                    get_flash_message('entregador', 'campos_obrigatorios_edicao'),
                    'entregador_error'
                )
                return redirect(url_for('editar_entregador', id_entregador=id_entregador))
            
            try:
                EntregadoresService.atualizar_entregador(id_entregador, dados)
                flash(
                    get_flash_message('entregador', 'atualizado'),
                    'entregador_success'
                )
                return redirect(url_for('entregadores'))
            except Exception as e:
                flash(str(e), 'entregador_error')
        else:
            try:
                entregador = EntregadoresService.buscar_entregador_por_id(id_entregador)
                if entregador:
                    return render_template(
                        TEMPLATES_ENTREGADORES['form'],
                        entregador=entregador
                    )
                else:
                    flash(
                        get_flash_message('entregador', 'nao_encontrado'),
                        'entregador_error'
                    )
                    return redirect(url_for('entregadores'))
            except Exception as e:
                flash(
                    f'Erro ao carregar dados do entregador: {str(e)}',
                    'entregador_error'
                )
                return redirect(url_for('entregadores'))
    
    @app.route('/entregador/excluir/<string:id_entregador>')
    @adm_or_master_required
    def excluir_entregador(id_entregador):
        """Exclui um entregador"""
        try:
            EntregadoresService.excluir_entregador(id_entregador)
            flash(
                get_flash_message('entregador', 'excluido'),
                'entregador_success'
            )
        except Exception as e:
            flash(str(e), 'entregador_error')
        
        return redirect(url_for('entregadores'))
