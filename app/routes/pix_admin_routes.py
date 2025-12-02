"""
Rotas administrativas para gerenciamento de PIX
"""
from flask import render_template, request, send_file, redirect, url_for
from app.utils.auth_decorators import login_required, master_required
from app.models.database import get_db_connection, is_postgresql_connection
from datetime import datetime
import csv
import os
import tempfile
from app.utils.constants import (
    TEMPLATES_PIX,
    STATUS_PIX
)


# Queries SQL reutilizáveis
def _get_query_pix_aprovados(placeholder="?"):
    """Retorna query com placeholders corretos"""
    return f"""
    SELECT 
        h.id, h.chave_pix, h.tipo_de_chave_pix, h.data_registro, h.cpf as h_cpf, h.status,
        e.id_da_pessoa_entregadora, e.recebedor, e.cpf as e_cpf, e.subpraca
    FROM historico_pix h
    LEFT JOIN entregadores e 
        ON e.id_da_pessoa_entregadora = h.id_da_pessoa_entregadora
    WHERE h.status = {placeholder}
    ORDER BY h.data_registro DESC
"""

def _get_query_pix_todos(placeholder="?"):
    """Retorna query com placeholders corretos"""
    return f"""
    SELECT 
        h.id, h.chave_pix, h.tipo_de_chave_pix, h.data_registro, h.cpf as h_cpf, h.cnpj as h_cnpj, h.status,
        h.nome as h_nome, h.praca as h_praca,
        e.id_da_pessoa_entregadora, e.recebedor, e.cpf as e_cpf, e.cnpj as e_cnpj, e.subpraca
    FROM historico_pix h
    LEFT JOIN entregadores e ON e.id_da_pessoa_entregadora = h.id_da_pessoa_entregadora
    WHERE h.status IN ({placeholder}, {placeholder})
        AND (h.nome IS NOT NULL AND h.nome != '' OR h.praca IS NOT NULL AND h.praca != '')
    ORDER BY h.data_registro DESC
"""

def _get_query_pix_pendentes(placeholder="?"):
    """Retorna query com placeholders corretos"""
    return f"""
    SELECT h.id, h.chave_pix, h.tipo_de_chave_pix, h.data_registro, h.cpf as h_cpf,
           e.recebedor, e.cpf as e_cpf, e.subpraca
    FROM historico_pix h
    LEFT JOIN entregadores e 
        ON e.id_da_pessoa_entregadora = h.id_da_pessoa_entregadora
    WHERE h.status = {placeholder}
    ORDER BY h.data_registro DESC
"""


def _aplicar_filtros(registros, busca, filtro_tipo, filtro_praca, filtro_data, filtro_ultimas):
    """Aplica filtros em memória aos registros"""
    if busca:
        termo = busca.lower()
        registros = [
            r for r in registros
            if termo in (r.get("recebedor") or "").lower()
            or termo in (r.get("e_cpf") or r.get("h_cpf") or "")
            or termo in (r.get("chave_pix") or "").lower()
        ]
    
    if filtro_tipo:
        registros = [r for r in registros if r.get("tipo_de_chave_pix") == filtro_tipo]
    
    if filtro_praca:
        registros = [r for r in registros if (r.get("h_praca") or "") == filtro_praca]
    
    if filtro_data:
        def _formatar_data(data):
            """Converte data para string no formato YYYY-MM-DD"""
            if data is None:
                return ""
            if isinstance(data, datetime):
                return data.strftime("%Y-%m-%d")
            # Se já for string, retornar os primeiros 10 caracteres
            return str(data)[:10] if data else ""
        
        registros = [r for r in registros if _formatar_data(r.get("data_registro")) == filtro_data]
    
    if filtro_ultimas == "1":
        ultimos = {}
        for r in registros:
            id_ent = r.get("id_da_pessoa_entregadora")
            if id_ent and id_ent not in ultimos:
                ultimos[id_ent] = r
        registros = list(ultimos.values())
    
    return registros


