(() => {
  const $ = id => document.getElementById(id);
  const campo = $("campo-nome");
  const erro = campo.querySelector(".field-error");
  const dlg = $("dlg-renomear");

  let categorias = [];
  let renomeando = null;

  async function carregar() {
    const [rc, rt] = await Promise.all([API.get("/categorias"), API.get("/transacoes")]);
    if (!rc.sucesso) {
      $("lista").innerHTML = `<tr><td colspan="4" class="muted">Não foi possível carregar as categorias. ${UI.esc(rc.erro)}</td></tr>`;
      return;
    }
    const trans = rt.dados ?? [];
    categorias = rc.dados;
    $("lista").innerHTML = categorias.length
      ? categorias.map(c => {
          const doCat = trans.filter(t => t.categoria_id === c.id);
          const total = doCat.reduce((s, t) => s + t.valor, 0);
          return `<tr><td>${UI.esc(c.nome)}</td><td class="num">${doCat.length}</td><td class="num">${API.fmt.moeda(total)}</td>
            <td><div class="row-actions"><button type="button" class="btn btn-ghost" data-renomear="${c.id}">Renomear</button></div></td></tr>`;
        }).join("")
      : '<tr><td colspan="4" class="muted">Nenhuma categoria ainda. Crie a primeira para o agente conseguir categorizar.</td></tr>';
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

  $("lista").addEventListener("click", e => {
    const b = e.target.closest("[data-renomear]");
    if (!b) return;
    renomeando = categorias.find(c => c.id === Number(b.dataset.renomear));
    $("ren-erro").hidden = true;
    $("r-nome").value = renomeando.nome;
    dlg.showModal();
    $("r-nome").select();
  });

  $("form-renomear").addEventListener("submit", async e => {
    e.preventDefault();
    const nome = $("r-nome").value.trim();
    const falhar = texto => {
      $("ren-erro").textContent = texto;
      $("ren-erro").hidden = false;
    };
    if (!nome) return falhar("Dê um nome para a categoria.");

    $("btn-renomear").disabled = true;
    const r = await API.put(`/categorias/${renomeando.id}`, { nome });
    $("btn-renomear").disabled = false;
    if (!r.sucesso) return falhar(r.status === 409 ? `Já existe uma categoria chamada "${nome}".` : r.erro);

    dlg.close();
    UI.toast("Categoria renomeada.");
    carregar();
  });

  dlg.querySelector("[data-fechar]").addEventListener("click", () => dlg.close());

  carregar();
})();
