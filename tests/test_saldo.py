from app import create_app
from app.extensions import db
from app.models import Conta, Transacao
from app.services.saldo import recalcular_saldo


def _app_com_banco_limpo():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
    return app


def test_saldo_soma_entrada_e_subtrai_saida():
    app = _app_com_banco_limpo()

    with app.app_context():
        conta = Conta(nome="Conta Teste", saldo_atual=0)
        db.session.add(conta)
        db.session.commit()

        db.session.add(Transacao(valor=100, tipo="entrada", conta_id=conta.id))
        db.session.add(Transacao(valor=30, tipo="saida", conta_id=conta.id))
        db.session.commit()

        resultado = recalcular_saldo(conta.id)

        assert float(resultado.saldo_atual) == 70.0


def test_saldo_conta_inexistente_retorna_none():
    app = _app_com_banco_limpo()

    with app.app_context():
        assert recalcular_saldo(999) is None