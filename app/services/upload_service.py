import os
import re
import pandas as pd
import sqlite3
from app.models.database import get_db_connection
from app.utils.path_manager import get_week_folder
from config import Config


class UploadService:

    # ======================================
    # 🔧 UTILITÁRIO DE LIMPEZA DE CNPJ
    # ======================================
    @staticmethod
    def limpar_cnpj(valor):
        """Remove pontuação e retorna apenas números do CNPJ"""
        if not valor:
            return ''
        valor = re.sub(r'\D', '', str(valor))
        return valor if len(valor) == 14 else ''

    # ======================================
    # 📥 LEITURA E NORMALIZAÇÃO DO EXCEL
    # ======================================
    @staticmethod
    def ler_planilha(arquivo, upload_base="uploads"):
        """
        Lê e valida o arquivo Excel, salvando automaticamente
        em uma subpasta da semana atual (ex: uploads/semanas/semana46).
        Aceita tanto FileStorage (upload direto) quanto caminho de arquivo.
        """
        semana_path = get_week_folder(upload_base)
        os.makedirs(semana_path, exist_ok=True)

        # Se for um FileStorage (upload via form)
        if hasattr(arquivo, "filename") and hasattr(arquivo, "save"):
            filename = arquivo.filename
            file_path = os.path.join(semana_path, filename)
            arquivo.save(file_path)
            print(f"📂 Arquivo salvo em: {file_path}")

        # Se for uma string (caminho já existente)
        elif isinstance(arquivo, str) and os.path.exists(arquivo):
            file_path = arquivo
            print(f"📂 Lendo arquivo existente: {file_path}")

        else:
            raise Exception("❌ Arquivo inválido: deve ser FileStorage ou caminho existente")

        # Lê a planilha e padroniza colunas
        df = pd.read_excel(file_path, sheet_name=0)
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

        # Mapeia nomes alternativos
        mapa_colunas = {
            'id_da_pessoa_entregadora': ['id_da_pessoa_entregadora', 'id', 'id_entregador'],
            'recebedor': ['recebedor', 'nome', 'entregador', 'nome_entregador'],
            'email': ['email', 'e-mail', 'mail'],
            'cpf': ['cpf', 'documento'],
            'cnpj': ['cnpj', 'cnpj_empresa', 'empresa'],
            'subpraca': ['subpraca', 'sub_praca', 'sub-praça'],
            'emissor': ['emissor', 'criado_por', 'responsavel'],
            'tipo_de_chave_pix': ['tipo_de_chave_pix', 'tipo_pix', 'tipo_chave'],
            'chave_pix': ['chave_pix', 'pix', 'chave']
        }

        # Identifica colunas existentes
        colunas_encontradas = {}
        for padrao, alternativas in mapa_colunas.items():
            for alt in alternativas:
                if alt in df.columns:
                    colunas_encontradas[padrao] = alt
                    break

        # Verifica se colunas obrigatórias estão presentes
        obrigatorias = ['id_da_pessoa_entregadora', 'recebedor']
        faltando = [c for c in obrigatorias if c not in colunas_encontradas]
        if faltando:
            raise Exception(f"Colunas obrigatórias ausentes: {', '.join(faltando)}")

        # Renomeia e preenche
        df_padronizado = df.rename(columns=colunas_encontradas)
        df_padronizado = df_padronizado.fillna('')
        df_padronizado['status'] = 'Ativo'

        # Normaliza CNPJ
        if 'cnpj' in df_padronizado.columns:
            df_padronizado['cnpj'] = df_padronizado['cnpj'].apply(UploadService.limpar_cnpj)

        return df_padronizado

    # ======================================
    # 💾 INSERÇÃO NO BANCO
    # ======================================
    @staticmethod
    def salvar_no_banco(lista_dados):
        conn = get_db_connection()
        from app.models.database import get_db_cursor, get_db_placeholder, is_postgresql_connection
        
        is_postgresql = is_postgresql_connection(conn)
        placeholder = get_db_placeholder(conn)
        cursor = get_db_cursor(conn)
        inseridos, erros = 0, 0

        try:
            for item in lista_dados:
                try:
                    id_ent = str(item.get('id_da_pessoa_entregadora', '')).strip()
                    recebedor = str(item.get('recebedor', '')).strip()
                    email = str(item.get('email', '')).strip()
                    cpf = str(item.get('cpf', '')).strip()
                    cnpj = UploadService.limpar_cnpj(item.get('cnpj', ''))
                    subpraca = str(item.get('subpraca', '')).strip()
                    chave_pix = str(item.get('chave_pix', '')).strip()
                    tipo_pix = str(item.get('tipo_de_chave_pix', '')).strip()

                    if not id_ent or not recebedor:
                        erros += 1
                        print(f"⚠️ Linha ignorada (sem id ou recebedor): {item}")
                        continue

                    # Usar placeholder dinâmico
                    if is_postgresql:
                        cursor.execute(f"""
                            INSERT INTO entregadores
                            (id_da_pessoa_entregadora, recebedor, email, cpf, cnpj, subpraca, emissor, status)
                            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, 'Proprio', 'Ativo')
                            ON CONFLICT (id_da_pessoa_entregadora) DO NOTHING
                        """, (id_ent, recebedor, email, cpf, cnpj, subpraca))
                    else:
                        cursor.execute("""
                            INSERT OR IGNORE INTO entregadores
                            (id_da_pessoa_entregadora, recebedor, email, cpf, cnpj, subpraca, emissor, status)
                            VALUES (?, ?, ?, ?, ?, ?, 'Proprio', 'Ativo')
                        """, (id_ent, recebedor, email, cpf, cnpj, subpraca))

                    if chave_pix:
                        cursor.execute(f"""
                            INSERT INTO historico_pix
                            (id_da_pessoa_entregadora, chave_pix, tipo_de_chave_pix)
                            VALUES ({placeholder}, {placeholder}, {placeholder})
                        """, (id_ent, chave_pix, tipo_pix))

                    inseridos += 1

                except Exception as e:
                    erros += 1
                    print(f"❌ Erro ao inserir entregador {id_ent}: {e}")

            conn.commit()
            print(f"✅ Inseridos: {inseridos} | ⚠️ Erros: {erros}")
            return inseridos
        except Exception as e:
            conn.rollback()
            print(f"❌ Erro ao salvar no banco: {e}")
            raise
        finally:
            conn.close()
