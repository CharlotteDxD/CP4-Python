from datetime import UTC, datetime, timedelta

from app import create_app
from app.extensions import db
from app.models import Conta, Transacao
from app.services.saldo import calcular_saldo_projetado, nivel_risco, recalcular_saldo


def _app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
    return app


def test_saldo_atual_ignora_transacao_futura():
    app = _app()
    with app.app_context():
        conta = Conta(nome="Conta Teste", saldo_atual=0)
        db.session.add(conta)
        db.session.commit()

        ontem = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)
        amanha = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1)

        db.session.add(Transacao(valor=200, tipo="entrada", conta_id=conta.id, data=ontem))
        db.session.add(Transacao(valor=50, tipo="saida", conta_id=conta.id, data=amanha))
        db.session.commit()

        resultado = recalcular_saldo(conta.id)
        projetado = calcular_saldo_projetado(conta.id)

        assert float(resultado.saldo_atual) == 200.0
        assert float(projetado) == 150.0


def test_projetado_negativo_nao_conta_duas_vezes():
    app = _app()
    with app.app_context():
        conta = Conta(nome="Conta Teste", saldo_atual=0)
        db.session.add(conta)
        db.session.commit()

        ontem = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)
        amanha = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1)

        db.session.add(Transacao(valor=100, tipo="entrada", conta_id=conta.id, data=ontem))
        db.session.add(Transacao(valor=250, tipo="saida", conta_id=conta.id, data=amanha))
        db.session.commit()

        recalcular_saldo(conta.id)
        projetado = calcular_saldo_projetado(conta.id)

        assert float(db.session.get(Conta, conta.id).saldo_atual) == 100.0
        assert float(projetado) == -150.0
        assert nivel_risco(projetado) == "medio"


def test_saldo_conta_inexistente_retorna_none():
    app = _app()
    with app.app_context():
        assert recalcular_saldo(999) is None
        assert calcular_saldo_projetado(999) is None
