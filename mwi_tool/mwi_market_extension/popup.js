document.getElementById("update").onclick = () => {
    const nameInput = document.getElementById("itemName");
    const itemName = nameInput.value.trim();

    if (!itemName) {
        document.getElementById("status").innerText = "Digite o nome do item primeiro.";
        nameInput.focus();
        return;
    }

    document.getElementById("status").innerText = "Lendo preços na aba ativa...";

    chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
        if (!tabs.length) {
            document.getElementById("status").innerText = "Nenhuma aba ativa encontrada.";
            return;
        }

        chrome.tabs.sendMessage(
            tabs[0].id,
            { action: "SCRAPE" },
            async (response) => {
                if (chrome.runtime.lastError) {
                    console.error(chrome.runtime.lastError);
                    document.getElementById("status").innerText =
                        "Não consegui falar com a página. Deixe o jogo ativo e tente de novo.";
                    return;
                }

                if (!response || !response.data) {
                    document.getElementById("status").innerText = "Nenhum dado de market encontrado.";
                    return;
                }

                const { best_ask, best_bid } = response.data;

                if (best_ask == null && best_bid == null) {
                    document.getElementById("status").innerText = "Não foi possível ler Ask/Bid.";
                    return;
                }

                const payload = {
                    [itemName]: {
                        best_ask: best_ask,
                        best_bid: best_bid
                    }
                };

                document.getElementById("status").innerText =
                    "Enviando dados ao MWI Tool...";

                try {
                    await fetch("http://127.0.0.1:5000/update_market", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(payload)
                    });
                    document.getElementById("status").innerText =
                        `Servidor respondeu OK. Item: ${itemName}, Ask=${best_ask ?? "-"}, Bid=${best_bid ?? "-"}`;
                } catch (e) {
                    console.error(e);
                    document.getElementById("status").innerText = "Erro ao enviar para o MWI Tool.";
                }
            }
        );
    });
};
