# Agente Financeiro de Fluxo de Caixa

Projeto Acadêmico Integrador — FIAP, Tecnólogo em Inteligência Artificial
**Tema 7: Gestor Empresarial utilizando Agentes de IA**

## Integrantes
- Rafael — Banco de Dados
- Charles — Backend & API
- Anthony — Integração de IA & Swagger
- Gustavo — QA, Organização & README

## Problema
Pequenas empresas e autônomos perdem o controle do caixa porque não enxergam,
em tempo real, se as próximas contas vão deixar o saldo negativo.

## Público-alvo
Pequenos negócios e autônomos sem um financeiro dedicado.

## Objetivo
Um agente de IA que monitora o fluxo de caixa a partir das transações
registradas, categoriza automaticamente, projeta o saldo futuro e alerta
com recomendação quando o risco de saldo negativo aparece.

## Funcionalidades (CP1)
- Registro de transações (entrada/saída)
- Categorização automática via LLM
- Cálculo e recálculo do saldo da conta
- Projeção de saldo futuro e detecção de risco
- Geração de alerta com recomendação da IA

## Regra de negócio central
Toda vez que uma `Transacao` é criada sem categoria informada, o backend
chama a IA para categorizar a partir da descrição. O saldo da `Conta` é
recalculado a cada transação. Se a projeção de saldo ficar negativa, o
sistema cria um `Alerta` com uma recomendação gerada pela IA. A IA nunca
bloqueia o cadastro da transação: se a chamada falhar, a transação é salva
mesmo assim, sem categoria.

## Entidades

| Entidade | Campos |
|---|---|
| `Conta` | id, nome, saldo_atual, criado_em |
| `Categoria` | id, nome |
| `Transacao` | id, valor, tipo (entrada/saida), categoria_id, conta_id, data, descricao |
| `Alerta` | id, conta_id, mensagem, recomendacao, data, nivel_risco (baixo/medio/alto) |

**Relacionamentos:** `Conta` 1—N `Transacao` · `Conta` 1—N `Alerta` ·
`Categoria` 1—N `Transacao` (categoria pode ser nula)

## Tecnologias
Python, Flask, Flask-SQLAlchemy, Flask-Migrate, PostgreSQL, Flask-CORS,
flasgger (Swagger/OpenAPI), Anthropic API (LLM), python-dotenv, pytest.

## Arquitetura
Cliente → API REST (Flask, blueprints por entidade) → Regras de negócio
(services: saldo.py, ia.py) → SQLAlchemy → PostgreSQL. A IA (Anthropic API)
é chamada pelo backend em dois pontos: categorização de transação e geração
de recomendação de alerta.

## Como rodar localmente

```bash
git clone https://github.com/CharlotteDxD/CP4-Python.git
cd CP4-Python

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# preencha DATABASE_URL (Rafael) e ANTHROPIC_API_KEY (Anthony)

python run.py
```

A API sobe em `http://127.0.0.1:5000`.

## Variáveis de ambiente
- `DATABASE_URL` — conexão do PostgreSQL (Render)
- `ANTHROPIC_API_KEY` — chave da API de LLM
- `ANTHROPIC_MODEL`, `ANTHROPIC_TIMEOUT` — configuração da chamada de IA
- `SECRET_KEY` — chave Flask

## Rodando os testes
```bash
pytest
```
34 testes automatizados cobrindo saldo, transações, categorias, contas e o
fluxo do agente de ponta a ponta.

## Banco de dados
PostgreSQL hospedado no Render. Migrations gerenciadas via Flask-Migrate
(Alembic). Seed inicial disponível em `seed.py`.

## Principais endpoints

| Método | Rota | Descrição |
|---|---|---|
| GET | `/transacoes` | Lista transações |
| GET | `/transacoes/:id` | Detalha uma transação |
| POST | `/transacoes` | Cria transação (dispara IA + recálculo de saldo + checagem de risco) |
| PUT | `/transacoes/:id` | Atualiza transação |
| DELETE | `/transacoes/:id` | Remove transação |
| GET | `/categorias` | Lista categorias |
| GET | `/contas/:id/saldo` | Saldo atual e projetado da conta |
| GET | `/alertas` | Lista alertas gerados pelo agente |
| GET | `/health` | Health-check da aplicação e do banco |

## Documentação da API
Swagger disponível em `/apidocs` após subir a aplicação.

## Gestão do projeto
Quadro de tarefas: [Trello](https://trello.com/b/Ou73DtwH/agente-financeiro-de-fluxo-de-caixa-cp4)
