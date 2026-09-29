# Revisão das queries do dashboard

Revisão do `GET /dashboard/resumo` à luz dos índices novos (dia 8 do CP2, feita junto com o Charles). As consultas estão em `app/blueprints/dashboard/routes.py`.

## O que a rota faz no banco

| Consulta | Índice que usa | Situação |
|---|---|---|
| Totais do mês por tipo (`SUM` agrupado por `tipo`, filtro por conta e período) | `idx_transacao_conta_data` | Já estava certa |
| Saídas do mês por categoria (`JOIN` com categoria, `GROUP BY`) | `idx_transacao_conta_data` para o filtro | Já estava certa |
| Contagem de alertas da conta | `idx_alerta_conta_data` | Já estava certa |
| Evolução diária do saldo | `idx_transacao_conta_data` | **Trocada** |

## O que mudou

A evolução do saldo carregava todas as transações da conta como objetos do SQLAlchemy e somava em Python. O trabalho e a memória cresciam com o tamanho do histórico, e o dashboard é a tela que mais vai ser aberta.

Agora o banco agrupa por dia (`GROUP BY date(data)`) e devolve o total do dia e o total do que já venceu (`data <= agora`). O Python só faz o acumulado corrido sobre uma linha por dia com movimento. A conta continua sendo feita a partir dos mesmos dados e a regra do saldo atual não mudou.

Medido no SQLite, uma conta com histórico de cerca de um ano e meio (a versão antiga contra a nova, tempo da função):

| Transações | Antes | Depois |
|---|---|---|
| 2.000 | 19 ms | 5 ms |
| 50.000 | 673 ms | 133 ms |

Nas duas cargas o resultado saiu idêntico ao da versão antiga (mesmos pontos, mesmo saldo atual). O plano do SQLite mostra `SEARCH ... USING INDEX idx_transacao_conta_data (conta_id=?)`. Não rodei `EXPLAIN ANALYZE` no Postgres desta vez, o Docker estava desligado, então o ganho no Postgres não está medido.

O número de consultas por chamada não depende mais do histórico. Há um teste para isso (`test_resumo_faz_o_mesmo_numero_de_consultas_com_muito_ou_pouco_historico`).

## O que continua pesado

- `recalcular_saldo` e `calcular_saldo_projetado` (`app/services/saldo.py`) ainda carregam `conta.transacoes` inteira a cada escrita de transação. Dá para trocar por um `SUM` no banco, mas mexe na regra que todas as rotas de escrita usam, então fica para combinar com o Charles.
- A tela de categorias baixa a lista completa de transações para contar e somar por categoria no navegador. Um endpoint agregado resolveria, se o volume crescer.
- O total por categoria do mês lê todas as saídas do período. Agregar lê tudo por natureza, o índice não ajuda esse trecho.
