import { getCurrentLang } from './i18n.js';

// ── DOM utilities ─────────────────────────────────────────────────

/**
 * Sets the inner text of an element by ID.
 * Falls back to "--" if the value is null or undefined.
 *
 * @param {string} id    - Target element ID.
 * @param {*}      value - Value to display.
 */
export function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.innerText = value ?? "--";
}

/**
 * Formats a number using the active locale's number formatting rules.
 * Produces "1.234,56" in PT-BR and "1,234.56" in EN-US.
 *
 * @param {number} n - Number to format.
 * @returns {string} Localised number string.
 */
export function fmt(n) {
    const locale = getCurrentLang() === "pt" ? "pt-BR" : "en-US";
    return (n ?? 0).toLocaleString(locale);
}

// ── Global tooltip ────────────────────────────────────────────────

/**
 * Initialises a single floating tooltip element appended to <body>.
 *
 * This avoids overflow clipping from card containers. The tooltip follows
 * the cursor and reads its text from the hovered element's data-tooltip attribute.
 * It automatically repositions when it would overflow the viewport edge.
 */
export function initTooltip() {
    const tip = document.createElement("div");
    tip.id = "classic-tooltip";
    document.body.appendChild(tip);

    document.addEventListener("mouseover", e => {
        const icon = e.target.closest(".classic-info-icon");
        if (!icon) return;
        tip.textContent = icon.dataset.tooltip || "";
        tip.classList.add("visible");
    });

    document.addEventListener("mousemove", e => {
        if (!tip.classList.contains("visible")) return;
        const GAP = 12;
        const W   = tip.offsetWidth;
        const H   = tip.offsetHeight;
        let x = e.clientX + GAP;
        let y = e.clientY - H - GAP;
        // Prevent the tooltip from overflowing the right or bottom of the viewport
        x = Math.min(x, window.innerWidth  - W - 8);
        x = Math.max(x, 8);
        y = Math.min(y, window.innerHeight - H - 8);
        // If it would appear above the viewport, flip it below the cursor
        if (y < 8) y = e.clientY + GAP;
        tip.style.left = x + "px";
        tip.style.top  = y + "px";
    });

    document.addEventListener("mouseout", e => {
        if (e.target.closest(".classic-info-icon")) tip.classList.remove("visible");
    });
}

// ── Insight badges ────────────────────────────────────────────────

// Reference values used to classify performance as above/below average
const BENCHMARKS = { winrate: 50, kda: 2.5 };

// Localised strings for the three insight badge states
const INSIGHT_STRINGS = {
    pt: {
        aboveAvg: (label, pct) => `${label} ${pct}% acima da média`,
        belowAvg: (label, pct) => `${label} ${pct}% abaixo da média`,
        onAvg:    (label)      => `${label} na média`,
        played:   "jogados",
        winrate:  "Winrate",
        kda:      "KDA",
    },
    en: {
        aboveAvg: (label, pct) => `${label} ${pct}% above average`,
        belowAvg: (label, pct) => `${label} ${pct}% below average`,
        onAvg:    (label)      => `${label} at average`,
        played:   "played",
        winrate:  "Win Rate",
        kda:      "KDA",
    },
};

/**
 * Builds the HTML for a single insight badge comparing a metric to its benchmark.
 *
 * A ±5% relative dead zone around the benchmark is treated as "on average"
 * to avoid showing misleading directional arrows for negligible differences.
 *
 * @param {"winrate" | "kda"} labelKey - Which metric to evaluate.
 * @param {number} value               - The player's actual metric value.
 * @param {number} bench               - The benchmark value to compare against.
 * @returns {string} HTML string for the badge element.
 */
function insightBadge(labelKey, value, bench) {
    const lang  = getCurrentLang();
    const s     = INSIGHT_STRINGS[lang] || INSIGHT_STRINGS.pt;
    const label = labelKey === "winrate" ? s.winrate : s.kda;
    const diff  = value - bench;
    // "On average" zone: within ±5% of the benchmark
    const zone  = Math.abs(diff) < bench * 0.05;

    let cls, icon, text;
    if (zone) {
        cls = "neutral"; icon = "fa-minus";
        text = s.onAvg(label);
    } else if (diff > 0) {
        cls = "positive"; icon = "fa-arrow-up";
        text = s.aboveAvg(label, Math.abs(Math.round((diff / bench) * 100)));
    } else {
        cls = "negative"; icon = "fa-arrow-down";
        text = s.belowAvg(label, Math.abs(Math.round((diff / bench) * 100)));
    }
    return `<span class="hero-badge-insight ${cls}"><i class="fas ${icon}"></i>${text}</span>`;
}

/**
 * Builds the full insights bar HTML: win rate badge, KDA badge and total time played.
 *
 * @param {object} stats - Stats object from the analysis result (general or champion).
 * @returns {string} HTML string for the insights container.
 */
export function buildInsights(stats) {
    const lang  = getCurrentLang();
    const s     = INSIGHT_STRINGS[lang] || INSIGHT_STRINGS.pt;
    const tempo = stats.sizePlayed.total_time_played || "--";
    return `<div class="hero-insights">
        ${insightBadge("winrate", stats.matchResult.win_rate, BENCHMARKS.winrate)}
        ${insightBadge("kda",     stats.kda.kda_ratio,        BENCHMARKS.kda)}
        <span class="hero-badge-insight neutral"><i class="fas fa-clock"></i>${tempo} ${s.played}</span>
    </div>`;
}

