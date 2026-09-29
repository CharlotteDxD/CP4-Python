(() => {
  const $ = id => document.getElementById(id);
  const campo = $("campo-nome");
  const erro = campo.querySelector(".field-error");
  const dlg = $("dlg-renomear");

  let categorias = [];
  let renomeando = null;

  async function carregar() {
    if (!categorias.length) $("lista").innerHTML = UI.esqueleto(4);
    const [rc, rt] = await Promise.all([API.get("/categorias"), API.get("/transacoes")]);
    if (!rc.sucesso) {
      if (categorias.length) return UI.toast(`Não foi possível atualizar a lista. ${rc.erro}`, "erro");
      $("aviso").hidden = true;
      $("lista").innerHTML = UI.falhaDeCarga(4, "Não foi possível carregar as categorias.", rc);
      return;
    }

    // sem as transações não dá para contar nem somar; mostrar 0 seria mentir
    $("aviso").hidden = rt.sucesso;
    if (!rt.sucesso) $("aviso-texto").textContent = `Não foi possível carregar os totais por categoria. ${rt.erro}`;
    const trans = rt.dados ?? [];

    categorias = rc.dados;
    $("lista").innerHTML = categorias.length
      ? categorias.map(c => {
          const doCat = trans.filter(t => t.categoria_id === c.id);
          const total = doCat.reduce((s, t) => s + t.valor, 0);
          const qtd = rt.sucesso ? doCat.length : "-";
          const soma = rt.sucesso ? API.fmt.moeda(total) : "-";
          return `<tr><td>${UI.esc(c.nome)}</td><td class="num">${qtd}</td><td class="num">${soma}</td>
            <td><div class="row-actions"><button type="button" class="btn btn-ghost" data-renomear="${c.id}">Renomear</button></div></td></tr>`;
        }).join("")
      : '<tr><td colspan="4" class="muted">Nenhuma categoria ainda. Crie a primeira para o agente conseguir categorizar.</td></tr>';
  }

  function mostrarErro(texto) {
    campo.classList.add("has-error");
    erro.textContent = texto;
    erro.hidden = false;
    $("c-nome").setAttribute("aria-invalid", "true");
    $("c-nome").focus();
  }

  function limparErro() {
    campo.classList.remove("has-error");
    erro.hidden = true;
    $("c-nome").removeAttribute("aria-invalid");
  }

  function erroNoDialogo(texto) {
    $("ren-erro").textContent = texto;
    $("ren-erro").hidden = false;
    $("r-nome").setAttribute("aria-invalid", "true");
    $("r-nome").focus();
  }

  $("c-nome").addEventListener("input", limparErro);
  $("r-nome").addEventListener("input", () => {
    $("ren-erro").hidden = true;
    $("r-nome").removeAttribute("aria-invalid");
  });

  $("form-cat").addEventListener("submit", async e => {
    e.preventDefault();
    limparErro();

    const nome = $("c-nome").value.trim();
    if (!nome) return mostrarErro("Dê um nome para a categoria.");

    $("btn-criar").disabled = true;
    const r = await API.post("/categorias", { nome });
    $("btn-criar").disabled = false;

    if (!r.sucesso) return UI.falha(r, texto => mostrarErro(r.status === 409 ? `Já existe uma categoria chamada "${nome}".` : texto));

    $("c-nome").value = "";
    UI.toast(`Categoria ${r.dados.nome} criada.`);
    carregar();
  });

  document.addEventListener("click", e => {
    if (e.target.closest("[data-tentar]")) carregar();
  });

  $("lista").addEventListener("click", e => {
    const b = e.target.closest("[data-renomear]");
    if (!b) return;
    renomeando = categorias.find(c => c.id === Number(b.dataset.renomear));
    $("ren-erro").hidden = true;
    $("r-nome").removeAttribute("aria-invalid");
    $("r-nome").value = renomeando.nome;
    dlg.showModal();
    $("r-nome").select();
  });

  $("form-renomear").addEventListener("submit", async e => {
    e.preventDefault();
    const nome = $("r-nome").value.trim();
    if (!nome) return erroNoDialogo("Dê um nome para a categoria.");

    $("btn-renomear").disabled = true;
    const r = await API.put(`/categorias/${renomeando.id}`, { nome });
    $("btn-renomear").disabled = false;
    if (!r.sucesso) {
      if (r.status === 404) {
        dlg.close();
        UI.toast(r.erro, "erro");
        return carregar();
      }
      return erroNoDialogo(r.status === 409 ? `Já existe uma categoria chamada "${nome}".` : r.erro);
    }

    dlg.close();
    UI.toast("Categoria renomeada.");
    carregar();
  });

  dlg.querySelector("[data-fechar]").addEventListener("click", () => dlg.close());

  carregar();
})();
