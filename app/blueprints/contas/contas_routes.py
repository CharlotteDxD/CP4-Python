from flask import Blueprint, request

from app.extensions import db
from app.models import Conta
from app.services.saldo import calcular_saldo_projetado, recalcular_saldo
from app.utils.responses import error_response, success_response

contas_bp = Blueprint("contas", __name__)


def _nome_da_conta():
    """Lê e valida 'nome' do corpo. Devolve (nome, resposta_de_erro)."""
    body = request.get_json(silent=True) or {}
    nome = str(body.get("nome") or "").strip()
    if not nome:
        return None, error_response("Campo 'nome' é obrigatório", status_code=400)
    if len(nome) > 120:
        return None, error_response("Campo 'nome' deve ter no máximo 120 caracteres", status_code=400)
    return nome, None


def _conta_com_saldos(conta):
    dados = conta.to_dict()
    dados["saldo_projetado"] = float(calcular_saldo_projetado(conta.id))
    return dados


@contas_bp.route("", methods=["GET"])
def listar_contas():
    """
    Lista as contas com saldo atual e projetado
    ---
    tags:
      - Contas
    responses:
      200:
        description: Lista de contas
    """
    contas = Conta.query.order_by(Conta.id).all()
    for conta in contas:
        recalcular_saldo(conta.id)
    return success_response(data=[_conta_com_saldos(c) for c in contas])


@contas_bp.route("", methods=["POST"])
def criar_conta():
    """
    Cria uma conta. O saldo começa em zero e passa a ser calculado pelas transações.
    ---
    tags:
      - Contas
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [nome]
          properties:
            nome:
              type: string
              example: "Caixa da loja"
    responses:
      201:
        description: Conta criada
      400:
        description: Campo 'nome' ausente ou maior que 120 caracteres
    """
    nome, erro = _nome_da_conta()
    if erro:
        return erro

    conta = Conta(nome=nome, saldo_atual=0)
    db.session.add(conta)
    db.session.commit()
    return success_response(data=_conta_com_saldos(conta), status_code=201)


@contas_bp.route("/<int:conta_id>", methods=["PUT"])
def atualizar_conta(conta_id):
    """
    Renomeia uma conta
    ---
    tags:
      - Contas
    parameters:
      - in: path
        name: conta_id
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [nome]
          properties:
            nome:
              type: string
    responses:
      200:
        description: Conta atualizada
      400:
        description: Campo 'nome' ausente ou maior que 120 caracteres
      404:
        description: Conta não encontrada
    """
    conta = db.session.get(Conta, conta_id)
    if not conta:
        return error_response("Conta não encontrada", status_code=404)

    nome, erro = _nome_da_conta()
    if erro:
        return erro

    conta.nome = nome
    db.session.commit()
    return success_response(data=_conta_com_saldos(conta))


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