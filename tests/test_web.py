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
