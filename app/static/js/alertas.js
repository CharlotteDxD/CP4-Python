(async () => {
  const $ = id => document.getElementById(id);
  const r = await API.get("/alertas");

  if (!r.sucesso) {
    $("vazio").innerHTML = `<strong>Não foi possível carregar os alertas.</strong>${UI.esc(r.erro)}`;
    $("vazio").hidden = false;
    return;
  }

  const moedaNaMensagem = m => m.replace(/R\$ (-?\d+(?:\.\d+)?)/, (_, v) => API.fmt.moeda(Number(v)));

  function render() {
    const nivel = $("f-nivel").value;
    const lista = r.dados.filter(a => !nivel || a.nivel_risco === nivel);

    $("vazio").hidden = lista.length > 0;
    $("vazio").innerHTML = r.dados.length
      ? "<strong>Nenhum alerta com esse nível.</strong>Escolha outro nível de risco."
      : "<strong>Nenhum alerta até agora.</strong>O agente cria um alerta quando a projeção do saldo fica negativa.";

    $("lista").innerHTML = lista.map(a => `
      <li class="block alert">
        <div class="alert-side">
          <span class="chip risk-${a.nivel_risco}">Risco ${UI.nivel(a.nivel_risco).toLowerCase()}</span>
          <span>${API.fmt.dataHora(a.data)}</span>
        </div>
        <div>
          <p class="alert-msg">${UI.esc(moedaNaMensagem(a.mensagem))}</p>
          ${a.recomendacao
            ? `<p class="alert-rec"><span class="alert-rec-label">Recomendação do agente</span>${UI.esc(a.recomendacao)}</p>`
            : `<p class="alert-rec is-missing"><span class="alert-rec-label">Sem recomendação</span>A IA não respondeu a tempo. O alerta foi salvo mesmo assim.</p>`}
        </div>
      </li>`).join("");
  }

  $("f-nivel").addEventListener("input", render);
  render();
})();
