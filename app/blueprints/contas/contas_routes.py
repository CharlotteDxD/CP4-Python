from flask import Blueprint

from app.services.saldo import calcular_saldo_projetado, recalcular_saldo
from app.utils.responses import error_response, success_response

contas_bp = Blueprint("contas", __name__)


@contas_bp.route("/<int:conta_id>/saldo", methods=["GET"])
def saldo_da_conta(conta_id):
    """
    Devolve o saldo atual e o saldo projetado da conta
    ---
    tags:
      - Contas
    parameters:
      - in: path
        name: conta_id
        type: integer
        required: true
    responses:
      200:
        description: Saldo atual e projetado da conta
      404:
        description: Conta não encontrada
    """
    # recalcula na leitura: transação com data futura que já venceu
    # não muda o saldo_atual guardado até a próxima escrita na conta
    conta = recalcular_saldo(conta_id)
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