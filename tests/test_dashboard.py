from datetime import UTC, datetime, timedelta

from sqlalchemy import event

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


def test_evolucao_junta_lancamentos_do_mesmo_dia_num_ponto_so():
    app = create_app("testing")
    agora = _agora()
    anteontem = (agora - timedelta(days=2)).replace(hour=9, minute=0, second=0, microsecond=0)
    with app.app_context():
        db.create_all()
        conta = Conta(nome="Mesmo dia", saldo_atual=0)
        db.session.add(conta)
        db.session.flush()
        db.session.add_all([
            Transacao(valor=100, tipo="entrada", conta_id=conta.id, data=anteontem),
            Transacao(valor=30, tipo="saida", conta_id=conta.id, data=anteontem + timedelta(hours=3)),
            Transacao(valor=50, tipo="saida", conta_id=conta.id, data=agora + timedelta(days=3)),
        ])
        db.session.commit()
        conta_id = conta.id

    dados = app.test_client().get(f"/dashboard/resumo?conta_id={conta_id}").get_json()["dados"]

    assert [(p["saldo"], p["projetado"]) for p in dados["evolucao_saldo"]] == [(70.0, False), (20.0, True)]
    assert dados["conta"]["saldo_atual"] == 70.0
    assert dados["conta"]["saldo_projetado"] == 20.0


def test_resumo_faz_o_mesmo_numero_de_consultas_com_muito_ou_pouco_historico():
    def consultas(qtd):
        app = create_app("testing")
        agora = _agora()
        with app.app_context():
            db.create_all()
            conta = Conta(nome="Carga", saldo_atual=0)
            db.session.add(conta)
            db.session.flush()
            db.session.add_all(
                Transacao(valor=10, tipo="entrada", conta_id=conta.id, data=agora - timedelta(hours=i))
                for i in range(qtd)
            )
            db.session.commit()
            conta_id = conta.id
            selects = []
            event.listen(
                db.engine, "before_cursor_execute",
                lambda conn, cur, stmt, *a: selects.append(stmt) if stmt.lstrip().upper().startswith("SELECT") else None,
            )
        app.test_client().get(f"/dashboard/resumo?conta_id={conta_id}")
        return len(selects)

    assert consultas(3) == consultas(300)
