from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import Categoria, Conta, Transacao


def _client():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        conta = Conta(nome="Caixa", saldo_atual=0)
        cat = Categoria(nome="Aluguel")
        db.session.add_all([conta, cat])
        db.session.commit()
        conta_id = conta.id
        cat_id = cat.id
    client = app.test_client()
    return app, client, conta_id, cat_id


def test_post_sem_categoria_chama_ia_e_grava():
    app, client, conta_id, _ = _client()

    with patch("app.blueprints.transacoes.transacoes_routes.categorizar_transacao", return_value="Aluguel"):
        with patch("app.blueprints.transacoes.transacoes_routes.gerar_recomendacao", return_value="Adie o pagamento"):
            resp = client.post(
                "/transacoes",
                json={
                    "valor": 80,
                    "tipo": "saida",
                    "conta_id": conta_id,
                    "descricao": "aluguel do ponto",
                },
            )

    assert resp.status_code == 201
    body = resp.get_json()["data"]
    assert body["categoria_id"] is not None


def test_post_com_saida_futura_grande_gera_alerta():
    app, client, conta_id, cat_id = _client()
    amanha = (datetime.now(UTC) + timedelta(days=2)).replace(tzinfo=None).isoformat()

    with app.app_context():
        db.session.add(
            Transacao(
                valor=100,
                tipo="entrada",
                conta_id=conta_id,
                categoria_id=cat_id,
                data=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1),
            )
        )
        db.session.commit()

    with patch("app.blueprints.transacoes.transacoes_routes.gerar_recomendacao", return_value="Negocie prazo"):
        resp = client.post(
            "/transacoes",
            json={
                "valor": 500,
                "tipo": "saida",
                "conta_id": conta_id,
                "categoria_id": cat_id,
                "descricao": "fornecedor",
                "data": amanha,
            },
        )

    assert resp.status_code == 201
    body = resp.get_json()["data"]
    assert "alerta_gerado" in body
    assert body["saldo_projetado"] < 0

    lista = client.get("/alertas")
    assert lista.status_code == 200
    alertas = lista.get_json()["data"]
    assert len(alertas) >= 1
    assert alertas[0]["recomendacao"] == "Negocie prazo"
