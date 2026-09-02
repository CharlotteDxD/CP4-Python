from datetime import datetime, timezone

from flask import Blueprint, jsonify
from sqlalchemy import text

from app.extensions import db

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    """
    Health check da API.
    ---
    tags:
      - Health
    responses:
      200:
        description: API está no ar. O campo "banco_de_dados" mostra se a
          conexão com o Postgres também está funcionando.
        examples:
          application/json: {
            "status": "ok",
            "timestamp": "2026-09-02T14:00:00+00:00",
            "banco_de_dados": "conectado"
          }
    """
    payload = {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "banco_de_dados": "não verificado",
    }

    # Só tenta falar com o banco se houver uma DATABASE_URL configurada.
    # Isso mantém o /health funcionando mesmo antes do Rafael terminar
    # a configuração do banco (Dia 1/2), em vez de quebrar o endpoint inteiro.
    try:
        db.session.execute(text("SELECT 1"))
        payload["banco_de_dados"] = "conectado"
    except Exception as exc:  # noqa: BLE001 — health check deve responder sempre, nunca 500
        payload["banco_de_dados"] = "indisponível"
        payload["banco_de_dados_erro"] = str(exc)

    return jsonify(payload), 200
