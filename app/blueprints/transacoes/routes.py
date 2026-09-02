from flask import Blueprint

from app.utils.responses import error_response

transacoes_bp = Blueprint("transacoes", __name__)

# TODO (Charles, com apoio do Rafael e do Anthony — Dias 2, 3 e 5):
#   GET    /transacoes        -> lista todas as transações
#   GET    /transacoes/:id    -> detalha uma transação
#   POST   /transacoes        -> cria a transação; se a categoria não vier
#                                 informada, chama a categorização por IA
#                                 (Anthony), recalcula o saldo da conta
#                                 (Rafael) e cria um Alerta se o saldo
#                                 projetado ficar negativo
#   PUT    /transacoes/:id    -> atualiza uma transação
#   DELETE /transacoes/:id    -> remove uma transação
#
# Essa é a regra de negócio central do projeto — é ela que faz o Tema 7
# (agente de IA) acontecer de verdade, não só um CRUD comum.


@transacoes_bp.route("", methods=["GET"])
def listar_transacoes():
    return error_response("Endpoint ainda não implementado — ver TODO em routes.py", status_code=501)
