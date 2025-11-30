/**
 * Mapeamentos centralizados de Praças e Subpraças
 * Fonte única de verdade para evitar duplicação
 */

// Lista de praças disponíveis
const PRACAS = [
    'Rio Barra',
    'Rio Zona Sul',
    'Rio Campo Grande & Santa Cruz',
    'Rio Madureira'
];

// Mapeamento de praças para subpraças
const SUBPRACAS_POR_PRACA = {
    'Rio Barra': ['Barra Centro', 'Recreio', 'Taquara', 'Jacarepaguá', 'Freguesia'],
    'Rio Zona Sul': ['Centro ZS', 'Ipanema', 'Copacabana', 'Botafogo', 'Vila Isabel', 'São Cristóvão'],
    'Rio Campo Grande & Santa Cruz': ['Centro CG', 'Monteiro', 'Santa Cruz'],
    'Rio Madureira': ['Penha', 'Irajá', 'Rocha Miranda', 'Realengo']
};

// Mapeamento para normalização de nomes de praças (case-insensitive)
const MAPA_PRACAS_NORMALIZACAO = {
    'rio barra': 'Rio Barra',
    'barra': 'Rio Barra',
    'rio zona sul': 'Rio Zona Sul',
    'zona sul': 'Rio Zona Sul',
    'rio campo grande': 'Rio Campo Grande & Santa Cruz',
    'rio campo grande & santa cruz': 'Rio Campo Grande & Santa Cruz',
    'campo grande': 'Rio Campo Grande & Santa Cruz',
    'rio madureira': 'Rio Madureira',
    'madureira': 'Rio Madureira'
};

/**
 * Normaliza nome de praça para formato padrão
 * @param {string} praca - Nome da praça a normalizar
 * @returns {string} Nome normalizado
 */
function normalizarPraca(praca) {
    if (!praca) return '';
    return MAPA_PRACAS_NORMALIZACAO[praca.toLowerCase().trim()] || praca;
}

/**
 * Retorna lista de subpraças para uma praça
 * @param {string} praca - Nome da praça
 * @returns {Array<string>} Lista de subpraças
 */
function getSubpracas(praca) {
    return SUBPRACAS_POR_PRACA[praca] || [];
}

/**
 * Popula select de subpraças baseado na praça selecionada
 * @param {HTMLSelectElement} selectPraca - Select de praça
 * @param {HTMLSelectElement} selectSubpraca - Select de subpraça
 * @param {string} subpracaSelecionada - Subpraça a ser selecionada (opcional)
 */
function popularSubpracas(selectPraca, selectSubpraca, subpracaSelecionada = '') {
    if (!selectPraca || !selectSubpraca) return;
    
    const pracaSelecionada = selectPraca.value;
    selectSubpraca.innerHTML = '<option value="">Selecione a sub-praça...</option>';
    
    if (pracaSelecionada && SUBPRACAS_POR_PRACA[pracaSelecionada]) {
        SUBPRACAS_POR_PRACA[pracaSelecionada].forEach(subpraca => {
            const option = document.createElement('option');
            option.value = subpraca;
            option.textContent = subpraca;
            if (subpracaSelecionada && subpraca === subpracaSelecionada) {
                option.selected = true;
            }
            selectSubpraca.appendChild(option);
        });
    }
}

/**
 * Cria options de praças para um select
 * @param {HTMLSelectElement} select - Elemento select
 * @param {string} praçaSelecionada - Praça a ser selecionada (opcional)
 */
function popularPracas(select, praçaSelecionada = '') {
    if (!select) return;
    
    select.innerHTML = '<option value="">Selecione a praça...</option>';
    PRACAS.forEach(praca => {
        const option = document.createElement('option');
        option.value = praca;
        option.textContent = praca;
        if (praçaSelecionada && praca === praçaSelecionada) {
            option.selected = true;
        }
        select.appendChild(option);
    });
}

