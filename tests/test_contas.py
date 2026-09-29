from datetime import UTC, datetime, timedelta

from app import create_app
from app.extensions import db
from app.models import Conta, Transacao


def _app_com_banco_limpo():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
    return app


def _cria_conta(app, saldo_atual=0):
    with app.app_context():
        conta = Conta(nome="Conta Teste", saldo_atual=saldo_atual)
        db.session.add(conta)
        db.session.commit()
        return conta.id


def test_saldo_da_conta_existente():
    app = _app_com_banco_limpo()
    conta_id = _cria_conta(app)
    client = app.test_client()
    client.post("/transacoes", json={"valor": 150, "tipo": "entrada", "conta_id": conta_id})

    response = client.get(f"/contas/{conta_id}/saldo")

    assert response.status_code == 200
    body = response.get_json()["dados"]
    assert body["conta_id"] == conta_id
    assert body["saldo_atual"] == 150.0
    assert "saldo_projetado" in body


def test_saldo_da_conta_inexistente_retorna_404():
    app = _app_com_banco_limpo()
    client = app.test_client()

    response = client.get("/contas/999/saldo")

    assert response.status_code == 404
    assert response.get_json()["sucesso"] is False


def test_saldo_reflete_transacao_criada_via_api():
    app = _app_com_banco_limpo()
    conta_id = _cria_conta(app, saldo_atual=0)
    client = app.test_client()

    client.post("/transacoes", json={"valor": 300, "tipo": "entrada", "conta_id": conta_id})
    client.post("/transacoes", json={"valor": 80, "tipo": "saida", "conta_id": conta_id})

    response = client.get(f"/contas/{conta_id}/saldo")

    assert response.get_json()["dados"]["saldo_atual"] == 220.0


def test_saldo_recalcula_transacao_futura_que_ja_venceu():
    app = _app_com_banco_limpo()
    conta_id = _cria_conta(app, saldo_atual=0)
    ontem = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)
    amanha = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1)
    with app.app_context():
        # inserida direto, sem passar pela rota: saldo_atual fica defasado em 0
        db.session.add(Transacao(valor=200, tipo="entrada", conta_id=conta_id, data=ontem))
        db.session.add(Transacao(valor=50, tipo="saida", conta_id=conta_id, data=amanha))
        db.session.commit()
    client = app.test_client()

    body = client.get(f"/contas/{conta_id}/saldo").get_json()["dados"]

    assert body["saldo_atual"] == 200.0
    assert body["saldo_projetado"] == 150.0


def test_listar_contas_traz_saldo_atual_e_projetado():
    app = _app_com_banco_limpo()
    conta_id = _cria_conta(app)
    client = app.test_client()
    client.post("/transacoes", json={"valor": 100, "tipo": "entrada", "conta_id": conta_id})
    futuro = (datetime.now(UTC) + timedelta(days=5)).replace(tzinfo=None).isoformat()
    client.post("/transacoes", json={"valor": 30, "tipo": "saida", "conta_id": conta_id, "data": futuro})

    dados = client.get("/contas").get_json()["dados"]

    assert len(dados) == 1
    assert dados[0]["nome"] == "Conta Teste"
    assert dados[0]["saldo_atual"] == 100.0
    assert dados[0]["saldo_projetado"] == 70.0


def test_criar_conta_comeca_com_saldo_zero():
    client = _app_com_banco_limpo().test_client()

    response = client.post("/contas", json={"nome": "  Caixa da loja "})

    assert response.status_code == 201
    dados = response.get_json()["dados"]
    assert dados["nome"] == "Caixa da loja"
    assert dados["saldo_atual"] == 0 and dados["saldo_projetado"] == 0


def test_criar_e_renomear_conta_validam_nome():
    client = _app_com_banco_limpo().test_client()
    conta_id = client.post("/contas", json={"nome": "Caixa"}).get_json()["dados"]["id"]

    assert client.post("/contas", json={}).status_code == 400
    assert client.post("/contas", json={"nome": "x" * 121}).status_code == 400
    assert client.put(f"/contas/{conta_id}", json={"nome": ""}).status_code == 400
    assert client.put("/contas/999", json={"nome": "Caixa"}).status_code == 404


def test_renomear_conta():
    client = _app_com_banco_limpo().test_client()
    conta_id = client.post("/contas", json={"nome": "Caixa"}).get_json()["dados"]["id"]

    response = client.put(f"/contas/{conta_id}", json={"nome": "Banco principal"})

    assert response.status_code == 200
    assert response.get_json()["dados"]["nome"] == "Banco principal"
