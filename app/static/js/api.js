// Camada de dados do frontend. Com USE_MOCK = true tudo roda em memória, no
// mesmo formato de resposta da API ({sucesso, dados} / {sucesso, erro}).
// Para ligar no backend real, troque para false: as páginas não mudam.
const USE_MOCK = true;

// Contrato proposto para o endpoint agregado do painel (ainda não existe no backend):
// GET /dashboard/resumo?conta_id=1 -> {
//   conta: {id, nome, saldo_atual, saldo_projetado},
//   totais_mes: {entradas, saidas},
//   saidas_por_categoria: [{categoria, total}],
//   evolucao_saldo: [{data, saldo, projetado}],
//   data_saldo_negativo: "AAAA-MM-DD" | null,
//   alertas_abertos: number
// }

const API = (() => {
  const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
  // "AAAA-MM-DD" sozinho é lido como UTC e volta um dia no fuso do Brasil.
  const data = iso => new Date(iso.length === 10 ? `${iso}T12:00:00` : iso);
  const fmt = {
    moeda: v => brl.format(v),
    dataCurta: iso => data(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }),
    dataLonga: iso => data(iso).toLocaleDateString("pt-BR", { day: "numeric", month: "long" }),
    dataHora: iso => data(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }),
  };

  const hoje = () => (USE_MOCK ? new Date("2026-09-23T12:00:00") : new Date());

  async function request(method, path, body) {
    if (USE_MOCK) {
      await new Promise(r => setTimeout(r, 220));
      return Mock.handle(method, path, body);
    }
    try {
      const res = await fetch(path, {
        method,
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
      const json = await res.json().catch(() => ({ sucesso: false, erro: "Resposta inválida do servidor" }));
      return { status: res.status, ...json };
    } catch {
      return { status: 0, sucesso: false, erro: "Não foi possível falar com o servidor. Confira se a API está rodando." };
    }
  }

  return {
    fmt,
    hoje,
    get: path => request("GET", path),
    post: (path, body) => request("POST", path, body),
    put: (path, body) => request("PUT", path, body),
    del: path => request("DELETE", path),
  };
})();

