"""
Rafael — é aqui que entram os models (Dia 2, "Escrever o models.py com
SQLAlchemy").

Sugestão de organização: um arquivo por entidade dentro de app/models/
(conta.py, categoria.py, transacao.py, alerta.py) e depois importar as
classes aqui embaixo, para que o Flask-Migrate consiga enxergá-las quando
você rodar `flask db migrate`.

Exemplo de esqueleto para app/models/conta.py:

    from app.extensions import db

    class Conta(db.Model):
        __tablename__ = "contas"

        id = db.Column(db.Integer, primary_key=True)
        nome = db.Column(db.String(120), nullable=False)
        saldo_atual = db.Column(db.Numeric(12, 2), nullable=False, default=0)

        transacoes = db.relationship("Transacao", backref="conta", lazy=True)
        alertas = db.relationship("Alerta", backref="conta", lazy=True)

Depois de criar cada model, descomente as linhas correspondentes abaixo:

# from .conta import Conta
# from .categoria import Categoria
# from .transacao import Transacao
# from .alerta import Alerta
"""
