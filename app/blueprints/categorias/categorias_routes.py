from flask import Blueprint, request

from app.extensions import db
from app.models import Categoria
from app.utils.responses import error_response, success_response

categorias_bp = Blueprint("categorias", __name__)


@categorias_bp.route("", methods=["GET"])
def listar_categorias():
    """
    Lista as categorias
    ---
    tags:
      - Categorias
    responses:
      200:
        description: Lista de categorias
    """
    categorias = Categoria.query.order_by(Categoria.nome).all()
    return success_response(data=[c.to_dict() for c in categorias])


@categorias_bp.route("", methods=["POST"])
def criar_categoria():
    """
    Cria uma categoria
    ---
    tags:
      - Categorias
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [nome]
          properties:
            nome:
              type: string
              example: "Educação"
    responses:
      201:
        description: Categoria criada
      400:
        description: Campo 'nome' ausente
      409:
        description: Já existe uma categoria com esse nome
    """
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


@categorias_bp.route("/<int:categoria_id>", methods=["PUT"])
def atualizar_categoria(categoria_id):
    """
    Renomeia uma categoria
    ---
    tags:
      - Categorias
    parameters:
      - in: path
        name: categoria_id
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [nome]
          properties:
            nome:
              type: string
              example: "Manutenção"
    responses:
      200:
        description: Categoria atualizada
      400:
        description: Campo 'nome' ausente ou maior que 80 caracteres
      404:
        description: Categoria não encontrada
      409:
        description: Já existe outra categoria com esse nome
    """
    categoria = db.session.get(Categoria, categoria_id)
    if not categoria:
        return error_response("Categoria não encontrada", status_code=404)

    body = request.get_json(silent=True) or {}
    nome = str(body.get("nome") or "").strip()
    if not nome:
        return error_response("Campo 'nome' é obrigatório", status_code=400)
    if len(nome) > 80:
        return error_response("Campo 'nome' deve ter no máximo 80 caracteres", status_code=400)

    if Categoria.query.filter(Categoria.nome == nome, Categoria.id != categoria_id).first():
        return error_response("Já existe uma categoria com esse nome", status_code=409)

    categoria.nome = nome
    db.session.commit()
    return success_response(data=categoria.to_dict())