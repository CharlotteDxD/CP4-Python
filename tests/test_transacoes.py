from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import Categoria, Conta, Transacao


def _app_com_banco_limpo():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
    return app


def _cria_conta(app, saldo_atual=0, nome="Conta Teste"):
    with app.app_context():
        conta = Conta(nome=nome, saldo_atual=saldo_atual)
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


def test_listar_transacoes_filtra_por_conta_id():
    app = _app_com_banco_limpo()
    conta_a = _cria_conta(app, nome="Caixa A")
    conta_b = _cria_conta(app, nome="Caixa B")
    client = app.test_client()

    client.post("/transacoes", json={"valor": 10, "tipo": "entrada", "conta_id": conta_a})
    client.post("/transacoes", json={"valor": 20, "tipo": "entrada", "conta_id": conta_b})

    response = client.get(f"/transacoes?conta_id={conta_a}")
    body = response.get_json()["dados"]

    assert response.status_code == 200
    assert len(body) == 1
    assert body[0]["conta_id"] == conta_a
    assert float(body[0]["valor"]) == 10.0


def _cria_cenario_de_filtros(app):
    conta_id = _cria_conta(app)
    categoria_id = _cria_categoria(app, nome="Aluguel")
    client = app.test_client()
    for valor, tipo, data, categoria in [
        (100, "entrada", "2026-09-01T10:00:00", None),
        (200, "saida", "2026-09-15T10:00:00", categoria_id),
        (300, "saida", "2026-09-30T18:00:00", None),
        (400, "entrada", "2026-10-05T10:00:00", None),
    ]:
        body = {"valor": valor, "tipo": tipo, "conta_id": conta_id, "data": data}
        if categoria:
            body["categoria_id"] = categoria
        with patch("app.blueprints.transacoes.transacoes_routes.gerar_recomendacao", return_value="ok"):
            client.post("/transacoes", json=body)
    return client, categoria_id


def test_listar_transacoes_filtra_por_tipo():
    app = _app_com_banco_limpo()
    client, _ = _cria_cenario_de_filtros(app)

    dados = client.get("/transacoes?tipo=saida").get_json()["dados"]

    assert [t["valor"] for t in dados] == [300.0, 200.0]


def test_listar_transacoes_filtra_por_categoria():
    app = _app_com_banco_limpo()
    client, categoria_id = _cria_cenario_de_filtros(app)

    dados = client.get(f"/transacoes?categoria_id={categoria_id}").get_json()["dados"]

    assert [t["valor"] for t in dados] == [200.0]


def test_listar_transacoes_filtra_por_intervalo_de_data_incluindo_o_dia_final():
    app = _app_com_banco_limpo()
    client, _ = _cria_cenario_de_filtros(app)

    dados = client.get("/transacoes?data_inicio=2026-09-15&data_fim=2026-09-30").get_json()["dados"]

    assert [t["valor"] for t in dados] == [300.0, 200.0]


def test_listar_transacoes_filtra_sem_categoria():
    app = _app_com_banco_limpo()
    client, categoria_id = _cria_cenario_de_filtros(app)

    dados = client.get("/transacoes?sem_categoria=true").get_json()["dados"]
    assert len(dados) == 3
    assert all(t["categoria_id"] is None for t in dados)

    # categoria_id explícito vence sem_categoria
    dados = client.get(f"/transacoes?sem_categoria=true&categoria_id={categoria_id}").get_json()["dados"]
    assert [t["categoria_id"] for t in dados] == [categoria_id]


def test_listar_transacoes_busca_na_descricao_sem_diferenciar_maiusculas():
    app = _app_com_banco_limpo()
    conta_id = _cria_conta(app)
    client = app.test_client()
    for descricao in ["Conta de Energia", "Aluguel do ponto", "Desconto 10% fornecedor"]:
        client.post("/transacoes", json={
            "valor": 10, "tipo": "saida", "conta_id": conta_id,
            "descricao": descricao, "categoria_id": None,
        })

    achou = client.get("/transacoes?busca=energia").get_json()["dados"]
    assert [t["descricao"] for t in achou] == ["Conta de Energia"]

    # % é texto, não curinga: só a descrição com "10%" bate
    achou = client.get("/transacoes?busca=10%25").get_json()["dados"]
    assert [t["descricao"] for t in achou] == ["Desconto 10% fornecedor"]
    assert client.get("/transacoes?busca=%25").get_json()["dados"] != []
    assert client.get("/transacoes?busca=inexistente").get_json()["dados"] == []


def test_listar_transacoes_paginada_devolve_metadados():
    app = _app_com_banco_limpo()
    client, _ = _cria_cenario_de_filtros(app)

    dados = client.get("/transacoes?pagina=2&por_pagina=3").get_json()["dados"]

    assert dados["pagina"] == 2
    assert dados["por_pagina"] == 3
    assert dados["total"] == 4
    assert dados["total_paginas"] == 2
    assert [t["valor"] for t in dados["itens"]] == [100.0]


def test_listar_transacoes_com_filtros_invalidos_retorna_400():
    app = _app_com_banco_limpo()
    client = app.test_client()

    for query in [
        "tipo=transferencia",
        "categoria_id=abc",
        "data_inicio=30/09/2026",
        "data_inicio=2026-10-01&data_fim=2026-09-01",
        "pagina=0",
        "por_pagina=x",
    ]:
        response = client.get(f"/transacoes?{query}")
        assert response.status_code == 400, query
        assert response.get_json()["sucesso"] is False


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
    payload = response.get_json()["dados"]
    assert payload["saldo_projetado"] == 200.0
    with app.app_context():
        conta = db.session.get(Conta, conta_id)
        assert float(conta.saldo_atual) == 200.0


def test_criar_transacao_sem_categoria_chama_ia():
    app = _app_com_banco_limpo()
    conta_id = _cria_conta(app)
    categoria_id = _cria_categoria(app, nome="Aluguel")
    client = app.test_client()

    with patch(
        "app.blueprints.transacoes.transacoes_routes.categorizar_transacao",
        return_value="Aluguel",
    ):
        response = client.post(
            "/transacoes",
            json={
                "valor": 80,
                "tipo": "saida",
                "conta_id": conta_id,
                "descricao": "aluguel do ponto",
            },
        )

    assert response.status_code == 201
    assert response.get_json()["dados"]["categoria_id"] == categoria_id


def test_criar_transacao_ia_falhou_ainda_grava():
    app = _app_com_banco_limpo()
    conta_id = _cria_conta(app)
    _cria_categoria(app)
    client = app.test_client()

    from app.services.ia import IAServiceError

    with patch(
        "app.blueprints.transacoes.transacoes_routes.categorizar_transacao",
        side_effect=IAServiceError("timeout"),
    ):
        response = client.post(
            "/transacoes",
            json={
                "valor": 10,
                "tipo": "entrada",
                "conta_id": conta_id,
                "descricao": "venda avulsa",
            },
        )

    assert response.status_code == 201
    body = response.get_json()["dados"]
    assert body["categoria_id"] is None
    assert "aviso_ia" in body


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
    assert response.get_json()["sucesso"] is True
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
