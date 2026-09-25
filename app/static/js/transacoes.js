(() => {
  const { fmt } = API;
  const $ = id => document.getElementById(id);
  const dlg = $("dlg-transacao");
  const form = $("form-transacao");
  const dlgExcluir = $("dlg-excluir");

  const POR_PAGINA = 15;

  let transacoes = [];
  let categorias = [];
  let editando = null;
  let pagina = 1;
  let ultimaReq = 0;
  let debounce;

  const nomeCat = id => categorias.find(c => c.id === id)?.nome;

  const lerFiltros = () => ({
    busca: $("f-busca").value.trim(),
    tipo: $("f-tipo").value,
    cat: $("f-categoria").value,
    de: $("f-de").value,
    ate: $("f-ate").value,
  });

  function queryDaLista(f) {
    const q = new URLSearchParams();
    if (f.busca) q.set("busca", f.busca);
    if (f.tipo) q.set("tipo", f.tipo);
    if (f.cat === "sem") q.set("sem_categoria", "true");
    else if (f.cat) q.set("categoria_id", f.cat);
    if (f.de) q.set("data_inicio", f.de);
    if (f.ate) q.set("data_fim", f.ate);
    q.set("pagina", pagina);
    q.set("por_pagina", POR_PAGINA);
    return q.toString();
  }

  async function carregarCategorias() {
    const r = await API.get("/categorias");
    if (!r.sucesso) return UI.toast(r.erro ?? "Não foi possível carregar as categorias.", "erro");
    categorias = r.dados;
    const opcoes = categorias.map(c => `<option value="${c.id}">${UI.esc(c.nome)}</option>`).join("");
    $("f-categoria").innerHTML = `<option value="">Todas</option><option value="sem">Sem categoria</option>${opcoes}`;
    $("c-categoria").innerHTML = `<option value="">Deixar o agente escolher</option>${opcoes}`;
  }

  async function carregarLista() {
    const f = lerFiltros();
    $("f-limpar").hidden = !Object.values(f).some(Boolean);
    $("vazio").hidden = true;
    $("pager").hidden = true;

    if (f.de && f.ate && f.de > f.ate) {
      $("lista").innerHTML = "";
      return mostrarVazio("Período inválido.", "A data inicial é depois da data final.");
    }

    $("lista").innerHTML = Array.from({ length: 5 }, () =>
      `<tr><td colspan="5"><span class="skeleton"></span></td></tr>`).join("");

    // se o usuário mexer nos filtros com uma resposta ainda em voo, só a última vale
    const minha = ++ultimaReq;
    const r = await API.get(`/transacoes?${queryDaLista(f)}`);
    if (minha !== ultimaReq) return;

    if (!r.sucesso) {
      $("lista").innerHTML = "";
      return mostrarVazio("Não foi possível carregar as transações.", r.erro);
    }

    const { itens, total, total_paginas } = r.dados;
    // apagou o último item da página: volta uma
    if (!itens.length && total > 0 && pagina > total_paginas) {
      pagina = total_paginas;
      return carregarLista();
    }
    transacoes = itens;
    render(f, total, total_paginas);
  }

  function mostrarVazio(titulo, texto) {
    $("vazio").innerHTML = `<strong>${UI.esc(titulo)}</strong>${UI.esc(texto ?? "")}`;
    $("vazio").hidden = false;
  }

  function render(f, total, totalPaginas) {
    const hoje = API.hoje();

    $("vazio").hidden = true;
    if (!total) {
      if (Object.values(f).some(Boolean)) mostrarVazio("Nenhuma transação com esses filtros.", "Limpe os filtros ou ajuste o período.");
      else mostrarVazio("Nenhuma transação ainda.", "Registre a primeira entrada ou saída da conta.");
    }

    $("lista").innerHTML = transacoes.map(t => {
      const futura = new Date(t.data) > hoje;
      return `<tr class="${futura ? "is-future" : ""}">
        <td>${fmt.dataCurta(t.data)}</td>
        <td class="desc">${UI.esc(t.descricao ?? "Sem descrição")} ${futura ? '<span class="chip chip-plain chip-future">Agendada</span>' : ""}</td>
        <td class="col-hide-sm">${nomeCat(t.categoria_id) ? UI.esc(nomeCat(t.categoria_id)) : '<span class="muted">Sem categoria</span>'}</td>
        <td class="num ${t.tipo === "entrada" ? "val-pos" : "val-neg"}">${t.tipo === "entrada" ? "+" : "-"} ${fmt.moeda(t.valor)}</td>
        <td><div class="row-actions">
          <button type="button" class="btn btn-ghost" data-editar="${t.id}">Editar</button>
          <button type="button" class="btn btn-ghost" data-excluir="${t.id}">Excluir</button>
        </div></td>
      </tr>`;
    }).join("");

    renderPager(total, totalPaginas);
  }

  function renderPager(total, totalPaginas) {
    if (!total) return;
    const de = (pagina - 1) * POR_PAGINA + 1;
    const ate = de + transacoes.length - 1;
    $("pager-info").textContent = `${de}-${ate} de ${total}`;
    $("pager-btns").hidden = totalPaginas <= 1;
    $("pg-atual").textContent = `Página ${pagina} de ${totalPaginas}`;
    $("pg-ant").disabled = pagina <= 1;
    $("pg-prox").disabled = pagina >= totalPaginas;
    $("pager").hidden = false;
  }

  function filtroMudou() {
    pagina = 1;
    carregarLista();
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
    if (!editando) pagina = 1;
    await carregarLista();

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
        carregarLista();
      }, { once: true });
    }
  });

  form.querySelector("[data-fechar]").addEventListener("click", () => dlg.close());
  $("btn-nova").addEventListener("click", () => abrir());

  // a busca espera o usuário parar de digitar; os outros filtros disparam na hora
  $("f-busca").addEventListener("input", () => {
    clearTimeout(debounce);
    debounce = setTimeout(filtroMudou, 300);
  });
  ["f-tipo", "f-categoria", "f-de", "f-ate"].forEach(id => $(id).addEventListener("change", filtroMudou));

  $("f-limpar").addEventListener("click", () => {
    ["f-busca", "f-tipo", "f-categoria", "f-de", "f-ate"].forEach(id => { $(id).value = ""; });
    filtroMudou();
  });

  $("pg-ant").addEventListener("click", () => { pagina -= 1; carregarLista(); });
  $("pg-prox").addEventListener("click", () => { pagina += 1; carregarLista(); });

  carregarCategorias().then(carregarLista).then(() => {
    if (new URLSearchParams(location.search).has("nova")) abrir();
  });
})();
