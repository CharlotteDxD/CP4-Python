from app.extensions import db


class Transacao(db.Model):
    __tablename__ = "transacao"
    __table_args__ = (
        db.CheckConstraint("valor > 0", name="ck_transacao_valor_positivo"),
        db.CheckConstraint("tipo IN ('entrada', 'saida')", name="ck_transacao_tipo_valido"),
        db.Index("idx_transacao_conta_id", "conta_id"),
        db.Index("idx_transacao_data", "data"),
    )

    id = db.Column(db.Integer, primary_key=True)
    valor = db.Column(db.Numeric(12, 2), nullable=False)
    tipo = db.Column(db.String(10), nullable=False)

    # NULL = ainda não categorizado( a "alavanca/gatilho/polvora" pro backend chamar a IA)
    categoria_id = db.Column(
        db.Integer, db.ForeignKey("categoria.id", ondelete="SET NULL"), nullable=True
    )
    conta_id = db.Column(
        db.Integer, db.ForeignKey("conta.id", ondelete="CASCADE"), nullable=False
    )
    data = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    descricao = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "valor": float(self.valor),
            "tipo": self.tipo,
            "categoria_id": self.categoria_id,
            "conta_id": self.conta_id,
            "data": self.data.isoformat() if self.data else None,
            "descricao": self.descricao,
        }