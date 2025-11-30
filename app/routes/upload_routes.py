"""
Rotas para upload e processamento de arquivos CSV/XLSX
"""
from flask import render_template, request, redirect, url_for, flash, send_file, session
import os
from app.utils.auth_decorators import login_required, master_required, adm_or_master_required
from datetime import datetime, timedelta
from app.services.processador_csv_service import ProcessadorCSVService
from config import Config
from app.models.database import formatar_nome
from app.services.upload_service import UploadService
import pandas as pd
import uuid
import json
from app.utils.path_manager import get_week_folder
from flask import jsonify
from app.utils.constants import (
    TEMPLATES_UPLOAD,
    MESSAGES,
    PAGINATION_PER_PAGE_UPLOAD,
    ARQUIVO_ULTIMO_RESULTADO,
    ARQUIVO_ULTIMO_CONSOLIDADO,
    ARQUIVO_CONSOLIDADO_DIARIO,
    FORMATO_DATA_ARQUIVO
)
from app.utils.route_helpers import (
    paginate_items,
    get_page_from_request,
    get_flash_message
)
from app.utils.form_control import form_is_open
from app.services.storage_service import StorageService


UPLOAD_HISTORY_FILE = "uploads_history.json"
UPLOAD_RETENTION_HOURS = 8
HISTORICO_MAX_REGISTROS = 75


def _normalizar_nomes_consolidado(consolidado_dict):
    """Normaliza nomes no consolidado"""
    import math
    
    for row in consolidado_dict:
        if row.get('recebedor'):
            row['recebedor'] = formatar_nome(row['recebedor'])
        # Tratar subpracas - remover NaN e valores inválidos
        if 'subpracas' in row:
            subpracas = row['subpracas']
            # Verificar se é NaN ou valor inválido
            is_invalid = False
            try:
                if isinstance(subpracas, float) and math.isnan(subpracas):
                    is_invalid = True
                elif pd.isna(subpracas):
                    is_invalid = True
                elif str(subpracas).lower() in ['nan', 'none', '']:
                    is_invalid = True
                elif isinstance(subpracas, str) and subpracas.strip() == '':
                    is_invalid = True
            except (TypeError, ValueError):
                # Se não conseguir verificar, considera inválido se for string vazia
                if not subpracas or str(subpracas).strip() == '':
                    is_invalid = True
            
            if is_invalid:
                row['subpracas'] = "-"
    return consolidado_dict


def _get_historico_path(pasta_uploads):
    """Mantido para compatibilidade, mas agora usa banco"""
    return os.path.join(pasta_uploads, UPLOAD_HISTORY_FILE)


def _carregar_historico_uploads(pasta_uploads):
    """Carrega histórico de uploads do banco de dados (PostgreSQL)"""
    try:
        # Carregar do banco de dados
        uploads_db = StorageService.carregar_upload_history(pasta_uploads, HISTORICO_MAX_REGISTROS)
        if uploads_db:
            # Converter formato do banco para formato esperado
            uploads = []
            for item in uploads_db:
                dados_json = item.get('dados_json', {})
                uploads.append({
                    "id": item.get('lote_id', ''),
                    "arquivos": dados_json.get('arquivos', []),
                    "titulo": item.get('titulo', 'Upload'),
                    "total_entregadores": item.get('total_entregadores', 0),
                    "valor_total": float(item.get('valor_total', 0)),
                    "arquivos_sucesso": dados_json.get('arquivos_sucesso', 0),
                    "arquivos_com_erro": dados_json.get('arquivos_com_erro', 0),
                    "qtd_erros": dados_json.get('qtd_erros', 0),
                    "criado_em": item.get('data_upload', ''),
                    "criado_em_ts": None,  # Será calculado se necessário
                })
            return uploads
        return []
    except Exception as e:
        print(f"❌ Erro ao carregar histórico do banco: {e}")
        # Não usar fallback JSON - retornar vazio
        return []


