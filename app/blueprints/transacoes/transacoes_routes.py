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


POR_PAGINA_PADRAO = 20
POR_PAGINA_MAXIMO = 100


def _data_do_filtro(nome):
    """Lê data_inicio/data_fim da query string. Data sem hora em data_fim vale o dia inteiro."""
    valor = request.args.get(nome)
    if not valor:
        return None, None
    try:
        data = datetime.fromisoformat(valor)
    except ValueError:
        return None, error_response(
            f"Parâmetro '{nome}' deve estar em formato ISO 8601 (ex.: 2026-09-30)",
            status_code=400,
        )
    if nome == "data_fim" and len(valor) == 10:
        data = data.replace(hour=23, minute=59, second=59, microsecond=999999)
    return data, None


def _inteiro_positivo(nome, padrao=None):
    valor = request.args.get(nome)
    if valor is None:
        return padrao, None
    try:
        numero = int(valor)
    except ValueError:
        numero = 0
    if numero < 1:
        return None, error_response(
            f"Parâmetro '{nome}' deve ser um número inteiro maior que zero", status_code=400
        )
    return numero, None


@transacoes_bp.route("", methods=["GET"])
def listar_transacoes():
    """
    Lista transações, com filtros opcionais e paginação opcional
    ---
    tags:
      - Transações
    parameters:
      - in: query
        name: conta_id
        type: integer
        required: false
        description: Filtra por conta
      - in: query
        name: tipo
        type: string
        enum: [entrada, saida]
        required: false
      - in: query
        name: categoria_id
        type: integer
        required: false
      - in: query
        name: sem_categoria
        type: boolean
        required: false
        description: Com true, só transações sem categoria (ignorado se categoria_id vier junto)
      - in: query
        name: busca
        type: string
        required: false
        description: Texto contido na descrição, sem diferenciar maiúsculas de minúsculas
      - in: query
        name: data_inicio
        type: string
        required: false
        description: ISO 8601 (ex. 2026-09-01). Inclui a data informada.
      - in: query
        name: data_fim
        type: string
        required: false
        description: ISO 8601 (ex. 2026-09-30). Data sem hora inclui o dia inteiro.
      - in: query
        name: pagina
        type: integer
        required: false
        description: >
          Liga a paginação. Sem pagina e sem por_pagina, a resposta continua
          sendo a lista completa (formato do CP1).
      - in: query
        name: por_pagina
        type: integer
        required: false
        description: Itens por página (padrão 20, máximo 100)
    responses:
      200:
        description: >
          Sem paginação, dados é a lista de transações. Com paginação, dados é
          {itens, pagina, por_pagina, total, total_paginas}.
      400:
        description: Parâmetro de filtro ou de paginação inválido
    """
    query = Transacao.query

    conta_id = request.args.get("conta_id", type=int)
    if conta_id is not None:
        query = query.filter_by(conta_id=conta_id)

    tipo = request.args.get("tipo")
    if tipo is not None:
        if tipo not in ("entrada", "saida"):
            return error_response("Parâmetro 'tipo' deve ser 'entrada' ou 'saida'", status_code=400)
        query = query.filter_by(tipo=tipo)

    if request.args.get("categoria_id") is not None:
        categoria_id = request.args.get("categoria_id", type=int)
        if categoria_id is None:
            return error_response("Parâmetro 'categoria_id' deve ser um número inteiro", status_code=400)
        query = query.filter_by(categoria_id=categoria_id)
    elif request.args.get("sem_categoria", "").lower() == "true":
        query = query.filter(Transacao.categoria_id.is_(None))

    busca = request.args.get("busca", "").strip()
    if busca:
        # '!' escapa % e _ pra busca ser por texto literal, não por padrão LIKE
        literal = busca.replace("!", "!!").replace("%", "!%").replace("_", "!_")
        query = query.filter(Transacao.descricao.ilike(f"%{literal}%", escape="!"))

    data_inicio, erro = _data_do_filtro("data_inicio")
    if erro:
        return erro
    data_fim, erro = _data_do_filtro("data_fim")
    if erro:
        return erro
    if data_inicio and data_fim and data_inicio > data_fim:
        return error_response("'data_inicio' não pode ser depois de 'data_fim'", status_code=400)
    if data_inicio:
        query = query.filter(Transacao.data >= data_inicio)
    if data_fim:
        query = query.filter(Transacao.data <= data_fim)

    query = query.order_by(Transacao.data.desc(), Transacao.id.desc())

    paginar = "pagina" in request.args or "por_pagina" in request.args
    if not paginar:
        return success_response(data=[t.to_dict() for t in query.all()])

    pagina, erro = _inteiro_positivo("pagina", padrao=1)
    if erro:
        return erro
    por_pagina, erro = _inteiro_positivo("por_pagina", padrao=POR_PAGINA_PADRAO)
    if erro:
        return erro
    por_pagina = min(por_pagina, POR_PAGINA_MAXIMO)

    total = query.order_by(None).count()
    itens = query.offset((pagina - 1) * por_pagina).limit(por_pagina).all()
    return success_response(data={
        "itens": [t.to_dict() for t in itens],
        "pagina": pagina,
        "por_pagina": por_pagina,
        "total": total,
        "total_paginas": (total + por_pagina - 1) // por_pagina,
    })


