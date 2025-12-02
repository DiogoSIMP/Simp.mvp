from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from datetime import datetime, time
from app.models.database import get_db_connection
from app.utils.form_control import (
    get_form_config,
    abrir_formulario,
    fechar_formulario
)
from app.utils.form_logs import registrar_log
from app.services.backup_service import executar_backup_diario


# ======================================
# SCHEDULER CONFIG
# ======================================
executors = {
    'default': ThreadPoolExecutor(1)   # evita concorrência
}

scheduler = BackgroundScheduler(executors=executors)


# ======================================
# FUNÇÃO AUXILIAR
# ======================================
def _normalizar_horario(horario):
    """Converte horário para string no formato HH:MM"""
    if horario is None:
        return None
    if isinstance(horario, time):
        return horario.strftime("%H:%M")
    if isinstance(horario, str):
        # Se já for string, retornar apenas HH:MM (pode ter segundos)
        return horario[:5] if len(horario) >= 5 else horario
    # Para qualquer outro tipo, converter para string primeiro
    horario_str = str(horario)
    # Se for um objeto datetime, extrair apenas hora:minuto
    if hasattr(horario, 'strftime'):
        try:
            return horario.strftime("%H:%M")
        except:
            pass
    return horario_str[:5] if len(horario_str) >= 5 else horario_str

def _set_form_status(aberto: bool, motivo: str):
    cfg = get_form_config()
    print("📄 CONFIG DO BANCO:", cfg)
    if not cfg:
        return

    estado_atual = bool(cfg["is_open"])

    if aberto and not estado_atual:
        abrir_formulario()
        registrar_log("ABERTO", motivo)
        print(f"🟢 Formulário ABERTO: {motivo}")

    elif not aberto and estado_atual:
        fechar_formulario()
        registrar_log("FECHADO", motivo)
        print(f"🔴 Formulário FECHADO: {motivo}")


# ======================================
# HORÁRIO FIXO DIÁRIO
# ======================================
def verificar_horario_fixo(cfg):

    # 🚨 SE EXISTE AGENDAMENTO → NÃO APLICAR HORÁRIO FIXO
    if cfg.get("scheduled_open") or cfg.get("scheduled_close"):
        return

    if not cfg or cfg["auto_mode"] == 0:
        return

    agora = datetime.now()
    hora_atual = agora.strftime("%H:%M")

    dias_str = cfg.get("days_enabled")

    if not dias_str:
        _set_form_status(False, "Nenhum dia habilitado")
        return

    dias_ativados = [int(d) for d in dias_str.split(',') if d.isdigit()]

    dia_semana = (agora.weekday() + 1) % 7  # segunda=0 ... domingo=6

    if dia_semana not in dias_ativados:
        _set_form_status(False, f"Dia não habilitado ({dia_semana})")
        return

    hora_abre = cfg.get("auto_open_time")
    hora_fecha = cfg.get("auto_close_time")

    if not hora_abre or not hora_fecha:
        return

    # Normalizar horários para string no formato HH:MM
    hora_abre_str = _normalizar_horario(hora_abre)
    hora_fecha_str = _normalizar_horario(hora_fecha)

    if not hora_abre_str or not hora_fecha_str:
        return

    # Comparação de strings no formato HH:MM (funciona lexicograficamente)
    if hora_abre_str <= hora_atual <= hora_fecha_str:
        _set_form_status(True, "Dentro do horário automático")
    else:
        _set_form_status(False, "Fora do horário automático")


# ======================================
# AGENDAMENTOS ÚNICOS
# ======================================
def verificar_agendamentos():
    print("🔍 [Scheduler] Rodando verificação às", datetime.now().strftime("%H:%M:%S"))

    cfg = get_form_config()
    if not cfg:
        return

    agora = datetime.now()

    # 1️⃣ PROCESSAR AGENDAMENTO (PRIORIDADE MÁXIMA)
    if cfg.get("scheduled_open"):
        dt_abre = datetime.strptime(cfg["scheduled_open"], "%Y-%m-%d %H:%M:%S")
        if agora >= dt_abre:
            _set_form_status(True, "Abertura programada executada")

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE form_config SET scheduled_open = NULL WHERE id = 1"
            )
            conn.commit()
            conn.close()

            return  # impede horário fixo de fechar logo depois

    if cfg.get("scheduled_close"):
        dt_fecha = datetime.strptime(cfg["scheduled_close"], "%Y-%m-%d %H:%M:%S")
        if agora >= dt_fecha:
            _set_form_status(False, "Fechamento programado executado")

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE form_config SET scheduled_close = NULL WHERE id = 1"
            )
            conn.commit()
            conn.close()

            return  # impede conflito com horário fixo

    # 2️⃣ HORÁRIO FIXO (executa somente se NÃO houver agendamentos)
    verificar_horario_fixo(cfg)


# ======================================
# START
# ======================================
_scheduler_started = False

def iniciar_scheduler():
    global _scheduler_started

    if _scheduler_started:
        print("⚠️ Scheduler já iniciado.")
        return

    scheduler.add_job(
        verificar_agendamentos,
        "interval",
        seconds=30,
        id="job_verificar_agendamentos",
        replace_existing=True
    )
    
    # Job de backup diário às 22h00
    scheduler.add_job(
        executar_backup_diario,
        "cron",
        hour=22,
        minute=0,
        id="job_backup_diario",
        replace_existing=True
    )

    scheduler.start()
    _scheduler_started = True
    print("🟢 Scheduler iniciado (30s por ciclo).")
    print("💾 Backup diário agendado para 22h00.")
