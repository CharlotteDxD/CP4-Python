from datetime import datetime

from flask import Blueprint, request

from app.extensions import db
from app.models import Categoria, Transacao
from app.services.saldo import recalcular_saldo
from app.utils.responses import error_response, success_response

transacoes_bp = Blueprint("transacoes", __name__)

# TODO (Anthony — Dia 5): se "categoria_id" não vier no corpo do POST,
# chamar a categorização por IA aqui antes de criar a Transacao.
# TODO (Charles/Anthony — Dia 4/5): depois do recalcular_saldo, checar
# calcular_saldo_projetado(conta_id) e criar um Alerta (com recomendação
# da IA) se a projeção ficar negativa.
#
# Essa é a regra de negócio central do projeto — é ela que faz o Tema 7
# (agente de IA) acontecer de verdade, não só um CRUD comum.


def _campos_invalidos_transacao(body, parcial=False):
    """Validações compartilhadas por POST e PUT. Devolve uma error_response
    pronta se algo estiver errado, ou None se estiver tudo certo."""
    if "tipo" in body and body["tipo"] not in ("entrada", "saida"):
        return error_response("Campo 'tipo' deve ser 'entrada' ou 'saida'", status_code=400)

    if "valor" in body:
        try:
            valor = float(body["valor"])
        except (TypeError, ValueError):
            return error_response("Campo 'valor' deve ser numérico", status_code=400)
        if valor <= 0:
            return error_response("Campo 'valor' deve ser maior que zero", status_code=400)

    if "categoria_id" in body and body["categoria_id"] is not None:
        if not db.session.get(Categoria, body["categoria_id"]):
            return error_response("Categoria informada não existe", status_code=404)

    if "data" in body and body["data"]:
        try:
            datetime.fromisoformat(body["data"])
        except ValueError:
            return error_response("Campo 'data' deve estar em formato ISO 8601", status_code=400)

    if not parcial:
        faltando = [c for c in ("valor", "tipo", "conta_id") if body.get(c) is None]
        if faltando:
            return error_response(
                f"Campos obrigatórios faltando: {', '.join(faltando)}", status_code=400
            )

    return None


@transacoes_bp.route("", methods=["GET"])
def listar_transacoes():
    transacoes = Transacao.query.order_by(Transacao.data.desc()).all()
    return success_response(data=[t.to_dict() for t in transacoes])


@transacoes_bp.route("/<int:transacao_id>", methods=["GET"])
def detalhar_transacao(transacao_id):
    transacao = db.session.get(Transacao, transacao_id)
    if not transacao:
        return error_response("Transação não encontrada", status_code=404)
    return success_response(data=transacao.to_dict())


@transacoes_bp.route("", methods=["POST"])
def criar_transacao():
    body = request.get_json(silent=True) or {}

    erro = _campos_invalidos_transacao(body)
    if erro:
        return erro

    transacao = Transacao(
        valor=float(body["valor"]),
        tipo=body["tipo"],
        conta_id=body["conta_id"],
        categoria_id=body.get("categoria_id"),
        descricao=body.get("descricao"),
    )
    if body.get("data"):
        transacao.data = datetime.fromisoformat(body["data"])

    db.session.add(transacao)
    db.session.commit()

    # Regra central: toda vez que uma transação é criada, o saldo da
    # conta é recalculado na hora — nunca fica desatualizado.
    if recalcular_saldo(transacao.conta_id) is None:
        db.session.delete(transacao)
        db.session.commit()
        return error_response("Conta informada não existe", status_code=404)

    return success_response(data=transacao.to_dict(), status_code=201)


@transacoes_bp.route("/<int:transacao_id>", methods=["PUT"])
def atualizar_transacao(transacao_id):
    transacao = db.session.get(Transacao, transacao_id)
    if not transacao:
        return error_response("Transação não encontrada", status_code=404)

    body = request.get_json(silent=True) or {}
    erro = _campos_invalidos_transacao(body, parcial=True)
    if erro:
        return erro

    contas_afetadas = {transacao.conta_id}

    if "valor" in body:
        transacao.valor = float(body["valor"])
    if "tipo" in body:
        transacao.tipo = body["tipo"]
    if "categoria_id" in body:
        transacao.categoria_id = body["categoria_id"]
    if "descricao" in body:
        transacao.descricao = body["descricao"]
    if "data" in body and body["data"]:
        transacao.data = datetime.fromisoformat(body["data"])
    if "conta_id" in body and body["conta_id"] != transacao.conta_id:
        transacao.conta_id = body["conta_id"]
        contas_afetadas.add(body["conta_id"])

    db.session.commit()

    # Se a transação mudou de conta, as duas contas (a antiga e a nova)
    # precisam ter o saldo recalculado — não só a nova.
    for conta_id in contas_afetadas:
        if recalcular_saldo(conta_id) is None:
            return error_response("Conta informada não existe", status_code=404)

    return success_response(data=transacao.to_dict())


@transacoes_bp.route("/<int:transacao_id>", methods=["DELETE"])
def remover_transacao(transacao_id):
    transacao = db.session.get(Transacao, transacao_id)
    if not transacao:
        return error_response("Transação não encontrada", status_code=404)

    conta_id = transacao.conta_id
    db.session.delete(transacao)
    db.session.commit()

    recalcular_saldo(conta_id)

    return success_response(message="Transação removida com sucesso")
