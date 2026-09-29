from flask import Blueprint, request
from sqlalchemy import Date, case, func

from app.extensions import db
from app.models import Alerta, Categoria, Conta, Transacao
from app.services.saldo import _agora
from app.utils.responses import error_response, success_response

dashboard_bp = Blueprint("dashboard", __name__)


def _evolucao_diaria(conta_id, agora):
    """Saldo acumulado ao fim de cada dia com movimento e o saldo atual (mesma regra do saldo.py: data <= agora).

    O banco agrupa por dia e devolve uma linha por dia com movimento, não uma
    por transação; só o acumulado corrido é feito aqui.
    """
    delta = case(
        (Transacao.tipo == "entrada", Transacao.valor),
        (Transacao.tipo == "saida", -Transacao.valor),
        else_=0,
    )
    dia = func.date(Transacao.data, type_=Date)
    linhas = (
        db.session.query(
            dia,
            func.sum(delta),
            func.sum(case((Transacao.data <= agora, delta), else_=0)),
        )
        .filter(Transacao.conta_id == conta_id)
        .group_by(dia)
        .order_by(dia)
        .all()
    )

    hoje = agora.date()
    evolucao = []
    saldo = 0.0
    saldo_atual = 0.0
    for data_dia, movimento, ja_vencido in linhas:
        saldo = round(saldo + float(movimento), 2)
        saldo_atual += float(ja_vencido)
        evolucao.append({"data": data_dia.isoformat(), "saldo": saldo, "projetado": data_dia > hoje})
    return evolucao, round(saldo_atual, 2)


def _data_saldo_negativo(evolucao, saldo_atual, agora):
    if saldo_atual < 0:
        return agora.date().isoformat()
    return next((p["data"] for p in evolucao if p["projetado"] and p["saldo"] < 0), None)


@dashboard_bp.route("/resumo", methods=["GET"])
def resumo():
    """
    Resumo da conta para o painel de controle
    ---
    tags:
      - Dashboard
    parameters:
      - in: query
        name: conta_id
        type: integer
        required: true
        example: 1
    responses:
      200:
        description: >
          Saldo atual e projetado, totais do mês corrente (até hoje), saídas
          do mês por categoria, evolução diária do saldo (dias futuros vêm com
          projetado=true), a primeira data em que o saldo fica negativo (ou
          null) e a quantidade de alertas da conta.
        examples:
          application/json: {
            "sucesso": true,
            "dados": {
              "conta": {"id": 1, "nome": "Padaria Boa Massa", "saldo_atual": 11308.6, "saldo_projetado": -4841.4},
              "totais_mes": {"entradas": 23650.0, "saidas": 12341.4},
              "saidas_por_categoria": [{"categoria": "Folha de pagamento", "total": 4200.0}],
              "evolucao_saldo": [{"data": "2026-09-01", "saldo": 6200.0, "projetado": false}],
              "data_saldo_negativo": "2026-10-10",
              "alertas_abertos": 3
            }
          }
      400:
        description: conta_id ausente ou inválido
      404:
        description: Conta não encontrada
    """
    conta_id = request.args.get("conta_id", type=int)
    if conta_id is None:
        return error_response(
            "Parâmetro 'conta_id' é obrigatório e deve ser um número inteiro", status_code=400
        )
    conta = db.session.get(Conta, conta_id)
    if not conta:
        return error_response("Conta não encontrada", status_code=404)

    agora = _agora()
    inicio_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    do_mes = (
        Transacao.conta_id == conta_id,
        Transacao.data >= inicio_mes,
        Transacao.data <= agora,
    )

    totais = dict(
        db.session.query(Transacao.tipo, func.sum(Transacao.valor))
        .filter(*do_mes)
        .group_by(Transacao.tipo)
        .all()
    )

    total_saida = func.sum(Transacao.valor)
    por_categoria = (
        db.session.query(Categoria.nome, total_saida)
        .select_from(Transacao)
        .outerjoin(Categoria, Transacao.categoria_id == Categoria.id)
        .filter(*do_mes, Transacao.tipo == "saida")
        .group_by(Categoria.id, Categoria.nome)
        .order_by(total_saida.desc())
        .all()
    )

    evolucao, saldo_atual = _evolucao_diaria(conta_id, agora)
    saldo_projetado = evolucao[-1]["saldo"] if evolucao else 0.0

    alertas = db.session.query(func.count(Alerta.id)).filter(Alerta.conta_id == conta_id).scalar()

    return success_response(data={
        "conta": {
            "id": conta.id,
            "nome": conta.nome,
            "saldo_atual": saldo_atual,
            "saldo_projetado": saldo_projetado,
        },
        "totais_mes": {
            "entradas": float(totais.get("entrada") or 0),
            "saidas": float(totais.get("saida") or 0),
        },
        "saidas_por_categoria": [
            {"categoria": nome or "Sem categoria", "total": float(total)}
            for nome, total in por_categoria
        ],
        "evolucao_saldo": evolucao,
        "data_saldo_negativo": _data_saldo_negativo(evolucao, saldo_atual, agora),
        "alertas_abertos": alertas,
    })
