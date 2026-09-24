(async () => {
  const { fmt } = API;
  const [resumo, alertas, transacoes, categorias] = await Promise.all([
    API.get("/dashboard/resumo?conta_id=1"),
    API.get("/alertas"),
    API.get("/transacoes"),
    API.get("/categorias"),
  ]);

  if (!resumo.sucesso) {
    document.getElementById("headline").textContent = "Não foi possível carregar o resumo da conta.";
    document.getElementById("headline-sub").textContent = resumo.erro;
    return;
  }

  const r = resumo.dados;
  const nomeCat = id => categorias.dados?.find(c => c.id === id)?.nome;

  document.getElementById("conta-nome").textContent = r.conta.nome;
  document.getElementById("headline").textContent = r.data_saldo_negativo
    ? `Saldo de ${fmt.moeda(r.conta.saldo_atual)} hoje. Com as contas já agendadas, o caixa fica negativo em ${fmt.dataLonga(r.data_saldo_negativo)}.`
    : `Saldo de ${fmt.moeda(r.conta.saldo_atual)} hoje. Com as contas já agendadas, o caixa continua positivo.`;

  document.getElementById("f-entradas").textContent = fmt.moeda(r.totais_mes.entradas);
  document.getElementById("f-saidas").textContent = fmt.moeda(r.totais_mes.saidas);
  const proj = document.getElementById("f-projetado");
  proj.textContent = fmt.moeda(r.conta.saldo_projetado);
  proj.classList.toggle("is-neg", r.conta.saldo_projetado < 0);
  document.getElementById("f-alertas").textContent = r.alertas_abertos;

  const max = Math.max(...r.saidas_por_categoria.map(c => c.total), 1);
  document.getElementById("bars").innerHTML = r.saidas_por_categoria.length
    ? r.saidas_por_categoria.map(c => {
        const sem = c.categoria === "Sem categoria";
        return `<li><span class="${sem ? "muted-name" : ""}">${UI.esc(c.categoria)}</span><span>${fmt.moeda(c.total)}</span>` +
          `<span class="bar${sem ? " is-uncat" : ""}"><i style="width:${(c.total / max) * 100}%"></i></span></li>`;
      }).join("")
    : '<li class="muted">Nenhuma saída registrada este mês.</li>';

  const ultimo = alertas.dados?.[0];
  document.getElementById("advice").innerHTML = ultimo
    ? `<div class="advice-meta"><span class="chip risk-${ultimo.nivel_risco}">Risco ${UI.nivel(ultimo.nivel_risco).toLowerCase()}</span>${fmt.dataHora(ultimo.data)}</div>
       <p class="advice-text">${UI.esc(ultimo.recomendacao ?? "O agente não conseguiu gerar uma recomendação para este alerta.")}</p>
       <p class="advice-msg">${UI.esc(ultimo.mensagem)}</p>`
    : '<p class="muted">Nenhum alerta até agora. O agente avisa aqui quando a projeção ficar negativa.</p>';

  const hoje = API.hoje();
  document.getElementById("ultimas").innerHTML = (transacoes.dados ?? [])
    .filter(t => new Date(t.data) <= hoje)
    .slice(0, 6)
    .map(t => `<tr>
      <td>${fmt.dataCurta(t.data)}</td>
      <td class="desc">${UI.esc(t.descricao ?? "Sem descrição")}</td>
      <td class="col-hide-sm">${nomeCat(t.categoria_id) ? UI.esc(nomeCat(t.categoria_id)) : '<span class="muted">Sem categoria</span>'}</td>
      <td class="num ${t.tipo === "entrada" ? "val-pos" : "val-neg"}">${t.tipo === "entrada" ? "+" : "−"} ${fmt.moeda(t.valor)}</td>
    </tr>`).join("");

  desenharGrafico(r.evolucao_saldo, hoje);
})();

function desenharGrafico(pontos, hoje) {
  if (!window.Chart) return;
  const css = getComputedStyle(document.documentElement);
  const cor = n => css.getPropertyValue(n).trim();

  const idxHoje = pontos.findLastIndex(p => new Date(p.data) <= hoje);

  const linhaHoje = {
    id: "linhaHoje",
    afterDatasetsDraw(chart) {
      if (idxHoje < 0) return;
      const { ctx, chartArea, scales } = chart;
      const x = scales.x.getPixelForValue(idxHoje);
      ctx.save();
      ctx.strokeStyle = cor("--ink-2");
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(x, chartArea.top);
      ctx.lineTo(x, chartArea.bottom);
      ctx.stroke();
      ctx.fillStyle = cor("--ink-2");
      ctx.font = `500 12px ${cor("--font")}`;
      ctx.fillText("Hoje", x + 6, chartArea.top + 12);
      ctx.restore();
    },
  };

  new Chart(document.getElementById("chart-saldo"), {
    type: "line",
    data: {
      labels: pontos.map(p => API.fmt.dataCurta(p.data)),
      datasets: [{
        data: pontos.map(p => p.saldo),
        borderColor: cor("--brand"),
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointBackgroundColor: cor("--brand"),
        tension: 0,
        stepped: "before",
        fill: { target: { value: 0 }, above: "rgba(14, 90, 100, 0.07)", below: cor("--neg-soft") },
        segment: { borderDash: c => (pontos[c.p1DataIndex].projetado ? [5, 4] : undefined) },
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: cor("--ink"),
          padding: 10,
          displayColors: false,
          callbacks: {
            title: items => `${items[0].label}${pontos[items[0].dataIndex].projetado ? " (projetado)" : ""}`,
            label: item => API.fmt.moeda(item.parsed.y),
          },
        },
      },
      scales: {
        x: { grid: { display: false }, border: { color: cor("--line") }, ticks: { color: cor("--mute"), maxRotation: 0, autoSkipPadding: 16 } },
        y: {
          border: { display: false },
          grid: { color: c => (c.tick.value === 0 ? cor("--ink-2") : cor("--line")) },
          ticks: { color: cor("--mute"), callback: v => API.fmt.moeda(v).replace(",00", "") },
        },
      },
    },
    plugins: [linhaHoje],
  });
}
