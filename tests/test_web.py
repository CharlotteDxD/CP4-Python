import pytest

from app import create_app


@pytest.fixture
def client():
    return create_app("testing").test_client()


@pytest.mark.parametrize("path", ["/app", "/app/transacoes", "/app/alertas", "/app/categorias", "/app/contas"])
def test_paginas_do_frontend_respondem_200(client, path):
    response = client.get(path)

    assert response.status_code == 200
    assert b"Agente Financeiro" in response.data


def test_raiz_redireciona_para_o_painel(client):
    response = client.get("/")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/app")


def test_url_desconhecida_do_app_mostra_pagina_404_com_caminho_de_volta(client):
    response = client.get("/app/nao-existe")

    assert response.status_code == 404
    assert "Página não encontrada".encode() in response.data
    assert b'href="/app"' in response.data


def test_404_fora_do_app_continua_sendo_o_padrao_da_api(client):
    response = client.get("/rota-que-nao-existe")

    assert response.status_code == 404
    assert "Página não encontrada".encode() not in response.data
