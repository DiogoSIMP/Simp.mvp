import os
import json
import sqlite3  # Sempre importar para fallback
from config import Config

# ====================================================
# 🗂️ CONFIGURAÇÃO DO BANCO
# ====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "Drives_abjp.db")

# Detectar qual banco usar
USE_POSTGRESQL = Config.USE_POSTGRESQL

if USE_POSTGRESQL:
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        POSTGRESQL_AVAILABLE = True
    except ImportError:
        POSTGRESQL_AVAILABLE = False
        print("⚠️ psycopg2 não instalado. Usando SQLite como fallback.")
        USE_POSTGRESQL = False
else:
    POSTGRESQL_AVAILABLE = False

# ====================================================
# 🔌 CONEXÃO
# ====================================================
def is_postgresql_connection(conn):
    """Verifica se a conexão é PostgreSQL"""
    # Método mais seguro: verificar pela representação string do tipo
    # sem acessar atributos que possam causar erros
    try:
        type_str = str(type(conn))
        # PostgreSQL connections contêm 'psycopg2' no nome do tipo
        if 'psycopg2' in type_str:
            return True
        # SQLite connections contêm 'sqlite3' no nome do tipo
        if 'sqlite3' in type_str:
            return False
    except Exception:
        pass
    
    # Fallback: usar a configuração global
    return USE_POSTGRESQL and POSTGRESQL_AVAILABLE

def get_db_connection():
    """Retorna conexão com o banco de dados (PostgreSQL ou SQLite)"""
    if USE_POSTGRESQL and POSTGRESQL_AVAILABLE:
        try:
            conn = psycopg2.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                database=Config.DB_NAME,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD
            )
            return conn
        except Exception as e:
            print(f"⚠️ Erro ao conectar ao PostgreSQL: {e}")
            print("⚠️ Tentando usar SQLite como fallback...")
            # Fallback para SQLite
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            return conn
    else:
        # SQLite
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def get_db_cursor(conn):
    """
    Retorna cursor apropriado para o tipo de banco (PostgreSQL ou SQLite)
    Helper centralizado para evitar duplicação de código
    """
    is_pg = is_postgresql_connection(conn)
    if is_pg:
        from psycopg2.extras import RealDictCursor
        return conn.cursor(cursor_factory=RealDictCursor)
    else:
        # SQLite já tem row_factory configurado na conexão
        return conn.cursor()


def get_db_placeholder(conn):
    """
    Retorna placeholder correto baseado no tipo de banco
    Helper centralizado para evitar duplicação de código
    """
    is_pg = is_postgresql_connection(conn)
    return "%s" if is_pg else "?"

