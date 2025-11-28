"""
Serviço de Verificação em Duas Etapas (2FA)
Gera e valida códigos de verificação
"""
import random
import string
from datetime import datetime, timedelta
from config import Config


class TwoFAService:
    """Serviço para gerenciar códigos de verificação 2FA"""
    
    @staticmethod
    def gerar_codigo():
        """
        Gera um código de verificação: 4 letras maiúsculas + 3 números
        Exemplo: ABCD123
        """
        letras = ''.join(random.choices(string.ascii_uppercase, k=4))
        numeros = ''.join(random.choices(string.digits, k=3))
        return f"{letras}{numeros}"
    
    @staticmethod
    def validar_codigo(codigo_inserido, codigo_esperado):
        """
        Valida se o código inserido corresponde ao esperado
        (case-insensitive)
        """
        if not codigo_inserido or not codigo_esperado:
            return False
        
        # Remover espaços e converter para maiúsculo
        codigo_inserido = codigo_inserido.strip().upper()
        codigo_esperado = codigo_esperado.strip().upper()
        
        return codigo_inserido == codigo_esperado
    
    @staticmethod
    def codigo_expirado(data_geracao):
        """
        Verifica se o código expirou
        """
        if not data_geracao:
            return True
        
        try:
            data_geracao = datetime.fromisoformat(data_geracao)
            tempo_expiracao = timedelta(minutes=Config.TWO_FA_CODE_EXPIRY)
            return datetime.now() > data_geracao + tempo_expiracao
        except:
            return True
    
    @staticmethod
    def formatar_codigo_para_exibicao(codigo):
        """
        Formata código para exibição: ABCD-123
        """
        if len(codigo) == 7:
            return f"{codigo[:4]}-{codigo[4:]}"
        return codigo

