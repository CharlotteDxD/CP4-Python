from app import create_app
from app.extensions import db
from app.models import Conta


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
    conta_id = _cria_conta(app, saldo_atual=150)
    client = app.test_client()

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
