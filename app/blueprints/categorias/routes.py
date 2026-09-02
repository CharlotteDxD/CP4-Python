from flask import Blueprint

from app.utils.responses import error_response

categorias_bp = Blueprint("categorias", __name__)

# TODO (Charles — Dia 4):
#   GET  /categorias -> lista as categorias
#   POST /categorias -> cria uma categoria


@categorias_bp.route("", methods=["GET"])
def listar_categorias():
    return error_response("Endpoint ainda não implementado — ver TODO em routes.py", status_code=501)
