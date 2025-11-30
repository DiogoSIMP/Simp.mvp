"""
Serviço para gerenciar armazenamento de dados JSON no banco de dados
Substitui arquivos JSON por tabelas no PostgreSQL/SQLite
"""
import json
from datetime import datetime, timedelta
from app.models.database import get_db_connection, is_postgresql_connection
from config import Config

USE_POSTGRESQL = Config.USE_POSTGRESQL


class StorageService:
    """Serviço para armazenar e recuperar dados que antes eram salvos em JSON"""
    
    @staticmethod
    def _is_postgresql(cursor):
        """Verifica se está usando PostgreSQL (usando helper centralizado)"""
        try:
            if hasattr(cursor, 'connection'):
                return is_postgresql_connection(cursor.connection)
            # Tentar verificar pelo tipo do cursor
            cursor_type = str(type(cursor))
            return 'psycopg2' in cursor_type.lower()
        except:
            return False
    
    @staticmethod
    def _serialize_json(data):
        """Serializa dados para JSON (string ou JSONB)"""
        if data is None:
            return None
        if isinstance(data, str):
            return data
        return json.dumps(data, ensure_ascii=False)
    
    @staticmethod
    def _deserialize_json(data):
        """Deserializa JSON do banco"""
        if data is None:
            return None
        if isinstance(data, str):
            try:
                return json.loads(data)
            except (json.JSONDecodeError, TypeError):
                return data
        return data
    
    # ==================== UPLOAD HISTORY ====================
    
    @staticmethod
    def salvar_upload_history(lote_id, titulo, data_upload, total_arquivos, 
                            total_entregadores, valor_total, pasta_uploads, dados_json=None):
        """Salva histórico de upload no banco"""
        from app.utils.db_helpers import db_connection
        from app.models.database import get_db_cursor, get_db_placeholder
        
        try:
            dados_json_str = StorageService._serialize_json(dados_json)
            
            with db_connection() as conn:
                cursor = get_db_cursor(conn)
                placeholder = get_db_placeholder(conn)
                is_pg = is_postgresql_connection(conn)
                
                if is_pg:
                    cursor.execute("""
                        INSERT INTO upload_history 
                        (lote_id, titulo, data_upload, total_arquivos, total_entregadores, 
                         valor_total, pasta_uploads, dados_json)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                        ON CONFLICT (lote_id) DO UPDATE SET
                            titulo = EXCLUDED.titulo,
                            data_upload = EXCLUDED.data_upload,
                            total_arquivos = EXCLUDED.total_arquivos,
                            total_entregadores = EXCLUDED.total_entregadores,
                            valor_total = EXCLUDED.valor_total,
                            pasta_uploads = EXCLUDED.pasta_uploads,
                            dados_json = EXCLUDED.dados_json
                    """, (lote_id, titulo, data_upload, total_arquivos, total_entregadores, 
                          valor_total, pasta_uploads, dados_json_str))
                else:
                    cursor.execute("""
                        INSERT OR REPLACE INTO upload_history 
                        (lote_id, titulo, data_upload, total_arquivos, total_entregadores, 
                         valor_total, pasta_uploads, dados_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (lote_id, titulo, data_upload, total_arquivos, total_entregadores, 
                          valor_total, pasta_uploads, dados_json_str))
            
            return True
        except Exception as e:
            print(f"Erro ao salvar upload history: {e}")
            return False
    
    @staticmethod
    def carregar_upload_history(pasta_uploads=None, limit=75):
        """Carrega histórico de uploads do banco"""
        from app.utils.db_helpers import db_connection, row_to_dict
        from app.models.database import get_db_cursor, get_db_placeholder
        
        try:
            with db_connection() as conn:
                cursor = get_db_cursor(conn)
                placeholder = get_db_placeholder(conn)
                
                if pasta_uploads:
                    query = f"""
                        SELECT * FROM upload_history 
                        WHERE pasta_uploads = {placeholder}
                        ORDER BY data_upload DESC
                        LIMIT {placeholder}
                    """
                    cursor.execute(query, (pasta_uploads, limit))
                else:
                    query = f"""
                        SELECT * FROM upload_history 
                        ORDER BY data_upload DESC
                        LIMIT {placeholder}
                    """
                    cursor.execute(query, (limit,))
                
                rows = cursor.fetchall()
                results = []
                
                for row in rows:
                    item = row_to_dict(row)
                    if item:
                        # Deserializar JSON
                        if 'dados_json' in item:
                            item['dados_json'] = StorageService._deserialize_json(item['dados_json'])
                        results.append(item)
                
                return results
        except Exception as e:
            print(f"Erro ao carregar upload history: {e}")
            return []
    
    @staticmethod
    def excluir_upload_history(lote_id):
        """Exclui um registro de upload history"""
        from app.utils.db_helpers import db_connection
        from app.models.database import get_db_cursor, get_db_placeholder
        
        try:
            with db_connection() as conn:
                cursor = get_db_cursor(conn)
                placeholder = get_db_placeholder(conn)
                cursor.execute(f"DELETE FROM upload_history WHERE lote_id = {placeholder}", (lote_id,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Erro ao excluir upload history: {e}")
            return False
    
    # ==================== PROCESSAMENTO RESULTADOS ====================
    
    @staticmethod
    def salvar_processamento_resultado(pasta_uploads, resultado, dados_json=None):
        """Salva resultado de processamento no banco"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            is_pg = StorageService._is_postgresql(cursor)
            dados_json_str = StorageService._serialize_json(dados_json)
            
            if is_pg:
                cursor.execute("""
                    INSERT INTO processamento_resultados 
                    (pasta_uploads, data_processamento, total_entregadores, valor_total_geral,
                     total_arquivos, arquivos_sucesso, arquivos_com_erro,
                     total_entregadores_cadastrados, entregadores_com_dados, erros, dados_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (pasta_uploads) DO UPDATE SET
                        data_processamento = EXCLUDED.data_processamento,
                        total_entregadores = EXCLUDED.total_entregadores,
                        valor_total_geral = EXCLUDED.valor_total_geral,
                        total_arquivos = EXCLUDED.total_arquivos,
                        arquivos_sucesso = EXCLUDED.arquivos_sucesso,
                        arquivos_com_erro = EXCLUDED.arquivos_com_erro,
                        total_entregadores_cadastrados = EXCLUDED.total_entregadores_cadastrados,
                        entregadores_com_dados = EXCLUDED.entregadores_com_dados,
                        erros = EXCLUDED.erros,
                        dados_json = EXCLUDED.dados_json
                """, (
                    pasta_uploads,
                    resultado.get('data_processamento', datetime.now().isoformat()),
                    resultado.get('total_entregadores', 0),
                    float(resultado.get('valor_total_geral', 0)),
                    resultado.get('total_arquivos', 0),
                    resultado.get('arquivos_sucesso', 0),
                    resultado.get('arquivos_com_erro', 0),
                    resultado.get('total_entregadores_cadastrados', 0),
                    resultado.get('entregadores_com_dados', 0),
                    json.dumps(resultado.get('erros', [])) if resultado.get('erros') else None,
                    dados_json_str
                ))
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO processamento_resultados 
                    (pasta_uploads, data_processamento, total_entregadores, valor_total_geral,
                     total_arquivos, arquivos_sucesso, arquivos_com_erro,
                     total_entregadores_cadastrados, entregadores_com_dados, erros, dados_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pasta_uploads,
                    resultado.get('data_processamento', datetime.now().isoformat()),
                    resultado.get('total_entregadores', 0),
                    float(resultado.get('valor_total_geral', 0)),
                    resultado.get('total_arquivos', 0),
                    resultado.get('arquivos_sucesso', 0),
                    resultado.get('arquivos_com_erro', 0),
                    resultado.get('total_entregadores_cadastrados', 0),
                    resultado.get('entregadores_com_dados', 0),
                    json.dumps(resultado.get('erros', [])) if resultado.get('erros') else None,
                    dados_json_str
                ))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Erro ao salvar processamento resultado: {e}")
            return False
        finally:
            conn.close()
    
    @staticmethod
    def carregar_processamento_resultado(pasta_uploads):
        """Carrega resultado de processamento do banco"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            is_pg = StorageService._is_postgresql(cursor)
            
            if is_pg:
                cursor.execute("""
                    SELECT * FROM processamento_resultados 
                    WHERE pasta_uploads = %s
                    ORDER BY data_processamento DESC
                    LIMIT 1
                """, (pasta_uploads,))
            else:
                cursor.execute("""
                    SELECT * FROM processamento_resultados 
                    WHERE pasta_uploads = ?
                    ORDER BY data_processamento DESC
                    LIMIT 1
                """, (pasta_uploads,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            if is_pg:
                result = dict(row)
            else:
                result = dict(row)
            
            # Deserializar JSON
            if 'dados_json' in result:
                result['dados_json'] = StorageService._deserialize_json(result['dados_json'])
            if 'erros' in result and result['erros']:
                try:
                    result['erros'] = json.loads(result['erros'])
                except:
                    pass
            
            return result
        except Exception as e:
            print(f"Erro ao carregar processamento resultado: {e}")
            return None
        finally:
            conn.close()
    
    # ==================== ARQUIVOS TEMPORÁRIOS ====================
    
    @staticmethod
    def salvar_arquivo_temp(token, pasta_uploads, dados_json, expires_hours=24):
        """Salva arquivo temporário no banco"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            is_pg = StorageService._is_postgresql(cursor)
            dados_json_str = StorageService._serialize_json(dados_json)
            expires_at = datetime.now() + timedelta(hours=expires_hours)
            
            if is_pg:
                cursor.execute("""
                    INSERT INTO processamento_arquivos_temp 
                    (token, pasta_uploads, dados_json, expires_at)
                    VALUES (%s, %s, %s::jsonb, %s)
                    ON CONFLICT (token) DO UPDATE SET
                        pasta_uploads = EXCLUDED.pasta_uploads,
                        dados_json = EXCLUDED.dados_json,
                        expires_at = EXCLUDED.expires_at
                """, (token, pasta_uploads, dados_json_str, expires_at))
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO processamento_arquivos_temp 
                    (token, pasta_uploads, dados_json, expires_at)
                    VALUES (?, ?, ?, ?)
                """, (token, pasta_uploads, dados_json_str, expires_at.isoformat()))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Erro ao salvar arquivo temp: {e}")
            return False
        finally:
            conn.close()
    
    @staticmethod
    def carregar_arquivo_temp(token):
        """Carrega arquivo temporário do banco"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            is_pg = StorageService._is_postgresql(cursor)
            now = datetime.now()
            
            if is_pg:
                cursor.execute("""
                    SELECT * FROM processamento_arquivos_temp 
                    WHERE token = %s AND (expires_at IS NULL OR expires_at > %s)
                """, (token, now))
            else:
                cursor.execute("""
                    SELECT * FROM processamento_arquivos_temp 
                    WHERE token = ? AND (expires_at IS NULL OR expires_at > ?)
                """, (token, now.isoformat()))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            if is_pg:
                result = dict(row)
            else:
                result = dict(row)
            
            # Deserializar JSON
            if 'dados_json' in result:
                result['dados_json'] = StorageService._deserialize_json(result['dados_json'])
            
            return result
        except Exception as e:
            print(f"Erro ao carregar arquivo temp: {e}")
            return None
        finally:
            conn.close()
    
    @staticmethod
    def limpar_arquivos_temp_expirados():
        """Remove arquivos temporários expirados"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            is_pg = StorageService._is_postgresql(cursor)
            now = datetime.now()
            
            if is_pg:
                cursor.execute("""
                    DELETE FROM processamento_arquivos_temp 
                    WHERE expires_at IS NOT NULL AND expires_at <= %s
                """, (now,))
            else:
                cursor.execute("""
                    DELETE FROM processamento_arquivos_temp 
                    WHERE expires_at IS NOT NULL AND expires_at <= ?
                """, (now.isoformat(),))
            
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            conn.rollback()
            print(f"Erro ao limpar arquivos temp: {e}")
            return 0
        finally:
            conn.close()

