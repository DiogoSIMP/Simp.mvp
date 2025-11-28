const subpracasPorPraca = {
  'Rio Barra': ['Barra Centro', 'Recreio', 'Taquara', 'Jacarepaguá', 'Freguesia'],
  'Rio Zona Sul': ['Centro ZS', 'Ipanema', 'Copacabana', 'Botafogo', 'Vila Isabel', 'São Cristóvão'],
  'Rio Campo Grande & Santa Cruz': ['Centro CG', 'Monteiro', 'Santa Cruz'],
  'Rio Madureira': ['Penha', 'Irajá', 'Rocha Miranda', 'Realengo']
};

function setPracaValor(praca) {
  const selectPraca = document.getElementById("editPraca");
  if (!selectPraca) return;
  const option = Array.from(selectPraca.options).find(opt => opt.value === praca);
  selectPraca.value = option ? option.value : "";
}

function popularSubpracas(praca, selecionada = "") {
  const select = document.getElementById("editSubpraca");
  if (!select) return;
  const valorAnterior = selecionada || select.value;
  select.innerHTML = '<option value="">Selecione a sub-praça...</option>';
  if (praca && subpracasPorPraca[praca]) {
    subpracasPorPraca[praca].forEach(sub => {
      const option = document.createElement("option");
      option.value = sub;
      option.textContent = sub;
      if ((valorAnterior && valorAnterior === sub) || (!valorAnterior && sub === selecionada)) {
        option.selected = true;
      }
      select.appendChild(option);
    });
  }
}

const selectPracaGlobal = document.getElementById("editPraca");
if (selectPracaGlobal) {
  selectPracaGlobal.addEventListener("change", (e) => {
    popularSubpracas(e.target.value);
  });
}

// ===== VISUALIZAR DETALHES =====
async function verDetalhes(id) {
  const aside = document.getElementById("asideDetalhes");
  const conteudo = document.getElementById("detalhesConteudo");
  const btnEditar = document.getElementById("btnEditar");

  conteudo.innerHTML = "<p>Carregando...</p>";
  aside.classList.add("ativo");

  try {
    const response = await fetch(`/entregador/${id}/detalhes-json`);
    if (!response.ok) throw new Error("Erro ao carregar entregador");

    const data = await response.json();
    if (data.error) throw new Error(data.error);

    // Garantir que os dados existam
    const nome = data.recebedor || '—';
    const email = data.email || '—';
    const cpf = data.cpf || '—';
    const cnpj = data.cnpj || '—';
    const praca = data.praca || '—';
    const subpraca = data.subpraca || '—';
    const status = data.status || '—';
    const emissor = data.emissor || '—';
    const chavePix = data.chave_pix || '—';

    conteudo.innerHTML = `
      <div class="info-item"><span class="label">Nome</span><span class="valor">${nome}</span></div>
      <div class="info-item"><span class="label">E-mail</span><span class="valor">${email}</span></div>
      <div class="info-item"><span class="label">CPF</span><span class="valor">${cpf}</span></div>
      <div class="info-item"><span class="label">CNPJ</span><span class="valor">${cnpj}</span></div>
      <div class="info-item"><span class="label">Praça</span><span class="valor">${praca}</span></div>
      <div class="info-item"><span class="label">Sub-Praça</span><span class="valor">${subpraca}</span></div>
      <div class="info-item"><span class="label">Status</span><span class="valor">${status}</span></div>
      <div class="info-item"><span class="label">Emissor</span><span class="valor">${emissor}</span></div>
      <div class="info-item"><span class="label">Pix</span><span class="valor">${chavePix}</span></div>
    `;

    // Só definir o onclick se o botão existir (não existe para Operacional)
    if (btnEditar) {
      btnEditar.onclick = () => abrirModalEditar(data);
    }

  } catch (err) {
    console.error("Erro ao carregar detalhes:", err);
    conteudo.innerHTML = "<p>❌ Erro ao carregar dados.</p>";
  }
}

