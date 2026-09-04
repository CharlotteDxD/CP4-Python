from datetime import datetime

from flask import Blueprint, request

from app.extensions import db
from app.models import Categoria, Conta, Transacao
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


def _validar_fk(modelo, valor, nome_campo):
    """Valida uma foreign key (conta_id, categoria_id): confere que o valor
    é um inteiro válido e que o registro existe. Devolve (id_convertido,
    None) se ok, ou (None, error_response) se algo estiver errado.

    Existe pra nunca deixar um tipo estranho (lista, dict, texto) chegar
    direto numa query do SQLAlchemy — sem isso, algo como
    {"conta_id": [1, 2]} derruba a rota com um 500 cru em vez de um 400
    claro.
    """
    try:
        valor_id = int(valor)
    except (TypeError, ValueError):
        return None, error_response(f"Campo '{nome_campo}' deve ser um número inteiro", status_code=400)
    if not db.session.get(modelo, valor_id):
        nome_legivel = "Conta" if modelo is Conta else "Categoria"
        return None, error_response(f"{nome_legivel} informada não existe", status_code=404)
    return valor_id, None


def _campos_invalidos_transacao(body, parcial=False):
    """Validações de formato compartilhadas por POST e PUT (tipo, valor,
    data). Não valida conta_id/categoria_id aqui — isso é feito à parte
    com _validar_fk, porque o resultado (o id já convertido pra int)
    precisa ser reaproveitado na hora de gravar."""
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
            return error_response("Campo 'data' deve estar em formato ISO 8601 (texto)", status_code=400)

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

    conta_id, erro = _validar_fk(Conta, body.get("conta_id"), "conta_id")
    if erro:
        return erro

    categoria_id = None
    if body.get("categoria_id") is not None:
        categoria_id, erro = _validar_fk(Categoria, body["categoria_id"], "categoria_id")
        if erro:
            return erro

    # A partir daqui conta_id e categoria_id já são inteiros válidos e
    # existentes no banco — nada mais pode dar 404 depois deste ponto.
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

    # Regra central: toda vez que uma transação é criada, o saldo da
    # conta é recalculado na hora — nunca fica desatualizado.
    recalcular_saldo(conta_id)

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
            novo_categoria_id, erro = _validar_fk(Categoria, body["categoria_id"], "categoria_id")
            if erro:
                return erro

    # Só a partir daqui o banco é tocado — tudo que pode falhar (tipo
    # errado, FK inexistente) já foi validado antes do primeiro write,
    # então a transação nunca fica commitada num estado inválido.
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

    # Se a transação mudou de conta, as duas contas (a antiga e a nova)
    # precisam ter o saldo recalculado — não só a nova.
    for conta_id in contas_afetadas:
        recalcular_saldo(conta_id)

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
