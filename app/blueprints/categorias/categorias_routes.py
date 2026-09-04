from flask import Blueprint, request

from app.extensions import db
from app.models import Categoria
from app.utils.responses import error_response, success_response

categorias_bp = Blueprint("categorias", __name__)


@categorias_bp.route("", methods=["GET"])
def listar_categorias():
    categorias = Categoria.query.order_by(Categoria.nome).all()
    return success_response(data=[c.to_dict() for c in categorias])


@categorias_bp.route("", methods=["POST"])
def criar_categoria():
    body = request.get_json(silent=True) or {}
    nome = body.get("nome")

    if not nome or not str(nome).strip():
        return error_response("Campo 'nome' é obrigatório", status_code=400)

    nome = str(nome).strip()

    # nome é unique no banco (ver models/categoria.py) — checar antes evita
    # depender só da exceção do banco e devolve um 409 claro em vez de 500.
    if Categoria.query.filter_by(nome=nome).first():
        return error_response("Já existe uma categoria com esse nome", status_code=409)

    categoria = Categoria(nome=nome)
    db.session.add(categoria)
    db.session.commit()

    return success_response(data=categoria.to_dict(), status_code=201)
