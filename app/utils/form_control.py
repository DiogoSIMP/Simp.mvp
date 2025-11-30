from datetime import datetime
from app.models.database import get_db_connection, is_postgresql_connection


# =====================================================
# FUNÇÃO AUXILIAR PARA MAPEAR RESULTADOS COMO DICIONÁRIO
# =====================================================
def dict_row(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def get_form_config():
    """Retorna o único registro da tabela form_config."""
    conn = get_db_connection()
    is_postgresql = is_postgresql_connection(conn)
    
    if is_postgresql:
        from psycopg2.extras import RealDictCursor
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        conn.row_factory = dict_row
        cursor = conn.cursor()
    
    placeholder = "%s" if is_postgresql else "?"
    cursor.execute(f"SELECT * FROM form_config WHERE id = {placeholder}", (1,))
    row = cursor.fetchone()
    conn.close()
    return row


# =====================================================
def form_is_open():
    cfg = get_form_config()
    if not cfg:
        return False

    # Apenas isso importa
    return bool(cfg["is_open"])

# =====================================================
# ALTERAÇÕES SIMPLES DE ESTADO (SEM LOG)
# =====================================================
def abrir_formulario():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE form_config SET is_open = 1 WHERE id = 1")
    conn.commit()
    conn.close()


def fechar_formulario():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE form_config SET is_open = 0 WHERE id = 1")
    conn.commit()
    conn.close()


# =====================================================
# AGENDAMENTOS
# =====================================================
def agendar_abertura(data_hora):
    conn = get_db_connection()
    cursor = conn.cursor()
    is_postgresql = is_postgresql_connection(conn)
    placeholder = "%s" if is_postgresql else "?"
    cursor.execute(f"""
        UPDATE form_config
        SET scheduled_open = {placeholder}
        WHERE id = 1
    """, (data_hora,))
    conn.commit()
    conn.close()


def agendar_fechamento(data_hora):
    conn = get_db_connection()
    cursor = conn.cursor()
    is_postgresql = is_postgresql_connection(conn)
    placeholder = "%s" if is_postgresql else "?"
    cursor.execute(f"""
        UPDATE form_config
        SET scheduled_close = {placeholder}
        WHERE id = 1
    """, (data_hora,))
    conn.commit()
    conn.close()
