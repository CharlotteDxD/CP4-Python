# Revisão do schema (CP2, dia 1)

Li os models em `app/models/`, a migration `0c68856f9520` e o `app/services/saldo.py` no dia 23/09. Ainda não mexi em nada no banco: esta é só a lista do que precisa ser revisado nos dias 2 a 4.

Hoje são 4 tabelas (`conta`, `categoria`, `transacao`, `alerta`), uma migration e 34 testes passando.

## Índices

O roadmap manda criar índice em `transacao.conta_id` e `transacao.data` no dia 3, mas os dois já existem (`idx_transacao_conta_id` e `idx_transacao_data`), no model e na migration. Então o dia 3 muda de foco. O que ainda falta:

- Um índice composto `(conta_id, data)` em `transacao`. O dashboard vai filtrar por conta e ordenar por data, e o composto resolve as duas coisas de uma vez. Com ele, `idx_transacao_conta_id` passa a ser redundante e pode sair.
- Um índice em `transacao.categoria_id`. O Postgres não cria índice para chave estrangeira sozinho, então o total por categoria do dashboard e o `ON DELETE SET NULL` (ao apagar uma categoria) varrem a tabela inteira.
- Um índice `(conta_id, data)` em `alerta`, para listar os alertas recentes. Hoje só existe `idx_alerta_conta_id`.
- `transacao.tipo` fica sem índice, porque só tem dois valores.

## Duplicidade e redundância

- `conta.saldo_atual` é derivado das transações. Manter o campo denormalizado continua fazendo sentido, já que evita somar o histórico a cada leitura. Só que `recalcular_saldo` conta apenas as transações com `data <= agora` no momento do recálculo. Se uma transação futura vence depois, o `saldo_atual` não muda até alguém escrever na conta de novo, e `GET /contas/:id/saldo` devolve o valor guardado sem recalcular. Essa limitação foi resolvida no dia 2: o endpoint agora recalcula ao ler e a justificativa escrita cobre o caso.
- `recalcular_saldo` carrega todas as transações da conta, soma em `float` no Python e só então grava em `Numeric(12,2)`. Com o volume atual não pesa. Para o dashboard, um `SUM` no banco com `Decimal` é mais seguro.
- Todo POST, PUT ou DELETE de transação com projeção negativa cria um `Alerta` novo, sem verificar se já existe um igual. Uma conta no vermelho vai juntando alertas repetidos e o dashboard mostra todos. Falta uma regra, por exemplo um alerta aberto por conta e nível, ou uma coluna de status. Isso está na lógica do Charles, então vale combinar com ele antes.
- `alerta.mensagem` guarda o valor projetado só como texto. Se o dashboard quiser exibir ou ordenar por esse valor, vai precisar de uma coluna numérica.

### Fechamento da análise (dia 2)

Passei por todas as colunas atrás de dado guardado duas vezes. Resultado:

- `conta.saldo_atual`: duplicado de propósito. Justificativa completa em [decisao-saldo-atual.md](decisao-saldo-atual.md), com a origem conferida no histórico do CP1. Fica.
- Saldo projetado: não é guardado, é calculado a cada chamada. Sem duplicidade.
- `alerta.nivel_risco`: dá para calcular a partir do saldo projetado (`nivel_risco()` em `saldo.py`), mas o alerta registra o nível daquele momento e o projetado muda depois. É um retrato histórico, então fica.
- `alerta.mensagem`: repete o valor projetado dentro do texto. É a única duplicação sem justificativa clara, e já está na lista acima (coluna numérica se o dashboard precisar).
- `idx_transacao_conta_id`: redundante quando o composto `(conta_id, data)` entrar. Também já listado nos índices.
- `transacao.tipo` junto com `valor > 0`: o sinal vem só do `tipo`, sem coluna extra de sinal. Sem duplicidade.
- `transacao.conta_id`, `transacao.categoria_id` e `alerta.conta_id`: cada chave estrangeira aparece uma vez. Sem duplicidade.

Fora do schema, mas que vi no caminho: `calcular_saldo_projetado` roda duas vezes no POST de transação (dentro de `_avaliar_risco` e de novo para montar a resposta), e o docstring de `app/models/__init__.py` ainda tem o esqueleto antigo com `__tablename__ = "contas"`. Nenhum dos dois muda o schema.

## Integridade

- `categoria.nome` é `UNIQUE`, mas diferencia maiúsculas de minúsculas: "Vendas" e "vendas" entram como duas categorias. A checagem em `categorias_routes.py` também compara o texto exato. A correção é um índice único sobre `lower(nome)` e a mesma normalização na rota.
- `alerta.nivel_risco` aceita `NULL`, mas `_avaliar_risco` só cria alerta quando há um nível. Pode virar `NOT NULL`.
- `_avaliar_risco` faz um commit para a transação e outro para o saldo. Se o segundo falhar, a transação fica gravada e o saldo defasado. Duas requisições simultâneas na mesma conta também podem sobrescrever o saldo uma da outra.
- `Conta` apaga em cascata `transacao` e `alerta`. Como não existe `DELETE /contas`, hoje isso não causa problema, mas a decisão precisa constar na justificativa. No model, `passive_deletes=True` deixaria o Postgres fazer a cascata em vez de o SQLAlchemy carregar tudo antes.
- A migration foi gerada em SQLite (`server_default` com `(CURRENT_TIMESTAMP)` e `batch_alter_table`). Ainda não a rodei num Postgres limpo nem conferi com `flask db check` se o model e o banco batem.

