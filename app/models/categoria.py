from app.extensions import db


class Categoria(db.Model):
    __tablename__ = "categoria"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False, unique=True)

    # Apagar categoria n apaga transação,
    # ela só volta pra categoria_id = NULL (ver Transacao.categoria_id).
    transacoes = db.relationship("Transacao", backref="categoria", lazy=True)

    def to_dict(self):
        return {"id": self.id, "nome": self.nome}