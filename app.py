from app import create_app
from config import Config
import os
import socket
from app.models.database import DB_PATH, USE_POSTGRESQL, POSTGRESQL_AVAILABLE

app = create_app()

def get_local_ip():
    """Obtém o IP local da máquina na rede"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"

if __name__ == '__main__':
    # Verificar banco de dados
    # USE_POSTGRESQL já é tratado no database.py como truthy/falsy
    if USE_POSTGRESQL and POSTGRESQL_AVAILABLE:
        # Usando PostgreSQL - não precisa verificar arquivo
        print('🚀 Servidor iniciado com sucesso!')
        print(f'📊 Banco: PostgreSQL ({Config.DB_NAME})')
    elif os.path.exists(DB_PATH):
        # Usando SQLite e arquivo existe
        print('🚀 Servidor iniciado com sucesso!')
        print(f'📊 Banco: SQLite ({Config.DATABASE})')
    else:
        # SQLite mas arquivo não existe
        print('⚠️  Banco de dados não encontrado. Execute create_database.py primeiro!')
    
    local_ip = get_local_ip()
    print(f'🌐 Acesse localmente: http://localhost:5000')
    print(f'🌐 Acesse na rede: http://{local_ip}:5000')

    app.run(host='0.0.0.0', port=5000, debug=Config.DEBUG, use_reloader=True)

