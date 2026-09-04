from flask import Blueprint

from app.extensions import db
from app.models import Conta
from app.services.saldo import calcular_saldo_projetado
from app.utils.responses import error_response, success_response

contas_bp = Blueprint("contas", __name__)


@contas_bp.route("/<int:conta_id>/saldo", methods=["GET"])
def saldo_da_conta(conta_id):
    conta = db.session.get(Conta, conta_id)
    if not conta:
        return error_response("Conta não encontrada", status_code=404)

    return success_response(data={
        "conta_id": conta.id,
        "nome": conta.nome,
        "saldo_atual": float(conta.saldo_atual),
        # bônus: já usa a função do Rafael pra dar visibilidade do risco
        # antes mesmo do endpoint /alertas existir.
        "saldo_projetado": float(calcular_saldo_projetado(conta_id)),
    })
