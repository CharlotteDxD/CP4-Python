# Por que `conta.saldo_atual` continua denormalizado

`saldo_atual` é a soma das transações da conta com `data <= agora`. Dá para calcular esse valor a qualquer momento a partir da tabela `transacao`, então ele é informação duplicada. Mantive o campo de propósito. Este texto registra o motivo, o custo e uma limitação que já conheço.

## Como funciona hoje

Toda escrita em transação passa por `_avaliar_risco` (`transacoes_routes.py`), que chama `recalcular_saldo(conta_id)` logo no começo. Isso vale para POST, PUT e DELETE. No PUT que troca a transação de conta, as duas contas são recalculadas.

`recalcular_saldo` soma o histórico inteiro e sobrescreve o campo. Ela não faz `saldo += delta`.

`GET /contas/<id>/saldo` também chama `recalcular_saldo` antes de responder (ver a seção sobre transação futura). O `saldo_projetado` (todas as transações, inclusive as futuras) não é guardado: `calcular_saldo_projetado` roda a cada chamada.

## Origem no CP1

Conferi no histórico do git do CP1. O campo `saldo_atual` entrou no model `Conta` no primeiro commit dos models (`ba8a699`, 02/09), com `Numeric(12, 2)` e default 0. No mesmo dia veio o `recalcular_saldo` (`451af55`), que já somava o histórico inteiro e sobrescrevia o campo. A regra de só contar transações com `data <= agora` veio logo depois, em `0597183`, junto com o saldo projetado. A migration inicial (`0c68856f9520`, 08/09) e o README do CP1 já listam o campo.

Ou seja, a denormalização é a mesma desde o início do CP1. O CP2 não introduz nada aqui, só passa a justificar por escrito.

## Por que manter o campo

O saldo é a leitura mais comum do sistema. Aparece no endpoint da conta e vai aparecer no dashboard, enquanto transação nova entra de vez em quando. Guardar o total permite que o dashboard e as listagens leiam uma coluna em vez de somar o histórico de cada conta.

Só as três rotas de transação escrevem em `transacao`, e as três terminam em `recalcular_saldo`. Não existe DELETE de conta, importação em lote nem outro caminho que mexa no histórico sem passar por ali. O `seed.py` cria a conta com saldo 0 e nenhuma transação, então também não desalinha nada.

Como o recálculo é completo, qualquer divergência se corrige na próxima escrita da conta. Um saldo errado por causa de uma falha no meio do caminho não vira erro permanente, o que seria o risco de uma atualização incremental.

Um ponto de honestidade: com o volume atual (seed de uma conta e três categorias, mais os testes) a diferença de desempenho é pequena. A escolha vale pelo padrão de uso, leitura muito mais frequente que escrita, e porque o custo de manter é baixo. Também vale notar que a escrita continua O(n), já que `recalcular_saldo` carrega todas as transações da conta. O que muda é que esse custo sai da leitura e fica só na escrita.

## Alternativas que considerei

Calcular sempre na leitura com um `SUM`. Não duplica nada e não tem risco de divergência, mas cada GET soma o histórico e precisa repetir o filtro de data. Com o índice composto `(conta_id, data)` previsto para o dia 3, seria aceitável em volume pequeno. Fica como plano B se a limitação abaixo pesar.

Atualização incremental. A escrita seria mais barata, mas o PUT pode mudar valor, tipo, data e conta ao mesmo tempo, então seria preciso desfazer o efeito antigo antes de aplicar o novo. Qualquer erro nessa conta acumula. Descartei.

View materializada. É demais para quatro tabelas.

## Transação com data futura

`recalcular_saldo` decide o que já venceu no momento em que roda. Se hoje entra uma saída de R$ 50 com data daqui a dois dias, ela fica fora do `saldo_atual`, o que está certo. Só que, quando a data chegar, nada dispara um novo cálculo, e o valor guardado ficaria defasado até a próxima escrita naquela conta.

Para fechar essa brecha, o `GET /contas/<id>/saldo` recalcula o saldo antes de responder, então quem consulta esse endpoint sempre vê o valor correto. O custo é uma soma por leitura, só nesse endpoint, e o GET passa a gravar na conta (o `recalcular_saldo` faz commit).

A coluna `saldo_atual` continua podendo ficar velha entre uma leitura e outra. Qualquer consumidor que leia o campo direto, sem passar pelo endpoint, como o dashboard futuro, precisa chamar `recalcular_saldo` primeiro ou aceitar o atraso. O teste `test_saldo_recalcula_transacao_futura_que_ja_venceu` cobre o caso do endpoint.

Se o custo do recálculo por leitura pesar, a alternativa é um job diário que recalcula todas as contas.

## Para explicar na apresentação

O saldo é uma informação derivada que eu guardo de propósito, porque é lida muito mais vezes do que é escrita. Toda escrita recalcula o valor do zero, então uma divergência não acumula, e o endpoint de saldo recalcula de novo na leitura para pegar transações futuras que já venceram.
