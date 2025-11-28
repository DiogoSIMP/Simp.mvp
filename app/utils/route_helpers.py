"""
Helpers para rotas - funções auxiliares reutilizáveis
"""

from flask import request, jsonify
from functools import wraps
from app.utils.constants import MESSAGES


def paginate_items(items, page, per_page):
    """
    Pagina uma lista de itens
    
    Args:
        items: Lista de itens
        page: Número da página (começa em 1)
        per_page: Itens por página
    
    Returns:
        tuple: (items_paginados, total_pages)
    """
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    items_paginados = items[start:end]
    total_pages = (total + per_page - 1) // per_page
    
    return items_paginados, total_pages


def get_page_from_request(default=1):
    """Obtém o número da página da query string"""
    return request.args.get('page', default, type=int)


def is_ajax_request():
    """Verifica se a requisição é AJAX"""
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def json_response(success=True, message="", data=None, status_code=200):
    """
    Cria uma resposta JSON padronizada
    
    Args:
        success: Se a operação foi bem-sucedida
        message: Mensagem de resposta
        data: Dados adicionais
        status_code: Código HTTP
    
    Returns:
        Response JSON
    """
    response = {
        'success': success,
        'message': message
    }
    if data:
        response['data'] = data
    
    return jsonify(response), status_code


def extract_form_data(fields, strip=True):
    """
    Extrai dados do formulário
    
    Args:
        fields: Lista de nomes de campos
        strip: Se deve remover espaços em branco
    
    Returns:
        dict: Dados do formulário
    """
    data = {}
    for field in fields:
        value = request.form.get(field, '').strip() if strip else request.form.get(field, '')
        data[field] = value
    return data


def validate_required_fields(data, required_fields):
    """
    Valida campos obrigatórios
    
    Args:
        data: Dicionário com dados
        required_fields: Lista de campos obrigatórios
    
    Returns:
        tuple: (is_valid, missing_fields)
    """
    missing = [field for field in required_fields if not data.get(field)]
    return len(missing) == 0, missing


def normalize_cpf(cpf):
    """
    Remove caracteres não numéricos do CPF
    
    Args:
        cpf: CPF com ou sem formatação
    
    Returns:
        str: CPF apenas com números
    """
    if not cpf:
        return ''
    import re
    return re.sub(r'\D', '', str(cpf))


def format_datetime_local_to_sql(datetime_local):
    """
    Converte datetime-local para formato SQL
    
    Args:
        datetime_local: String no formato YYYY-MM-DDTHH:MM
    
    Returns:
        str: String no formato YYYY-MM-DD HH:MM:SS
    """
    if not datetime_local:
        return None
    return datetime_local.replace("T", " ") + ":00"


def get_flash_message(category, key, **kwargs):
    """
    Obtém mensagem flash formatada
    
    Args:
        category: Categoria (entregador, upload, etc)
        key: Chave da mensagem
        **kwargs: Valores para formatação
    
    Returns:
        str: Mensagem formatada
    """
    message = MESSAGES.get(category, {}).get(key, '')
    if kwargs:
        message = message.format(**kwargs)
    return message

