from flask import Blueprint

from app.utils.responses import error_response

alertas_bp = Blueprint("alertas", __name__)

# TODO (Charles + Anthony — Dia 4):
#   GET /alertas -> lista os alertas gerados pelo agente (com a
#                   recomendação escrita pela IA em cada um)


@alertas_bp.route("", methods=["GET"])
def listar_alertas():
    return error_response("Endpoint ainda não implementado — ver TODO em routes.py", status_code=501)
