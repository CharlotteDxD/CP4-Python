"""Saldo atual e saldo projetado da Conta.

Regra (corrige a conta dupla):
- saldo_atual  = soma das transações com data <= agora
- saldo_projetado = soma de TODAS as transações (passado + futuro)

Assim o recálculo e a projeção não se sobrepõem.
"""

from datetime import UTC, datetime

from app.extensions import db
from app.models import Conta


def _agora():
    return datetime.now(UTC).replace(tzinfo=None)


def _delta(transacao):
    if transacao.tipo == "entrada":
        return float(transacao.valor)
    if transacao.tipo == "saida":
        return -float(transacao.valor)
    return 0.0


def recalcular_saldo(conta_id):
    """Recalcula e persiste o saldo_atual (somente o que já venceu)."""
    conta = db.session.get(Conta, conta_id)
    if conta is None:
        return None

    agora = _agora()
    total = 0.0
    for t in conta.transacoes:
        if t.data is None or t.data <= agora:
            total += _delta(t)

    conta.saldo_atual = total
    db.session.commit()
    return conta


def calcular_saldo_projetado(conta_id):
    """Estima o caixa futuro somando todas as transações da conta."""
    conta = db.session.get(Conta, conta_id)
    if conta is None:
        return None

    return sum(_delta(t) for t in conta.transacoes)


def nivel_risco(projetado):
    if projetado is None or projetado >= 0:
        return None
    if projetado <= -500:
        return "alto"
    if projetado <= -100:
        return "medio"
    return "baixo"
