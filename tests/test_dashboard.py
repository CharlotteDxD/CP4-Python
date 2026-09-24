from datetime import UTC, datetime, timedelta

from app import create_app
from app.extensions import db
from app.models import Alerta, Categoria, Conta, Transacao


def _agora():
    return datetime.now(UTC).replace(tzinfo=None)


def _app_com_cenario():
    """Conta com 1000 de entrada e 500 de saída já realizados e 800 de saída agendada."""
    app = create_app("testing")
    agora = _agora()
    futuro = agora + timedelta(days=5)
    with app.app_context():
        db.create_all()
        conta = Conta(nome="Padaria", saldo_atual=0)
        aluguel = Categoria(nome="Aluguel")
        db.session.add_all([conta, aluguel])
        db.session.flush()
        db.session.add_all([
            Transacao(valor=1000, tipo="entrada", conta_id=conta.id, data=agora - timedelta(seconds=2)),
            Transacao(valor=300, tipo="saida", conta_id=conta.id, categoria_id=aluguel.id, data=agora - timedelta(seconds=1)),
            Transacao(valor=200, tipo="saida", conta_id=conta.id, data=agora - timedelta(seconds=1)),
            Transacao(valor=800, tipo="saida", conta_id=conta.id, data=futuro),
            Alerta(conta_id=conta.id, mensagem="Saldo projetado negativo", nivel_risco="medio"),
        ])
        db.session.commit()
        return app, conta.id, futuro.date().isoformat()


def test_resumo_devolve_saldos_totais_e_categorias():
    app, conta_id, _ = _app_com_cenario()

    response = app.test_client().get(f"/dashboard/resumo?conta_id={conta_id}")

    assert response.status_code == 200
    dados = response.get_json()["dados"]
    assert dados["conta"] == {"id": conta_id, "nome": "Padaria", "saldo_atual": 500.0, "saldo_projetado": -300.0}
    assert dados["totais_mes"] == {"entradas": 1000.0, "saidas": 500.0}
    assert dados["saidas_por_categoria"] == [
        {"categoria": "Aluguel", "total": 300.0},
        {"categoria": "Sem categoria", "total": 200.0},
    ]
    assert dados["alertas_abertos"] == 1


def test_resumo_marca_projecao_e_data_em_que_o_caixa_fica_negativo():
    app, conta_id, data_futura = _app_com_cenario()

    dados = app.test_client().get(f"/dashboard/resumo?conta_id={conta_id}").get_json()["dados"]

    ultimo = dados["evolucao_saldo"][-1]
    assert ultimo == {"data": data_futura, "saldo": -300.0, "projetado": True}
    assert dados["evolucao_saldo"][0]["projetado"] is False
    assert dados["data_saldo_negativo"] == data_futura


def test_resumo_de_conta_sem_transacoes_devolve_zeros():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        conta = Conta(nome="Vazia", saldo_atual=0)
        db.session.add(conta)
        db.session.commit()
        conta_id = conta.id

    dados = app.test_client().get(f"/dashboard/resumo?conta_id={conta_id}").get_json()["dados"]

    assert dados["conta"]["saldo_projetado"] == 0.0
    assert dados["evolucao_saldo"] == []
    assert dados["saidas_por_categoria"] == []
    assert dados["data_saldo_negativo"] is None


def test_resumo_sem_conta_id_retorna_400():
    app = create_app("testing")

    response = app.test_client().get("/dashboard/resumo")

    assert response.status_code == 400
    assert response.get_json()["sucesso"] is False


def test_resumo_de_conta_inexistente_retorna_404():
    app = create_app("testing")
    with app.app_context():
        db.create_all()

    response = app.test_client().get("/dashboard/resumo?conta_id=999")

    assert response.status_code == 404