const Mock = (() => {
  let seq = 100;
  const conta = { id: 1, nome: "Padaria Boa Massa", criado_em: "2026-08-01T09:00:00" };

  const categorias = [
    "Vendas", "Fornecedores", "Aluguel", "Folha de pagamento", "Energia", "Impostos", "Marketing",
  ].map((nome, i) => ({ id: i + 1, nome }));
  const cat = nome => categorias.find(c => c.nome === nome).id;

  const t = (data, tipo, valor, categoria, descricao) => ({
    id: ++seq, valor, tipo, conta_id: 1, categoria_id: categoria ? cat(categoria) : null,
    data: `2026-${data}T10:00:00`, descricao,
  });

  const transacoes = [
    t("09-01", "entrada", 6200, "Vendas", "Vendas do balcão, semana 1"),
    t("09-02", "saida", 2800, "Aluguel", "Aluguel do ponto, setembro"),
    t("09-04", "saida", 1350, "Fornecedores", "Farinha e fermento, Moinho Sul"),
    t("09-08", "entrada", 5900, "Vendas", "Vendas do balcão, semana 2"),
    t("09-10", "saida", 4200, "Folha de pagamento", "Folha, 1ª quinzena"),
    t("09-12", "saida", 486.9, "Energia", "Conta de energia elétrica"),
    t("09-15", "entrada", 6450, "Vendas", "Vendas do balcão, semana 3"),
    t("09-16", "saida", 1720, "Fornecedores", "Laticínios, Fazenda Serra"),
    t("09-18", "saida", 390, "Marketing", "Anúncio no Instagram"),
    t("09-20", "saida", 1180, "Impostos", "DAS Simples Nacional"),
    t("09-21", "saida", 214.5, null, "Manutenção da masseira"),
    t("09-22", "entrada", 5100, "Vendas", "Vendas do balcão, semana 4"),
    t("09-25", "saida", 4200, "Folha de pagamento", "Folha, 2ª quinzena"),
    t("09-30", "saida", 3900, "Fornecedores", "Forno novo, parcela 3 de 6"),
    t("10-02", "saida", 2800, "Aluguel", "Aluguel do ponto, outubro"),
    t("10-03", "entrada", 2400, "Vendas", "Encomenda de buffet para evento"),
    t("10-05", "saida", 1600, "Fornecedores", "Farinha e fermento, Moinho Sul"),
    t("10-10", "saida", 4200, "Folha de pagamento", "Folha, 1ª quinzena"),
    t("10-14", "saida", 1850, "Impostos", "DAS Simples Nacional"),
  ];

  const alertas = [
    {
      id: 3, conta_id: 1, nivel_risco: "alto", data: "2026-09-22T18:40:00",
      mensagem: "Saldo projetado da conta ficou negativo: R$ -4841.40",
      recomendacao: "A folha do dia 10/10 e o DAS do dia 14/10 caem depois que o caixa já zerou. Negocie o vencimento da parcela do forno para depois do dia 15 ou peça sinal de 50% na encomenda do buffet. Qualquer uma das duas mantém o saldo positivo até o fim de outubro.",
    },
    {
      id: 2, conta_id: 1, nivel_risco: "medio", data: "2026-09-16T11:05:00",
      mensagem: "Saldo projetado da conta ficou negativo: R$ -380.00",
      recomendacao: "A compra de laticínios desta semana foi 27% maior que a média do mês. Se parte for estoque, dá para dividir o pagamento em duas vezes sem juros com o fornecedor.",
    },
    {
      id: 1, conta_id: 1, nivel_risco: "baixo", data: "2026-09-04T09:12:00",
      mensagem: "Saldo projetado da conta ficou negativo: R$ -64.00",
      recomendacao: null,
    },
  ];

  const PALAVRAS = [
    [/energia|luz|eletric/i, "Energia"],
    [/aluguel/i, "Aluguel"],
    [/farinha|fermento|fornecedor|latic|insumo|forno/i, "Fornecedores"],
    [/venda|encomenda|pix recebido|buffet/i, "Vendas"],
    [/folha|sal[aá]rio/i, "Folha de pagamento"],
    [/imposto|das|simples/i, "Impostos"],
    [/an[uú]ncio|instagram|marketing|panfleto/i, "Marketing"],
  ];

  const ok = (dados, status = 200) => ({ status, sucesso: true, dados });
  const msg = (mensagem, status = 200) => ({ status, sucesso: true, mensagem });
  const erro = (texto, status = 400) => ({ status, sucesso: false, erro: texto });

  const assinado = x => (x.tipo === "entrada" ? x.valor : -x.valor);
  const soma = lista => Math.round(lista.reduce((s, x) => s + assinado(x), 0) * 100) / 100;
  const saldoAtual = () => soma(transacoes.filter(x => new Date(x.data) <= API.hoje()));
  const saldoProjetado = () => soma(transacoes);

  function nivelRisco(projetado) {
    if (projetado >= 0) return null;
    if (projetado <= -500) return "alto";
    if (projetado <= -100) return "medio";
    return "baixo";
  }

  function validar(body, parcial) {
    if ("tipo" in body && !["entrada", "saida"].includes(body.tipo)) return "Campo 'tipo' deve ser 'entrada' ou 'saida'";
    if ("valor" in body) {
      const v = Number(body.valor);
      if (body.valor === "" || Number.isNaN(v)) return "Campo 'valor' deve ser numérico";
      if (v <= 0) return "Campo 'valor' deve ser maior que zero";
    }
    if (body.data && Number.isNaN(Date.parse(body.data))) return "Campo 'data' deve estar em formato ISO 8601 (texto)";
    if (!parcial) {
      const faltando = ["valor", "tipo", "conta_id"].filter(c => body[c] == null || body[c] === "");
      if (faltando.length) return `Campos obrigatórios faltando: ${faltando.join(", ")}`;
    }
    return null;
  }

  function avaliarRisco() {
    const projetado = saldoProjetado();
    const nivel = nivelRisco(projetado);
    if (!nivel) return null;
    const alerta = {
      id: ++seq, conta_id: 1, nivel_risco: nivel, data: new Date().toISOString(),
      mensagem: `Saldo projetado da conta ficou negativo: R$ ${projetado.toFixed(2)}`,
      recomendacao: "Recomendação de exemplo: adie a próxima saída agendada ou antecipe um recebimento para cobrir a diferença.",
    };
    alertas.unshift(alerta);
    return alerta;
  }

  function resumo() {
    const agora = API.hoje();
    const mes = x => new Date(x.data).getMonth() === agora.getMonth() && new Date(x.data) <= agora;
    const doMes = transacoes.filter(mes);

    const porCategoria = {};
    doMes.filter(x => x.tipo === "saida").forEach(x => {
      const nome = categorias.find(c => c.id === x.categoria_id)?.nome ?? "Sem categoria";
      porCategoria[nome] = (porCategoria[nome] || 0) + x.valor;
    });

    let saldo = 0;
    let negativo = null;
    const evolucao = [...transacoes]
      .sort((a, b) => a.data.localeCompare(b.data))
      .map(x => {
        saldo = Math.round((saldo + assinado(x)) * 100) / 100;
        const projetado = new Date(x.data) > agora;
        if (projetado && saldo < 0 && !negativo) negativo = x.data.slice(0, 10);
        return { data: x.data, saldo, projetado };
      });

    return {
      conta: { id: conta.id, nome: conta.nome, saldo_atual: saldoAtual(), saldo_projetado: saldoProjetado() },
      totais_mes: {
        entradas: doMes.filter(x => x.tipo === "entrada").reduce((s, x) => s + x.valor, 0),
        saidas: doMes.filter(x => x.tipo === "saida").reduce((s, x) => s + x.valor, 0),
      },
      saidas_por_categoria: Object.entries(porCategoria)
        .map(([categoria, total]) => ({ categoria, total }))
        .sort((a, b) => b.total - a.total),
      evolucao_saldo: evolucao,
      data_saldo_negativo: negativo,
      alertas_abertos: alertas.length,
    };
  }

  function salvarTransacao(body, existente) {
    const e = validar(body, !!existente);
    if (e) return erro(e);
    if ("conta_id" in body && Number(body.conta_id) !== conta.id) return erro("Conta informada não existe", 404);
    if (body.categoria_id != null && body.categoria_id !== "" && !categorias.some(c => c.id === Number(body.categoria_id))) {
      return erro("Categoria informada não existe", 404);
    }

    const alvo = existente ?? { id: ++seq, conta_id: conta.id, data: API.hoje().toISOString().slice(0, 19) };
    if ("valor" in body) alvo.valor = Number(body.valor);
    if ("tipo" in body) alvo.tipo = body.tipo;
    if ("descricao" in body) alvo.descricao = body.descricao || null;
    if (body.data) alvo.data = body.data;
    if ("categoria_id" in body) alvo.categoria_id = body.categoria_id == null || body.categoria_id === "" ? null : Number(body.categoria_id);

    if (!existente && alvo.categoria_id == null && alvo.descricao) {
      const achou = PALAVRAS.find(([re]) => re.test(alvo.descricao));
      alvo.categoria_id = achou ? cat(achou[1]) : null;
    }
    if (!existente) transacoes.push(alvo);

    const payload = { ...alvo };
    const alerta = avaliarRisco();
    if (alerta) payload.alerta_gerado = alerta;
    payload.saldo_projetado = saldoProjetado();
    return ok(payload, existente ? 200 : 201);
  }

  function handle(method, path, body = {}) {
    const url = new URL(path, location.origin);
    const p = url.pathname.replace(/\/$/, "");
    const id = Number(p.split("/").pop());

    if (method === "GET" && p === "/categorias") return ok([...categorias].sort((a, b) => a.nome.localeCompare(b.nome)));
    if (method === "POST" && p === "/categorias") {
      const nome = String(body.nome ?? "").trim();
      if (!nome) return erro("Campo 'nome' é obrigatório");
      if (categorias.some(c => c.nome.toLowerCase() === nome.toLowerCase())) return erro("Já existe uma categoria com esse nome", 409);
      const nova = { id: ++seq, nome };
      categorias.push(nova);
      return ok(nova, 201);
    }

    if (method === "GET" && p === "/transacoes") return ok([...transacoes].sort((a, b) => b.data.localeCompare(a.data)));
    if (method === "POST" && p === "/transacoes") return salvarTransacao(body);
    if (p.startsWith("/transacoes/")) {
      const alvo = transacoes.find(x => x.id === id);
      if (!alvo) return erro("Transação não encontrada", 404);
      if (method === "GET") return ok(alvo);
      if (method === "PUT") return salvarTransacao(body, alvo);
      if (method === "DELETE") {
        transacoes.splice(transacoes.indexOf(alvo), 1);
        avaliarRisco();
        return msg("Transação removida com sucesso");
      }
    }

    if (method === "GET" && p === `/contas/${conta.id}/saldo`) {
      return ok({ conta_id: conta.id, nome: conta.nome, saldo_atual: saldoAtual(), saldo_projetado: saldoProjetado() });
    }
    if (method === "GET" && p === "/alertas") return ok(alertas);
    if (method === "GET" && p === "/dashboard/resumo") return ok(resumo());

    return erro("Rota não encontrada", 404);
  }

  return { handle };
})();

const UI = {
  toast(texto, tipo = "info", acao) {
    const el = document.createElement("div");
    el.className = `toast toast-${tipo}`;
    el.textContent = texto;
    if (acao) {
      const a = document.createElement("a");
      a.href = acao.href;
      a.textContent = acao.label;
      el.append(" ", a);
    }
    document.getElementById("toasts").append(el);
    setTimeout(() => el.remove(), 6000);
  },
  esc: s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])),
  nivel: n => ({ alto: "Alto", medio: "Médio", baixo: "Baixo" }[n] ?? "Sem nível"),
};

(async () => {
  if (!USE_MOCK) document.getElementById("modo-dados").textContent = "Conectado à API";
  const r = await API.get("/alertas");
  const badge = document.getElementById("nav-alertas");
  if (r.sucesso && r.dados.length && badge) {
    badge.textContent = r.dados.length;
    badge.hidden = false;
  }
})();
