import { getCurrentLang } from './i18n.js';

/**
 * Escapes a value for safe insertion into HTML content.
 * Prevents XSS when rendering API-sourced strings like player/champion names.
 *
 * @param {*} str - Value to escape (coerced to string).
 * @returns {string} HTML-safe string.
 */
function escapeHtml(str) {
    return String(str ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

/**
 * Renders the match history list into the #match-history-list container.
 *
 * Each match row shows: champion portrait, game mode, result label,
 * KDA block (with colour-coded ratio), stat summary and match metadata.
 *
 * KDA colour thresholds:
 *   ≥ 5.0 → legendary (gold)
 *   ≥ 3.0 → good      (green)
 *   < 1.0 → bad       (red)
 *   else  → neutral   (no class)
 *
 * @param {Array<object>} history - Array of match summary objects from the API.
 */
export function buildMatchHistory(history) {
    const container = document.getElementById("match-history-list");
    if (!container || !history || !history.length) return;

    const isPT = getCurrentLang() === "pt";

    container.innerHTML = history.map(m => {
        // CSS class and localised label vary by match outcome
        const resultClass = m.win ? "match-win" : "match-loss";
        const resultLabel = m.win
            ? (isPT ? "Vitória" : "Victory")
            : (isPT ? "Derrota" : "Defeat");

        // KDA ratio drives the colour class on the KDA display
        const kdaClass = m.kda >= 5 ? "kda-legendary"
                       : m.kda >= 3 ? "kda-good"
                       : m.kda < 1  ? "kda-bad"
                       : "";

        // Use locale-aware number formatting for gold and damage
        const lang      = getCurrentLang();
        const locale    = lang === "pt" ? "pt-BR" : "en-US";
        const goldFmt   = Number(m.gold).toLocaleString(locale);
        const damageFmt = Number(m.damage).toLocaleString(locale);

        return `
        <div class="match-row ${resultClass}">
            <img class="match-champ-img" src="${escapeHtml(m.champion_img)}" alt="${escapeHtml(m.champion)}"
                 onerror="this.src='https://ddragon.leagueoflegends.com/cdn/img/champion/tiles/Lux_0.jpg'">
            <div class="match-info">
                <span class="match-champ-name">${escapeHtml(m.champion)}</span>
                <span class="match-mode">${escapeHtml(m.gameMode)}</span>
            </div>
            <div class="match-result-label ${resultClass}">${resultLabel}</div>
            <div class="match-kda-block">
                <span class="match-kda ${kdaClass}">${escapeHtml(m.kills)} / <span class="match-deaths">${escapeHtml(m.deaths)}</span> / ${escapeHtml(m.assists)}</span>
                <span class="match-kda-ratio">${escapeHtml(m.kda)} KDA</span>
            </div>
            <div class="match-stats">
                <span><i class="fas fa-coins"></i> ${goldFmt}</span>
                <span><i class="fas fa-fire"></i> ${damageFmt}</span>
                <span><i class="fas fa-leaf"></i> ${escapeHtml(m.cs)} CS</span>
            </div>
            <div class="match-meta">
                <span class="match-duration"><i class="fas fa-clock"></i> ${escapeHtml(m.duration)}</span>
                <span class="match-date">${escapeHtml(m.date)}</span>
            </div>
        </div>`;
    }).join("");
}