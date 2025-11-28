"""
Serviço de envio de e-mail para 2FA
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config


class EmailService:
    """Serviço para envio de e-mails"""
    
    @staticmethod
    def enviar_codigo_2fa(email_destino, codigo, nome_usuario):
        """
        Envia código de verificação 2FA por e-mail
        
        Args:
            email_destino: E-mail do destinatário
            codigo: Código de verificação (4 letras + 3 números)
            nome_usuario: Nome do usuário
        """
        if not Config.MAIL_USERNAME or not Config.MAIL_PASSWORD:
            print(f"⚠️  E-mail não configurado. Código 2FA seria: {codigo}")
            print(f"   Enviado para: {email_destino}")
            return False
        
        try:
            # Criar mensagem
            msg = MIMEMultipart('alternative')
            msg['Subject'] = 'Código de Verificação - SIMP'
            msg['From'] = Config.MAIL_DEFAULT_SENDER
            msg['To'] = email_destino
            
            # Corpo do e-mail (HTML)
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                        background: #f4f6fc;
                    }}
                    .card {{
                        background: white;
                        padding: 30px;
                        border-radius: 10px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .code-box {{
                        background: #0b5cff;
                        color: white;
                        padding: 20px;
                        border-radius: 8px;
                        text-align: center;
                        font-size: 32px;
                        font-weight: bold;
                        letter-spacing: 8px;
                        margin: 20px 0;
                        font-family: 'Courier New', monospace;
                    }}
                    .warning {{
                        background: #fef3c7;
                        padding: 15px;
                        border-radius: 6px;
                        margin-top: 20px;
                        border-left: 4px solid #f59e0b;
                    }}
                    .footer {{
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 1px solid #e2e8f0;
                        font-size: 12px;
                        color: #6b7280;
                        text-align: center;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="card">
                        <h1 style="color: #0b5cff;">Verificação em Duas Etapas</h1>
                        <p>Olá, <strong>{nome_usuario}</strong>!</p>
                        <p>Você solicitou acesso ao sistema SIMP. Use o código abaixo para completar o login:</p>
                        
                        <div class="code-box">{codigo}</div>
                        
                        <p>Este código é válido por <strong>10 minutos</strong>.</p>
                        
                        <div class="warning">
                            <strong>⚠️ Importante:</strong> Nunca compartilhe este código com ninguém. 
                            Se você não solicitou este código, ignore este e-mail.
                        </div>
                        
                        <div class="footer">
                            <p>Sistema Interno de Gestão - SIMP</p>
                            <p>Este é um e-mail automático, não responda.</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Versão texto simples
            text_body = f"""
            Verificação em Duas Etapas - SIMP
            
            Olá, {nome_usuario}!
            
            Você solicitou acesso ao sistema SIMP. Use o código abaixo para completar o login:
            
            {codigo}
            
            Este código é válido por 10 minutos.
            
            ⚠️ Importante: Nunca compartilhe este código com ninguém.
            Se você não solicitou este código, ignore este e-mail.
            
            ---
            Sistema Interno de Gestão - SIMP
            Este é um e-mail automático, não responda.
            """
            
            # Adicionar partes ao e-mail
            part1 = MIMEText(text_body, 'plain', 'utf-8')
            part2 = MIMEText(html_body, 'html', 'utf-8')
            
            msg.attach(part1)
            msg.attach(part2)
            
            # Enviar e-mail
            context = ssl.create_default_context()
            
            with smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT) as server:
                if Config.MAIL_USE_TLS:
                    server.starttls(context=context)
                server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
                server.send_message(msg)
            
            print(f"✅ Código 2FA enviado para: {email_destino}")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao enviar e-mail 2FA: {str(e)}")
            # Em caso de erro, ainda mostra o código no console para desenvolvimento
            print(f"   Código 2FA seria: {codigo}")
            return False