def init_pix_admin_routes(app):
    
    @app.route("/admin/bancario", methods=["GET"])
    @login_required
    def admin_bancario():
        busca = (request.args.get("busca") or "").strip().lower()
        filtro_tipo = request.args.get("tipo", "")
        filtro_praca = request.args.get("praca", "")
        filtro_data = request.args.get("data", "")
        filtro_ultimas = request.args.get("ultimas", "")
        
        from app.models.database import get_db_cursor, get_db_placeholder
        from app.utils.db_helpers import db_connection, row_to_dict
        from app.utils.route_helpers import normalize_cpf
        
        # Buscar tanto aprovados quanto pendentes, mas apenas os que vieram do formulário público
        with db_connection() as conn:
            placeholder = get_db_placeholder(conn)
            cursor = get_db_cursor(conn)
            query = _get_query_pix_todos(placeholder)
            cursor.execute(query, (STATUS_PIX['APROVADO'], STATUS_PIX['PENDENTE']))
            registros_raw = cursor.fetchall()
        
        # Fazer JOIN por CPF em Python (já que SQLite não suporta múltiplos REPLACE aninhados)
        # Buscar todos os entregadores para fazer match por CPF
        with db_connection() as conn:
            cursor = get_db_cursor(conn)
            cursor.execute("SELECT id_da_pessoa_entregadora, recebedor, cpf, subpraca FROM entregadores")
            rows = cursor.fetchall()
        
        # Converter para dicionários
        todos_entregadores = {}
        for e in rows:
            e_dict = row_to_dict(e)
            if e_dict:
                cpf_normalizado = normalize_cpf(e_dict.get('cpf') or '')
                if cpf_normalizado:
                    todos_entregadores[cpf_normalizado] = e_dict
        
        # Processar registros e fazer match por CPF
        registros = []
        for r in registros_raw:
            r_dict = dict(r)
            # Normalizar CPF: usar h_cpf se existir, senão e_cpf
            r_dict['cpf'] = r_dict.get('h_cpf') or r_dict.get('e_cpf') or ''
            # Normalizar CNPJ: usar h_cnpj se existir, senão e_cnpj
            r_dict['cnpj'] = r_dict.get('h_cnpj') or r_dict.get('e_cnpj') or ''
            
            # Se não tiver entregador vinculado por ID, tentar por CPF
            if not r_dict.get('id_da_pessoa_entregadora') and r_dict.get('cpf'):
                cpf_norm = normalize_cpf(r_dict['cpf'])
                if cpf_norm in todos_entregadores:
                    entregador = todos_entregadores[cpf_norm]
                    r_dict['id_da_pessoa_entregadora'] = entregador['id_da_pessoa_entregadora']
                    r_dict['recebedor'] = entregador['recebedor']
                    r_dict['e_cpf'] = entregador['cpf']
                    r_dict['subpraca'] = entregador['subpraca']
            
            registros.append(r_dict)
        
        registros = _aplicar_filtros(
            registros, busca, filtro_tipo, filtro_praca, filtro_data, filtro_ultimas
        )
        
        # Coletar todas as praças únicas dos registros
        pracas = sorted({r.get("h_praca") for r in registros if r.get("h_praca")})
        
        return render_template(
            TEMPLATES_PIX['admin_lista'],
            registros=registros,
            pracas=pracas,
            filtro_busca=busca,
            filtro_tipo=filtro_tipo,
            filtro_praca=filtro_praca,
            filtro_data=filtro_data,
            filtro_ultimas=filtro_ultimas
        )
    
    @app.route("/admin/bancario/exportar", methods=["GET"])
    def admin_bancario_exportar():
        conn = get_db_connection()
        from app.models.database import is_postgresql_connection
        is_postgresql = is_postgresql_connection(conn)
        placeholder = "%s" if is_postgresql else "?"
        
        if is_postgresql:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            import sqlite3
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
        
        query = _get_query_pix_aprovados(placeholder)
        cursor.execute(query, (STATUS_PIX['APROVADO'],))
        registros = [dict(r) for r in cursor.fetchall()]
        conn.close()
        
        # Normalizar CPF: usar h_cpf se existir, senão e_cpf
        for r in registros:
            r['cpf'] = r.get('h_cpf') or r.get('e_cpf') or ''
            if not r.get('recebedor') and r.get('cpf'):
                r['recebedor'] = 'Entregador não cadastrado ainda'
        
        # Usar diretório temporário
        temp_dir = tempfile.gettempdir()
        filename = f"pix_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path = os.path.join(temp_dir, filename)
        
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Nome", "CPF", "Subpraça", "Tipo", "Chave", "Data Registro"
            ])
            for r in registros:
                writer.writerow([
                    r.get("recebedor") or "",
                    r.get("cpf") or "",
                    r.get("subpraca") or "",
                    r.get("tipo_de_chave_pix") or "",
                    r.get("chave_pix") or "",
                    r.get("data_registro") or ""
                ])
        
        return send_file(path, as_attachment=True, download_name="pix_export.csv")
    
    @app.route("/admin/bancario/logs", methods=["GET"])
    @master_required
    def admin_pix_logs():
        # Buscar parâmetros de filtro
        filtro_busca = request.args.get("busca", "").strip()
        filtro_motivo = request.args.get("motivo", "")
        data_inicio = request.args.get("inicio", "")
        data_fim = request.args.get("fim", "")
        
        from app.models.database import get_db_connection, is_postgresql_connection, get_db_cursor, get_db_placeholder
        from app.utils.db_helpers import db_connection, row_to_dict
        
        with db_connection() as conn:
            placeholder = get_db_placeholder(conn)
            cursor = get_db_cursor(conn)
            
            # Construir query com filtros
            where_conditions = []
            params = []
            
            if filtro_busca:
                where_conditions.append(f"(LOWER(cpf) LIKE {placeholder} OR LOWER(chave_pix) LIKE {placeholder} OR LOWER(motivo) LIKE {placeholder})")
                busca_term = f"%{filtro_busca.lower()}%"
                params.extend([busca_term, busca_term, busca_term])
            
            if filtro_motivo:
                where_conditions.append(f"motivo = {placeholder}")
                params.append(filtro_motivo)
            
            if data_inicio:
                where_conditions.append(f"DATE(data_hora) >= {placeholder}")
                params.append(data_inicio)
            
            if data_fim:
                where_conditions.append(f"DATE(data_hora) <= {placeholder}")
                params.append(data_fim)
            
            # Montar query final
            query = "SELECT * FROM pix_logs"
            if where_conditions:
                query += " WHERE " + " AND ".join(where_conditions)
            query += " ORDER BY data_hora DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            logs = []
            for row in rows:
                log_dict = row_to_dict(row)
                if log_dict:
                    # Formatar data_hora se for datetime
                    if 'data_hora' in log_dict and isinstance(log_dict['data_hora'], datetime):
                        log_dict['data_hora'] = log_dict['data_hora'].strftime("%Y-%m-%d %H:%M:%S")
                    logs.append(log_dict)
            
            # Buscar motivos únicos para o dropdown
            cursor.execute("SELECT DISTINCT motivo FROM pix_logs WHERE motivo IS NOT NULL AND motivo != '' ORDER BY motivo")
            motivos_rows = cursor.fetchall()
            motivos = []
            for row in motivos_rows:
                motivo = None
                if isinstance(row, (tuple, list)) and len(row) > 0:
                    motivo = row[0]
                elif isinstance(row, dict):
                    motivo = row.get('motivo')
                else:
                    row_dict = row_to_dict(row)
                    if row_dict:
                        motivo = row_dict.get('motivo')
                
                if motivo and motivo not in motivos:
                    motivos.append(motivo)
        
        return render_template(
            TEMPLATES_PIX['admin_logs'],
            logs=logs,
            filtro_busca=filtro_busca,
            filtro_motivo=filtro_motivo,
            data_inicio=data_inicio,
            data_fim=data_fim,
            motivos=motivos
        )
    
    @app.route("/admin/bancario/logs/exportar", methods=["GET"])
    @master_required
    def admin_pix_logs_exportar():
        conn = get_db_connection()
        is_postgresql = is_postgresql_connection(conn)
        
        if is_postgresql:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            import sqlite3
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
        
        cursor.execute("""
            SELECT cpf, chave_pix, tipo_chave, motivo, ip, user_agent, data_hora
            FROM pix_logs
            ORDER BY data_hora DESC
        """)
        logs = [dict(r) for r in cursor.fetchall()]
        conn.close()
        
        # Usar diretório temporário
        filename = f"pix_logs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path = os.path.join(tempfile.gettempdir(), filename)
        
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["CPF", "Chave", "Tipo", "Motivo", "IP", "User Agent", "Data"])
            for r in logs:
                writer.writerow([
                    r.get("cpf"), r.get("chave_pix"), r.get("tipo_chave"),
                    r.get("motivo"), r.get("ip"), r.get("user_agent"), r.get("data_hora")
                ])
        
        return send_file(path, as_attachment=True, download_name="pix_logs_export.csv")
    
    @app.route("/admin/bancario/aprovacao", methods=["GET"])
    def admin_pix_aprovacao():
        conn = get_db_connection()
        from app.models.database import is_postgresql_connection
        is_postgresql = is_postgresql_connection(conn)
        placeholder = "%s" if is_postgresql else "?"
        
        if is_postgresql:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            import sqlite3
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
        
        query = _get_query_pix_pendentes(placeholder)
        cursor.execute(query, (STATUS_PIX['PENDENTE'],))
        pendentes = [dict(r) for r in cursor.fetchall()]
        conn.close()
        
        # Normalizar CPF: usar h_cpf se existir, senão e_cpf
        for p in pendentes:
            p['cpf'] = p.get('h_cpf') or p.get('e_cpf') or ''
        
        return render_template(TEMPLATES_PIX['admin_aprovacao'], pendentes=pendentes)
    
    @app.route("/admin/bancario/aprovar/<int:id>", methods=["POST"])
    def aprov_pix(id):
        conn = get_db_connection()
        is_postgresql = is_postgresql_connection(conn)
        placeholder = "%s" if is_postgresql else "?"
        
        cursor = conn.cursor()
        cursor.execute(f"""
            UPDATE historico_pix
            SET status = {placeholder}
            WHERE id = {placeholder}
        """, (STATUS_PIX['APROVADO'], id))
        conn.commit()
        conn.close()
        
        return redirect(url_for("admin_pix_aprovacao"))
    
    @app.route("/admin/bancario/excluir/<int:id>", methods=["POST"])
    def excluir_pix(id):
        from flask import flash
        
        conn = get_db_connection()
        from app.models.database import is_postgresql_connection
        is_postgresql = is_postgresql_connection(conn)
        placeholder = "%s" if is_postgresql else "?"
        
        if is_postgresql:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            import sqlite3
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
        
        # Buscar informações antes de excluir (CPF para limpar logs)
        cursor.execute(f"SELECT chave_pix, cpf FROM historico_pix WHERE id = {placeholder}", (id,))
        registro = cursor.fetchone()
        
        if registro:
            if isinstance(registro, dict):
                cpf_registro = registro.get('cpf')
            else:
                cpf_registro = registro[1] if len(registro) > 1 else None
            
            # Excluir o registro do historico_pix
            cursor.execute(f"DELETE FROM historico_pix WHERE id = {placeholder}", (id,))
            
            # Limpar logs do pix_logs para permitir novo envio do formulário
            if cpf_registro:
                cursor.execute(f"DELETE FROM pix_logs WHERE cpf = {placeholder}", (cpf_registro,))
            
            conn.commit()
            flash(f"Chave PIX excluída com sucesso! O entregador poderá usar o formulário novamente.", "pix_success")
        else:
            flash(f"Solicitação não encontrada.", "pix_error")
        
        conn.close()
        return redirect(url_for("admin_bancario"))
