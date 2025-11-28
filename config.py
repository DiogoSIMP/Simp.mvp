import os
from dotenv import load_dotenv

class Config:
    # ======== CONFIGURAÇÕES BÁSICAS ========
    SECRET_KEY = 'sua_chave_secreta_aqui'
    DATABASE = 'Drives_abjp.db'
    DEBUG = True

    # ======== CAMINHOS DE PASTAS PRINCIPAIS ========
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # 📁 Diretórios principais
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    RELATORIOS_FOLDER = os.path.join(BASE_DIR, 'relatorios')
    PROFILE_PHOTOS_FOLDER = os.path.join(BASE_DIR, 'app', 'assets', 'static', 'img', 'profiles')

    # ======== SUBPASTAS ========
    # (caso queira controlar depois temp, semanas, etc)
    TEMP_FOLDER = os.path.join(UPLOAD_FOLDER, 'temp')
    SEMANAS_FOLDER = os.path.join(UPLOAD_FOLDER, 'semanas')

    # ======== OUTRAS CONFIGURAÇÕES (se quiser expandir depois) ========
    ITEMS_PER_PAGE = 50
    
    # ======== CONFIGURAÇÕES DE E-MAIL (2FA) ========
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@simp.com')
    
    # Tempo de expiração do código 2FA (em minutos)
    TWO_FA_CODE_EXPIRY = 10