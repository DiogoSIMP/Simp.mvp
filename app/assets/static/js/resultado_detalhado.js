// ========================
// === ABRIR PAINEL =======
// ========================
function abrirPainel(id) {
    document.getElementById("asideDetalhes").classList.add("open");
    document.getElementById("detalhesConteudo").innerHTML = "Carregando...";

    fetch(`/entregador/${id}/detalhes-json`)
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                document.getElementById("detalhesConteudo").innerHTML =
                    "<p>Erro ao carregar dados.</p>";
                return;
            }

            let html = `
                <p><strong>Nome:</strong> ${data.recebedor}</p>
                <p><strong>Email:</strong> ${data.email || '-'}</p>
                <p><strong>CPF:</strong> ${data.cpf || '-'}</p>
                <p><strong>Subpraça:</strong> ${data.subpraca || '-'}</p>
                <p><strong>Status:</strong> ${data.status}</p>
                <p><strong>Chave Pix:</strong> ${data.chave_pix || '-'}</p>
            `;

            document.getElementById("detalhesConteudo").innerHTML = html;
        });
}

function fecharAside() {
    document.getElementById("asideDetalhes").classList.remove("open");
}

// ========================
// === CLIQUE NO NOME =====
// ========================
document.querySelectorAll("#tabelaResultados tbody tr .abrirDetalhes")
  .forEach(el => {
    el.addEventListener("click", function () {
        let id = this.closest("tr").dataset.id;
        abrirPainel(id);
    });
});

// ========================
// === BUSCA GLOBAL =======
// ========================
const searchInput = document.getElementById("searchInput");
const tabelaResultados = document.getElementById("tabelaResultados");
const tabelaCompleta = document.getElementById("tabelaCompleta");

// === FILTRO GLOBAL ===
if (searchInput) {
    searchInput.addEventListener("keyup", function () {
        let termo = this.value.toLowerCase().trim();

        let tabelaAtual = document.querySelector("#tabelaResultados tbody");
        let tabelaCompleta = document.querySelectorAll("#tabelaCompleta tbody tr");

        // Se o campo estiver vazio → restaura a paginação normal
        if (termo === "") {
            const pagination = document.querySelector(".pagination");
            if (pagination) {
                pagination.style.display = "flex";
            }
            window.location.reload(); // volta à página original paginada
            return;
        }

        // Oculta a paginação enquanto filtra
        const pagination = document.querySelector(".pagination");
        if (pagination) {
            pagination.style.display = "none";
        }

        // Limpa a tabela atual
        if (tabelaAtual) {
            tabelaAtual.innerHTML = "";

            // Insere apenas linhas filtradas
            tabelaCompleta.forEach(linha => {
                if (linha.innerText.toLowerCase().includes(termo)) {
                    tabelaAtual.appendChild(linha.cloneNode(true));
                }
            });
        }
    });
}

// ========================
// === MODAL DE UPLOAD ====
// ========================
function abrirModalUpload() {
    const modal = document.getElementById('modalUpload');
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function fecharModalUpload() {
    const modal = document.getElementById('modalUpload');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

// Fechar modal ao pressionar ESC
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        fecharModalUpload();
    }
});

// ========================
// === DROPDOWN EXPORTAR ===
// ========================
function initDropdownExportar() {
    const btnExportar = document.getElementById('btnExportarExcel');
    const dropdownContainer = document.getElementById('dropdownExportarContainer');
    
    if (!btnExportar || !dropdownContainer) {
        return;
    }
    
    // Event listener no botão
    btnExportar.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        dropdownContainer.classList.toggle('active');
    });
    
    // Fechar dropdown ao clicar fora
    document.addEventListener('click', function(e) {
        if (dropdownContainer && !dropdownContainer.contains(e.target)) {
            dropdownContainer.classList.remove('active');
        }
    });
    
    // Fechar dropdown ao clicar em um item
    const dropdownItems = dropdownContainer.querySelectorAll('.dropdown-item');
    dropdownItems.forEach(item => {
        item.addEventListener('click', function() {
            setTimeout(function() {
                dropdownContainer.classList.remove('active');
            }, 100);
        });
    });
}

// Inicializar quando o DOM estiver pronto
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDropdownExportar);
} else {
    // DOM já está pronto
    setTimeout(initDropdownExportar, 100);
}

// ========================
// === UPLOAD MODAL =======
// ========================
document.addEventListener('DOMContentLoaded', function() {
    function updateFileListModal() {
        const input = document.getElementById('arquivos-modal');
        const fileList = document.getElementById('file-list-modal');
    
        if (input && fileList && input.files.length > 0) {
            let html = '<strong>Arquivos selecionados:</strong><br>';
            for (let i = 0; i < input.files.length; i++) {
                html += `• ${input.files[i].name}<br>`;
            }
            fileList.innerHTML = html;
        } else if (fileList) {
            fileList.innerHTML = '';
        }
    }

    // Drag & Drop no modal
    const dropAreaModal = document.getElementById('drop-area-modal');
    if (dropAreaModal) {
        dropAreaModal.addEventListener('dragover', e => {
            e.preventDefault();
            dropAreaModal.classList.add('hover');
        });
        
        dropAreaModal.addEventListener('dragleave', () => {
            dropAreaModal.classList.remove('hover');
        });
        
        dropAreaModal.addEventListener('drop', e => {
            e.preventDefault();
            dropAreaModal.classList.remove('hover');
            const input = document.getElementById('arquivos-modal');
            if (input) {
                input.files = e.dataTransfer.files;
                updateFileListModal();
            }
        });
    }

    // Overlay de carregamento
    const formModal = document.getElementById('uploadFormModal');
    const overlay = document.getElementById('loading-overlay');
    
    if (formModal && overlay) {
        formModal.addEventListener('submit', function() {
            overlay.classList.add('active');
        });
    }
});
