// === Aside Editar ===
function abrirAsideEditar() {
  document.getElementById("asideEditar").classList.add("ativo");
}
function fecharAsideEditar() {
  document.getElementById("asideEditar").classList.remove("ativo");
}

// === Modal Excluir ===
function abrirModalExcluir() {
  document.getElementById("modalExcluir").style.display = "flex";
}
function fecharModalExcluir() {
  document.getElementById("modalExcluir").style.display = "none";
}

// Fecha modal clicando fora
window.onclick = function(event) {
  const modal = document.getElementById("modalExcluir");
  if (event.target === modal) modal.style.display = "none";
};
