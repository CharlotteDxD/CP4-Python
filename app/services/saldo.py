from app.extensions import db
from app.models import Conta
from datetime import datetime, UTC


def recalcular_saldo(conta_id):
    """Recalcula e persiste o saldo_atual de uma Conta somando suas transações.
    ...
    """
    conta = db.session.get(Conta, conta_id)
    if conta is None:
        return None

    total = 0
    for t in conta.transacoes:
        if t.tipo == "entrada":
            total += t.valor
        elif t.tipo == "saida":
            total -= t.valor

    conta.saldo_atual = total
    db.session.commit()
    return conta


def calcular_saldo_projetado(conta_id):
    """Estima o saldo futuro somando transações com data > agora ao saldo_atual.
    ...
    """
    conta = db.session.get(Conta, conta_id)
    if conta is None:
        return None

    agora = datetime.now(UTC).replace(tzinfo=None)
    projetado = conta.saldo_atual

    for t in conta.transacoes:
        if t.data and t.data > agora:
            if t.tipo == "entrada":
                projetado += t.valor
            elif t.tipo == "saida":
                projetado -= t.valor

    return projetado