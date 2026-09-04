from app import create_app
from app.extensions import db
from app.models import Categoria, Conta, Transacao


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


def _cria_categoria(app, nome="Vendas"):
    with app.app_context():
        categoria = Categoria(nome=nome)
        db.session.add(categoria)
        db.session.commit()
        return categoria.id


# ---------- GET ----------


def test_listar_transacoes_vazio_retorna_lista_vazia():
    app = _app_com_banco_limpo()
    client = app.test_client()

    response = client.get("/transacoes")

    assert response.status_code == 200
    body = response.get_json()
    assert body["sucesso"] is True
    assert body["dados"] == []


def test_detalhar_transacao_inexistente_retorna_404():
    app = _app_com_banco_limpo()
    client = app.test_client()

    response = client.get("/transacoes/999")

    assert response.status_code == 404
    assert response.get_json()["sucesso"] is False


# ---------- POST ----------


def test_criar_transacao_recalcula_saldo_da_conta():
    app = _app_com_banco_limpo()
    conta_id = _cria_conta(app, saldo_atual=0)
    client = app.test_client()

    response = client.post(
        "/transacoes", json={"valor": 200, "tipo": "entrada", "conta_id": conta_id}
    )

    assert response.status_code == 201
    with app.app_context():
        conta = db.session.get(Conta, conta_id)
        assert float(conta.saldo_atual) == 200.0


def test_criar_transacao_sem_campos_obrigatorios_retorna_400():
    app = _app_com_banco_limpo()
    client = app.test_client()

    response = client.post("/transacoes", json={"valor": 50})

    assert response.status_code == 400


def test_criar_transacao_com_tipo_invalido_retorna_400():
    app = _app_com_banco_limpo()
    conta_id = _cria_conta(app)
    client = app.test_client()

    response = client.post(
        "/transacoes", json={"valor": 10, "tipo": "transferencia", "conta_id": conta_id}
    )

    assert response.status_code == 400


def test_criar_transacao_com_valor_negativo_retorna_400():
    app = _app_com_banco_limpo()
    conta_id = _cria_conta(app)
    client = app.test_client()

    response = client.post(
        "/transacoes", json={"valor": -10, "tipo": "entrada", "conta_id": conta_id}
    )

    assert response.status_code == 400


def test_criar_transacao_com_conta_inexistente_retorna_404():
    app = _app_com_banco_limpo()
    client = app.test_client()

    response = client.post(
        "/transacoes", json={"valor": 10, "tipo": "entrada", "conta_id": 999}
    )

    assert response.status_code == 404


def test_criar_transacao_com_conta_id_com_tipo_errado_retorna_400_sem_quebrar():
    # Regressão: {"conta_id": [1, 2]} chegava a derrubar a rota com um 500
    # do SQLAlchemy antes da validação de tipo existir.
    app = _app_com_banco_limpo()
    client = app.test_client()

    response = client.post(
        "/transacoes", json={"valor": 10, "tipo": "entrada", "conta_id": [1, 2]}
    )

    assert response.status_code == 400


def test_criar_transacao_com_categoria_inexistente_retorna_404():
    app = _app_com_banco_limpo()
    conta_id = _cria_conta(app)
    client = app.test_client()

    response = client.post(
        "/transacoes",
        json={"valor": 10, "tipo": "entrada", "conta_id": conta_id, "categoria_id": 999},
    )

    assert response.status_code == 404


def test_criar_transacao_com_categoria_valida_associa_corretamente():
    app = _app_com_banco_limpo()
    conta_id = _cria_conta(app)
    categoria_id = _cria_categoria(app)
    client = app.test_client()

    response = client.post(
        "/transacoes",
        json={
            "valor": 10,
            "tipo": "entrada",
            "conta_id": conta_id,
            "categoria_id": categoria_id,
        },
    )

    assert response.status_code == 201
    assert response.get_json()["dados"]["categoria_id"] == categoria_id


# ---------- PUT ----------


def test_atualizar_transacao_recalcula_saldo():
    app = _app_com_banco_limpo()
    conta_id = _cria_conta(app)
    client = app.test_client()

    criada = client.post(
        "/transacoes", json={"valor": 200, "tipo": "entrada", "conta_id": conta_id}
    ).get_json()["dados"]

    response = client.put(f"/transacoes/{criada['id']}", json={"valor": 150})

    assert response.status_code == 200
    with app.app_context():
        conta = db.session.get(Conta, conta_id)
        assert float(conta.saldo_atual) == 150.0


def test_atualizar_transacao_inexistente_retorna_404():
    app = _app_com_banco_limpo()
    client = app.test_client()

    response = client.put("/transacoes/999", json={"valor": 10})

    assert response.status_code == 404


def test_atualizar_transacao_para_conta_inexistente_nao_corrompe_o_dado():
    # Regressão: um PUT que falhava na troca de conta ainda assim commitava
    # a transação com o conta_id inválido antes da validação existir.
    app = _app_com_banco_limpo()
    conta_id = _cria_conta(app)
    client = app.test_client()

    criada = client.post(
        "/transacoes", json={"valor": 10, "tipo": "entrada", "conta_id": conta_id}
    ).get_json()["dados"]

    response = client.put(f"/transacoes/{criada['id']}", json={"conta_id": 999})

    assert response.status_code == 404
    with app.app_context():
        transacao = db.session.get(Transacao, criada["id"])
        assert transacao.conta_id == conta_id


def test_atualizar_transacao_mudando_de_conta_recalcula_as_duas():
    app = _app_com_banco_limpo()
    conta_origem_id = _cria_conta(app)
    conta_destino_id = _cria_conta(app)
    client = app.test_client()

    criada = client.post(
        "/transacoes", json={"valor": 100, "tipo": "entrada", "conta_id": conta_origem_id}
    ).get_json()["dados"]

    response = client.put(
        f"/transacoes/{criada['id']}", json={"conta_id": conta_destino_id}
    )

    assert response.status_code == 200
    with app.app_context():
        origem = db.session.get(Conta, conta_origem_id)
        destino = db.session.get(Conta, conta_destino_id)
        assert float(origem.saldo_atual) == 0.0
        assert float(destino.saldo_atual) == 100.0


# ---------- DELETE ----------


def test_remover_transacao_recalcula_saldo():
    app = _app_com_banco_limpo()
    conta_id = _cria_conta(app)
    client = app.test_client()

    criada = client.post(
        "/transacoes", json={"valor": 100, "tipo": "entrada", "conta_id": conta_id}
    ).get_json()["dados"]

    response = client.delete(f"/transacoes/{criada['id']}")

    assert response.status_code == 200
    with app.app_context():
        conta = db.session.get(Conta, conta_id)
        assert float(conta.saldo_atual) == 0.0


def test_remover_transacao_ja_removida_retorna_404():
    app = _app_com_banco_limpo()
    conta_id = _cria_conta(app)
    client = app.test_client()

    criada = client.post(
        "/transacoes", json={"valor": 100, "tipo": "entrada", "conta_id": conta_id}
    ).get_json()["dados"]

    client.delete(f"/transacoes/{criada['id']}")
    response = client.delete(f"/transacoes/{criada['id']}")

    assert response.status_code == 404
