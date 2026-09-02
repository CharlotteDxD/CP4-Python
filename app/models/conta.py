from app.extensions import db


class Conta(db.Model):
    __tablename__ = "conta"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    saldo_atual = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    criado_em = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    # cascade="all, delete-orphan": espelha o ON DELETE CASCADE do schema(apagar uma conta apaga o histórico dela.)
    transacoes = db.relationship(
        "Transacao", backref="conta", cascade="all, delete-orphan", lazy=True
    )
    alertas = db.relationship(
        "Alerta", backref="conta", cascade="all, delete-orphan", lazy=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "saldo_atual": float(self.saldo_atual),
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }