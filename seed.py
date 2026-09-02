"""
seed.py — Seed inicial do banco (Dia 2 · dono: Rafael)

Cria 1 conta e 3 categorias, só pra ter dado mínimo assim que o banco
estiver de pé — o suficiente pro Charles plugar o CRUD e pro Anthony
testar a categorização por IA sem banco vazio.

Como rodar (com o venv ativado, na raiz do projeto, ao lado de run.py):
    python seed.py
"""

from dotenv import load_dotenv

# Precisa rodar ANTES do `from app import create_app` — o config.py lê o
# DATABASE_URL assim que é importado, e isso acontece antes do load_dotenv()
# que existe dentro de create_app() (que só roda tarde demais nesse caminho).
load_dotenv()

from app import create_app
from app.extensions import db
from app.models import Conta, Categoria


def run_seed():
    """Insere o dado inicial. Precisa rodar dentro de um app_context ativo."""
    if Conta.query.first() or Categoria.query.first():
        print("Seed não rodou: já existe conta ou categoria no banco. "
              "Apague os dados antigos primeiro se quiser recriar do zero.")
        return

    conta = Conta(nome="Conta Principal", saldo_atual=0)
    categorias = [
        Categoria(nome="Vendas"),
        Categoria(nome="Fornecedores"),
        Categoria(nome="Despesas Fixas"),
    ]

    db.session.add(conta)
    db.session.add_all(categorias)
    db.session.commit()

    print(f"Seed ok: conta '{conta.nome}' (id={conta.id}) + {len(categorias)} categorias criadas")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        run_seed()