// ===== FECHAR ASIDE =====
function fecharAside() {
  document.getElementById("asideDetalhes").classList.remove("ativo");
}

// ===== ABRIR MODAL DE EDIÇÃO =====
function abrirModalEditar(data) {
  const modal = document.getElementById("modalEditar");
  modal.classList.add("ativo");

  document.getElementById("editId").value = data.id_da_pessoa_entregadora;
  document.getElementById("editNome").value = data.recebedor;
  document.getElementById("editEmail").value = data.email || "";
  document.getElementById("editCpf").value = data.cpf || "";
  document.getElementById("editCnpj").value = data.cnpj || "";
  setPracaValor(data.praca || "");
  popularSubpracas(document.getElementById("editPraca").value, data.subpraca || "");
  document.getElementById("editStatus").value = data.status || "Ativo";
  document.getElementById("editTipoPix").value = data.tipo_de_chave_pix || "";
  document.getElementById("editChavePix").value = data.chave_pix || "";
}

// ===== FECHAR MODAL DE EDIÇÃO =====
function fecharModalEditar() {
  const modal = document.getElementById("modalEditar");
  modal.classList.add("fadeOut");
  setTimeout(() => {
    modal.classList.remove("ativo", "fadeOut");
  }, 250);
}

// ===== SALVAR EDIÇÃO VIA AJAX =====
document.getElementById("formEditarEntregador").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("editId").value;
  const dados = {
    recebedor: document.getElementById("editNome").value,
    email: document.getElementById("editEmail").value,
    cpf: document.getElementById("editCpf").value,
    cnpj: document.getElementById("editCnpj").value,
    praca: document.getElementById("editPraca").value,
    subpraca: document.getElementById("editSubpraca").value,
    status: document.getElementById("editStatus").value,
    tipo_de_chave_pix: document.getElementById("editTipoPix").value,
    chave_pix: document.getElementById("editChavePix").value,
    emissor: "Proprio"
  };

  try {
    const res = await fetch(`/entregador/${id}/editar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(dados)
    });

    const result = await res.json();
    if (result.success) {
      mostrarToast("✅ Alterações salvas!");
      fecharModalEditar();
      fecharAside();
      setTimeout(() => window.location.reload(), 800);
    } else {
      mostrarToast("❌ Erro ao salvar: " + (result.message || result.error || "Erro desconhecido"));
    }
  } catch (err) {
    mostrarToast("❌ Falha de conexão.");
    console.error("Erro completo:", err);
  }
});

// ===== TOAST DE NOTIFICAÇÃO =====
function mostrarToast(texto) {
  let toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = texto;
  document.body.appendChild(toast);

  setTimeout(() => toast.classList.add("show"), 100);
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 400);
  }, 1800);
}

// ===== FECHAR MODAL AO CLICAR FORA =====
window.addEventListener("mousedown", (e) => {
  const modal = document.getElementById("modalEditar");
  const content = modal.querySelector(".modal-content");

  if (modal.classList.contains("ativo") && !content.contains(e.target)) {
    fecharModalEditar();
  }
});

// ===== DECIDE ENTRE MODAL OU PÁGINA =====
function abrirDetalhes(id) {
  // se for mobile (tela menor que 768px), redireciona
  if (window.innerWidth <= 768) {
    window.location.href = `/entregador/${id}/detalhes`;
  } 
  // se for desktop, abre o painel lateral normalmente
  else {
    verDetalhes(id);
  }
}

// ===== CONFIRMAR E EXCLUIR ENTREGADOR =====
function confirmarExclusao() {
  const id = document.getElementById("editId").value;
  const nome = document.getElementById("editNome").value;
  
  if (confirm(`Tem certeza que deseja excluir o entregador "${nome}"?\n\nEsta ação não pode ser desfeita!`)) {
    fecharModalEditar();
    fecharAside();
    window.location.href = `/entregador/excluir/${id}`;
  }
}

