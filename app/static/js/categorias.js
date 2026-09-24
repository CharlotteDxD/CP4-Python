(() => {
  const $ = id => document.getElementById(id);
  const campo = $("campo-nome");
  const erro = campo.querySelector(".field-error");

  async function carregar() {
    const [rc, rt] = await Promise.all([API.get("/categorias"), API.get("/transacoes")]);
    if (!rc.sucesso) {
      $("lista").innerHTML = `<tr><td colspan="3" class="muted">Não foi possível carregar as categorias. ${UI.esc(rc.erro)}</td></tr>`;
      return;
    }
    const trans = rt.dados ?? [];
    $("lista").innerHTML = rc.dados.length
      ? rc.dados.map(c => {
          const doCat = trans.filter(t => t.categoria_id === c.id);
          const total = doCat.reduce((s, t) => s + t.valor, 0);
          return `<tr><td>${UI.esc(c.nome)}</td><td class="num">${doCat.length}</td><td class="num">${API.fmt.moeda(total)}</td></tr>`;
        }).join("")
      : '<tr><td colspan="3" class="muted">Nenhuma categoria ainda. Crie a primeira para o agente conseguir categorizar.</td></tr>';
  }

  function mostrarErro(texto) {
    campo.classList.add("has-error");
    erro.textContent = texto;
    erro.hidden = false;
    $("c-nome").focus();
  }

  $("form-cat").addEventListener("submit", async e => {
    e.preventDefault();
    campo.classList.remove("has-error");
    erro.hidden = true;

    const nome = $("c-nome").value.trim();
    if (!nome) return mostrarErro("Dê um nome para a categoria.");

    $("btn-criar").disabled = true;
    const r = await API.post("/categorias", { nome });
    $("btn-criar").disabled = false;

    if (!r.sucesso) return mostrarErro(r.status === 409 ? `Já existe uma categoria chamada "${nome}".` : r.erro);

    $("c-nome").value = "";
    UI.toast(`Categoria ${r.dados.nome} criada.`);
    carregar();
  });

  carregar();
})();
