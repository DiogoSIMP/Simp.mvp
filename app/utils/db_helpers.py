"""
Helpers centralizados para operações de banco de dados
Reduz duplicação de código e padroniza acesso ao banco
"""
from contextlib import contextmanager
from app.models.database import get_db_connection, get_db_cursor, get_db_placeholder, is_postgresql_connection


@contextmanager
def db_connection():
    """
    Context manager para conexões de banco de dados
    Garante fechamento automático mesmo em caso de erro
    
    Uso:
        with db_connection() as conn:
            cursor = get_db_cursor(conn)
            cursor.execute(...)
    """
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def db_cursor():
    """
    Context manager para cursor de banco de dados
    Inclui conexão e cursor, com commit/rollback automático
    
    Uso:
        with db_cursor() as cursor:
            cursor.execute(...)
            results = cursor.fetchall()
    """
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_query(query_template, params=None, fetch_one=False, fetch_all=False):
    """
    Executa query com placeholders dinâmicos e retorna resultados
    
    Args:
        query_template: Query SQL com {placeholder} ou %s/?
        params: Tupla ou lista de parâmetros
        fetch_one: Se True, retorna apenas um resultado
        fetch_all: Se True, retorna todos os resultados
    
    Returns:
        Resultado da query ou None
    """
    with db_cursor() as cursor:
        conn = cursor.connection if hasattr(cursor, 'connection') else None
        if conn:
            placeholder = get_db_placeholder(conn)
            # Substituir {placeholder} pelo placeholder correto
            query = query_template.replace('{placeholder}', placeholder)
        else:
            query = query_template
        
        cursor.execute(query, params or ())
        
        if fetch_one:
            return cursor.fetchone()
        elif fetch_all:
            return cursor.fetchall()
        else:
            return cursor.rowcount


def execute_query_dict(query_template, params=None, fetch_one=False, fetch_all=False):
    """
    Executa query e retorna resultados como dicionários
    
    Args:
        query_template: Query SQL com {placeholder}
        params: Tupla ou lista de parâmetros
        fetch_one: Se True, retorna apenas um resultado (dict)
        fetch_all: Se True, retorna todos os resultados (lista de dicts)
    
    Returns:
        Dict ou lista de dicts
    """
    with db_cursor() as cursor:
        conn = cursor.connection if hasattr(cursor, 'connection') else None
        if conn:
            placeholder = get_db_placeholder(conn)
            query = query_template.replace('{placeholder}', placeholder)
        else:
            query = query_template
        
        cursor.execute(query, params or ())
        
        if fetch_one:
            row = cursor.fetchone()
            return dict(row) if row else None
        elif fetch_all:
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        else:
            return cursor.rowcount


def row_to_dict(row):
    """
    Converte row (tuple, dict, Row) para dicionário
    Helper centralizado para conversão de resultados
    """
    if row is None:
        return None
    if isinstance(row, dict):
        return dict(row)
    if hasattr(row, 'keys'):
        return dict(row)
    return None

