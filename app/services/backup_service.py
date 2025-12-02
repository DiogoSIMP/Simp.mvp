"""
Serviço de backup diário das informações críticas do sistema
Backup automático às 22h00 de:
- Cadastros de entregadores
- Solicitações de adiantamento (quem solicitou diário)
- Forms bancários (histórico PIX)
"""
from datetime import datetime, date
from app.models.database import get_db_connection, is_postgresql_connection, get_db_cursor, get_db_placeholder
from app.utils.db_helpers import row_to_dict


def executar_backup_diario():
    """
    Executa backup diário de todas as tabelas críticas
    Retorna dict com estatísticas do backup
    """
    conn = get_db_connection()
    is_postgresql = is_postgresql_connection(conn)
    cursor = get_db_cursor(conn)
    placeholder = get_db_placeholder(conn)
    
    hoje = date.today()
    hoje_str = hoje.isoformat() if not is_postgresql else hoje
    
    stats = {
        'backup_date': hoje_str,
        'total_entregadores': 0,
        'total_solicitacoes': 0,
        'total_historico_pix': 0,
        'status': 'sucesso',
        'mensagem': 'Backup executado com sucesso'
    }
    
    try:
        # Verificar se já existe backup para hoje
        if is_postgresql:
            cursor.execute("""
                SELECT id FROM backup_logs 
                WHERE backup_date = %s
            """, (hoje,))
        else:
            cursor.execute("""
                SELECT id FROM backup_logs 
                WHERE backup_date = ?
            """, (hoje_str,))
        
        backup_existente = cursor.fetchone()
        if backup_existente:
            print(f"⚠️ Backup para {hoje_str} já existe. Pulando...")
            stats['mensagem'] = 'Backup já executado hoje'
            conn.close()
            return stats
        
        # 1. BACKUP DE ENTREGADORES (cadastro)
        print("📦 Fazendo backup de entregadores...")
        if is_postgresql:
            cursor.execute("""
                INSERT INTO backup_entregadores 
                (backup_date, id_da_pessoa_entregadora, recebedor, email, cpf, cnpj, 
                 praca, subpraca, emissor, status)
                SELECT %s, id_da_pessoa_entregadora, recebedor, email, cpf, cnpj,
                       praca, subpraca, emissor, status
                FROM entregadores
                ON CONFLICT (backup_date, id_da_pessoa_entregadora) DO NOTHING
            """, (hoje,))
        else:
            cursor.execute("""
                INSERT OR IGNORE INTO backup_entregadores 
                (backup_date, id_da_pessoa_entregadora, recebedor, email, cpf, cnpj, 
                 praca, subpraca, emissor, status)
                SELECT ?, id_da_pessoa_entregadora, recebedor, email, cpf, cnpj,
                       praca, subpraca, emissor, status
                FROM entregadores
            """, (hoje_str,))
        
        stats['total_entregadores'] = cursor.rowcount
        
        # 2. BACKUP DE SOLICITAÇÕES DE ADIANTAMENTO (quem solicitou diário)
        print("📦 Fazendo backup de solicitações de adiantamento...")
        if is_postgresql:
            cursor.execute("""
                INSERT INTO backup_solicitacoes_adiantamento 
                (backup_date, original_id, email, nome, cpf, praca, valor_informado, 
                 concorda, data_envio, cpf_bate, dados_json)
                SELECT %s, id, email, nome, cpf, praca, valor_informado, 
                       concorda, data_envio, cpf_bate, dados_json
                FROM solicitacoes_adiantamento
                ON CONFLICT (backup_date, original_id) DO NOTHING
            """, (hoje,))
        else:
            cursor.execute("""
                INSERT OR IGNORE INTO backup_solicitacoes_adiantamento 
                (backup_date, original_id, email, nome, cpf, praca, valor_informado, 
                 concorda, data_envio, cpf_bate, dados_json)
                SELECT ?, id, email, nome, cpf, praca, valor_informado, 
                       concorda, data_envio, cpf_bate, dados_json
                FROM solicitacoes_adiantamento
            """, (hoje_str,))
        
        stats['total_solicitacoes'] = cursor.rowcount
        
        # 3. BACKUP DE HISTÓRICO PIX (forms bancários)
        print("📦 Fazendo backup de histórico PIX...")
        if is_postgresql:
            cursor.execute("""
                INSERT INTO backup_historico_pix 
                (backup_date, original_id, id_da_pessoa_entregadora, cpf, chave_pix, 
                 tipo_de_chave_pix, data_registro, status, nome, avaliacao, praca, cnpj, email)
                SELECT %s, id, id_da_pessoa_entregadora, cpf, chave_pix, 
                       tipo_de_chave_pix, data_registro, status, nome, avaliacao, praca, cnpj, email
                FROM historico_pix
                ON CONFLICT (backup_date, original_id) DO NOTHING
            """, (hoje,))
        else:
            cursor.execute("""
                INSERT OR IGNORE INTO backup_historico_pix 
                (backup_date, original_id, id_da_pessoa_entregadora, cpf, chave_pix, 
                 tipo_de_chave_pix, data_registro, status, nome, avaliacao, praca, cnpj, email)
                SELECT ?, id, id_da_pessoa_entregadora, cpf, chave_pix, 
                       tipo_de_chave_pix, data_registro, status, nome, avaliacao, praca, cnpj, email
                FROM historico_pix
            """, (hoje_str,))
        
        stats['total_historico_pix'] = cursor.rowcount
        
        # 4. REGISTRAR LOG DO BACKUP
        if is_postgresql:
            cursor.execute("""
                INSERT INTO backup_logs 
                (backup_date, total_entregadores, total_solicitacoes, total_historico_pix, status, mensagem)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (backup_date) DO UPDATE SET
                    total_entregadores = EXCLUDED.total_entregadores,
                    total_solicitacoes = EXCLUDED.total_solicitacoes,
                    total_historico_pix = EXCLUDED.total_historico_pix,
                    status = EXCLUDED.status,
                    mensagem = EXCLUDED.mensagem
            """, (
                hoje,
                stats['total_entregadores'],
                stats['total_solicitacoes'],
                stats['total_historico_pix'],
                stats['status'],
                stats['mensagem']
            ))
        else:
            cursor.execute("""
                INSERT OR REPLACE INTO backup_logs 
                (backup_date, total_entregadores, total_solicitacoes, total_historico_pix, status, mensagem)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                hoje_str,
                stats['total_entregadores'],
                stats['total_solicitacoes'],
                stats['total_historico_pix'],
                stats['status'],
                stats['mensagem']
            ))
        
        conn.commit()
        
        print(f"✅ Backup diário concluído:")
        print(f"   - Entregadores: {stats['total_entregadores']}")
        print(f"   - Solicitações: {stats['total_solicitacoes']}")
        print(f"   - Histórico PIX: {stats['total_historico_pix']}")
        
        return stats
        
    except Exception as e:
        conn.rollback()
        error_msg = f"Erro ao executar backup: {str(e)}"
        print(f"❌ {error_msg}")
        stats['status'] = 'erro'
        stats['mensagem'] = error_msg
        
        # Registrar erro no log
        try:
            if is_postgresql:
                cursor.execute("""
                    INSERT INTO backup_logs 
                    (backup_date, total_entregadores, total_solicitacoes, total_historico_pix, status, mensagem)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (backup_date) DO UPDATE SET
                        status = EXCLUDED.status,
                        mensagem = EXCLUDED.mensagem
                """, (hoje, 0, 0, 0, 'erro', error_msg))
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO backup_logs 
                    (backup_date, total_entregadores, total_solicitacoes, total_historico_pix, status, mensagem)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (hoje_str, 0, 0, 0, 'erro', error_msg))
            conn.commit()
        except Exception as log_error:
            print(f"❌ Erro ao registrar log de backup: {log_error}")
        
        return stats
        
    finally:
        conn.close()


def obter_historico_backups(limite=30):
    """
    Retorna histórico dos últimos backups
    """
    conn = get_db_connection()
    is_postgresql = is_postgresql_connection(conn)
    cursor = get_db_cursor(conn)
    placeholder = get_db_placeholder(conn)
    
    try:
        if is_postgresql:
            cursor.execute("""
                SELECT backup_date, total_entregadores, total_solicitacoes, 
                       total_historico_pix, status, mensagem, created_at
                FROM backup_logs
                ORDER BY backup_date DESC
                LIMIT %s
            """, (limite,))
        else:
            cursor.execute("""
                SELECT backup_date, total_entregadores, total_solicitacoes, 
                       total_historico_pix, status, mensagem, created_at
                FROM backup_logs
                ORDER BY backup_date DESC
                LIMIT ?
            """, (limite,))
        
        backups = []
        for row in cursor.fetchall():
            backup = row_to_dict(row)
            backups.append(backup)
        
        return backups
        
    except Exception as e:
        print(f"❌ Erro ao obter histórico de backups: {e}")
        return []
    finally:
        conn.close()

