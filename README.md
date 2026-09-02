# CP4-Python — Agente Financeiro de Fluxo de Caixa

> As seções de problema, público-alvo, regras de negócio, endpoints etc.
> entram aqui pelo Gustavo (Dia 2 em diante). Por enquanto, só o essencial
> pra rodar o projeto localmente.

## Como rodar localmente

```bash
git clone https://github.com/CharlotteDxD/CP4-Python.git
cd CP4-Python

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# edite o .env com a DATABASE_URL real (Rafael tem esse valor) e a
# ANTHROPIC_API_KEY (Anthony tem essa)

python run.py
```

A API sobe em `http://127.0.0.1:5000`. Endpoints úteis pra conferir que
está tudo de pé:

- `GET /health` — health-check, mostra se o Postgres está conectado
- `GET /apidocs` — Swagger UI (Anthony vai preenchendo as rotas conforme
  o projeto avança)

## Rodando os testes

```bash
pytest
```

## Estrutura de pastas

```
app/
├── __init__.py          # application factory (create_app)
├── config.py             # configuração por ambiente (dev/test/prod)
├── extensions.py         # instâncias do SQLAlchemy e do Migrate
├── models/                # Rafael: um arquivo por entidade (Dia 2)
└── blueprints/
    ├── health/            # /health — já funcionando
    ├── transacoes/         # /transacoes — esqueleto, Charles preenche
    ├── categorias/          # /categorias — esqueleto
    ├── contas/               # /contas/:id/saldo — esqueleto
    └── alertas/                # /alertas — esqueleto
```