@transacoes_bp.route("/<int:transacao_id>", methods=["GET"])
def detalhar_transacao(transacao_id):
    """
    Detalha uma transação
    ---
    tags:
      - Transações
    parameters:
      - in: path
        name: transacao_id
        type: integer
        required: true
    responses:
      200:
        description: Dados da transação
      404:
        description: Transação não encontrada
    """
    transacao = db.session.get(Transacao, transacao_id)
    if not transacao:
        return error_response("Transação não encontrada", status_code=404)
    return success_response(data=transacao.to_dict())


@transacoes_bp.route("", methods=["POST"])
def criar_transacao():
    """
    Cria uma transação. Se a categoria não vier informada, a IA tenta
    categorizar pela descrição. Recalcula o saldo da conta e, se o saldo
    projetado ficar negativo, cria um Alerta com recomendação da IA.
    ---
    tags:
      - Transações
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [valor, tipo, conta_id]
          properties:
            valor:
              type: number
              example: 150.50
            tipo:
              type: string
              enum: [entrada, saida]
            categoria_id:
              type: integer
              description: Opcional — se ausente, a IA tenta escolher pela descrição
            conta_id:
              type: integer
              example: 1
            descricao:
              type: string
              example: "Pagamento da conta de energia elétrica"
            data:
              type: string
              description: ISO 8601. Se for futura, entra só no saldo projetado
              example: "2026-09-15T10:00:00"
    responses:
      201:
        description: >
          Transação criada. Se a IA falhar (erro, timeout ou nenhuma
          categoria cadastrada), a transação ainda é salva com
          categoria_id nulo — a IA nunca bloqueia o cadastro.
      400:
        description: Corpo da requisição inválido
      404:
        description: Conta informada não existe
    """
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
    """
    Atualiza uma transação e recalcula saldo/projeção da(s) conta(s)
    ---
    tags:
      - Transações
    parameters:
      - in: path
        name: transacao_id
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            valor:
              type: number
            tipo:
              type: string
              enum: [entrada, saida]
            categoria_id:
              type: integer
            conta_id:
              type: integer
            descricao:
              type: string
            data:
              type: string
    responses:
      200:
        description: Transação atualizada
      400:
        description: Corpo inválido
      404:
        description: Transação não encontrada
    """
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
    """
    Remove uma transação e recalcula saldo/projeção da conta
    ---
    tags:
      - Transações
    parameters:
      - in: path
        name: transacao_id
        type: integer
        required: true
    responses:
      200:
        description: Transação removida
      404:
        description: Transação não encontrada
    """
    transacao = db.session.get(Transacao, transacao_id)
    if not transacao:
        return error_response("Transação não encontrada", status_code=404)

    conta_id = transacao.conta_id
    db.session.delete(transacao)
    db.session.commit()

    _avaliar_risco(conta_id)
    return success_response(message="Transação removida com sucesso")
