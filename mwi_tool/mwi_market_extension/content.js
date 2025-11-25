function findHeaderByText(text) {
    const all = Array.from(document.querySelectorAll("*"));
    return all.find(el =>
        el.childElementCount === 0 &&
        el.textContent.trim().toLowerCase() === text.toLowerCase()
    );
}

function getColumnBestPrice(headerText, type) {
    const headerEl = findHeaderByText(headerText);
    if (!headerEl) {
        console.warn("[MWI] Cabeçalho não encontrado:", headerText);
        return null;
    }

    const hRect = headerEl.getBoundingClientRect();
    const targetX = (hRect.left + hRect.right) / 2;

    const candidates = [];
    const elems = document.querySelectorAll("span, div");

    elems.forEach(el => {
        const txt = (el.textContent || "").trim();
        if (!/\d/.test(txt)) return;

        const rect = el.getBoundingClientRect();
        if (!rect || rect.width === 0 || rect.height === 0) return;

        if (rect.top <= hRect.bottom + 5) return;

        const centerX = (rect.left + rect.right) / 2;
        const distX = Math.abs(centerX - targetX);

        if (distX > 40) return;

        const numStr = txt.replace(/[^0-9]/g, "");
        if (!numStr) return;

        const val = parseInt(numStr, 10);
        if (isNaN(val)) return;

        candidates.push(val);
    });

    if (!candidates.length) {
        console.warn("[MWI]", headerText, "sem candidatos.");
        return null;
    }

    const top = candidates.slice(0, 4);

    let best;
    if (type === "ask") {
        best = Math.min(...top);
    } else {
        best = Math.max(...top);
    }

    console.log(`[MWI] ${headerText} candidatos (top 4):`, top, "=> melhor =", best);
    return best;
}

function scrapeMarket() {
    console.log("[MWI] Iniciando scrape geométrico do market...");

    const bestAsk = getColumnBestPrice("Ask Price", "ask");
    const bestBid = getColumnBestPrice("Bid Price", "bid");

    console.log("[MWI] Resultado final -> bestAsk:", bestAsk, "bestBid:", bestBid);

    if (bestAsk == null && bestBid == null) {
        return null;
    }

    return {
        best_ask: bestAsk,
        best_bid: bestBid
    };
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.action === "SCRAPE") {
        const data = scrapeMarket();
        sendResponse({ data });
    }
    return true;
});

console.log("[MWI] content.js carregado na página:", window.location.href);
