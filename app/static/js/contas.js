(() => {
  const $ = id => document.getElementById(id);
  const campo = $("campo-nome");
  const erro = campo.querySelector(".field-error");
  const dlg = $("dlg-renomear");

  let contas = [];
  let renomeando = null;

  async function carregar() {
    // esqueleto só quando não há nada na tela; numa atualização a lista antiga fica até a nova chegar
    if (!contas.length) $("lista").innerHTML = UI.esqueleto(4);
    const r = await API.get("/contas");
    if (!r.sucesso) {
      if (contas.length) return UI.toast(`Não foi possível atualizar a lista. ${r.erro}`, "erro");
      $("lista").innerHTML = UI.falhaDeCarga(4, "Não foi possível carregar as contas.", r);
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

  $("form-conta").addEventListener("submit", async e => {
    e.preventDefault();
    limparErro();

    const nome = $("c-nome").value.trim();
    if (!nome) return mostrarErro("Dê um nome para a conta.");

    $("btn-criar").disabled = true;
    const r = await API.post("/contas", { nome });
    $("btn-criar").disabled = false;
    if (!r.sucesso) return UI.falha(r, mostrarErro);

    $("c-nome").value = "";
    UI.toast(`Conta ${r.dados.nome} criada.`);
    carregar();
  });

  $("lista").addEventListener("click", e => {
    if (e.target.closest("[data-tentar]")) return carregar();
    const b = e.target.closest("[data-renomear]");
    if (!b) return;
    renomeando = contas.find(c => c.id === Number(b.dataset.renomear));
    $("ren-erro").hidden = true;
    $("r-nome").removeAttribute("aria-invalid");
    $("r-nome").value = renomeando.nome;
    dlg.showModal();
    $("r-nome").select();
  });

  $("form-renomear").addEventListener("submit", async e => {
    e.preventDefault();
    const nome = $("r-nome").value.trim();
    if (!nome) return erroNoDialogo("Dê um nome para a conta.");

    $("btn-renomear").disabled = true;
    const r = await API.put(`/contas/${renomeando.id}`, { nome });
    $("btn-renomear").disabled = false;
    if (!r.sucesso) {
      // outra aba ou outra pessoa já apagou: não há o que renomear, então fecha e atualiza
      if (r.status === 404) {
        dlg.close();
        UI.toast(r.erro, "erro");
        return carregar();
      }
      // toast ficaria atrás do diálogo modal, por isso o erro fica dentro dele
      return erroNoDialogo(r.erro);
    }

    dlg.close();
    UI.toast("Conta renomeada.");
    carregar();
  });

  dlg.querySelector("[data-fechar]").addEventListener("click", () => dlg.close());

  carregar();
})();
