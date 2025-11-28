"""
Rotas administrativas para gerenciamento de PIX
"""
from flask import render_template, request, send_file, redirect, url_for
from app.utils.auth_decorators import login_required, master_required
from app.models.database import get_db_connection
from datetime import datetime
import csv
from app.utils.constants import (
    TEMPLATES_PIX,
    STATUS_PIX
)


# Queries SQL reutilizáveis
QUERY_PIX_APROVADOS = """
    SELECT 
        h.id, h.chave_pix, h.tipo_de_chave_pix, h.data_registro, h.cpf as h_cpf, h.status,
        e.id_da_pessoa_entregadora, e.recebedor, e.cpf as e_cpf, e.subpraca
    FROM historico_pix h
    LEFT JOIN entregadores e 
        ON e.id_da_pessoa_entregadora = h.id_da_pessoa_entregadora
    WHERE h.status = ?
    ORDER BY h.data_registro DESC
"""

QUERY_PIX_TODOS = """
    SELECT 
        h.id, h.chave_pix, h.tipo_de_chave_pix, h.data_registro, h.cpf as h_cpf, h.cnpj as h_cnpj, h.status,
        h.nome as h_nome, h.praca as h_praca,
        e.id_da_pessoa_entregadora, e.recebedor, e.cpf as e_cpf, e.cnpj as e_cnpj, e.subpraca
    FROM historico_pix h
    LEFT JOIN entregadores e ON e.id_da_pessoa_entregadora = h.id_da_pessoa_entregadora
    WHERE h.status IN (?, ?)
        AND (h.nome IS NOT NULL AND h.nome != '' OR h.praca IS NOT NULL AND h.praca != '')
    ORDER BY h.data_registro DESC
"""

QUERY_PIX_PENDENTES = """
    SELECT h.id, h.chave_pix, h.tipo_de_chave_pix, h.data_registro, h.cpf as h_cpf,
           e.recebedor, e.cpf as e_cpf, e.subpraca
    FROM historico_pix h
    LEFT JOIN entregadores e 
        ON e.id_da_pessoa_entregadora = h.id_da_pessoa_entregadora
    WHERE h.status = ?
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
        registros = [r for r in registros if (r.get("data_registro") or "")[:10] == filtro_data]
    
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        # Buscar tanto aprovados quanto pendentes, mas apenas os que vieram do formulário público
        # (têm nome ou praca preenchidos)
        cursor.execute(QUERY_PIX_TODOS, (STATUS_PIX['APROVADO'], STATUS_PIX['PENDENTE']))
        registros_raw = cursor.fetchall()
        conn.close()
        
        # Fazer JOIN por CPF em Python (já que SQLite não suporta múltiplos REPLACE aninhados)
        from app.utils.route_helpers import normalize_cpf
        
        # Buscar todos os entregadores para fazer match por CPF
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_da_pessoa_entregadora, recebedor, cpf, subpraca FROM entregadores")
        todos_entregadores = {normalize_cpf(e['cpf'] or ''): e for e in cursor.fetchall() if normalize_cpf(e['cpf'] or '')}
        conn.close()
        
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
        cursor = conn.cursor()
        cursor.execute(QUERY_PIX_APROVADOS, (STATUS_PIX['APROVADO'],))
        registros = [dict(r) for r in cursor.fetchall()]
        conn.close()
        
        # Normalizar CPF: usar h_cpf se existir, senão e_cpf
        for r in registros:
            r['cpf'] = r.get('h_cpf') or r.get('e_cpf') or ''
            if not r.get('recebedor') and r.get('cpf'):
                r['recebedor'] = 'Entregador não cadastrado ainda'
        
        path = "pix_export.csv"
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
        
        return send_file(path, as_attachment=True)
    
    @app.route("/admin/bancario/logs", methods=["GET"])
    @master_required
    def admin_pix_logs():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pix_logs ORDER BY data_hora DESC")
        logs = [dict(r) for r in cursor.fetchall()]
        conn.close()
        
        return render_template(TEMPLATES_PIX['admin_logs'], logs=logs)
    
    @app.route("/admin/bancario/logs/exportar", methods=["GET"])
    @master_required
    def admin_pix_logs_exportar():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cpf, chave_pix, tipo_chave, motivo, ip, user_agent, data_hora
            FROM pix_logs
            ORDER BY data_hora DESC
        """)
        logs = cursor.fetchall()
        conn.close()
        
        path = "pix_logs_export.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["CPF", "Chave", "Tipo", "Motivo", "IP", "User Agent", "Data"])
            for r in logs:
                writer.writerow([
                    r.get("cpf"), r.get("chave_pix"), r.get("tipo_chave"),
                    r.get("motivo"), r.get("ip"), r.get("user_agent"), r.get("data_hora")
                ])
        
        return send_file(path, as_attachment=True)
    
    @app.route("/admin/bancario/aprovacao", methods=["GET"])
    def admin_pix_aprovacao():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(QUERY_PIX_PENDENTES, (STATUS_PIX['PENDENTE'],))
        pendentes = [dict(r) for r in cursor.fetchall()]
        conn.close()
        
        # Normalizar CPF: usar h_cpf se existir, senão e_cpf
        for p in pendentes:
            p['cpf'] = p.get('h_cpf') or p.get('e_cpf') or ''
        
        return render_template(TEMPLATES_PIX['admin_aprovacao'], pendentes=pendentes)
    
    @app.route("/admin/bancario/aprovar/<int:id>", methods=["POST"])
    def aprov_pix(id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE historico_pix
            SET status = ?
            WHERE id = ?
        """, (STATUS_PIX['APROVADO'], id))
        conn.commit()
        conn.close()
        
        return redirect(url_for("admin_pix_aprovacao"))
    
    @app.route("/admin/bancario/excluir/<int:id>", methods=["POST"])
    def excluir_pix(id):
        from flask import flash
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar informações antes de excluir (CPF para limpar logs)
        cursor.execute("SELECT chave_pix, cpf FROM historico_pix WHERE id = ?", (id,))
        registro = cursor.fetchone()
        
        if registro:
            cpf_registro = registro['cpf']
            
            # Excluir o registro do historico_pix
            cursor.execute("DELETE FROM historico_pix WHERE id = ?", (id,))
            
            # Limpar logs do pix_logs para permitir novo envio do formulário
            if cpf_registro:
                cursor.execute("DELETE FROM pix_logs WHERE cpf = ?", (cpf_registro,))
            
            conn.commit()
            flash(f"Chave PIX excluída com sucesso! O entregador poderá usar o formulário novamente.", "pix_success")
        else:
            flash(f"Solicitação não encontrada.", "pix_error")
        
        conn.close()
        return redirect(url_for("admin_bancario"))
