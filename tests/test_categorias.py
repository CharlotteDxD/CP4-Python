from app import create_app
from app.extensions import db
from app.models import Categoria


def _app_com_banco_limpo():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
    return app


def test_listar_categorias_vazio_retorna_lista_vazia():
    app = _app_com_banco_limpo()
    client = app.test_client()

    response = client.get("/categorias")

    assert response.status_code == 200
    assert response.get_json()["dados"] == []


def test_criar_categoria_com_sucesso():
    app = _app_com_banco_limpo()
    client = app.test_client()

    response = client.post("/categorias", json={"nome": "Vendas"})

    assert response.status_code == 201
    body = response.get_json()
    assert body["dados"]["nome"] == "Vendas"
    assert "id" in body["dados"]


def test_criar_categoria_sem_nome_retorna_400():
    app = _app_com_banco_limpo()
    client = app.test_client()

    response = client.post("/categorias", json={})

    assert response.status_code == 400


def test_criar_categoria_com_nome_so_espacos_retorna_400():
    app = _app_com_banco_limpo()
    client = app.test_client()

    response = client.post("/categorias", json={"nome": "   "})

    assert response.status_code == 400


def test_criar_categoria_duplicada_retorna_409():
    app = _app_com_banco_limpo()
    client = app.test_client()

    client.post("/categorias", json={"nome": "Vendas"})
    response = client.post("/categorias", json={"nome": "Vendas"})

    assert response.status_code == 409


def test_listar_categorias_retorna_ordenado_por_nome():
    app = _app_com_banco_limpo()
    with app.app_context():
        db.session.add_all([Categoria(nome="Vendas"), Categoria(nome="Despesas Fixas")])
        db.session.commit()
    client = app.test_client()

    response = client.get("/categorias")

    nomes = [c["nome"] for c in response.get_json()["dados"]]
    assert nomes == ["Despesas Fixas", "Vendas"]