# ====================================================
# 🧱 CRIAÇÃO AUTOMÁTICA DE TABELAS
# ====================================================
def init_db():
    """Inicializa o banco de dados criando todas as tabelas necessárias"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar se é PostgreSQL pela conexão
    is_postgresql = is_postgresql_connection(conn)
    
    try:
        # === ENTREGADORES ===
        if is_postgresql:
            # Verificar se a tabela existe e tem as colunas corretas
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'entregadores'
            """)
            existing_columns = [row[0] for row in cursor.fetchall()]
            
            if not existing_columns:
                # Tabela não existe, criar
                cursor.execute("""
                CREATE TABLE entregadores (
                    id_da_pessoa_entregadora VARCHAR(255) PRIMARY KEY,
                    recebedor VARCHAR(255) NOT NULL,
                    email VARCHAR(255),
                    cpf VARCHAR(14),
                    cnpj VARCHAR(18),
                    praca VARCHAR(255),
                    subpraca VARCHAR(255),
                    emissor VARCHAR(255),
                    status VARCHAR(50)
                );
                """)
            else:
                # Tabela existe, verificar e adicionar colunas faltantes
                required_columns = {
                    'cpf': 'VARCHAR(14)',
                    'cnpj': 'VARCHAR(18)',
                    'email': 'VARCHAR(255)',
                    'praca': 'VARCHAR(255)',
                    'subpraca': 'VARCHAR(255)',
                    'emissor': 'VARCHAR(255)',
                    'status': 'VARCHAR(50)'
                }
                
                for col_name, col_def in required_columns.items():
                    if col_name not in existing_columns:
                        try:
                            cursor.execute(f"ALTER TABLE entregadores ADD COLUMN {col_name} {col_def}")
                        except Exception as e:
                            print(f"⚠️ Aviso ao adicionar coluna {col_name}: {e}")
        else:
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
        
        # === HISTÓRICO PIX ===
        if is_postgresql:
            # Verificar se a tabela existe e tem as colunas corretas
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'historico_pix'
            """)
            existing_columns = [row[0] for row in cursor.fetchall()]
            
            if not existing_columns:
                # Tabela não existe, criar
                cursor.execute("""
                CREATE TABLE historico_pix (
                    id SERIAL PRIMARY KEY,
                    id_da_pessoa_entregadora VARCHAR(255),
                    cpf VARCHAR(14),
                    chave_pix VARCHAR(255),
                    tipo_de_chave_pix VARCHAR(50),
                    data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50),
                    nome VARCHAR(255),
                    avaliacao INTEGER,
                    praca VARCHAR(255),
                    cnpj VARCHAR(18),
                    email VARCHAR(255),
                    FOREIGN KEY (id_da_pessoa_entregadora)
                        REFERENCES entregadores (id_da_pessoa_entregadora)
                );
                """)
            else:
                # Tabela existe, verificar e adicionar colunas faltantes
                required_columns = {
                    'id_da_pessoa_entregadora': 'VARCHAR(255)',
                    'cpf': 'VARCHAR(14)',
                    'chave_pix': 'VARCHAR(255)',
                    'tipo_de_chave_pix': 'VARCHAR(50)',
                    'data_registro': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                    'status': 'VARCHAR(50)',
                    'nome': 'VARCHAR(255)',
                    'avaliacao': 'INTEGER',
                    'praca': 'VARCHAR(255)',
                    'cnpj': 'VARCHAR(18)',
                    'email': 'VARCHAR(255)'
                }
                
                for col_name, col_def in required_columns.items():
                    if col_name not in existing_columns:
                        try:
                            cursor.execute(f"ALTER TABLE historico_pix ADD COLUMN {col_name} {col_def}")
                        except Exception as e:
                            print(f"⚠️ Aviso ao adicionar coluna {col_name}: {e}")
        else:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico_pix (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_da_pessoa_entregadora TEXT,
                cpf TEXT,
                chave_pix TEXT,
                tipo_de_chave_pix TEXT,
                data_registro TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT,
                nome TEXT,
                avaliacao INTEGER,
                praca TEXT,
                cnpj TEXT,
                email TEXT,
                FOREIGN KEY (id_da_pessoa_entregadora)
                    REFERENCES entregadores (id_da_pessoa_entregadora)
            );
            """)
        
        # === SOLICITAÇÕES DE ADIANTAMENTO ===
        if is_postgresql:
            # Verificar se a tabela existe e tem as colunas corretas
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'solicitacoes_adiantamento'
            """)
            existing_columns = [row[0] for row in cursor.fetchall()]
            
            if not existing_columns:
                # Tabela não existe, criar
                cursor.execute("""
                CREATE TABLE solicitacoes_adiantamento (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255),
                    nome VARCHAR(255),
                    cpf VARCHAR(14),
                    praca VARCHAR(255),
                    valor_informado DECIMAL(10, 2),
                    concorda TEXT,
                    data_envio TIMESTAMP,
                    cpf_bate INTEGER DEFAULT 0,
                    dados_json JSONB
                );
                """)
            else:
                # Tabela existe, verificar e adicionar colunas faltantes
                required_columns = {
                    'email': 'VARCHAR(255)',
                    'nome': 'VARCHAR(255)',
                    'cpf': 'VARCHAR(14)',
                    'praca': 'VARCHAR(255)',
                    'valor_informado': 'DECIMAL(10, 2)',
                    'concorda': 'TEXT',
                    'data_envio': 'TIMESTAMP',
                    'cpf_bate': 'INTEGER DEFAULT 0',
                    'dados_json': 'JSONB'
                }
                
                for col_name, col_def in required_columns.items():
                    if col_name not in existing_columns:
                        try:
                            cursor.execute(f"ALTER TABLE solicitacoes_adiantamento ADD COLUMN {col_name} {col_def}")
                            print(f"✅ Coluna {col_name} adicionada à tabela solicitacoes_adiantamento")
                        except Exception as e:
                            print(f"⚠️ Aviso ao adicionar coluna {col_name}: {e}")
        else:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS solicitacoes_adiantamento (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                nome TEXT,
                cpf TEXT,
                praca TEXT,
                valor_informado REAL,
                concorda TEXT,
                data_envio TEXT,
                cpf_bate INTEGER DEFAULT 0,
                dados_json TEXT
            );
            """)

        # === ⚠️ FORM CONFIG (FUNDAMENTAL) ===
        if is_postgresql:
            # Verificar se a tabela existe e tem as colunas corretas
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'form_config'
            """)
            existing_columns = [row[0] for row in cursor.fetchall()]
            
            if not existing_columns:
                # Tabela não existe, criar
                cursor.execute("""
                CREATE TABLE form_config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    is_open INTEGER DEFAULT 0,
                    scheduled_open TIMESTAMP,
                    scheduled_close TIMESTAMP,
                    auto_mode INTEGER DEFAULT 0,
                    auto_open_time TIME,
                    auto_close_time TIME,
                    days_enabled VARCHAR(50)
                );
                """)
            else:
                # Tabela existe, verificar e adicionar colunas faltantes
                required_columns = {
                    'is_open': 'INTEGER DEFAULT 0',
                    'scheduled_open': 'TIMESTAMP',
                    'scheduled_close': 'TIMESTAMP',
                    'auto_mode': 'INTEGER DEFAULT 0',
                    'auto_open_time': 'TIME',
                    'auto_close_time': 'TIME',
                    'days_enabled': 'VARCHAR(50)'
                }
                
                for col_name, col_def in required_columns.items():
                    if col_name not in existing_columns:
                        try:
                            cursor.execute(f"ALTER TABLE form_config ADD COLUMN {col_name} {col_def}")
                        except Exception as e:
                            print(f"⚠️ Aviso ao adicionar coluna {col_name}: {e}")
        else:
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
        try:
            cursor.execute("SELECT COUNT(*) FROM form_config")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO form_config (id, is_open, auto_mode)
                    VALUES (1, 0, 0)
                """)
        except Exception as e:
            # Se falhar, tentar inserir apenas o id
            try:
                cursor.execute("SELECT COUNT(*) FROM form_config WHERE id = 1")
                if cursor.fetchone()[0] == 0:
                    if is_postgresql:
                        cursor.execute("INSERT INTO form_config (id) VALUES (1) ON CONFLICT (id) DO NOTHING")
                    else:
                        cursor.execute("INSERT OR IGNORE INTO form_config (id) VALUES (1)")
            except Exception as insert_error:
                print(f"⚠️ Aviso ao inserir registro padrão em form_config: {insert_error}")

        # === ⚠️ FORM LOGS ===
        if is_postgresql:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS form_logs (
                id SERIAL PRIMARY KEY,
                acao VARCHAR(255) NOT NULL,
                detalhe TEXT,
                data_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """)
        else:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS form_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                acao TEXT NOT NULL,
                detalhe TEXT,
                data_hora TEXT NOT NULL
            );
            """)

        # === 👥 USUÁRIOS INTERNOS ===
        if is_postgresql:
            # Verificar se a tabela existe e tem as colunas corretas
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'usuarios'
            """)
            existing_columns = [row[0] for row in cursor.fetchall()]
            
            if not existing_columns:
                # Tabela não existe, criar
                cursor.execute("""
                CREATE TABLE usuarios (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    senha_hash VARCHAR(255) NOT NULL,
                    nome_completo VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL CHECK(role IN ('Master', 'Adm', 'Lider', 'Operacional')),
                    ativo INTEGER DEFAULT 1,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ultimo_acesso TIMESTAMP,
                    foto_perfil VARCHAR(500)
                );
                """)
            else:
                # Tabela existe, verificar e adicionar colunas faltantes
                # Para colunas NOT NULL, adicionamos como nullable primeiro para evitar erros
                required_columns = {
                    'username': 'VARCHAR(255)',
                    'email': 'VARCHAR(255)',
                    'senha_hash': 'VARCHAR(255)',
                    'nome_completo': 'VARCHAR(255)',
                    'role': 'VARCHAR(50)',
                    'ativo': 'INTEGER DEFAULT 1',
                    'data_criacao': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                    'ultimo_acesso': 'TIMESTAMP',
                    'foto_perfil': 'VARCHAR(500)'
                }
                
                for col_name, col_def in required_columns.items():
                    if col_name not in existing_columns:
                        try:
                            cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {col_name} {col_def}")
                        except Exception as e:
                            print(f"⚠️ Aviso ao adicionar coluna {col_name}: {e}")
                
                # Migração: Se existe coluna 'nome' NOT NULL, torná-la nullable ou removê-la
                # A coluna 'nome' foi substituída por 'nome_completo'
                if 'nome' in existing_columns:
                    try:
                        # Verificar se a coluna é NOT NULL
                        cursor.execute("""
                            SELECT is_nullable 
                            FROM information_schema.columns 
                            WHERE table_name = 'usuarios' AND column_name = 'nome'
                        """)
                        nome_nullable = cursor.fetchone()
                        if nome_nullable and nome_nullable[0] == 'NO':
                            # Preencher valores NULL com nome_completo ANTES de tornar nullable
                            cursor.execute("""
                                UPDATE usuarios 
                                SET nome = COALESCE(nome, nome_completo) 
                                WHERE nome IS NULL AND nome_completo IS NOT NULL
                            """)
                            print("✅ Valores NULL da coluna 'nome' preenchidos com 'nome_completo'")
                            # Tornar nullable
                            cursor.execute("ALTER TABLE usuarios ALTER COLUMN nome DROP NOT NULL")
                            print("✅ Coluna 'nome' tornada nullable (migração)")
                            conn.commit()
                    except Exception as e:
                        print(f"⚠️ Aviso ao migrar coluna 'nome': {e}")
                        conn.rollback()
                
                # Migração: Se existe coluna 'senha' NOT NULL, torná-la nullable
                # A coluna 'senha' foi substituída por 'senha_hash'
                if 'senha' in existing_columns:
                    try:
                        # Verificar se a coluna é NOT NULL
                        cursor.execute("""
                            SELECT is_nullable 
                            FROM information_schema.columns 
                            WHERE table_name = 'usuarios' AND column_name = 'senha'
                        """)
                        senha_nullable = cursor.fetchone()
                        if senha_nullable and senha_nullable[0] == 'NO':
                            # Tornar nullable (não precisamos preencher, pois senha_hash já tem o valor)
                            cursor.execute("ALTER TABLE usuarios ALTER COLUMN senha DROP NOT NULL")
                            print("✅ Coluna 'senha' tornada nullable (migração)")
                            conn.commit()
                    except Exception as e:
                        print(f"⚠️ Aviso ao migrar coluna 'senha': {e}")
                        conn.rollback()
                
                # Adicionar constraints UNIQUE se não existirem
                try:
                    cursor.execute("""
                        SELECT constraint_name 
                        FROM information_schema.table_constraints 
                        WHERE table_name = 'usuarios' AND constraint_type = 'UNIQUE'
                    """)
                    unique_constraints = [row[0] for row in cursor.fetchall()]
                    
                    if not any('username' in str(c) for c in unique_constraints):
                        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS usuarios_username_key ON usuarios(username)")
                    if not any('email' in str(c) for c in unique_constraints):
                        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS usuarios_email_key ON usuarios(email)")
                except Exception as e:
                    print(f"⚠️ Aviso ao adicionar constraints UNIQUE: {e}")
                
                # Migração: Atualizar CHECK constraint para incluir 'Lider'
                try:
                    # Verificar se a constraint atual existe e precisa ser atualizada
                    cursor.execute("""
                        SELECT constraint_name, check_clause
                        FROM information_schema.check_constraints
                        WHERE constraint_name LIKE '%role%' 
                        AND constraint_schema = current_schema()
                    """)
                    role_constraints = cursor.fetchall()
                    
                    # Verificar se já existe a constraint usuarios_role_check com 'Lider'
                    constraint_ja_existe = False
                    constraint_atualizada = False
                    
                    for constraint_name, check_clause in role_constraints:
                        if constraint_name == 'usuarios_role_check' and 'Lider' in str(check_clause):
                            constraint_ja_existe = True
                            constraint_atualizada = True
                            break
                        elif 'Lider' not in str(check_clause):
                            # Remover constraint antiga sem 'Lider'
                            cursor.execute(f"ALTER TABLE usuarios DROP CONSTRAINT IF EXISTS {constraint_name}")
                            print(f"✅ Constraint antiga removida: {constraint_name}")
                    
                    # Adicionar nova constraint com 'Lider' apenas se não existir
                    if not constraint_ja_existe:
                        cursor.execute("""
                            ALTER TABLE usuarios 
                            ADD CONSTRAINT usuarios_role_check 
                            CHECK (role IN ('Master', 'Adm', 'Lider', 'Operacional'))
                        """)
                        print("✅ Constraint de role atualizada para incluir 'Lider'")
                        constraint_atualizada = True
                    elif constraint_atualizada:
                        print("✅ Constraint de role já está atualizada com 'Lider'")
                    
                    conn.commit()
                except Exception as e:
                    # Se a constraint já existe ou não pode ser criada, continuar silenciosamente
                    error_msg = str(e).lower()
                    if any(term in error_msg for term in ['already exists', 'duplicate', 'já existe', 'duplicado']):
                        # Constraint já existe, não é um erro
                        pass
                    else:
                        print(f"⚠️ Aviso ao atualizar constraint de role: {e}")
                    conn.rollback()
        else:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                senha_hash TEXT NOT NULL,
                nome_completo TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('Master', 'Adm', 'Lider', 'Operacional')),
                ativo INTEGER DEFAULT 1,
                data_criacao TEXT DEFAULT CURRENT_TIMESTAMP,
                ultimo_acesso TEXT,
                foto_perfil TEXT
            );
            """)

        # === 📦 HISTÓRICO DE UPLOADS (substitui uploads_history.json) ===
        if is_postgresql:
            # Criar savepoint para poder fazer rollback sem afetar o resto
            try:
                cursor.execute("SAVEPOINT upload_history_migration")
            except:
                pass
            
            # Verificar se a tabela existe
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'upload_history'
            """)
            existing_columns = [row[0] for row in cursor.fetchall()]
            
            if not existing_columns:
                # Tabela não existe, criar
                cursor.execute("""
                CREATE TABLE upload_history (
                    id SERIAL PRIMARY KEY,
                    lote_id VARCHAR(255) UNIQUE NOT NULL,
                    titulo VARCHAR(255) NOT NULL,
                    data_upload TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    total_arquivos INTEGER DEFAULT 0,
                    total_entregadores INTEGER DEFAULT 0,
                    valor_total DECIMAL(15, 2) DEFAULT 0,
                    pasta_uploads VARCHAR(500),
                    dados_json JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_upload_history_data_upload ON upload_history(data_upload);
                """)
            else:
                # Tabela existe, verificar e adicionar colunas faltantes
                required_columns = {
                    'lote_id': 'VARCHAR(255)',
                    'pasta_uploads': 'VARCHAR(500)',
                    'dados_json': 'JSONB',
                    'titulo': 'VARCHAR(255)',
                    'data_upload': 'TIMESTAMP',
                    'total_arquivos': 'INTEGER',
                    'total_entregadores': 'INTEGER',
                    'valor_total': 'DECIMAL(15, 2)',
                    'created_at': 'TIMESTAMP'
                }
                
                for col_name, col_def in required_columns.items():
                    if col_name not in existing_columns:
                        try:
                            # Adicionar coluna sem UNIQUE primeiro (para lote_id)
                            if col_name == 'lote_id':
                                cursor.execute(f"ALTER TABLE upload_history ADD COLUMN {col_name} {col_def}")
                            else:
                                cursor.execute(f"ALTER TABLE upload_history ADD COLUMN {col_name} {col_def}")
                            
                            # Adicionar valores padrão se necessário
                            if col_name == 'data_upload':
                                cursor.execute("ALTER TABLE upload_history ALTER COLUMN data_upload SET DEFAULT CURRENT_TIMESTAMP")
                            elif col_name == 'created_at':
                                cursor.execute("ALTER TABLE upload_history ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP")
                            elif col_name in ['total_arquivos', 'total_entregadores']:
                                cursor.execute(f"ALTER TABLE upload_history ALTER COLUMN {col_name} SET DEFAULT 0")
                            elif col_name == 'valor_total':
                                cursor.execute("ALTER TABLE upload_history ALTER COLUMN valor_total SET DEFAULT 0")
                            
                            print(f"✅ Coluna {col_name} adicionada à tabela upload_history")
                        except Exception as e:
                            print(f"⚠️ Aviso ao adicionar coluna {col_name}: {e}")
                            # Fazer rollback para savepoint se for PostgreSQL
                            if is_postgresql:
                                try:
                                    cursor.execute("ROLLBACK TO SAVEPOINT upload_history_migration")
                                    cursor.execute("SAVEPOINT upload_history_migration")
                                except:
                                    pass
                
                # Criar índice se não existir (usar bloco DO para não quebrar transação)
                try:
                    cursor.execute("""
                        DO $$ 
                        BEGIN
                            CREATE INDEX IF NOT EXISTS idx_upload_history_data_upload ON upload_history(data_upload);
                        EXCEPTION WHEN OTHERS THEN
                            -- Ignorar erro se índice já existir
                            NULL;
                        END $$;
                    """)
                except Exception as e:
                    print(f"⚠️ Aviso ao criar índice: {e}")
                    # Fazer rollback para savepoint
                    try:
                        cursor.execute("ROLLBACK TO SAVEPOINT upload_history_migration")
                        cursor.execute("SAVEPOINT upload_history_migration")
                    except:
                        pass
                
                # Adicionar constraint UNIQUE em lote_id se não existir e a coluna existir
                if 'lote_id' in existing_columns:
                    # Usar bloco DO para capturar exceções sem quebrar a transação
                    try:
                        cursor.execute("""
                            DO $$ 
                            BEGIN
                                IF NOT EXISTS (
                                    SELECT 1 FROM pg_constraint 
                                    WHERE conrelid = 'upload_history'::regclass 
                                    AND contype = 'u' 
                                    AND conkey::text LIKE '%lote_id%'
                                ) THEN
                                    ALTER TABLE upload_history 
                                    ADD CONSTRAINT upload_history_lote_id_key UNIQUE (lote_id);
                                END IF;
                            EXCEPTION WHEN OTHERS THEN
                                -- Ignorar erro se constraint já existir
                                NULL;
                            END $$;
                        """)
                    except Exception as e:
                        print(f"⚠️ Aviso ao adicionar constraint UNIQUE em lote_id: {e}")
                        # Fazer rollback para savepoint
                        try:
                            cursor.execute("ROLLBACK TO SAVEPOINT upload_history_migration")
                            cursor.execute("SAVEPOINT upload_history_migration")
                        except:
                            pass
                
                # Liberar savepoint
                try:
                    cursor.execute("RELEASE SAVEPOINT upload_history_migration")
                except:
                    pass
        else:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS upload_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lote_id TEXT UNIQUE NOT NULL,
                titulo TEXT NOT NULL,
                data_upload TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                total_arquivos INTEGER DEFAULT 0,
                total_entregadores INTEGER DEFAULT 0,
                valor_total REAL DEFAULT 0,
                pasta_uploads TEXT,
                dados_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """)

        # === 📊 RESULTADOS DE PROCESSAMENTO (substitui ultimo_resultado.json) ===
        if is_postgresql:
            # Verificar se a tabela existe e tem as colunas corretas
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'processamento_resultados'
            """)
            existing_columns = [row[0] for row in cursor.fetchall()]
            
            if not existing_columns:
                # Tabela não existe, criar
                cursor.execute("""
                CREATE TABLE processamento_resultados (
                    id SERIAL PRIMARY KEY,
                    pasta_uploads VARCHAR(500) NOT NULL,
                    data_processamento TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    total_entregadores INTEGER DEFAULT 0,
                    valor_total_geral DECIMAL(15, 2) DEFAULT 0,
                    total_arquivos INTEGER DEFAULT 0,
                    arquivos_sucesso INTEGER DEFAULT 0,
                    arquivos_com_erro INTEGER DEFAULT 0,
                    total_entregadores_cadastrados INTEGER DEFAULT 0,
                    entregadores_com_dados INTEGER DEFAULT 0,
                    erros TEXT,
                    dados_json JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(pasta_uploads)
                );
                CREATE INDEX IF NOT EXISTS idx_processamento_data ON processamento_resultados(data_processamento);
                """)
            else:
                # Tabela existe, verificar e adicionar colunas faltantes
                required_columns = {
                    'pasta_uploads': 'VARCHAR(500)',
                    'data_processamento': 'TIMESTAMP',
                    'total_entregadores': 'INTEGER',
                    'valor_total_geral': 'DECIMAL(15, 2)',
                    'total_arquivos': 'INTEGER',
                    'arquivos_sucesso': 'INTEGER',
                    'arquivos_com_erro': 'INTEGER',
                    'total_entregadores_cadastrados': 'INTEGER',
                    'entregadores_com_dados': 'INTEGER',
                    'erros': 'TEXT',
                    'dados_json': 'JSONB',
                    'created_at': 'TIMESTAMP'
                }
                
                for col_name, col_def in required_columns.items():
                    if col_name not in existing_columns:
                        try:
                            cursor.execute(f"ALTER TABLE processamento_resultados ADD COLUMN {col_name} {col_def}")
                            print(f"✅ Coluna {col_name} adicionada à tabela processamento_resultados")
                        except Exception as e:
                            print(f"⚠️ Aviso ao adicionar coluna {col_name}: {e}")
                
                # Adicionar constraint UNIQUE em pasta_uploads se não existir
                if 'pasta_uploads' in existing_columns:
                    try:
                        cursor.execute("""
                            DO $$ 
                            BEGIN
                                IF NOT EXISTS (
                                    SELECT 1 FROM pg_constraint 
                                    WHERE conrelid = 'processamento_resultados'::regclass 
                                    AND contype = 'u' 
                                    AND conkey::text LIKE '%pasta_uploads%'
                                ) THEN
                                    ALTER TABLE processamento_resultados 
                                    ADD CONSTRAINT processamento_resultados_pasta_uploads_key UNIQUE (pasta_uploads);
                                END IF;
                            EXCEPTION WHEN OTHERS THEN
                                NULL;
                            END $$;
                        """)
                    except Exception as e:
                        print(f"⚠️ Aviso ao adicionar constraint UNIQUE em pasta_uploads: {e}")
                
                # Criar índice se não existir
                try:
                    cursor.execute("""
                        DO $$ 
                        BEGIN
                            CREATE INDEX IF NOT EXISTS idx_processamento_data ON processamento_resultados(data_processamento);
                        EXCEPTION WHEN OTHERS THEN
                            NULL;
                        END $$;
                    """)
                except Exception as e:
                    print(f"⚠️ Aviso ao criar índice: {e}")
        else:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS processamento_resultados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pasta_uploads TEXT NOT NULL UNIQUE,
                data_processamento TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                total_entregadores INTEGER DEFAULT 0,
                valor_total_geral REAL DEFAULT 0,
                total_arquivos INTEGER DEFAULT 0,
                arquivos_sucesso INTEGER DEFAULT 0,
                arquivos_com_erro INTEGER DEFAULT 0,
                total_entregadores_cadastrados INTEGER DEFAULT 0,
                entregadores_com_dados INTEGER DEFAULT 0,
                erros TEXT,
                dados_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """)

        # === 📁 ARQUIVOS TEMPORÁRIOS DE PROCESSAMENTO ===
        if is_postgresql:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS processamento_arquivos_temp (
                id SERIAL PRIMARY KEY,
                token VARCHAR(255) UNIQUE NOT NULL,
                pasta_uploads VARCHAR(500),
                dados_json JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_temp_token ON processamento_arquivos_temp(token);
            CREATE INDEX IF NOT EXISTS idx_temp_expires ON processamento_arquivos_temp(expires_at);
            """)
        else:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS processamento_arquivos_temp (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                pasta_uploads TEXT,
                dados_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT
            );
            """)

        # === 💾 TABELAS DE BACKUP DIÁRIO ===
        if is_postgresql:
            # Backup de Entregadores (cadastro)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS backup_entregadores (
                id SERIAL PRIMARY KEY,
                backup_date DATE NOT NULL,
                id_da_pessoa_entregadora VARCHAR(255) NOT NULL,
                recebedor VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                cpf VARCHAR(14),
                cnpj VARCHAR(18),
                praca VARCHAR(255),
                subpraca VARCHAR(255),
                emissor VARCHAR(255),
                status VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(backup_date, id_da_pessoa_entregadora)
            );
            CREATE INDEX IF NOT EXISTS idx_backup_entregadores_date ON backup_entregadores(backup_date);
            """)
            
            # Backup de Solicitações de Adiantamento (quem solicitou diário)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS backup_solicitacoes_adiantamento (
                id SERIAL PRIMARY KEY,
                backup_date DATE NOT NULL,
                original_id INTEGER NOT NULL,
                email VARCHAR(255),
                nome VARCHAR(255),
                cpf VARCHAR(14),
                praca VARCHAR(255),
                valor_informado DECIMAL(10, 2),
                concorda TEXT,
                data_envio TIMESTAMP,
                cpf_bate INTEGER DEFAULT 0,
                dados_json JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(backup_date, original_id)
            );
            CREATE INDEX IF NOT EXISTS idx_backup_solicitacoes_date ON backup_solicitacoes_adiantamento(backup_date);
            """)
            
            # Backup de Histórico PIX (forms bancários)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS backup_historico_pix (
                id SERIAL PRIMARY KEY,
                backup_date DATE NOT NULL,
                original_id INTEGER NOT NULL,
                id_da_pessoa_entregadora VARCHAR(255),
                cpf VARCHAR(14),
                chave_pix VARCHAR(255),
                tipo_de_chave_pix VARCHAR(50),
                data_registro TIMESTAMP,
                status VARCHAR(50),
                nome VARCHAR(255),
                avaliacao INTEGER,
                praca VARCHAR(255),
                cnpj VARCHAR(18),
                email VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(backup_date, original_id)
            );
            CREATE INDEX IF NOT EXISTS idx_backup_pix_date ON backup_historico_pix(backup_date);
            """)
            
            # Log de Backups
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS backup_logs (
                id SERIAL PRIMARY KEY,
                backup_date DATE NOT NULL UNIQUE,
                total_entregadores INTEGER DEFAULT 0,
                total_solicitacoes INTEGER DEFAULT 0,
                total_historico_pix INTEGER DEFAULT 0,
                status VARCHAR(50) DEFAULT 'sucesso',
                mensagem TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_backup_logs_date ON backup_logs(backup_date);
            """)
        else:
            # Backup de Entregadores (cadastro)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS backup_entregadores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_date TEXT NOT NULL,
                id_da_pessoa_entregadora TEXT NOT NULL,
                recebedor TEXT NOT NULL,
                email TEXT,
                cpf TEXT,
                cnpj TEXT,
                praca TEXT,
                subpraca TEXT,
                emissor TEXT,
                status TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(backup_date, id_da_pessoa_entregadora)
            );
            """)
            
            # Backup de Solicitações de Adiantamento
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS backup_solicitacoes_adiantamento (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_date TEXT NOT NULL,
                original_id INTEGER NOT NULL,
                email TEXT,
                nome TEXT,
                cpf TEXT,
                praca TEXT,
                valor_informado REAL,
                concorda TEXT,
                data_envio TEXT,
                cpf_bate INTEGER DEFAULT 0,
                dados_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(backup_date, original_id)
            );
            """)
            
            # Backup de Histórico PIX
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS backup_historico_pix (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_date TEXT NOT NULL,
                original_id INTEGER NOT NULL,
                id_da_pessoa_entregadora TEXT,
                cpf TEXT,
                chave_pix TEXT,
                tipo_de_chave_pix TEXT,
                data_registro TEXT,
                status TEXT,
                nome TEXT,
                avaliacao INTEGER,
                praca TEXT,
                cnpj TEXT,
                email TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(backup_date, original_id)
            );
            """)
            
            # Log de Backups
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS backup_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_date TEXT NOT NULL UNIQUE,
                total_entregadores INTEGER DEFAULT 0,
                total_solicitacoes INTEGER DEFAULT 0,
                total_historico_pix INTEGER DEFAULT 0,
                status TEXT DEFAULT 'sucesso',
                mensagem TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """)

        conn.commit()
        db_type = "PostgreSQL" if is_postgresql else "SQLite"
        print(f"✅ Banco inicializado com todas as tabelas ({db_type}).")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao inicializar banco: {e}")
        raise
    finally:
        conn.close()


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
