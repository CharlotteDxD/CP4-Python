from app import create_app


def test_health_check_retorna_200_e_status_ok():
    app = create_app("testing")
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert "timestamp" in body


def test_erro_500_retorna_json():
    app = create_app("testing")
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.route("/boom")
    def boom():
        raise RuntimeError("x")

    response = app.test_client().get("/boom")

    assert response.status_code == 500
    assert response.get_json() == {"sucesso": False, "erro": "Erro interno do servidor"}
