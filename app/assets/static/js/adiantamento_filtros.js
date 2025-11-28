const searchInput = document.getElementById("searchInput");
const filtroDia = document.getElementById("filtroDia");
const filtroMes = document.getElementById("filtroMes");
const filtroStatusCPF = document.getElementById("filtroStatusCPF");
const filtroPraca = document.getElementById("filtroPraca");
const tabela = document.getElementById("tabelaSolicitacoes");

function aplicarFiltros() {
  const termo = searchInput.value.toLowerCase();
  const dia = filtroDia.value;
  const mes = filtroMes.value;
  const statusCPF = filtroStatusCPF.value;
  const praca = filtroPraca.value.toLowerCase();

  tabela.querySelectorAll("tbody tr").forEach(row => {
    const matchTermo =
      row.dataset.nome.includes(termo) ||
      row.dataset.cpf.includes(termo) ||
      row.dataset.praca.includes(termo);

    const matchDia = dia === "" || row.dataset.dia === dia;
    const matchMes = mes === "" || row.dataset.mes === mes;
    const matchPraca = praca === "" || row.dataset.praca === praca;
    const matchStatus = statusCPF === "" || row.dataset.cpfstatus === statusCPF;

    row.style.display = (matchTermo && matchDia && matchMes && matchPraca && matchStatus)
      ? ""
      : "none";
  });
}

searchInput.oninput = aplicarFiltros;
filtroDia.onchange = aplicarFiltros;
filtroMes.onchange = aplicarFiltros;
filtroPraca.onchange = aplicarFiltros;
filtroStatusCPF.onchange = aplicarFiltros;

function filtrarPorDia(dia) {
  filtroDia.value = dia;
  aplicarFiltros();
}