## O que já está certo

- `valor > 0` e `tipo IN ('entrada','saida')` em `transacao`.
- `nivel_risco IN ('baixo','medio','alto')` em `alerta`.
- Chaves estrangeiras com `CASCADE` (conta) e `SET NULL` (categoria), iguais no model e na migration.

## Ordem sugerida

1. Dia 2: fechar a análise de duplicidade e escrever a justificativa do `saldo_atual`, incluindo o caso da transação futura.
2. Dia 3: uma migration nova com os índices compostos e o índice de `categoria_id`, testada em Postgres limpo. O `lower(nome)` ficou de fora (ver o fechamento do dia 3, no fim do arquivo).
3. Dia 4: rodar a suíte inteira e os testes de saldo depois da migration.
4. Levar para o Charles os alertas repetidos e o commit duplo em `_avaliar_risco`.

## Fechamento do dia 3: índices

Migration `94bd0c73981a`, em cima da `0c68856f9520`. O que mudou:

| Tabela | Sai | Entra | Para quê |
|---|---|---|---|
| `transacao` | `idx_transacao_conta_id` | `idx_transacao_conta_data (conta_id, data)` | Filtrar por conta e ordenar por data, que é o que `GET /transacoes?conta_id=` e o dashboard fazem |
| `transacao` | | `idx_transacao_categoria_id (categoria_id)` | Total por categoria e o `ON DELETE SET NULL` ao apagar categoria |
| `alerta` | `idx_alerta_conta_id` | `idx_alerta_conta_data (conta_id, data)` | Alertas recentes de uma conta |

`idx_transacao_data` continua, porque o dashboard também vai olhar o período de todas as contas juntas, sem filtro de conta. `transacao.tipo` segue sem índice (só dois valores).

Os dois `idx_*_conta_id` saíram porque o composto começa por `conta_id` e responde a mesma busca. Manter os dois só encareceria toda escrita. A migration cria o novo antes de derrubar o antigo, então `conta_id` nunca fica sem índice, e o `downgrade` volta ao estado anterior.

O `alerta` merece uma ressalva: `GET /alertas` hoje lista tudo sem filtrar por conta, então essa rota não ganha nada com o composto. Ele só passa a valer quando o dashboard listar alertas por conta. Como ele substitui um índice que já existia, o custo é zero.

### Como conferi

Primeiro num SQLite descartável, depois num Postgres 16 limpo (container Docker) e, por último, no banco do Render.

**Postgres 16 limpo:** a cadeia inteira (`0c68856f9520` e depois `94bd0c73981a`) sobe do zero. `flask db check` responde "No new upgrade operations detected", ou seja, models e banco batem. `downgrade` e `upgrade` de novo funcionam. A suíte de 35 testes passa nele.

Um detalhe sobre os testes: eles chamam `create_all()` esperando um SQLite em memória, zerado a cada teste. Num banco persistente os dados vazam de um teste para o outro (7 falham por causa de `categoria.nome` duplicada, sem relação com os índices). Para rodar em Postgres usei um plugin temporário que faz `drop_all()` antes de cada teste, sem mexer nos testes. Se um dia o CI rodar em Postgres, precisa de algo assim.

**`EXPLAIN` no Postgres**, com 200 mil transações distribuídas em 20 contas:

- Conta + ordenação por data com `LIMIT 50`: `Index Scan Backward using idx_transacao_conta_data`. É o caso que motivou o índice, e a ordem sai do próprio índice, sem passo de sort.
- Busca por `categoria_id` (o que o `ON DELETE SET NULL` faz ao apagar uma categoria): `Bitmap Index Scan on idx_transacao_categoria_id`.
- Conta + intervalo de uma semana: o planejador escolheu `idx_transacao_data` com filtro em `conta_id`, e não o composto. Nesse volume e nessa faixa o custo estimado foi menor assim, então o composto não é usado em toda query de período.
- Total por categoria sobre a tabela inteira: `Seq Scan`. Agregar tudo lê tudo, e o índice não ajuda. O de `categoria_id` vale para filtro por categoria e para o `SET NULL`, não para esse `GROUP BY` completo.

**Render:** o banco estava na `0c68856f9520`, com 1 conta, 3 categorias, 3 transações e 2 alertas. Apliquei `flask db upgrade` em 23/09. Ficou na `94bd0c73981a`, os quatro índices esperados existem, os dados continuam iguais e `flask db check` responde limpo.

### Fora do dia 3

O índice único em `lower(categoria.nome)` não entrou. Ele é regra de integridade, não de desempenho, e para funcionar precisa da mesma normalização em `categorias_routes.py` e de uma checagem de duplicatas já existentes no banco (se houver "Vendas" e "vendas", a migration quebra). Fica para o dia 4 junto com a validação, ou para o bloco de integridade.
