from datetime import datetime
from app.models.database import get_db_connection, is_postgresql_connection


def _init_pix_logs_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    is_postgresql = is_postgresql_connection(conn)

    if is_postgresql:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pix_logs (
                id SERIAL PRIMARY KEY,
                cpf VARCHAR(14),
                chave_pix VARCHAR(255),
                tipo_chave VARCHAR(50),
                motivo TEXT,
                ip VARCHAR(45),
                user_agent TEXT,
                data_hora TIMESTAMP
            );
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pix_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cpf TEXT,
                chave_pix TEXT,
                tipo_chave TEXT,
                motivo TEXT,
                ip TEXT,
                user_agent TEXT,
                data_hora TEXT
            );
        """)

    conn.commit()
    conn.close()


_init_pix_logs_table()


def registrar_erro_pix(cpf, chave, tipo, motivo, ip, user_agent):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        is_postgresql = is_postgresql_connection(conn)
        
        # Usar %s para PostgreSQL e ? para SQLite
        placeholder = "%s" if is_postgresql else "?"
        placeholders = ", ".join([placeholder] * 7)

        cursor.execute(f"""
            INSERT INTO pix_logs
            (cpf, chave_pix, tipo_chave, motivo, ip, user_agent, data_hora)
            VALUES ({placeholders})
        """, (
            cpf,
            chave,
            tipo,
            motivo,
            ip,
            user_agent,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()
        conn.close()

        print(f"⚠️ [PIX-ERRO] {motivo} | CPF={cpf} | Chave={chave}")

    except Exception as e:
        print("❌ Erro ao registrar log PIX:", e)
