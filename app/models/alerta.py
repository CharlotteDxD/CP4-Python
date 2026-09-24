from app.extensions import db


class Alerta(db.Model):
    __tablename__ = "alerta"
    __table_args__ = (
        db.CheckConstraint(
            "nivel_risco IN ('baixo', 'medio', 'alto')", name="ck_alerta_nivel_risco_valido"
        ),
        db.Index("idx_alerta_conta_id", "conta_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    conta_id = db.Column(
        db.Integer, db.ForeignKey("conta.id", ondelete="CASCADE"), nullable=False
    )
    mensagem = db.Column(db.Text, nullable=False)
    recomendacao = db.Column(db.Text, nullable=True)  # gerada pela IA
    data = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    nivel_risco = db.Column(db.String(10), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "conta_id": self.conta_id,
            "mensagem": self.mensagem,
            "recomendacao": self.recomendacao,
            "data": self.data.isoformat() if self.data else None,
            "nivel_risco": self.nivel_risco,
        }