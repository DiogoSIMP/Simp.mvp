"""
Rotas para formulário público de PIX
"""
from flask import render_template, request
from app.models.database import get_db_connection, get_db_cursor, get_db_placeholder, is_postgresql_connection
from app.utils.pix_logs import registrar_erro_pix
from datetime import datetime
from app.utils.constants import (
    TEMPLATES_PIX,
    STATUS_PIX,
    TIPOS_CHAVE_PIX,
    FORMATO_DATA_SQL
)
from app.utils.route_helpers import normalize_cpf


def init_pix_routes(app):
    
    @app.route("/form-bancario", methods=["GET"])
    def form_bancario():
        return render_template(TEMPLATES_PIX['form_public'], modal=None)
    
    @app.route("/form-bancario/enviar", methods=["POST"])
    def form_bancario_enviar():
        nome = request.form.get("nome", "").strip()
        cpf = request.form.get("cpf")
        cnpj = request.form.get("cnpj", "").strip()
        praca = request.form.get("praca", "").strip()
        tipo_chave = request.form.get("tipo_chave_pix", "").strip()
        chave = request.form.get("chave_pix", "").strip()
        avaliacao = request.form.get("avaliacao")
        user_agent = request.headers.get("User-Agent", "")
        ip = request.remote_addr
        cpf_limpo = normalize_cpf(cpf)
        # Limpar CNPJ (remover pontuação)
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj)) if cnpj else None
        
        # Validar que tipo de chave não seja CPF
        if tipo_chave == "CPF" or tipo_chave == TIPOS_CHAVE_PIX['CPF']:
            return render_template(TEMPLATES_PIX['form_public'], modal={
                "type": "erro_tipo",
                "mensagem": "CPF não pode ser usado como tipo de chave PIX. Por favor, selecione outro tipo."
            })
        
        conn = get_db_connection()
        placeholder = get_db_placeholder(conn)
        cursor = get_db_cursor(conn)
        
        try:
            # Validar duplicatas: verificar se CPF já foi usado
            cursor.execute(f"""
                SELECT id FROM historico_pix
                WHERE cpf = {placeholder}
            """, (cpf_limpo,))
            
            cpf_existente = cursor.fetchone()
            if cpf_existente:
                return render_template(TEMPLATES_PIX['form_public'], modal={
                    "type": "erro_duplicado",
                    "mensagem": "Este CPF já foi utilizado para cadastrar uma chave PIX. Não é possível cadastrar novamente."
                })
            
            # Validar duplicatas: verificar se chave PIX já foi usada (qualquer status)
            cursor.execute(f"""
                SELECT id FROM historico_pix
                WHERE chave_pix = {placeholder}
            """, (chave,))
            
            chave_existente = cursor.fetchone()
            if chave_existente:
                return render_template(TEMPLATES_PIX['form_public'], modal={
                    "type": "erro_duplicado",
                    "mensagem": "Esta chave PIX já foi cadastrada. Não é possível cadastrar a mesma chave duas vezes."
                })
            
            # Validar entregador (normalizar CPF em Python para compatibilidade)
            is_postgresql = is_postgresql_connection(conn)
            if is_postgresql:
                # PostgreSQL: buscar todos e normalizar em Python
                cursor.execute("SELECT id_da_pessoa_entregadora, recebedor, cnpj, cpf FROM entregadores WHERE cpf IS NOT NULL")
            else:
                # SQLite: usar REPLACE
                cursor.execute("""
                    SELECT id_da_pessoa_entregadora, recebedor, cnpj, cpf
                    FROM entregadores
                    WHERE REPLACE(REPLACE(REPLACE(cpf,'.',''),'-',''),' ','') = ?
                """, (cpf_limpo,))
            
            entregadores = cursor.fetchall()
            entregador = None
            
            # Normalizar CPF em Python para encontrar match
            for e in entregadores:
                cpf_entregador = e.get('cpf') if isinstance(e, dict) else e[3]
                if normalize_cpf(cpf_entregador or '') == cpf_limpo:
                    entregador = e
                    break
            
            # Usar tipo informado pelo usuário, ou detectar automaticamente se não informado
            if not tipo_chave or tipo_chave == "":
                # Detectar tipo de chave PIX automaticamente
                tipo_chave = TIPOS_CHAVE_PIX['AUTO']
                chave_limpa = chave.replace('(', '').replace(')', '').replace('-', '').replace(' ', '').replace('.', '').replace('/', '')
                
                if '@' in chave and '.' in chave:
                    tipo_chave = 'EMAIL'
                elif chave_limpa.isdigit():
                    if len(chave_limpa) == 14:
                        tipo_chave = 'CNPJ'
                    elif len(chave_limpa) >= 10 and len(chave_limpa) <= 13:
                        tipo_chave = 'TELEFONE'
                elif len(chave) >= 25:
                    tipo_chave = 'ALEATORIA'
            
            if not entregador:
                # Criar registro pendente em historico_pix mesmo sem entregador cadastrado
                placeholders = ", ".join([placeholder] * 10)
                cursor.execute(f"""
                    INSERT INTO historico_pix
                    (id_da_pessoa_entregadora, cpf, cnpj, nome, praca, chave_pix, tipo_de_chave_pix, avaliacao, data_registro, status)
                    VALUES ({placeholders})
                """, (
                    None,  # id_da_pessoa_entregadora = NULL quando não cadastrado
                    cpf_limpo,  # CPF para identificação
                    cnpj_limpo,  # CNPJ informado
                    nome,  # Nome informado
                    praca,  # Praça selecionada
                    chave,
                    tipo_chave,
                    avaliacao if avaliacao else None,  # Avaliação de atendimento
                    datetime.now().strftime(FORMATO_DATA_SQL),
                    STATUS_PIX['PENDENTE']
                ))
                conn.commit()
                
                # Mostrar mensagem de sucesso mesmo quando CPF não encontrado
                return render_template(TEMPLATES_PIX['form_public'], modal={
                    "type": "sucesso",
                    "nome": nome
                })
            
            id_ent = entregador.get("id_da_pessoa_entregadora") if isinstance(entregador, dict) else entregador[0]
            
            # Gravar chave pendente para entregador cadastrado
            # Se não informou CNPJ no formulário, usa o CNPJ cadastrado do entregador
            cnpj_final = cnpj_limpo if cnpj_limpo else (entregador.get("cnpj") if isinstance(entregador, dict) else entregador[2])
            
            placeholders = ", ".join([placeholder] * 10)
            cursor.execute(f"""
                INSERT INTO historico_pix
                (id_da_pessoa_entregadora, cpf, cnpj, nome, praca, chave_pix, tipo_de_chave_pix, avaliacao, data_registro, status)
                VALUES ({placeholders})
            """, (
                id_ent,
                cpf_limpo,  # Também salvar CPF para facilitar identificação
                cnpj_final,  # CNPJ informado ou do cadastro
                nome,  # Nome informado
                praca,  # Praça selecionada
                chave,
                tipo_chave,
                avaliacao if avaliacao else None,  # Avaliação de atendimento
                datetime.now().strftime(FORMATO_DATA_SQL),
                STATUS_PIX['PENDENTE']
            ))
            
            conn.commit()
            
            return render_template(TEMPLATES_PIX['form_public'], modal={
                "type": "sucesso",
                "nome": nome or (entregador.get("recebedor") if isinstance(entregador, dict) else entregador[1])
            })
        except Exception as e:
            conn.rollback()
            print(f"❌ Erro ao processar formulário PIX: {e}")
            return render_template(TEMPLATES_PIX['form_public'], modal={
                "type": "erro",
                "mensagem": "Erro ao processar solicitação. Tente novamente."
            })
        finally:
            conn.close()
