from datetime import datetime
from app.models.database import get_db_connection
from flask import url_for

def registrar_log(acao, detalhe=None):
    """
    Registra logs com:
    - ação (ex: ABERTO, FECHADO, AGENDADO)
    - detalhe (origem da ação)
    - timestamp
    - link para o formulário público (/adiantamento)
    """

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Gera o link absoluto do formulário
        try:
            link_form = url_for("formulario_publico", _external=True)
        except:
            # Caso chamado por scheduler sem contexto Flask
            link_form = "http://localhost:5000/adiantamento"

        cursor.execute("""
            INSERT INTO form_logs (acao, detalhe, link_form, data_hora)
            VALUES (?, ?, ?, ?)
        """, (
            acao,
            detalhe or "",
            link_form,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()
        conn.close()

        print(f"📘 LOG: {acao} | {detalhe}")

    except Exception as e:
        print("❌ ERRO AO SALVAR LOG:", e)
