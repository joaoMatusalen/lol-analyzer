import { getCurrentLang } from './i18n.js';

export function buildMatchHistory(history) {
    const container = document.getElementById("match-history-list");
    if (!container || !history || !history.length) return;

    const isPT = getCurrentLang() === "pt";

    container.innerHTML = history.map(m => {
        const resultClass = m.win ? "match-win" : "match-loss";
        const resultLabel = m.win
            ? (isPT ? "Vitória" : "Victory")
            : (isPT ? "Derrota" : "Defeat");
        const kdaClass = m.kda >= 5 ? "kda-legendary"
                       : m.kda >= 3 ? "kda-good"
                       : m.kda < 1  ? "kda-bad"
                       : "";

        return `
        <div class="match-row ${resultClass}">
            <img class="match-champ-img" src="${m.champion_img}" alt="${m.champion}"
                 onerror="this.src='https://ddragon.leagueoflegends.com/cdn/img/champion/tiles/Lux_0.jpg'">
            <div class="match-info">
                <span class="match-champ-name">${m.champion}</span>
                <span class="match-mode">${m.gameMode}</span>
            </div>
            <div class="match-result-label ${resultClass}">${resultLabel}</div>
            <div class="match-kda-block">
                <span class="match-kda ${kdaClass}">${m.kills} / <span class="match-deaths">${m.deaths}</span> / ${m.assists}</span>
                <span class="match-kda-ratio">${m.kda} KDA</span>
            </div>
            <div class="match-stats">
                <span><i class="fas fa-coins"></i> ${m.gold.toLocaleString("pt-BR")}</span>
                <span><i class="fas fa-fire"></i> ${m.damage.toLocaleString("pt-BR")}</span>
                <span><i class="fas fa-leaf"></i> ${m.cs} CS</span>
            </div>
            <div class="match-meta">
                <span class="match-duration"><i class="fas fa-clock"></i> ${m.duration}</span>
                <span class="match-date">${m.date}</span>
            </div>
        </div>`;
    }).join("");
}