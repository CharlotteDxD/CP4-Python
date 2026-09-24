(() => {
  const { fmt } = API;
  const $ = id => document.getElementById(id);
  const dlg = $("dlg-transacao");
  const form = $("form-transacao");
  const dlgExcluir = $("dlg-excluir");

  let transacoes = [];
  let categorias = [];
  let editando = null;

  const nomeCat = id => categorias.find(c => c.id === id)?.nome;

  async function carregar() {
    $("lista").innerHTML = Array.from({ length: 5 }, () =>
      `<tr><td colspan="5"><span class="skeleton"></span></td></tr>`).join("");

    const [rt, rc] = await Promise.all([API.get("/transacoes"), API.get("/categorias")]);
    if (!rt.sucesso || !rc.sucesso) {
      $("lista").innerHTML = "";
      mostrarVazio("Não foi possível carregar as transações.", rt.erro || rc.erro);
      return;
    }
    transacoes = rt.dados;
    categorias = rc.dados;

    const opcoes = categorias.map(c => `<option value="${c.id}">${UI.esc(c.nome)}</option>`).join("");
    const filtroAtual = $("f-categoria").value;
    $("f-categoria").innerHTML = `<option value="">Todas</option><option value="sem">Sem categoria</option>${opcoes}`;
    $("f-categoria").value = filtroAtual;
    $("c-categoria").innerHTML = `<option value="">Deixar o agente escolher</option>${opcoes}`;
    render();
  }

  function mostrarVazio(titulo, texto) {
    $("vazio").innerHTML = `<strong>${UI.esc(titulo)}</strong>${UI.esc(texto ?? "")}`;
    $("vazio").hidden = false;
  }

  function render() {
    const busca = $("f-busca").value.trim().toLowerCase();
    const tipo = $("f-tipo").value;
    const cat = $("f-categoria").value;
    const hoje = API.hoje();

    const lista = transacoes.filter(t =>
      (!busca || (t.descricao ?? "").toLowerCase().includes(busca)) &&
      (!tipo || t.tipo === tipo) &&
      (!cat || (cat === "sem" ? t.categoria_id == null : t.categoria_id === Number(cat))));

    $("vazio").hidden = true;
    if (!transacoes.length) mostrarVazio("Nenhuma transação ainda.", "Registre a primeira entrada ou saída da conta.");
    else if (!lista.length) mostrarVazio("Nenhuma transação com esses filtros.", "Limpe a busca ou escolha outro tipo.");

    $("lista").innerHTML = lista.map(t => {
      const futura = new Date(t.data) > hoje;
      return `<tr class="${futura ? "is-future" : ""}">
        <td>${fmt.dataCurta(t.data)}</td>
        <td class="desc">${UI.esc(t.descricao ?? "Sem descrição")} ${futura ? '<span class="chip chip-plain chip-future">Agendada</span>' : ""}</td>
        <td class="col-hide-sm">${nomeCat(t.categoria_id) ? UI.esc(nomeCat(t.categoria_id)) : '<span class="muted">Sem categoria</span>'}</td>
        <td class="num ${t.tipo === "entrada" ? "val-pos" : "val-neg"}">${t.tipo === "entrada" ? "+" : "−"} ${fmt.moeda(t.valor)}</td>
        <td><div class="row-actions">
          <button type="button" class="btn btn-ghost" data-editar="${t.id}">Editar</button>
          <button type="button" class="btn btn-ghost" data-excluir="${t.id}">Excluir</button>
        </div></td>
      </tr>`;
    }).join("");
  }

  function abrir(t) {
    editando = t ?? null;
    form.reset();
    limparErros();
    $("dlg-titulo").textContent = t ? "Editar transação" : "Registrar transação";
    $("btn-salvar").textContent = t ? "Salvar alterações" : "Registrar transação";
    $("hint-ia").hidden = !!t;
    $("c-data").value = (t ? t.data : API.hoje().toISOString()).slice(0, 10);
    if (t) {
      $("c-descricao").value = t.descricao ?? "";
      $("c-valor").value = t.valor;
      form.tipo.value = t.tipo;
      $("c-categoria").value = t.categoria_id ?? "";
    }
    dlg.showModal();
    $("c-descricao").focus();
  }

  function limparErros() {
    $("form-erro").hidden = true;
    form.querySelectorAll(".field").forEach(f => {
      f.classList.remove("has-error");
      const e = f.querySelector(".field-error");
      if (e) e.hidden = true;
    });
  }

  function erroCampo(nome, texto) {
    const f = form.querySelector(`[data-campo="${nome}"]`);
    f.classList.add("has-error");
    const e = f.querySelector(".field-error");
    e.textContent = texto;
    e.hidden = false;
    f.querySelector(".input").focus();
  }

  form.addEventListener("submit", async e => {
    e.preventDefault();
    limparErros();

    const valor = Number($("c-valor").value);
    if (!$("c-valor").value || valor <= 0) return erroCampo("valor", "Informe um valor maior que zero.");

    const body = {
      descricao: $("c-descricao").value.trim(),
      valor,
      tipo: form.tipo.value,
      data: `${$("c-data").value}T12:00:00`,
    };
    const categoria = $("c-categoria").value;
    if (editando) body.categoria_id = categoria ? Number(categoria) : null;
    else {
      body.conta_id = 1;
      if (categoria) body.categoria_id = Number(categoria);
    }

    $("btn-salvar").disabled = true;
    const r = editando ? await API.put(`/transacoes/${editando.id}`, body) : await API.post("/transacoes", body);
    $("btn-salvar").disabled = false;

    if (!r.sucesso) {
      $("form-erro").textContent = r.erro;
      $("form-erro").hidden = false;
      return;
    }

    dlg.close();
    await carregar();

    let texto = editando ? "Alterações salvas." : "Transação registrada.";
    if (!editando && !categoria && r.dados.categoria_id) texto += ` O agente categorizou como ${nomeCat(r.dados.categoria_id)}.`;
    if (!editando && !categoria && !r.dados.categoria_id && body.descricao) texto += " O agente não encontrou uma categoria.";
    if (r.dados.aviso_ia) texto += ` ${r.dados.aviso_ia}`;
    UI.toast(texto);
    if (r.dados.alerta_gerado) {
      UI.toast("A projeção ficou negativa e o agente gerou um alerta.", "erro", { href: "/app/alertas", label: "Ver alerta" });
    }
  });

  $("lista").addEventListener("click", async e => {
    const ed = e.target.closest("[data-editar]");
    const ex = e.target.closest("[data-excluir]");
    if (ed) abrir(transacoes.find(t => t.id === Number(ed.dataset.editar)));
    if (ex) {
      const t = transacoes.find(x => x.id === Number(ex.dataset.excluir));
      $("excluir-texto").textContent = `${t.descricao ?? "Sem descrição"}, ${fmt.moeda(t.valor)} em ${fmt.dataCurta(t.data)}. O saldo e a projeção da conta serão recalculados.`;
      dlgExcluir.returnValue = "";
      dlgExcluir.showModal();
      dlgExcluir.addEventListener("close", async () => {
        if (dlgExcluir.returnValue !== "excluir") return;
        const r = await API.del(`/transacoes/${t.id}`);
        if (!r.sucesso) return UI.toast(r.erro, "erro");
        UI.toast("Transação excluída.");
        carregar();
      }, { once: true });
    }
  });

  form.querySelector("[data-fechar]").addEventListener("click", () => dlg.close());
  $("btn-nova").addEventListener("click", () => abrir());
  ["f-busca", "f-tipo", "f-categoria"].forEach(id => $(id).addEventListener("input", render));

  carregar().then(() => {
    if (new URLSearchParams(location.search).has("nova")) abrir();
  });
})();
