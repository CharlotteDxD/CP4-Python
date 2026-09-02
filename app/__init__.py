import os
from typing import Optional

from dotenv import load_dotenv
from flasgger import Swagger
from flask import Flask
from flask_cors import CORS

from .config import config_by_name
from .extensions import db, migrate


def create_app(config_name: Optional[str] = None) -> Flask:
    """Application factory.

    Cria e configura a instância do Flask. Nada de lógica de negócio aqui —
    esse arquivo só monta as peças (config, extensões, blueprints).

    config_name: 'development' | 'testing' | 'production'
                 Se não for passado, usa a variável de ambiente FLASK_ENV
                 (e cai em 'development' se ela também não existir).
    """
    load_dotenv()

    config_name = config_name or os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    _register_extensions(app)
    _register_blueprints(app)

    return app

def _register_extensions(app: Flask) -> None:
    db.init_app(app)
    from . import models  # registra Conta/Categoria/Transacao/Alerta no metadata
    migrate.init_app(app, db)
    CORS(app)

    # Swagger fica acessível em /apidocs assim que essa linha roda.
    # Anthony vai preencher as docstrings de cada rota com o formato
    # OpenAPI (é o que o flasgger lê para montar a página).
    app.config.setdefault(
        "SWAGGER",
        {
            "title": "Agente Financeiro de Fluxo de Caixa — API",
            "uiversion": 3,
        },
    )
    Swagger(app)


def _register_blueprints(app: Flask) -> None:
    from .blueprints.alertas.routes import alertas_bp
    from .blueprints.categorias.routes import categorias_bp
    from .blueprints.contas.routes import contas_bp
    from .blueprints.health.routes import health_bp
    from .blueprints.transacoes.routes import transacoes_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(transacoes_bp, url_prefix="/transacoes")
    app.register_blueprint(categorias_bp, url_prefix="/categorias")
    app.register_blueprint(contas_bp, url_prefix="/contas")
    app.register_blueprint(alertas_bp, url_prefix="/alertas")