def _salvar_historico_uploads(pasta_uploads, uploads):
    """Salva histórico de uploads no banco de dados"""
    try:
        # Salvar cada upload no banco
        for upload in uploads[:HISTORICO_MAX_REGISTROS]:
            lote_id = upload.get('id', uuid.uuid4().hex)
            dados_json = {
                'arquivos': upload.get('arquivos', []),
                'arquivos_sucesso': upload.get('arquivos_sucesso', 0),
                'arquivos_com_erro': upload.get('arquivos_com_erro', 0),
                'qtd_erros': upload.get('qtd_erros', 0),
            }
            
            # Converter timestamp se existir
            data_upload = datetime.utcnow()
            if upload.get('criado_em_ts'):
                data_upload = datetime.utcfromtimestamp(upload['criado_em_ts'])
            elif upload.get('criado_em'):
                try:
                    data_upload = datetime.fromisoformat(upload['criado_em'].replace('Z', '+00:00'))
                except:
                    pass
            
            StorageService.salvar_upload_history(
                lote_id=lote_id,
                titulo=upload.get('titulo', 'Upload'),
                data_upload=data_upload,
                total_arquivos=len(upload.get('arquivos', [])),
                total_entregadores=upload.get('total_entregadores', 0),
                valor_total=upload.get('valor_total', 0),
                pasta_uploads=pasta_uploads,
                dados_json=dados_json
            )
        print(f"✅ Histórico de uploads salvo no banco de dados")
    except Exception as e:
        print(f"❌ Erro ao salvar histórico no banco: {e}")
        # Não usar fallback JSON - forçar correção do banco
        raise


def _gerar_titulo_lote(arquivo_nome):
    base = os.path.splitext(os.path.basename(arquivo_nome))[0]
    partes = base.split('_', 2)
    if len(partes) >= 3:
        return partes[2].replace('-', ' ').title()
    return base.replace('_', ' ').title()


def _registrar_historico_upload(pasta_uploads, arquivos_salvos, resumo_resultado):
    uploads = _carregar_historico_uploads(pasta_uploads)
    agora = datetime.utcnow()
    arquivos_basename = [os.path.basename(a) for a in arquivos_salvos]
    entry = {
        "id": uuid.uuid4().hex,
        "arquivos": arquivos_basename,
        "titulo": _gerar_titulo_lote(arquivos_basename[0]) if arquivos_basename else "Upload",
        "total_entregadores": resumo_resultado.get('total_entregadores', 0),
        "valor_total": float(resumo_resultado.get('valor_total_geral', 0)),
        "arquivos_sucesso": resumo_resultado.get('arquivos_sucesso', len(arquivos_basename)),
        "arquivos_com_erro": resumo_resultado.get('arquivos_com_erro', 0),
        "qtd_erros": len(resumo_resultado.get('erros') or []),
        "criado_em": agora.isoformat() + "Z",
        "criado_em_ts": agora.timestamp(),
    }
    uploads.insert(0, entry)
    _salvar_historico_uploads(pasta_uploads, uploads)


