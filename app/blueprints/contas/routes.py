from flask import Blueprint

from app.utils.responses import error_response

contas_bp = Blueprint("contas", __name__)

# TODO (Charles, com o saldo calculado pelo Rafael — Dia 4):
#   GET /contas/:id/saldo -> devolve o saldo atual da conta


@contas_bp.route("/<int:conta_id>/saldo", methods=["GET"])
def saldo_da_conta(conta_id):
    return error_response("Endpoint ainda não implementado — ver TODO em routes.py", status_code=501)
