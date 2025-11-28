from app.models.database import get_db_connection, formatar_nome
import sqlite3

import sqlite3

class EntregadoresService:
    
    # ================================
    # 📋 LISTAR ENTREGADORES
    # ================================
    @staticmethod
    def listar_entregadores():
        """Lista todos os entregadores"""
        conn = get_db_connection()
        try:
            entregadores = conn.execute('''
                SELECT * FROM entregadores 
                ORDER BY status DESC, recebedor ASC
            ''').fetchall()
            
            entregadores_list = []
            for entregador in entregadores:
                e = dict(entregador)
                e['recebedor'] = formatar_nome(e['recebedor'])
                entregadores_list.append(e)
                
            return entregadores_list
            
        except sqlite3.Error as e:
            raise Exception(f'Erro ao carregar entregadores: {str(e)}')
        finally:
            conn.close()

    # ================================
    # 🔍 BUSCAR POR ID
    # ================================
    @staticmethod
    def buscar_entregador_por_id(id_entregador):
        """Busca entregador e último histórico de PIX"""
        conn = get_db_connection()
        try:
            entregador = conn.execute("""
                SELECT 
                    e.id_da_pessoa_entregadora,
                    e.recebedor,
                    e.email,
                    e.cpf,
                    e.cnpj,
                    e.praca,
                    e.subpraca,
                    e.emissor,
                    e.status,
                    h.chave_pix,
                    h.tipo_de_chave_pix
                FROM entregadores e
                LEFT JOIN historico_pix h
                    ON e.id_da_pessoa_entregadora = h.id_da_pessoa_entregadora
                WHERE e.id_da_pessoa_entregadora = ?
                ORDER BY h.data_registro DESC
                LIMIT 1
            """, (id_entregador,)).fetchone()

            if not entregador:
                return None
            
            # Converter para dict e garantir que todos os campos existam
            dados = dict(entregador)
            # Garantir que campos opcionais tenham valores padrão
            dados.setdefault('praca', None)
            dados.setdefault('subpraca', None)
            dados.setdefault('chave_pix', None)
            dados.setdefault('tipo_de_chave_pix', None)
            dados.setdefault('email', None)
            dados.setdefault('cpf', None)
            
            return dados

        except sqlite3.Error as e:
            raise Exception(f'Erro ao buscar entregador: {str(e)}')
        finally:
            conn.close()

    # ================================
    # 🔄 ATUALIZAR REGISTROS PIX PENDENTES
    # ================================
    @staticmethod
    def atualizar_pix_pendentes(id_entregador, cpf_limpo=None, chave_pix=None):
        """Atualiza registros PIX pendentes vinculando ao entregador"""
        from app.utils.constants import STATUS_PIX
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            registros_atualizados = 0
            
            # Atualizar registros pendentes por CPF
            if cpf_limpo:
                cursor.execute('''
                    UPDATE historico_pix
                    SET id_da_pessoa_entregadora = ?, status = ?
                    WHERE cpf = ? AND (id_da_pessoa_entregadora IS NULL OR id_da_pessoa_entregadora = '')
                ''', (id_entregador, STATUS_PIX['APROVADO'], cpf_limpo))
                registros_atualizados += cursor.rowcount
            
            # Atualizar registros pendentes por chave PIX (mesmo que já tenha sido atualizado por CPF)
            if chave_pix:
                cursor.execute('''
                    UPDATE historico_pix
                    SET id_da_pessoa_entregadora = ?, status = ?
                    WHERE chave_pix = ? AND (id_da_pessoa_entregadora IS NULL OR id_da_pessoa_entregadora = '')
                ''', (id_entregador, STATUS_PIX['APROVADO'], chave_pix))
                registros_atualizados += cursor.rowcount
            
            # Também atualizar registros que já têm o id_entregador mas status ainda está pendente
            cursor.execute('''
                UPDATE historico_pix
                SET status = ?
                WHERE id_da_pessoa_entregadora = ? AND (status IS NULL OR status = ? OR status = '')
            ''', (STATUS_PIX['APROVADO'], id_entregador, STATUS_PIX['PENDENTE']))
            registros_atualizados += cursor.rowcount
            
            conn.commit()
            return registros_atualizados
        except sqlite3.Error as e:
            raise Exception(f'Erro ao atualizar registros PIX pendentes: {str(e)}')
        finally:
            conn.close()

    # ================================
    # 🔍 BUSCAR ENTREGADOR POR CPF
    # ================================
    @staticmethod
    def buscar_entregador_por_cpf(cpf):
        """Busca entregador pelo CPF normalizado"""
        from app.utils.route_helpers import normalize_cpf
        
        cpf_limpo = normalize_cpf(cpf)
        if not cpf_limpo:
            return None
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # Buscar por CPF normalizado (removendo pontos, traços, espaços)
            cursor.execute('''
                SELECT * FROM entregadores
                WHERE REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                    LTRIM(RTRIM(COALESCE(cpf, ''))), 
                    '.', ''), '-', ''), ' ', ''), '(', ''), ')', ''), '/', '') = ?
            ''', (cpf_limpo,))
            
            resultado = cursor.fetchone()
            return dict(resultado) if resultado else None
        except sqlite3.Error as e:
            raise Exception(f'Erro ao buscar entregador por CPF: {str(e)}')
        finally:
            conn.close()

    # ================================
    # 🔍 BUSCAR DADOS BANCÁRIOS (FORM)
    # ================================
    @staticmethod
    def buscar_dados_bancarios_por_cpf(cpf):
        """Busca último registro de formulário bancário (historico_pix) pelo CPF"""
        from app.utils.route_helpers import normalize_cpf

        cpf_limpo = normalize_cpf(cpf)
        if not cpf_limpo:
            return None

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 
                    nome,
                    cpf,
                    praca,
                    tipo_de_chave_pix,
                    chave_pix,
                    data_registro
                FROM historico_pix
                WHERE REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                    LTRIM(RTRIM(COALESCE(cpf, ''))), 
                    '.', ''), '-', ''), ' ', ''), '(', ''), ')', ''), '/', '') = ?
                ORDER BY datetime(COALESCE(data_registro, CURRENT_TIMESTAMP)) DESC
                LIMIT 1
                """,
                (cpf_limpo,)
            )
            resultado = cursor.fetchone()
            return dict(resultado) if resultado else None
        except sqlite3.Error as e:
            raise Exception(f'Erro ao buscar dados bancários: {str(e)}')
        finally:
            conn.close()

    # ================================
    # 🔍 VALIDAR DUPLICATAS
    # ================================
    @staticmethod
    def validar_duplicatas(dados, id_entregador_excluir=None):
        """
        Valida se CPF, Email, CNPJ ou Chave PIX já estão cadastrados
        id_entregador_excluir: ID a ser ignorado na validação (útil para edição)
        """
        from app.utils.route_helpers import normalize_cpf
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            erros = []
            
            # Validar CPF
            cpf = dados.get('cpf', '').strip()
            if cpf:
                cpf_limpo = normalize_cpf(cpf)
                if cpf_limpo:
                    # Buscar todos os entregadores e normalizar CPF em Python
                    query = 'SELECT id_da_pessoa_entregadora, recebedor, cpf FROM entregadores WHERE cpf IS NOT NULL AND cpf != ""'
                    if id_entregador_excluir:
                        query += ' AND id_da_pessoa_entregadora != ?'
                        cursor.execute(query, (id_entregador_excluir,))
                    else:
                        cursor.execute(query)
                    
                    for row in cursor.fetchall():
                        cpf_existente_limpo = normalize_cpf(row['cpf'] or '')
                        if cpf_existente_limpo == cpf_limpo:
                            erros.append(f'CPF já cadastrado para o entregador: {row["recebedor"]}')
                            break
            
            # Validar Email
            email = dados.get('email', '').strip()
            if email:
                query = '''
                    SELECT id_da_pessoa_entregadora, recebedor 
                    FROM entregadores
                    WHERE LOWER(TRIM(email)) = LOWER(?)
                '''
                params = [email]
                
                if id_entregador_excluir:
                    query += ' AND id_da_pessoa_entregadora != ?'
                    params.append(id_entregador_excluir)
                
                cursor.execute(query, params)
                resultado = cursor.fetchone()
                if resultado:
                    erros.append(f'Email já cadastrado para o entregador: {resultado["recebedor"]}')
            
            # Validar CNPJ
            cnpj = dados.get('cnpj', '').strip()
            if cnpj:
                # Limpar CNPJ (remover pontos, traços, barras, espaços)
                import re
                cnpj_limpo = re.sub(r'\D', '', cnpj)
                if cnpj_limpo:
                    # Buscar todos os entregadores e normalizar CNPJ em Python
                    query = 'SELECT id_da_pessoa_entregadora, recebedor, cnpj FROM entregadores WHERE cnpj IS NOT NULL AND cnpj != ""'
                    if id_entregador_excluir:
                        query += ' AND id_da_pessoa_entregadora != ?'
                        cursor.execute(query, (id_entregador_excluir,))
                    else:
                        cursor.execute(query)
                    
                    for row in cursor.fetchall():
                        cnpj_existente_limpo = re.sub(r'\D', '', str(row['cnpj'] or ''))
                        if cnpj_existente_limpo == cnpj_limpo:
                            erros.append(f'CNPJ já cadastrado para o entregador: {row["recebedor"]}')
                            break
            
            # Validar Chave PIX
            chave_pix = dados.get('chave_pix', '').strip()
            if chave_pix:
                query = '''
                    SELECT h.id_da_pessoa_entregadora, e.recebedor
                    FROM historico_pix h
                    LEFT JOIN entregadores e ON h.id_da_pessoa_entregadora = e.id_da_pessoa_entregadora
                    WHERE h.chave_pix = ?
                '''
                params = [chave_pix]
                
                if id_entregador_excluir:
                    query += ' AND (h.id_da_pessoa_entregadora IS NULL OR h.id_da_pessoa_entregadora != ?)'
                    params.append(id_entregador_excluir)
                
                cursor.execute(query, params)
                resultado = cursor.fetchone()
                if resultado and resultado["id_da_pessoa_entregadora"]:
                    nome = resultado["recebedor"] if resultado["recebedor"] else "Entregador não identificado"
                    erros.append(f'Chave PIX já cadastrada para: {nome}')
            
            return erros
            
        except sqlite3.Error as e:
            raise Exception(f'Erro ao validar duplicatas: {str(e)}')
        finally:
            conn.close()

    # ================================
    # ➕ CRIAR ENTREGADOR
    # ================================
    @staticmethod
    def criar_entregador(dados):
        """Cria um novo entregador + histórico PIX"""
        from app.utils.route_helpers import normalize_cpf
        from app.utils.constants import STATUS_PIX
        
        # Validar duplicatas antes de criar
        erros_validacao = EntregadoresService.validar_duplicatas(dados)
        if erros_validacao:
            raise Exception(' | '.join(erros_validacao))
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # Insere entregador
            cursor.execute('''
                INSERT INTO entregadores 
                (id_da_pessoa_entregadora, recebedor, email, cpf, cnpj, praca, subpraca, emissor, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                dados['id_da_pessoa_entregadora'],
                dados['recebedor'],
                dados.get('email', ''),
                dados.get('cpf', ''),
                dados.get('cnpj', ''),
                dados.get('praca', ''),
                dados.get('subpraca', ''),
                dados.get('emissor', 'Proprio'),
                dados.get('status', 'Ativo')
            ))

            id_ent = dados['id_da_pessoa_entregadora']
            cpf_limpo = normalize_cpf(dados.get('cpf', ''))
            chave_pix = dados.get('chave_pix', '')

            # Fazer commit da inserção do entregador antes de atualizar PIX
            conn.commit()

            # Atualizar registros PIX pendentes que correspondem a este entregador
            # (usa conexão separada para evitar lock)
            EntregadoresService.atualizar_pix_pendentes(id_ent, cpf_limpo, chave_pix)

            # Insere histórico PIX (se existir e não foi atualizado acima)
            if chave_pix:
                # Reabrir cursor após commit (ou usar nova conexão)
                cursor = conn.cursor()
                # Verificar se já existe um registro para esta chave PIX
                cursor.execute('''
                    SELECT id FROM historico_pix 
                    WHERE chave_pix = ? AND id_da_pessoa_entregadora = ?
                ''', (chave_pix, id_ent))
                
                if not cursor.fetchone():
                    # Só insere se não existir
                    cursor.execute('''
                        INSERT INTO historico_pix
                        (id_da_pessoa_entregadora, chave_pix, tipo_de_chave_pix, cpf, status)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        id_ent,
                        chave_pix,
                        dados.get('tipo_de_chave_pix', ''),
                        cpf_limpo,
                        STATUS_PIX['APROVADO']
                    ))
                    conn.commit()

            return True

        except sqlite3.IntegrityError:
            raise Exception('ID do entregador já existe no sistema!')
        except sqlite3.Error as e:
            raise Exception(f'Erro ao cadastrar entregador: {str(e)}')
        finally:
            conn.close()

    # ================================
    # ✏️ ATUALIZAR ENTREGADOR
    # ================================
    @staticmethod
    def atualizar_entregador(id_entregador, dados):
        """Atualiza dados do entregador e registra nova chave PIX"""
        # Validar duplicatas antes de atualizar (excluindo o próprio entregador)
        erros_validacao = EntregadoresService.validar_duplicatas(dados, id_entregador_excluir=id_entregador)
        if erros_validacao:
            raise Exception(' | '.join(erros_validacao))
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE entregadores 
                SET recebedor = ?, email = ?, cpf = ?, cnpj = ?, praca = ?, subpraca = ?, emissor = ?, status = ?
                WHERE id_da_pessoa_entregadora = ?
            ''', (
                dados.get('recebedor', ''),
                dados.get('email', ''),
                dados.get('cpf', ''),
                dados.get('cnpj', ''),
                dados.get('praca', ''),
                dados.get('subpraca', ''),
                dados.get('emissor', 'Proprio'),
                dados.get('status', 'Ativo'),
                id_entregador
            ))

            # Se chave_pix for alterada, insere novo histórico
            if dados.get('chave_pix'):
                cursor.execute('''
                    INSERT INTO historico_pix (id_da_pessoa_entregadora, chave_pix, tipo_de_chave_pix)
                    VALUES (?, ?, ?)
                ''', (
                    id_entregador,
                    dados['chave_pix'],
                    dados.get('tipo_de_chave_pix', '')
                ))

            conn.commit()
            return True

        except sqlite3.Error as e:
            raise Exception(f'Erro ao atualizar entregador: {str(e)}')
        finally:
            conn.close()

    # ================================
    # ❌ EXCLUIR ENTREGADOR
    # ================================
    @staticmethod
    def excluir_entregador(id_entregador):
        """Exclui entregador e histórico associado"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM historico_pix WHERE id_da_pessoa_entregadora = ?', (id_entregador,))
            cursor.execute('DELETE FROM entregadores WHERE id_da_pessoa_entregadora = ?', (id_entregador,))
            conn.commit()
            return True
        except sqlite3.Error as e:
            raise Exception(f'Erro ao excluir entregador: {str(e)}')
        finally:
            conn.close()