// ── Section binder ────────────────────────────────────────────────

/**
 * Populates a dashboard section (general or champion-specific) with stat values.
 *
 * The prefix parameter allows the same binding logic to serve both the
 * general stats section (prefix = "") and the champion stats section
 * (prefix = "champ-"), since both share identical element ID patterns.
 *
 * General-only elements (objectives, individual ping breakdowns) are only
 * written when prefix is "".
 *
 * @param {string} prefix - Element ID prefix ("" or "champ-").
 * @param {object} stats  - Stats object from the analysis result.
 * @param {object} data   - Full analysis result payload (for player/champion metadata).
 */
export function bindSection(prefix, stats, data) {
    if (!stats) return;
    const p = prefix;

    // Player hero header (general section)
    if (p === "") {
        setText("player-hero-name", `${data.player_info.name}#${data.player_info.tag}`);
        const img = document.getElementById("player-icon-img");
        if (img && data.player_icon_img) { img.src = data.player_icon_img; img.alt = data.player_info.name; }
    } else {
        // Champion portrait (champion section)
        setText("champion-name", stats.champion || "--");
        const img = document.getElementById("champion-img");
        if (img && data.champion_img) { img.src = data.champion_img; img.alt = stats.champion; }
    }

    // Insight badges (win rate, KDA, time played)
    const insightsEl = document.getElementById(p === "" ? "player-insights" : "champ-insights");
    if (insightsEl) insightsEl.innerHTML = buildInsights(stats);

    // Core stats shared by both sections
    setText(`${p}winrate`,           `${stats.matchResult.win_rate}%`);
    setText(`${p}win-loss`,          `${stats.matchResult.total_win} / ${stats.matchResult.total_loss}`);
    setText(`${p}kda`,               stats.kda.kda_ratio.toFixed(1));
    setText(`${p}kda-detail`,        `${stats.kda.avg_kills.toFixed(1)} / ${stats.kda.avg_deaths.toFixed(1)} / ${stats.kda.avg_assists.toFixed(1)}`);
    setText(`${p}total-games`,       stats.sizePlayed.total_matchs);
    setText(`${p}total-time-played`, stats.sizePlayed.total_time_played);
    setText(`${p}avg-gold`,          fmt(stats.economy.avg_gold));
    setText(`${p}total-gold`,        fmt(stats.economy.total_gold));
    setText(`${p}avg-damage`,        fmt(stats.damage.avg));
    setText(`${p}total-damage`,      fmt(stats.damage.total));
    setText(`${p}avg-farm`,          stats.farm.avg);
    setText(`${p}total-farm`,        fmt(stats.farm.total));
    setText(`${p}avg-vision`,        stats.vision.avg);
    setText(`${p}total-vision`,      fmt(stats.vision.total));

    // Ping summary (present in both sections)
    const pg = stats.pings;
    if (pg) {
        setText(`${p}total-pings`,        fmt(pg.total));
        setText(`${p}avg-pings-per-game`, pg.avg_per_game);
    }

    // Raw KDA totals
    setText(`${p}total-kills`,   fmt(stats.kda.total_kills));
    setText(`${p}total-deaths`,  fmt(stats.kda.total_deaths));
    setText(`${p}total-assists`, fmt(stats.kda.total_assists));

    // Multi-kill counts
    setText(`${p}double-kills`, fmt(stats.multikills.double));
    setText(`${p}triple-kills`, fmt(stats.multikills.triple));
    setText(`${p}quadra-kills`, fmt(stats.multikills.quadra));
    setText(`${p}penta-kills`,  fmt(stats.multikills.penta));

    // Individual ping type breakdown (general section only)
    if (p === "" && pg) {
        setText("ping-all-in",         fmt(pg.all_in));
        setText("ping-enemy-missing",  fmt(pg.enemy_missing));
        setText("ping-danger",         fmt(pg.danger));
        setText("ping-get-back",       fmt(pg.get_back));
        setText("ping-enemy-vision",   fmt(pg.enemy_vision));
        setText("ping-vision-cleared", fmt(pg.vision_cleared));
        setText("ping-command",        fmt(pg.command));
        setText("ping-on-my-way",      fmt(pg.on_my_way));
        setText("ping-assist-me",      fmt(pg.assist_me));
        setText("ping-push",           fmt(pg.push));
        setText("ping-need-vision",    fmt(pg.need_vision));
        setText("ping-hold",           fmt(pg.hold));
    }

    // Objective stats (general section only — not tracked per champion)
    if (p === "") {
        const obj = stats.objectives;
        if (obj) {
            setText("total-towers",       fmt(obj.total_towers));
            setText("avg-towers",         obj.avg_towers);
            setText("total-inhibitors",   fmt(obj.total_inhibitor_kills));
            setText("avg-inhibitors",     obj.avg_inhibitor_kills);
            setText("total-barons",       fmt(obj.total_barons));
            setText("avg-barons",         obj.avg_barons);
            setText("total-rift-heralds", fmt(obj.total_rift_heralds));
            setText("avg-rift-heralds",   obj.avg_rift_heralds);
            setText("total-horde",        fmt(obj.total_horde_heralds));
            setText("avg-horde",          obj.avg_horde_heralds);
            setText("total-dragons",      fmt(obj.total_dragons));
            setText("avg-dragons",        obj.avg_dragons);
        }
    }
}