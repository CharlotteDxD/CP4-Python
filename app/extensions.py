"""
Instâncias únicas das extensões Flask, sem estarem presas a nenhum app
específico ainda (padrão "init_app" do Flask).

Isso existe separado do __init__.py só para evitar import circular:
- app/__init__.py importa db e migrate daqui para inicializar
- app/models/*.py importa db daqui para declarar as tabelas
Se tudo isso estivesse dentro de __init__.py, um importaria o outro em
loop.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()
