"""
Constantes e mapeamentos globais para o sistema
"""

# ===== PAGINAÇÃO =====
PAGINATION_PER_PAGE_ENTREGADORES = 20
PAGINATION_PER_PAGE_UPLOAD = 30

# ===== TEMPLATES =====
TEMPLATES_ENTREGADORES = {
    'index': 'entregadores/entregadores_index.html',
    'detalhes': 'entregadores/detalhes_entregador.html',
    'form': 'entregadores/form_entregador.html'
}

TEMPLATES_UPLOAD = {
    'upload_csv': 'upload/upload_csv.html',
    'resultado': 'upload/resultado_detalhado.html',
    'detalhes_completos': 'upload/detalhes_completos_entregador.html',
    'upload_entregadores': 'upload/upload_entregadores.html',
    'lotes': 'upload/lotes.html'
}

TEMPLATES_PIX = {
    'form_public': 'pix/form_bancario_public.html',
    'admin_lista': 'pix/pix_admin_lista.html',
    'admin_logs': 'pix/pix_admin_logs.html',
    'admin_aprovacao': 'pix/pix_admin_aprovacao.html'
}

TEMPLATES_ADIANTAMENTO = {
    'lista': 'adiantamento/adiantamento_lista.html',
    'form_public': 'adiantamento/adiantamento_form_public.html',
    'fechado': 'adiantamento/adiantamento_fechado.html',
    'bloqueado': 'adiantamento/adiantamento_bloqueado.html',
    'sucesso': 'adiantamento/adiantamento_sucesso.html'
}

TEMPLATES_ADMIN = {
    'form_config': 'admin/form_config.html',
    'form_config_modal': 'admin/form_config_modal.html',
    'form_logs': 'admin/form_logs.html'
}

# ===== MENSAGENS FLASH =====
MESSAGES = {
    'entregador': {
        'criado': 'Entregador cadastrado com sucesso!',
        'atualizado': 'Entregador atualizado com sucesso!',
        'excluido': 'Entregador excluído com sucesso!',
        'nao_encontrado': 'Entregador não encontrado.',
        'erro_carregar': 'Erro ao carregar entregadores: {error}',
        'erro_detalhes': 'Erro ao carregar detalhes: {error}',
        'campos_obrigatorios': 'Todos os campos obrigatórios devem ser preenchidos!',
        'campos_obrigatorios_edicao': 'Preencha os campos obrigatórios (Nome e Chave Pix)!'
    },
    'upload': {
        'nenhum_arquivo': 'Nenhum arquivo selecionado',
        'nenhum_csv': 'Nenhum arquivo CSV válido.',
        'erro_processar': 'Erro ao processar arquivos: {error}',
        'erro_carregar': 'Erro ao carregar resultados: {error}',
        'nenhum_resultado': 'Nenhum resultado encontrado. Faça upload de um CSV.',
        'relatorio_gerado': 'Relatório gerado com dados reais do processamento',
        'relatorio_exemplo': 'Relatório gerado com dados de exemplo - faça upload de CSVs para dados reais',
        'erro_relatorio': 'Erro ao gerar relatório: {error}',
        'arquivo_invalido': 'Selecione um arquivo .xlsx válido!',
        'erro_ler': 'Erro ao ler planilha: {error}',
        'carregados': '{count} entregadores carregados com sucesso!',
        'token_invalido': 'Token de importação inválido.',
        'dados_nao_encontrados': 'Dados temporários não encontrados. Faça o upload novamente.',
        'importados': '{count} entregadores importados com sucesso!',
        'erro_gravar': 'Erro ao gravar dados: {error}'
    },
    'pix': {
        'chave_duplicada': 'Chave já cadastrada por outra pessoa',
        'cpf_nao_encontrado': 'CPF não encontrado'
    },
    'adiantamento': {
        'form_aberto': 'Formulário ABERTO com sucesso!',
        'form_fechado': 'Formulário FECHADO com sucesso!',
        'agendamento_atualizado': 'Agendamentos atualizados com sucesso!',
        'config_salva': 'Configuração automática salva com sucesso!',
        'data_invalida': 'Data inválida. Use o formato AAAA-MM-DD.',
        'nenhuma_solicitacao': 'Nenhuma solicitação de adiantamento em {date}.',
        'consolidado_vazio': 'Consolidado do iFood está vazio.',
        'nenhum_registro': 'Nenhum registro no consolidado bate com as solicitações de adiantamento desse dia.',
        'diario_gerado': 'Arquivo diário gerado com sucesso: {filename}'
    }
}

