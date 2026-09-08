from datetime import datetime

from flask import Blueprint, request

from app.extensions import db
from app.models import Alerta, Categoria, Conta, Transacao
from app.services.ia import IAServiceError, categorizar_transacao, gerar_recomendacao
from app.services.saldo import (
    calcular_saldo_projetado,
    nivel_risco,
    recalcular_saldo,
)
from app.utils.responses import error_response, success_response

transacoes_bp = Blueprint("transacoes", __name__)


def _validar_fk(modelo, valor, nome_campo):
    try:
        valor_id = int(valor)
    except (TypeError, ValueError):
        return None, error_response(
            f"Campo '{nome_campo}' deve ser um número inteiro", status_code=400
        )
    if not db.session.get(modelo, valor_id):
        nome_legivel = "Conta" if modelo is Conta else "Categoria"
        return None, error_response(f"{nome_legivel} informada não existe", status_code=404)
    return valor_id, None


def _campos_invalidos_transacao(body, parcial=False):
    if "tipo" in body and body["tipo"] not in ("entrada", "saida"):
        return error_response("Campo 'tipo' deve ser 'entrada' ou 'saida'", status_code=400)

    if "valor" in body:
        try:
            valor = float(body["valor"])
        except (TypeError, ValueError):
            return error_response("Campo 'valor' deve ser numérico", status_code=400)
        if valor <= 0:
            return error_response("Campo 'valor' deve ser maior que zero", status_code=400)

    if "data" in body and body["data"]:
        try:
            datetime.fromisoformat(body["data"])
        except (TypeError, ValueError):
            return error_response(
                "Campo 'data' deve estar em formato ISO 8601 (texto)", status_code=400
            )

    if not parcial:
        faltando = [c for c in ("valor", "tipo", "conta_id") if body.get(c) is None]
        if faltando:
            return error_response(
                f"Campos obrigatórios faltando: {', '.join(faltando)}", status_code=400
            )

    return None


def _avaliar_risco(conta_id):
    """Recalcula saldo, projeta, e cria Alerta com recomendação se ficar negativo.

    A IA nunca bloqueia o fluxo: se falhar, o alerta ainda é gravado.
    """
    recalcular_saldo(conta_id)
    projetado = calcular_saldo_projetado(conta_id)
    if projetado is None:
        return None, None

    nivel = nivel_risco(float(projetado))
    if not nivel:
        return None, None

    mensagem = (
        f"Saldo projetado da conta ficou negativo: R$ {float(projetado):.2f}"
    )
    aviso_ia = None
    recomendacao_texto = None
    try:
        recomendacao_texto = gerar_recomendacao(mensagem)
    except IAServiceError as exc:
        aviso_ia = str(exc)

    alerta = Alerta(
        conta_id=conta_id,
        mensagem=mensagem,
        recomendacao=recomendacao_texto,
        nivel_risco=nivel,
    )
    db.session.add(alerta)
    db.session.commit()
    return alerta, aviso_ia


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

    conta_id, erro = _validar_fk(Conta, body.get("conta_id"), "conta_id")
    if erro:
        return erro

    categoria_id = None
    aviso_ia = None
    if body.get("categoria_id") is not None:
        categoria_id, erro = _validar_fk(Categoria, body["categoria_id"], "categoria_id")
        if erro:
            return erro
    elif body.get("descricao"):
        categorias = Categoria.query.all()
        try:
            nome = categorizar_transacao(body["descricao"], [c.nome for c in categorias])
            categoria = next((c for c in categorias if c.nome == nome), None)
            categoria_id = categoria.id if categoria else None
        except IAServiceError as exc:
            aviso_ia = str(exc)

    transacao = Transacao(
        valor=float(body["valor"]),
        tipo=body["tipo"],
        conta_id=conta_id,
        categoria_id=categoria_id,
        descricao=body.get("descricao"),
    )
    if body.get("data"):
        transacao.data = datetime.fromisoformat(body["data"])

    db.session.add(transacao)
    db.session.commit()

    alerta, aviso_risco = _avaliar_risco(conta_id)
    aviso_ia = aviso_ia or aviso_risco

    payload = transacao.to_dict()
    if aviso_ia:
        payload["aviso_ia"] = aviso_ia
    if alerta:
        payload["alerta_gerado"] = alerta.to_dict()
    payload["saldo_projetado"] = float(calcular_saldo_projetado(conta_id))

    return success_response(data=payload, status_code=201)


@transacoes_bp.route("/<int:transacao_id>", methods=["PUT"])
def atualizar_transacao(transacao_id):
    transacao = db.session.get(Transacao, transacao_id)
    if not transacao:
        return error_response("Transação não encontrada", status_code=404)

    body = request.get_json(silent=True) or {}
    erro = _campos_invalidos_transacao(body, parcial=True)
    if erro:
        return erro

    novo_conta_id = None
    if "conta_id" in body:
        novo_conta_id, erro = _validar_fk(Conta, body["conta_id"], "conta_id")
        if erro:
            return erro

    novo_categoria_id = "sem_alteracao"
    if "categoria_id" in body:
        if body["categoria_id"] is None:
            novo_categoria_id = None
        else:
            novo_categoria_id, erro = _validar_fk(
                Categoria, body["categoria_id"], "categoria_id"
            )
            if erro:
                return erro

    contas_afetadas = {transacao.conta_id}

    if "valor" in body:
        transacao.valor = float(body["valor"])
    if "tipo" in body:
        transacao.tipo = body["tipo"]
    if novo_categoria_id != "sem_alteracao":
        transacao.categoria_id = novo_categoria_id
    if "descricao" in body:
        transacao.descricao = body["descricao"]
    if "data" in body and body["data"]:
        transacao.data = datetime.fromisoformat(body["data"])
    if novo_conta_id is not None and novo_conta_id != transacao.conta_id:
        transacao.conta_id = novo_conta_id
        contas_afetadas.add(novo_conta_id)

    db.session.commit()

    alerta = None
    aviso_ia = None
    for cid in contas_afetadas:
        a, aviso = _avaliar_risco(cid)
        if a:
            alerta = a
        if aviso:
            aviso_ia = aviso

    payload = transacao.to_dict()
    if aviso_ia:
        payload["aviso_ia"] = aviso_ia
    if alerta:
        payload["alerta_gerado"] = alerta.to_dict()
    return success_response(data=payload)


@transacoes_bp.route("/<int:transacao_id>", methods=["DELETE"])
def remover_transacao(transacao_id):
    transacao = db.session.get(Transacao, transacao_id)
    if not transacao:
        return error_response("Transação não encontrada", status_code=404)

    conta_id = transacao.conta_id
    db.session.delete(transacao)
    db.session.commit()

    _avaliar_risco(conta_id)
    return success_response(message="Transação removida com sucesso")