def _formatar_tempo_relativo(dt, agora=None):
    if not dt:
        return ""
    agora = agora or datetime.utcnow()
    diff = agora - dt
    segundos = diff.total_seconds()
    if segundos < 60:
        return "agora"
    if segundos < 3600:
        minutos = int(segundos // 60)
        return f"{minutos} min atrás"
    if segundos < 86400:
        horas = int(segundos // 3600)
        return f"{horas} h atrás"
    dias = int(segundos // 86400)
    return f"{dias} dia(s) atrás"


def _obter_historico_para_template(pasta_uploads):
    uploads = _carregar_historico_uploads(pasta_uploads)
    agora = datetime.utcnow()
    historico = []
    for lote in uploads:
        ts = lote.get('criado_em_ts')
        dt = datetime.utcfromtimestamp(ts) if ts else None
        descricao_completa = ", ".join(lote.get('arquivos', []))
        descricao_resumida = ", ".join(lote.get('arquivos', [])[:2])
        restante = max(len(lote.get('arquivos', [])) - 2, 0)
        if restante > 0:
            descricao_resumida += f" +{restante}"
        historico.append({
            **lote,
            "tem_erro": (lote.get('arquivos_com_erro', 0) or lote.get('qtd_erros', 0)),
            "criado_em_display": dt.strftime('%d/%m/%Y %H:%M') if dt else "-",
            "tempo_relativo": _formatar_tempo_relativo(dt, agora) if dt else "",
            "descricao_resumida": descricao_resumida,
            "descricao_completa": descricao_completa,
            "arquivos_total": len(lote.get('arquivos', [])),
        })
    return historico


def _resultado_dentro_do_prazo(resultado_json, limite_horas=UPLOAD_RETENTION_HOURS):
    if not resultado_json:
        return False
    data_str = resultado_json.get('data_processamento')
    if not data_str:
        return False
    data_proc = None
    for fmt in ('%d/%m/%Y %H:%M', '%Y-%m-%d %H:%M:%S'):
        try:
            data_proc = datetime.strptime(data_str, fmt)
            break
        except ValueError:
            data_proc = None
    if not data_proc:
        return False
    return datetime.utcnow() - data_proc <= timedelta(hours=limite_horas)


def _processar_consolidado_diario(df_completo, data_hoje):
    """
    Processa consolidado diário baseado nas solicitações do formulário do dia
    Retorna DataFrame com apenas os entregadores que solicitaram no dia
    """
    from app.models.database import get_db_connection
    from app.utils.route_helpers import normalize_cpf
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Buscar solicitações do dia atual
    cursor.execute("""
        SELECT DISTINCT s.cpf, s.nome, e.id_da_pessoa_entregadora
        FROM solicitacoes_adiantamento s
        LEFT JOIN entregadores e ON REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
            LTRIM(RTRIM(COALESCE(s.cpf, ''))), 
            '.', ''), '-', ''), ' ', ''), '(', ''), ')', ''), '/', '') =
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                LTRIM(RTRIM(COALESCE(e.cpf, ''))), 
                '.', ''), '-', ''), ' ', ''), '(', ''), ')', ''), '/', '')
        WHERE DATE(s.data_envio) = ?
    """, (data_hoje,))
    
    solicitacoes = cursor.fetchall()
    conn.close()
    
    if not solicitacoes:
        return pd.DataFrame()
    
    # Coletar IDs e CPFs dos entregadores que solicitaram
    ids_entregadores = set()
    cpfs_solicitantes = set()
    
    for s in solicitacoes:
        # s é um sqlite3.Row, pode acessar por nome ou índice
        cpf = s['cpf'] if s['cpf'] else None
        id_entregador = s['id_da_pessoa_entregadora'] if s['id_da_pessoa_entregadora'] else None
        
        if id_entregador:
            ids_entregadores.add(str(id_entregador))
        if cpf:
            cpfs_solicitantes.add(normalize_cpf(cpf))
    
    if not ids_entregadores and not cpfs_solicitantes:
        return pd.DataFrame()
    
    # Filtrar DataFrame pelos entregadores que solicitaram
    if 'id_da_pessoa_entregadora' in df_completo.columns:
        df_completo['id_da_pessoa_entregadora'] = df_completo['id_da_pessoa_entregadora'].astype(str)
        mask_id = df_completo['id_da_pessoa_entregadora'].isin(ids_entregadores)
    else:
        mask_id = pd.Series([False] * len(df_completo))
    
    # Filtrar por CPF se disponível
    if 'cpf' in df_completo.columns:
        df_completo['cpf_norm'] = df_completo['cpf'].apply(normalize_cpf)
        mask_cpf = df_completo['cpf_norm'].isin(cpfs_solicitantes)
    else:
        mask_cpf = pd.Series([False] * len(df_completo))
    
    # Combinar máscaras
    mask = mask_id | mask_cpf
    df_diario = df_completo[mask].copy()
    
    return df_diario


def _salvar_resultado_processamento(pasta_uploads, resultado, arquivos_salvos, consolidado_diario=None):
    """Salva resultado do processamento no banco e CSV (geral e diário)"""
    resultado_serializavel = {
        'total_entregadores': resultado['total_entregadores'],
        'valor_total_geral': float(resultado['valor_total_geral']),
        'data_processamento': resultado['data_processamento'],
        'erros': resultado['erros'],
        'total_arquivos': resultado['total_arquivos'],
        'arquivos_sucesso': resultado['arquivos_sucesso'],
        'arquivos_com_erro': resultado['arquivos_com_erro'],
        'total_entregadores_cadastrados': resultado['total_entregadores_cadastrados'],
        'entregadores_com_dados': resultado['entregadores_com_dados'],
    }
    
    # Salvar no banco de dados (PostgreSQL)
    try:
        StorageService.salvar_processamento_resultado(
            pasta_uploads=pasta_uploads,
            resultado=resultado_serializavel,
            dados_json=resultado_serializavel
        )
        print(f"✅ Resultado salvo no banco de dados")
    except Exception as e:
        print(f"❌ Erro ao salvar no banco: {e}")
        # Não usar fallback JSON - forçar correção do banco
        raise
    
    # JSON removido - usando apenas PostgreSQL para segurança e consultas
    
    # Salvar CSV consolidado geral
    consolidado_path = None
    if resultado.get('consolidado_geral') is not None:
        consolidado_path = os.path.join(pasta_uploads, ARQUIVO_ULTIMO_CONSOLIDADO)
        resultado['consolidado_geral'].to_csv(consolidado_path, index=False, encoding='utf-8')
    
    # Salvar CSV consolidado diário (se fornecido)
    consolidado_diario_path = None
    if consolidado_diario is not None and not consolidado_diario.empty:
        consolidado_diario_path = os.path.join(pasta_uploads, ARQUIVO_CONSOLIDADO_DIARIO)
        consolidado_diario.to_csv(consolidado_diario_path, index=False, encoding='utf-8')
    else:
        diario_existente = os.path.join(pasta_uploads, ARQUIVO_CONSOLIDADO_DIARIO)
        if os.path.exists(diario_existente):
            os.remove(diario_existente)
    
    # Guardar na sessão
    session['ultimo_resultado_path'] = resultado_json_path
    session['ultimo_consolidado_path'] = consolidado_path
    session['ultimo_consolidado_diario_path'] = consolidado_diario_path
    session['arquivos_processados'] = [os.path.basename(a) for a in arquivos_salvos]
    
    return resultado_serializavel, consolidado_path, consolidado_diario_path


def _carregar_resultado_anterior(pasta_uploads):
    """Carrega resultado anterior do banco ou arquivo (geral e diário)"""
    # Tentar carregar do banco primeiro
    resultado_json = None
    try:
        resultado_db = StorageService.carregar_processamento_resultado(pasta_uploads)
        if resultado_db:
            resultado_json = {
                'total_entregadores': resultado_db.get('total_entregadores', 0),
                'valor_total_geral': float(resultado_db.get('valor_total_geral', 0)),
                'data_processamento': resultado_db.get('data_processamento', ''),
                'erros': resultado_db.get('erros', []),
                'total_arquivos': resultado_db.get('total_arquivos', 0),
                'arquivos_sucesso': resultado_db.get('arquivos_sucesso', 0),
                'arquivos_com_erro': resultado_db.get('arquivos_com_erro', 0),
                'total_entregadores_cadastrados': resultado_db.get('total_entregadores_cadastrados', 0),
                'entregadores_com_dados': resultado_db.get('entregadores_com_dados', 0),
            }
    except Exception as e:
        print(f"❌ Erro ao carregar resultado do banco: {e}")
        # Não usar fallback JSON - retornar None
        return None, None, None, None
    
    # Se não encontrou no banco, retornar None
    if not resultado_json:
        return None, None, None, None
    
    consolidado_path = session.get('ultimo_consolidado_path') or os.path.join(
        pasta_uploads, ARQUIVO_ULTIMO_CONSOLIDADO
    )
    consolidado_diario_path = session.get('ultimo_consolidado_diario_path') or os.path.join(
        pasta_uploads, ARQUIVO_CONSOLIDADO_DIARIO
    )
    
    # Carregar consolidado geral
    consolidado_dict_completo = []
    if os.path.exists(consolidado_path):
        df = pd.read_csv(consolidado_path, encoding='utf-8')
        consolidado_dict_completo = df.to_dict('records')
        consolidado_dict_completo = _normalizar_nomes_consolidado(consolidado_dict_completo)
    
    # Carregar consolidado diário
    consolidado_diario_dict = []
    if os.path.exists(consolidado_diario_path):
        df_diario = pd.read_csv(consolidado_diario_path, encoding='utf-8')
        consolidado_diario_dict = df_diario.to_dict('records')
        consolidado_diario_dict = _normalizar_nomes_consolidado(consolidado_diario_dict)
    
    return resultado_json, consolidado_dict_completo, consolidado_path, consolidado_diario_dict


def init_upload_routes(app):
    """Inicializa as rotas de upload e processamento de CSV"""
    
    @app.route('/upload-csv')
    def upload_csv_page():
        """Página de upload de arquivos CSV"""
        return render_template(TEMPLATES_UPLOAD['upload_csv'])
    
    @app.route('/processar-csv', methods=['GET', 'POST'])
    @adm_or_master_required
    def processar_csv():
        """Processa arquivos CSV (POST) ou mostra resultados (GET)"""
        tipo_consolidado = request.args.get('tipo', 'padrao')  # 'padrao' ou 'diario'
        base_uploads = Config.UPLOAD_FOLDER
        pasta_uploads = get_week_folder(base_uploads)
        os.makedirs(pasta_uploads, exist_ok=True)
        
        processador = ProcessadorCSVService()
        historico_uploads = _obter_historico_para_template(pasta_uploads)

        def render_dashboard(**kwargs):
            kwargs.setdefault('historico_uploads', historico_uploads)
            kwargs.setdefault('historico_limite_horas', UPLOAD_RETENTION_HOURS)
            return render_template(TEMPLATES_UPLOAD['resultado'], **kwargs)

        if request.method == 'POST':
            if 'arquivos' not in request.files:
                flash(
                    get_flash_message('upload', 'nenhum_arquivo'),
                    'error'
                )
                # Renderizar tela vazia em caso de erro
                return render_dashboard(
                    resultado=None,
                    consolidado_dict=None,
                    consolidado_todos=None,
                    page=1,
                    total_pages=0,
                    arquivos_processados=[],
                    entregadores_cadastrados_ids=[],
                    tipo_consolidado=tipo_consolidado
                )
            
            arquivos = request.files.getlist('arquivos')
            arquivos_salvos = []
            
            # Salvar arquivos CSV
            for arquivo in arquivos:
                if not arquivo.filename.endswith('.csv'):
                    continue
                filename = f"{datetime.now().strftime(FORMATO_DATA_ARQUIVO)}_{arquivo.filename}"
                caminho_arquivo = os.path.join(pasta_uploads, filename)
                arquivo.save(caminho_arquivo)
                arquivos_salvos.append(caminho_arquivo)
            
            if not arquivos_salvos:
                flash(
                    get_flash_message('upload', 'nenhum_csv'),
                    'error'
                )
                # Renderizar tela vazia em caso de erro
                return render_dashboard(
                    resultado=None,
                    consolidado_dict=None,
                    consolidado_todos=None,
                    page=1,
                    total_pages=0,
                    arquivos_processados=[],
                    entregadores_cadastrados_ids=[],
                    tipo_consolidado=tipo_consolidado
                )
            
            try:
                # Processar CSV sem filtrar por entregadores cadastrados - mostrar todos do CSV
                resultado = processador.processar_multiplos_csv(
                    arquivos_salvos,
                    data_filtro=None,
                    ids_entregadores=None,
                    filtrar_por_cadastrados=False  # Processar todos do CSV, não apenas cadastrados
                )
                
                # Processar consolidado diário baseado nas solicitações do dia
                from datetime import date
                data_hoje = date.today().strftime('%Y-%m-%d')
                df_diario = _processar_consolidado_diario(resultado['df_completo'], data_hoje)
                
                # Se houver dados diários, consolidar
                consolidado_diario = None
                if not df_diario.empty:
                    try:
                        consolidado_diario = processador.consolidar_entregadores(df_diario, data_filtro=None)
                        if consolidado_diario is None or consolidado_diario.empty:
                            consolidado_diario = None
                    except Exception as e:
                        print(f"⚠️ Erro ao consolidar diário: {str(e)}")
                        consolidado_diario = None
                
                resultado_serializavel, consolidado_path, consolidado_diario_path = _salvar_resultado_processamento(
                    pasta_uploads, resultado, arquivos_salvos, consolidado_diario
                )
                _registrar_historico_upload(pasta_uploads, arquivos_salvos, resultado_serializavel)
                
                # Normalizar nomes
                consolidado_dict_completo = resultado['consolidado_geral'].to_dict('records')
                consolidado_dict_completo = _normalizar_nomes_consolidado(consolidado_dict_completo)
                
                # Paginação
                page = get_page_from_request()
                consolidado_pag, total_pages = paginate_items(
                    consolidado_dict_completo, page, PAGINATION_PER_PAGE_UPLOAD
                )
                
                # Redirecionar para GET após sucesso para evitar reenvio
                flash(
                    f'Arquivos processados com sucesso! {len(arquivos_salvos)} arquivo(s) processado(s).',
                    'success'
                )
                return redirect(url_for('processar_csv'))
            except Exception as e:
                flash(
                    get_flash_message('upload', 'erro_processar', error=str(e)),
                    'error'
                )
                # Renderizar tela vazia em caso de erro
                return render_dashboard(
                    resultado=None,
                    consolidado_dict=None,
                    consolidado_todos=None,
                    page=1,
                    total_pages=0,
                    arquivos_processados=[],
                    entregadores_cadastrados_ids=[],
                    tipo_consolidado=tipo_consolidado
                )
        
        # GET - Carregar resultado anterior (geral e diário)
        try:
            resultado_json, consolidado_geral_dict, _, consolidado_diario_dict = _carregar_resultado_anterior(pasta_uploads)
            
            if resultado_json is None:
                # Renderizar tela vazia com botão de upload
                return render_dashboard(
                    resultado=None,
                    consolidado_dict=None,
                    consolidado_todos=None,
                    page=1,
                    total_pages=0,
                    arquivos_processados=[],
                    entregadores_cadastrados_ids=[],
                    tipo_consolidado=tipo_consolidado
                )
            
            if not _resultado_dentro_do_prazo(resultado_json):
                return render_dashboard(
                    resultado=None,
                    consolidado_dict=None,
                    consolidado_todos=None,
                    page=1,
                    total_pages=0,
                    arquivos_processados=[],
                    entregadores_cadastrados_ids=[],
                    tipo_consolidado=tipo_consolidado,
                    mensagem_expirado=f"Os dados foram ocultados após {UPLOAD_RETENTION_HOURS} horas. Envie um novo CSV para visualizar novamente."
                )
            
            # Escolher qual consolidado usar baseado no tipo selecionado
            if tipo_consolidado == 'diario':
                # Verificar se o formulário está aberto
                if form_is_open():
                    # Formulário ainda está aberto - mostrar mensagem
                    return render_dashboard(
                        resultado=resultado_json,
                        consolidado_dict=None,
                        consolidado_todos=None,
                        page=1,
                        total_pages=0,
                        arquivos_processados=session.get('arquivos_processados', []),
                        entregadores_cadastrados_ids=[],
                        tipo_consolidado=tipo_consolidado,
                        form_aberto=True,
                        mensagem_diario="O formulário ainda está aberto. Feche o formulário antes de visualizar o consolidado diário."
                    )
                
                # Verificar se há consolidado diário
                if consolidado_diario_dict and len(consolidado_diario_dict) > 0:
                    # Usar consolidado diário (quem solicitou no formulário)
                    consolidado_dict_completo = consolidado_diario_dict
                    # Ajustar resultado JSON para refletir dados diários
                    resultado_json_diario = resultado_json.copy()
                    resultado_json_diario['total_entregadores'] = len(consolidado_diario_dict)
                    resultado_json_diario['entregadores_com_dados'] = len(consolidado_diario_dict)
                    if consolidado_diario_dict:
                        resultado_json_diario['valor_total_geral'] = sum(float(row.get('valor_total', 0)) for row in consolidado_diario_dict)
                    resultado_json = resultado_json_diario
                else:
                    # Não há solicitações no dia
                    return render_dashboard(
                        resultado=resultado_json,
                        consolidado_dict=None,
                        consolidado_todos=None,
                        page=1,
                        total_pages=0,
                        arquivos_processados=session.get('arquivos_processados', []),
                        entregadores_cadastrados_ids=[],
                        tipo_consolidado=tipo_consolidado,
                        form_aberto=False,
                        mensagem_diario="Nenhum entregador solicitou adiantamento hoje."
                    )
            else:
                # Usar consolidado padrão (todos do CSV)
                consolidado_dict_completo = consolidado_geral_dict or []
            
            if not consolidado_dict_completo or len(consolidado_dict_completo) == 0:
                # Renderizar tela vazia se não houver dados (apenas para padrão)
                return render_dashboard(
                    resultado=None,
                    consolidado_dict=None,
                    consolidado_todos=None,
                    page=1,
                    total_pages=0,
                    arquivos_processados=[],
                    entregadores_cadastrados_ids=[],
                    tipo_consolidado=tipo_consolidado
                )
            
            # Obter lista de entregadores cadastrados para verificação
            processador_temp = ProcessadorCSVService()
            entregadores_cadastrados_ids = processador_temp._obter_entregadores_cadastrados()
            
            # Paginação
            page = get_page_from_request()
            consolidado_pag, total_pages = paginate_items(
                consolidado_dict_completo, page, PAGINATION_PER_PAGE_UPLOAD
            )
            
            return render_dashboard(
                resultado=resultado_json,
                consolidado_dict=consolidado_pag,
                consolidado_todos=consolidado_dict_completo,
                page=page,
                total_pages=total_pages,
                arquivos_processados=session.get('arquivos_processados', []),
                entregadores_cadastrados_ids=entregadores_cadastrados_ids,
                tipo_consolidado=tipo_consolidado
            )
        except Exception as e:
            flash(
                get_flash_message('upload', 'erro_carregar', error=str(e)),
                'error'
            )
            # Renderizar tela vazia mesmo em caso de erro
            return render_dashboard(
                resultado=None,
                consolidado_dict=None,
                consolidado_todos=None,
                page=1,
                total_pages=0,
                arquivos_processados=[],
                entregadores_cadastrados_ids=[],
                tipo_consolidado=tipo_consolidado
            )
    
    @app.route('/lotes')
    @login_required
    def listar_lotes():
        """Exibe o histórico de uploads/lotes processados"""
        base_uploads = Config.UPLOAD_FOLDER
        pasta_uploads = get_week_folder(base_uploads)
        os.makedirs(pasta_uploads, exist_ok=True)
        lotes = _obter_historico_para_template(pasta_uploads)
        return render_template(
            TEMPLATES_UPLOAD['lotes'],
            lotes=lotes,
            limite_horas=UPLOAD_RETENTION_HOURS
        )
    
    @app.route('/lotes/<lote_id>/excluir', methods=['POST'])
    @master_required
    def excluir_lote(lote_id):
        """Exclui um lote do histórico (apenas Master)"""
        try:
            # Tentar excluir do banco primeiro
            sucesso = StorageService.excluir_upload_history(lote_id)
            
            if sucesso:
                return jsonify({
                    'success': True,
                    'message': 'Lote excluído com sucesso'
                })
            
            # Fallback: tentar excluir do arquivo JSON
            base_uploads = Config.UPLOAD_FOLDER
            pasta_uploads = get_week_folder(base_uploads)
            
            uploads = _carregar_historico_uploads(pasta_uploads)
            
            # Encontrar e remover o lote
            uploads_original = len(uploads)
            uploads = [u for u in uploads if u.get('id') != lote_id]
            
            if len(uploads) == uploads_original:
                return jsonify({
                    'success': False,
                    'message': 'Lote não encontrado'
                }), 404
            
            # Salvar histórico atualizado
            _salvar_historico_uploads(pasta_uploads, uploads)
            
            return jsonify({
                'success': True,
                'message': 'Lote excluído com sucesso'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Erro ao excluir lote: {str(e)}'
            }), 500
    
    @app.route('/entregador/<string:id_entregador>/detalhes-completos')
    def detalhes_completos_entregador(id_entregador):
        """Mostra detalhes completos do processamento de um entregador"""
        try:
            processador = ProcessadorCSVService()
            dados_cadastrais = processador.obter_detalhes_entregador(id_entregador)
            
            if not dados_cadastrais:
                flash('Entregador não encontrado na base de dados', 'error')
                return redirect(url_for('entregadores'))
            
            pasta_uploads = get_week_folder(Config.UPLOAD_FOLDER)
            arquivos_csv = [
                os.path.join(pasta_uploads, f)
                for f in os.listdir(pasta_uploads)
                if f.endswith('.csv')
            ]
            
            # Dados padrão se não houver arquivos
            dados_processamento_padrao = {
                'valor_total': 0, 'corridas': 0, 'gorjeta': 0, 'promo': 0,
                'online_time': 0, 'outros': 0, 'valor_60_percent': 0,
                'valor_final': 0, 'periodos_trabalhados': [], 'subpracas': []
            }
            
            if not arquivos_csv:
                flash('⚠️ Usando dados de exemplo - faça upload de CSVs para dados reais', 'info')
                dados_processamento = dados_processamento_padrao.copy()
                dados_processamento.update({
                    'valor_total': 199.74, 'corridas': 150.00, 'gorjeta': 25.00,
                    'promo': 15.00, 'online_time': 9.74, 'valor_60_percent': 119.84,
                    'valor_final': 119.49, 'periodos_trabalhados': ['ALMOCO', 'TARDE', 'JANTAR'],
                    'subpracas': ['RIO - BARRA - FREGUESIA (OL DEDICADO)']
                })
            else:
                resultado_geral = processador.processar_multiplos_csv(arquivos_csv)
                df_completo = resultado_geral['df_completo']
                dados_processamento = processador.obter_detalhes_processamento_entregador(
                    id_entregador, df_completo
                )
                
                if not dados_processamento:
                    flash('Nenhum dado de processamento encontrado para este entregador', 'warning')
                    dados_processamento = dados_processamento_padrao
            
            dados_cadastrais['recebedor'] = formatar_nome(dados_cadastrais['recebedor'])
            
            return render_template(
                TEMPLATES_UPLOAD['detalhes_completos'],
                entregador=dados_cadastrais,
                processamento=dados_processamento
            )
        except Exception as e:
            flash(f'Erro ao carregar detalhes: {str(e)}', 'error')
            return redirect(url_for('entregadores'))
    
    @app.route('/gerar-relatorio-excel')
    def gerar_relatorio_excel():
        """Gera relatório Excel completo usando APENAS o último arquivo CSV enviado"""
        try:
            pasta_relatorios = get_week_folder(Config.RELATORIOS_FOLDER)
            os.makedirs(pasta_relatorios, exist_ok=True)
            
            nome_arquivo = f"relatorio_{datetime.now().strftime(FORMATO_DATA_ARQUIVO)}.xlsx"
            caminho_relatorio = os.path.join(pasta_relatorios, nome_arquivo)
            
            processador = ProcessadorCSVService()
            pasta_uploads = get_week_folder(Config.UPLOAD_FOLDER)
            
            # Buscar todos os arquivos CSV (exceto o consolidado)
            todos_arquivos = [
                os.path.join(pasta_uploads, f)
                for f in os.listdir(pasta_uploads)
                if f.endswith('.csv') and f != ARQUIVO_ULTIMO_CONSOLIDADO
            ]
            
            if not todos_arquivos:
                dados_exemplo = pd.DataFrame([{
                    'recebedor': 'Exemplo',
                    'id_da_pessoa_entregadora': 'exemplo-id',
                    'valor_total': 1000,
                    'valor_60_percent': 600,
                    'valor_final': 599.65
                }])
                processador.gerar_relatorio_excel(dados_exemplo, caminho_relatorio)
                flash(
                    get_flash_message('upload', 'relatorio_exemplo'),
                    'info'
                )
                return send_file(caminho_relatorio, as_attachment=True)
            
            # Pegar apenas o último arquivo (mais recente por data de modificação)
            ultimo_arquivo = max(todos_arquivos, key=os.path.getmtime)
            nome_ultimo = os.path.basename(ultimo_arquivo)
            
            print(f"📄 Processando apenas o último arquivo: {nome_ultimo}")
            
            # Processar apenas o último arquivo - sem filtrar por cadastrados
            resultado = processador.processar_multiplos_csv(
                [ultimo_arquivo],
                data_filtro=None,
                ids_entregadores=None,
                filtrar_por_cadastrados=False  # Processar todos do CSV
            )
            processador.gerar_relatorio_excel(resultado['consolidado_geral'], caminho_relatorio)
            flash(
                f'Relatório gerado com sucesso usando o arquivo: {nome_ultimo}',
                'success'
            )
            
            return send_file(caminho_relatorio, as_attachment=True)
        except Exception as e:
            flash(
                get_flash_message('upload', 'erro_relatorio', error=str(e)),
                'error'
            )
            return redirect(url_for('upload_csv_page'))
    
    @app.route('/upload-entregadores', methods=['GET', 'POST'])
    def upload_entregadores():
        """Tela de upload e pré-visualização de entregadores via XLSX"""
        if request.method == 'POST':
            file = request.files.get('arquivo')
            if not file or file.filename == '':
                flash(
                    get_flash_message('upload', 'arquivo_invalido'),
                    'error'
                )
                return redirect(url_for('upload_entregadores'))
            
            pasta_uploads = get_week_folder(Config.UPLOAD_FOLDER)
            os.makedirs(pasta_uploads, exist_ok=True)
            
            filename = f"{datetime.now().strftime(FORMATO_DATA_ARQUIVO)}_{file.filename}"
            caminho_temp = os.path.join(pasta_uploads, filename)
            file.save(caminho_temp)
            
            try:
                dados = UploadService.ler_planilha(caminho_temp)
                preview = dados.to_dict(orient='records')
                
                token = str(uuid.uuid4())
                pasta_temp = Config.TEMP_FOLDER
                os.makedirs(pasta_temp, exist_ok=True)
                
                # Salvar no banco de dados (PostgreSQL)
                try:
                    StorageService.salvar_arquivo_temp(
                        token=token,
                        pasta_uploads=pasta_temp,
                        dados_json=preview,
                        expires_hours=24
                    )
                    print(f"✅ Preview salvo no banco de dados")
                except Exception as e:
                    print(f"❌ Erro ao salvar preview no banco: {e}")
                    # Não usar fallback JSON - forçar correção do banco
                    raise
                
                flash(
                    get_flash_message('upload', 'carregados', count=len(preview)),
                    'success'
                )
                return render_template(
                    TEMPLATES_UPLOAD['upload_entregadores'],
                    preview=preview,
                    token=token
                )
            except Exception as e:
                flash(
                    get_flash_message('upload', 'erro_ler', error=str(e)),
                    'error'
                )
                return render_template(TEMPLATES_UPLOAD['upload_entregadores'], preview=None)
        
        return render_template(TEMPLATES_UPLOAD['upload_entregadores'], preview=None)
    
    @app.route('/confirmar-importacao-entregadores', methods=['POST'])
    def confirmar_importacao_entregadores():
        """Confirma e insere os entregadores no banco"""
        token = request.form.get('token')
        if not token:
            flash(
                get_flash_message('upload', 'token_invalido'),
                'error'
            )
            return redirect(url_for('upload_entregadores'))
        
        pasta_temp = Config.TEMP_FOLDER
        
        # Tentar carregar do banco primeiro
        preview = None
        try:
            arquivo_temp = StorageService.carregar_arquivo_temp(token)
            if arquivo_temp and arquivo_temp.get('dados_json'):
                preview = arquivo_temp['dados_json']
        except Exception as e:
            print(f"❌ Erro ao carregar preview do banco: {e}")
            flash(
                get_flash_message('upload', 'dados_nao_encontrados'),
                'error'
            )
            return redirect(url_for('upload_entregadores'))
        
        # Se não encontrou no banco, retornar erro
        if not preview:
            flash(
                get_flash_message('upload', 'dados_nao_encontrados'),
                'error'
            )
            return redirect(url_for('upload_entregadores'))
        
        try:
            
            inseridos = UploadService.salvar_no_banco(preview)
            flash(
                get_flash_message('upload', 'importados', count=inseridos),
                'success'
            )
            
            # Limpar arquivo temporário do banco (se necessário)
            # StorageService já gerencia expiração automática
            return redirect(url_for('entregadores'))
        except Exception as e:
            flash(
                get_flash_message('upload', 'erro_gravar', error=str(e)),
                'error'
            )
            return redirect(url_for('upload_entregadores'))
