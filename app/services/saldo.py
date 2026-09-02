from app.extensions import db
from app.models import Conta


def recalcular_saldo(conta_id):
    """Recalcula e persiste o saldo_atual de uma Conta somando suas transações.

    entrada soma, saida subtrai. Retorna a Conta atualizada, ou None se
    a conta não existir.
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