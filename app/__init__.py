from flask import Flask, send_from_directory
from app.models.database import init_db
from app.routes.entregadores_routes import init_entregadores_routes
from app.routes.upload_routes import init_upload_routes
from app.routes.adiantamento_routes import init_adiantamento_routes
from config import Config
from app.jobs.form_scheduler import iniciar_scheduler
from app.routes.pix_routes import init_pix_routes
from app.routes.pix_admin_routes import init_pix_admin_routes
from app.routes.auth_routes import init_auth_routes
import os




def create_app():
    app = Flask(
        __name__,
        static_folder="assets/static",
        template_folder="assets/templates"
    )

    app.config.from_object(Config)

    # Rota para favicon
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(
            os.path.join(app.root_path, 'assets', 'static', 'img'),
            'favicon.svg',
            mimetype='image/svg+xml'
        )
    
    # Inicializa banco
    init_db()

    # Registra blueprints / rotas
    init_auth_routes(app)  # Autenticação primeiro
    init_entregadores_routes(app)
    init_upload_routes(app)
    init_adiantamento_routes(app)
    init_pix_routes(app)
    init_pix_admin_routes(app)

    iniciar_scheduler()

    return app
