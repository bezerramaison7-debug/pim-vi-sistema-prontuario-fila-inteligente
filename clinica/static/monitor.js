const chamadas = document.querySelector("#chamadas");
const total = document.querySelector("#total");
const referencia = document.querySelector("#referencia");
const atualizacao = document.querySelector("#atualizacao");
let ultima = null;

async function atualizar() {
    try {
        const resposta = await fetch("/api/fila", { cache: "no-store", signal: AbortSignal.timeout(4500) });
        if (!resposta.ok) throw new Error("Painel indisponível");
        const dados = await resposta.json();
        const estado = JSON.stringify(dados.chamadas);
        if (estado !== ultima) {
            chamadas.replaceChildren();
            for (const chamada of dados.chamadas) {
                const linha = document.createElement("div");
                linha.className = "call";
                const senha = document.createElement("strong");
                senha.textContent = chamada.senha;
                const sala = document.createElement("span");
                sala.textContent = chamada.sala;
                linha.append(senha, sala);
                chamadas.append(linha);
            }
            if (!dados.chamadas.length) chamadas.textContent = "Nenhuma senha chamada no momento.";
            ultima = estado;
        }
        total.textContent = dados.aguardando;
        referencia.textContent = dados.aguardando
            ? `Referência para escoar a fila atual: ~${dados.referencia_min} min em uma sala.` : "Fila sem espera neste momento.";
        if (atualizacao.textContent !== "Atualização automática · a cada 5 segundos") {
            atualizacao.textContent = "Atualização automática · a cada 5 segundos";
        }
    } catch {
        chamadas.textContent = "Chamadas temporariamente indisponíveis.";
        total.textContent = "—";
        referencia.textContent = "";
        atualizacao.textContent = "Tentando reconectar. Em caso de dúvida, procure a recepção.";
        ultima = null;
    } finally {
        window.setTimeout(atualizar, 5000);
    }
}

atualizar();
