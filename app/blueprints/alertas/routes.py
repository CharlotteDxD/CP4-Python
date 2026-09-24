from flask import Blueprint

from app.models import Alerta
from app.utils.responses import success_response

alertas_bp = Blueprint("alertas", __name__)


@alertas_bp.route("", methods=["GET"])
def listar_alertas():
    """
    Lista os alertas gerados pelo agente (com a recomendação escrita pela IA)
    ---
    tags:
      - Alertas
    responses:
      200:
        description: Lista de alertas
    """
    alertas = Alerta.query.order_by(Alerta.data.desc()).all()
    return success_response(data=[a.to_dict() for a in alertas])
