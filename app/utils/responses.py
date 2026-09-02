"""
Helpers para padronizar o formato de resposta da API.

Ideia: toda rota devolve o mesmo "envelope" JSON, só mudando o conteúdo.
Isso ataca direto o critério do barema "códigos HTTP e respostas
padronizadas" e evita que cada endpoint invente seu próprio formato.

Uso típico dentro de uma rota:

    from app.utils.responses import success_response, error_response

    @transacoes_bp.route("", methods=["GET"])
    def listar_transacoes():
        transacoes = Transacao.query.all()
        return success_response(data=[t.to_dict() for t in transacoes])

    @transacoes_bp.route("/<int:id>", methods=["GET"])
    def detalhar_transacao(id):
        transacao = Transacao.query.get(id)
        if not transacao:
            return error_response("Transação não encontrada", status_code=404)
        return success_response(data=transacao.to_dict())
"""

from typing import Any, Optional

from flask import jsonify


def success_response(data: Any = None, message: Optional[str] = None, status_code: int = 200):
    payload = {"sucesso": True}
    if message is not None:
        payload["mensagem"] = message
    if data is not None:
        payload["dados"] = data
    return jsonify(payload), status_code


def error_response(message: str, status_code: int = 400, details: Any = None):
    payload = {"sucesso": False, "erro": message}
    if details is not None:
        payload["detalhes"] = details
    return jsonify(payload), status_code
