(() => {
  const $ = id => document.getElementById(id);
  const campo = $("campo-nome");
  const erro = campo.querySelector(".field-error");
  const dlg = $("dlg-renomear");

  let contas = [];
  let renomeando = null;

  async function carregar() {
    const r = await API.get("/contas");
    if (!r.sucesso) {
      $("lista").innerHTML = `<tr><td colspan="4" class="muted">Não foi possível carregar as contas. ${UI.esc(r.erro)}</td></tr>`;
      return;
    }
    contas = r.dados;
    $("lista").innerHTML = contas.length
      ? contas.map(c => `<tr>
          <td>${UI.esc(c.nome)}</td>
          <td class="num">${API.fmt.moeda(c.saldo_atual)}</td>
          <td class="num ${c.saldo_projetado < 0 ? "val-alert" : ""}">${API.fmt.moeda(c.saldo_projetado)}</td>
          <td><div class="row-actions"><button type="button" class="btn btn-ghost" data-renomear="${c.id}">Renomear</button></div></td>
        </tr>`).join("")
      : '<tr><td colspan="4" class="muted">Nenhuma conta ainda. Crie a primeira para registrar transações.</td></tr>';
  }

  function mostrarErro(texto) {
    campo.classList.add("has-error");
    erro.textContent = texto;
    erro.hidden = false;
    $("c-nome").focus();
  }

  $("form-conta").addEventListener("submit", async e => {
    e.preventDefault();
    campo.classList.remove("has-error");
    erro.hidden = true;

    const nome = $("c-nome").value.trim();
    if (!nome) return mostrarErro("Dê um nome para a conta.");

    $("btn-criar").disabled = true;
    const r = await API.post("/contas", { nome });
    $("btn-criar").disabled = false;
    if (!r.sucesso) return mostrarErro(r.erro);

    $("c-nome").value = "";
    UI.toast(`Conta ${r.dados.nome} criada.`);
    carregar();
  });

  $("lista").addEventListener("click", e => {
    const b = e.target.closest("[data-renomear]");
    if (!b) return;
    renomeando = contas.find(c => c.id === Number(b.dataset.renomear));
    $("ren-erro").hidden = true;
    $("r-nome").value = renomeando.nome;
    dlg.showModal();
    $("r-nome").select();
  });

  $("form-renomear").addEventListener("submit", async e => {
    e.preventDefault();
    const nome = $("r-nome").value.trim();
    if (!nome) {
      $("ren-erro").textContent = "Dê um nome para a conta.";
      $("ren-erro").hidden = false;
      return;
    }

    $("btn-renomear").disabled = true;
    const r = await API.put(`/contas/${renomeando.id}`, { nome });
    $("btn-renomear").disabled = false;
    if (!r.sucesso) {
      $("ren-erro").textContent = r.erro;
      $("ren-erro").hidden = false;
      return;
    }

    dlg.close();
    UI.toast("Conta renomeada.");
    carregar();
  });

  dlg.querySelector("[data-fechar]").addEventListener("click", () => dlg.close());

  carregar();
})();
