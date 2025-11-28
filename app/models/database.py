import sqlite3
import os

# ====================================================
# 🗂️ CONFIGURAÇÃO DO BANCO
# ====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "Drives_abjp.db")

# ====================================================
# 🔌 CONEXÃO
# ====================================================
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ====================================================
# 🧱 CRIAÇÃO AUTOMÁTICA DE TABELAS
# ====================================================
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # === ENTREGADORES ===
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS entregadores (
        id_da_pessoa_entregadora TEXT PRIMARY KEY,
        recebedor TEXT NOT NULL,
        email TEXT,
        cpf TEXT,
        cnpj TEXT,
        praca TEXT,
        subpraca TEXT,
        emissor TEXT,
        status TEXT
    );
    """)
    
    # Migração: adicionar coluna praca se não existir
    try:
        cursor.execute("ALTER TABLE entregadores ADD COLUMN praca TEXT")
    except sqlite3.OperationalError:
        # Coluna já existe, ignora o erro
        pass
    
    # Migração: adicionar coluna email se não existir (para bancos antigos)
    try:
        cursor.execute("ALTER TABLE entregadores ADD COLUMN email TEXT")
    except sqlite3.OperationalError:
        # Coluna já existe, ignora o erro
        pass

    # === HISTÓRICO PIX ===
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historico_pix (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_da_pessoa_entregadora TEXT,
        cpf TEXT,
        chave_pix TEXT,
        tipo_de_chave_pix TEXT,
        data_registro TEXT DEFAULT CURRENT_TIMESTAMP,
        status TEXT,
        FOREIGN KEY (id_da_pessoa_entregadora)
            REFERENCES entregadores (id_da_pessoa_entregadora)
    );
    """)
    
    # Migração: adicionar colunas cpf e status se não existirem (para bancos antigos)
    try:
        cursor.execute("ALTER TABLE historico_pix ADD COLUMN cpf TEXT")
    except sqlite3.OperationalError:
        # Coluna já existe, ignora o erro
        pass
    
    try:
        cursor.execute("ALTER TABLE historico_pix ADD COLUMN status TEXT")
    except sqlite3.OperationalError:
        # Coluna já existe, ignora o erro
        pass
    
    try:
        cursor.execute("ALTER TABLE historico_pix ADD COLUMN nome TEXT")
    except sqlite3.OperationalError:
        # Coluna já existe, ignora o erro
        pass
    
    try:
        cursor.execute("ALTER TABLE historico_pix ADD COLUMN avaliacao INTEGER")
    except sqlite3.OperationalError:
        # Coluna já existe, ignora o erro
        pass
    
    try:
        cursor.execute("ALTER TABLE historico_pix ADD COLUMN praca TEXT")
    except sqlite3.OperationalError:
        # Coluna já existe, ignora o erro
        pass
    
    try:
        cursor.execute("ALTER TABLE historico_pix ADD COLUMN cnpj TEXT")
    except sqlite3.OperationalError:
        # Coluna já existe, ignora o erro
        pass

    # === SOLICITAÇÕES DE ADIANTAMENTO ===
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS solicitacoes_adiantamento (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        nome TEXT,
        cpf TEXT,
        praca TEXT,
        valor_informado REAL,
        concorda TEXT,
        data_envio TEXT
    );
    """)

    # === ⚠️ FORM CONFIG (FUNDAMENTAL) ===
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS form_config (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        is_open INTEGER DEFAULT 0,
        scheduled_open TEXT,
        scheduled_close TEXT,
        auto_mode INTEGER DEFAULT 0,
        auto_open_time TEXT,
        auto_close_time TEXT,
        days_enabled TEXT
    );
    """)

    # Inserir registro único caso não exista
    cursor.execute("SELECT COUNT(*) FROM form_config")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO form_config (id, is_open, auto_mode)
            VALUES (1, 0, 0)
        """)

    # === ⚠️ FORM LOGS ===
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS form_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        acao TEXT NOT NULL,
        detalhe TEXT,
        data_hora TEXT NOT NULL
    );
    """)

    # === 👥 USUÁRIOS INTERNOS ===
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        senha_hash TEXT NOT NULL,
        nome_completo TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('Master', 'Adm', 'Operacional')),
        ativo INTEGER DEFAULT 1,
        data_criacao TEXT DEFAULT CURRENT_TIMESTAMP,
        ultimo_acesso TEXT,
        foto_perfil TEXT
    );
    """)
    
    # Migração: adicionar coluna foto_perfil se não existir
    try:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN foto_perfil TEXT")
    except sqlite3.OperationalError:
        # Coluna já existe, ignora o erro
        pass

    conn.commit()
    conn.close()
    print("✅ Banco inicializado com todas as tabelas (Drives_abjp.db).")


# ====================================================
# UTILITÁRIOS
# ====================================================
def formatar_nome(nome: str) -> str:
    if not nome:
        return ""
    return " ".join([p.capitalize() for p in nome.split()])


def limpar_cnpj(valor: str) -> str:
    import re
    if not valor:
        return ""
    valor = re.sub(r'\D', '', str(valor))
    return valor if len(valor) == 14 else ""


# ====================================================
# EXECUÇÃO DIRETA
# ====================================================
if __name__ == "__main__":
    init_db()
