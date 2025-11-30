// Mapeamento de praças para subpraças
const subpracasPorPraca = {
    'Rio Barra': ['Barra Centro', 'Recreio', 'Taquara', 'Jacarepaguá', 'Freguesia'],
    'Rio Zona Sul': ['Centro ZS', 'Ipanema', 'Copacabana', 'Botafogo', 'Vila Isabel', 'São Cristóvão'],
    'Rio Campo Grande & Santa Cruz': ['Centro CG', 'Monteiro', 'Santa Cruz'],
    'Rio Madureira': ['Penha', 'Irajá', 'Rocha Miranda', 'Realengo']
};

function popularSubpracas(praca, selecionada = "") {
    const selectSubpraca = document.getElementById('editSubpraca');
    if (!selectSubpraca) return;
    
    selectSubpraca.innerHTML = '<option value="">Selecione a sub-praça...</option>';
    
    if (praca && subpracasPorPraca[praca]) {
        subpracasPorPraca[praca].forEach(sub => {
            const option = document.createElement('option');
            option.value = sub;
            option.textContent = sub;
            if (sub === selecionada) {
                option.selected = true;
            }
            selectSubpraca.appendChild(option);
        });
    }
}

// === Aside Editar ===
let selectPracaListenerAdded = false;

function abrirAsideEditar() {
    const aside = document.getElementById("asideEditar");
    aside.classList.add("ativo");
    
    // Popular subpraças baseado na praça selecionada
    const selectPraca = document.getElementById('editPraca');
    const selectSubpraca = document.getElementById('editSubpraca');
    
    if (selectPraca && selectSubpraca) {
        // Obter dados do entregador (definidos no template)
        const pracaAtual = selectPraca.value;
        const subpracaAtual = typeof entregadorData !== 'undefined' ? entregadorData.subpraca : '';
        
        // Popular subpraças quando o formulário abre
        if (pracaAtual) {
            popularSubpracas(pracaAtual, subpracaAtual);
        }
        
        // Atualizar subpraças quando a praça muda (só adicionar listener uma vez)
        if (!selectPracaListenerAdded) {
            selectPraca.addEventListener('change', function() {
                popularSubpracas(this.value);
            });
            selectPracaListenerAdded = true;
        }
    }
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