# ===== CAMPOS OBRIGATÓRIOS =====
CAMPOS_OBRIGATORIOS_ENTREGADOR = ['id_da_pessoa_entregadora', 'recebedor', 'chave_pix']
CAMPOS_OBRIGATORIOS_ENTREGADOR_EDICAO = ['recebedor', 'chave_pix']

# ===== STATUS =====
STATUS_PIX = {
    'PENDENTE': 'pendente',
    'APROVADO': 'aprovado',
    'REJEITADO': 'rejeitado'
}

STATUS_ENTREGADOR = {
    'ATIVO': 'Ativo',
    'INATIVO': 'Inativo'
}

# ===== TIPOS DE CHAVE PIX =====
TIPOS_CHAVE_PIX = {
    'AUTO': 'AUTO',
    'CPF': 'CPF',
    'EMAIL': 'EMAIL',
    'TELEFONE': 'TELEFONE',
    'ALEATORIA': 'ALEATORIA'
}

# ===== AÇÕES DE LOG =====
ACOES_LOG = {
    'ABRIR_MANUAL': 'ABRIR_MANUAL',
    'FECHAR_MANUAL': 'FECHAR_MANUAL',
    'AGENDAMENTO_ALTERADO': 'AGENDAMENTO_ALTERADO',
    'ABRIR_AUTOMATICO': 'ABRIR_AUTOMATICO',
    'FECHAR_AUTOMATICO': 'FECHAR_AUTOMATICO'
}

# ===== VALORES PADRÃO =====
DEFAULT_EMISSOR = 'Proprio'
DEFAULT_STATUS = 'Ativo'
DEFAULT_TIPO_CHAVE = 'AUTO'

# ===== ARQUIVOS =====
ARQUIVO_ULTIMO_RESULTADO = 'ultimo_resultado.json'
ARQUIVO_ULTIMO_CONSOLIDADO = 'ultimo_consolidado.csv'
ARQUIVO_CONSOLIDADO_DIARIO = 'consolidado_diario.csv'
ARQUIVO_SOLICITACOES = 'solicitacoes.json'

# ===== FORMATOS DE DATA =====
FORMATO_DATA_SQL = "%Y-%m-%d %H:%M:%S"
FORMATO_DATA_ISO = "%Y-%m-%d"
FORMATO_DATA_DATETIME_LOCAL = "%Y-%m-%dT%H:%M"
FORMATO_DATA_ARQUIVO = "%Y%m%d_%H%M%S"
FORMATO_DATA_DIARIO = "%Y%m%d"

# ===== MAPEAMENTO DE PRAÇAS E SUBPRAÇAS =====
PRACAS = [
    'Rio Barra',
    'Rio Zona Sul',
    'Rio Campo Grande & Santa Cruz',
    'Rio Madureira'
]

SUBPRACAS_POR_PRACA = {
    'Rio Barra': ['Barra Centro', 'Recreio', 'Taquara', 'Jacarepaguá', 'Freguesia'],
    'Rio Zona Sul': ['Centro ZS', 'Ipanema', 'Copacabana', 'Botafogo', 'Vila Isabel', 'São Cristóvão'],
    'Rio Campo Grande & Santa Cruz': ['Centro CG', 'Monteiro', 'Santa Cruz'],
    'Rio Madureira': ['Penha', 'Irajá', 'Rocha Miranda', 'Realengo']
}

# Mapeamento para normalização de nomes de praças (case-insensitive)
MAPA_PRACAS_NORMALIZACAO = {
    'rio barra': 'Rio Barra',
    'barra': 'Rio Barra',
    'rio zona sul': 'Rio Zona Sul',
    'zona sul': 'Rio Zona Sul',
    'rio campo grande': 'Rio Campo Grande & Santa Cruz',
    'rio campo grande & santa cruz': 'Rio Campo Grande & Santa Cruz',
    'campo grande': 'Rio Campo Grande & Santa Cruz',
    'rio madureira': 'Rio Madureira',
    'madureira': 'Rio Madureira'
}

def normalizar_praca(praca):
    """Normaliza nome de praça para formato padrão"""
    if not praca:
        return ''
    return MAPA_PRACAS_NORMALIZACAO.get(praca.lower().strip(), praca)

def get_subpracas(praca):
    """Retorna lista de subpraças para uma praça"""
    return SUBPRACAS_POR_PRACA.get(praca, [])

