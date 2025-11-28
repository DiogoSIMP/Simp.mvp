document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("chave_pix");
    const tipoInput = document.getElementById("tipo_chave");
    const labelTipo = document.getElementById("tipo_detectado");

    input.addEventListener("input", () => {
        const chave = input.value.trim();

        let tipo = detectarTipo(chave);

        tipoInput.value = tipo;

        if (tipo) {
            labelTipo.innerHTML = "Tipo detectado: <strong>" + tipo + "</strong>";
            labelTipo.style.color = "#2563eb";
        } else {
            labelTipo.innerHTML = "Tipo não reconhecido";
            labelTipo.style.color = "#b91c1c";
        }
    });
});


function detectarTipo(chave) {
    const limpa = chave.replace(/\D/g, "");

    // CNPJ: 14 dígitos
    if (limpa.length === 14) return "CNPJ";

    // CPF: 11 dígitos
    if (limpa.length === 11) return "CPF";

    // Telefone (padrão nacional)
    if (limpa.length >= 10 && limpa.length <= 13) return "TELEFONE";

    // E-mail
    if (chave.includes("@") && chave.includes(".")) return "EMAIL";

    // Aleatória (UUID-like)
    if (chave.length >= 25) return "ALEATORIA";

    return "";
}
