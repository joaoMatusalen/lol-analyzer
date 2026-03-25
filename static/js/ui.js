import { getCurrentLang } from './i18n.js';

// ── Utilitários DOM ───────────────────────────────────────────────

export function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.innerText = value ?? "--";
}

export function fmt(n) {
    const locale = getCurrentLang() === "pt" ? "pt-BR" : "en-US";
    return (n ?? 0).toLocaleString(locale);
}

// ── Tooltip global (evita overflow:hidden dos cards) ──────────────

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
        x = Math.min(x, window.innerWidth  - W - 8);
        x = Math.max(x, 8);
        y = Math.min(y, window.innerHeight - H - 8);
        if (y < 8) y = e.clientY + GAP;
        tip.style.left = x + "px";
        tip.style.top  = y + "px";
    });

    document.addEventListener("mouseout", e => {
        if (e.target.closest(".classic-info-icon")) tip.classList.remove("visible");
    });
}

// ── Insight badges ────────────────────────────────────────────────

const BENCHMARKS = { winrate: 50, kda: 2.5 };

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

function insightBadge(labelKey, value, bench) {
    const lang  = getCurrentLang();
    const s     = INSIGHT_STRINGS[lang] || INSIGHT_STRINGS.pt;
    const label = labelKey === "winrate" ? s.winrate : s.kda;
    const diff  = value - bench;
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

// ── Bind section (geral e por campeão) ────────────────────────────

export function bindSection(prefix, stats, data) {
    if (!stats) return;
    const p = prefix;

    if (p === "") {
        setText("player-hero-name", `${data.player_info.name}#${data.player_info.tag}`);
        const img = document.getElementById("player-icon-img");
        if (img && data.player_icon_img) { img.src = data.player_icon_img; img.alt = data.player_info.name; }
    } else {
        setText("champion-name", stats.champion || "--");
        const img = document.getElementById("champion-img");
        if (img && data.champion_img) { img.src = data.champion_img; img.alt = stats.champion; }
    }

    const insightsEl = document.getElementById(p === "" ? "player-insights" : "champ-insights");
    if (insightsEl) insightsEl.innerHTML = buildInsights(stats);

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

    const pg = stats.pings;
    if (pg) {
        setText(`${p}total-pings`,        fmt(pg.total));
        setText(`${p}avg-pings-per-game`, pg.avg_per_game);
    }

    setText(`${p}total-kills`,   fmt(stats.kda.total_kills));
    setText(`${p}total-deaths`,  fmt(stats.kda.total_deaths));
    setText(`${p}total-assists`, fmt(stats.kda.total_assists));

    setText(`${p}double-kills`, fmt(stats.multikills.double));
    setText(`${p}triple-kills`, fmt(stats.multikills.triple));
    setText(`${p}quadra-kills`, fmt(stats.multikills.quadra));
    setText(`${p}penta-kills`,  fmt(stats.multikills.penta));

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