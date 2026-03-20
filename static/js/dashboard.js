// ================================================================
//  UTILS
// ================================================================

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.innerText = value ?? "--";
}

function fmt(n) {
    return (n ?? 0).toLocaleString("pt-BR");
}

// ================================================================
//  CHART CONSTANTS
// ================================================================

const GOLD_COLOR   = "rgba(201, 170, 113, 1)";
const GOLD_FILL    = "rgba(201, 170, 113, 0.15)";
const BLUE_COLOR   = "rgba(100, 180, 255, 1)";
const BLUE_FILL    = "rgba(100, 180, 255, 0.12)";
const RED_COLOR    = "rgba(255, 99, 99, 1)";
const RED_FILL     = "rgba(255, 99, 99, 0.12)";
const GREEN_COLOR  = "rgba(80, 220, 140, 1)";
const GREEN_FILL   = "rgba(80, 220, 140, 0.12)";
const PURPLE_COLOR = "rgba(180, 130, 255, 1)";
const PURPLE_FILL  = "rgba(180, 130, 255, 0.12)";

const BASE_FONT    = { family: "Inter, sans-serif", size: 12 };
const GRID_COLOR   = "rgba(255, 255, 255, 0.06)";
const TICK_COLOR   = "rgba(255, 255, 255, 0.4)";

const DEFAULT_TOOLTIP = {
    backgroundColor: "rgba(10, 22, 40, 0.95)",
    titleColor:      GOLD_COLOR,
    bodyColor:       "rgba(255,255,255,0.8)",
    borderColor:     "rgba(201,170,113,0.3)",
    borderWidth:     1,
    padding:         10,
};

// ================================================================
//  TOOLTIP GLOBAL (evita overflow:hidden dos cards)
// ================================================================

function initTooltip() {
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

// ================================================================
//  INSIGHT BADGES
// ================================================================

// Benchmarks de referência (médias aproximadas elo médio)
const BENCHMARKS = { winrate: 50, kda: 2.5 };

// Strings traduzíveis dos insights
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
    const lang = (typeof getCurrentLang === "function") ? getCurrentLang() : "pt";
    const s    = INSIGHT_STRINGS[lang] || INSIGHT_STRINGS.pt;
    const label = labelKey === "winrate" ? s.winrate : s.kda;
    const diff = value - bench;
    const zone = Math.abs(diff) < bench * 0.05;
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

function buildInsights(stats) {
    const lang  = (typeof getCurrentLang === "function") ? getCurrentLang() : "pt";
    const s     = INSIGHT_STRINGS[lang] || INSIGHT_STRINGS.pt;
    const tempo = stats.sizePlayed.total_time_played || "--";
    return `<div class="hero-insights">
        ${insightBadge("winrate", stats.matchResult.win_rate, BENCHMARKS.winrate)}
        ${insightBadge("kda",     stats.kda.kda_ratio,        BENCHMARKS.kda)}
        <span class="hero-badge-insight neutral"><i class="fas fa-clock"></i>${tempo} ${s.played}</span>
    </div>`;
}

// ================================================================
//  INIT
// ================================================================

document.addEventListener("DOMContentLoaded", () => {

    initTooltip();

    document.getElementById("logo").addEventListener("click", e => {
        e.stopPropagation();
        window.location.href = "/";
    });

    // Limpa inputs do header search (browser pode restaurar após reload)
    const nameInput = document.getElementById("header-playerName");
    const tagInput  = document.getElementById("header-playerTag");
    if (nameInput) nameInput.value = "";
    if (tagInput)  tagInput.value  = "";

    let data;
    try {
        data = JSON.parse(localStorage.getItem("analysisData"));
    } catch {
        console.warn("Dados corrompidos no localStorage. Redirecionando...");
        window.location.href = "/";
        return;
    }
    if (!data) {
        console.warn("Nenhum dado encontrado. Redirecionando...");
        window.location.href = "/";
        return;
    }

    // Header search form
    const headerForm = document.getElementById("headerSearchForm");
    if (headerForm) {
        headerForm.addEventListener("submit", async e => {
            e.preventDefault();
            const name   = document.getElementById("header-playerName").value.trim();
            const tag    = document.getElementById("header-playerTag").value.trim();
            const region = document.getElementById("header-region").value;
            if (!name || !tag || !region) return;

            const btn = headerForm.querySelector(".header-search-btn");
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

            try {
                const resp   = await fetch("/analyze", {
                    method:  "POST",
                    headers: { "Content-Type": "application/json" },
                    body:    JSON.stringify({ playerName: name, playerTag: tag, region }),
                });
                const result = await resp.json();
                if (result.error) {
                    alert(`Erro: ${result.error}`);
                } else {
                    localStorage.setItem("analysisData", JSON.stringify(result));
                    window.location.reload();
                }
            } catch {
                alert("Erro ao conectar com o servidor.");
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-search"></i>';
            }
        });
    }

    // Botão de forçar atualização com cooldown de 2 minutos (persiste no reload)
    const forceBtn   = document.getElementById("forceRefreshBtn");
    const timerLabel = document.getElementById("updateTimer");
    const COOLDOWN_KEY = "lolanalyzer_update_cooldown";
    const COOLDOWN_MS  = 2 * 60 * 1000;

    if (forceBtn && data.player_info) {

        let countdownInterval = null;

        function startCooldown(startedAt) {
            localStorage.setItem(COOLDOWN_KEY, startedAt);
            forceBtn.disabled = true;
            timerLabel.style.display = "inline";

            countdownInterval = setInterval(() => {
                const elapsed   = Date.now() - startedAt;
                const remaining = Math.max(0, Math.ceil((COOLDOWN_MS - elapsed) / 1000));
                const m = Math.floor(remaining / 60);
                const s = String(remaining % 60).padStart(2, "0");
                timerLabel.textContent = `${m}:${s}`;

                if (remaining <= 0) {
                    clearInterval(countdownInterval);
                    localStorage.removeItem(COOLDOWN_KEY);
                    forceBtn.disabled = false;
                    timerLabel.style.display = "none";
                    forceBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Update';
                }
            }, 1000);
        }

        // Retoma cooldown se ainda ativo após reload
        const savedAt = parseInt(localStorage.getItem(COOLDOWN_KEY), 10);
        if (savedAt && Date.now() - savedAt < COOLDOWN_MS) {
            startCooldown(savedAt);
        }

        forceBtn.addEventListener("click", async () => {
            if (forceBtn.disabled) return;

            forceBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Update';
            startCooldown(Date.now());

            let pollInterval = null;

            try {
                const resp = await fetch("/analyze", {
                    method:  "POST",
                    headers: { "Content-Type": "application/json" },
                    body:    JSON.stringify({
                        playerName: data.player_info.name,
                        playerTag:  data.player_info.tag,
                        region:     data.player_info.region,
                        force:      true,
                    }),
                });
                const init = await resp.json();

                if (init.error) {
                    alert(`Erro: ${init.error}`);
                    forceBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Update';
                    return;
                }

                pollInterval = setInterval(async () => {
                    try {
                        const sr  = await fetch(`/status/${init.job_id}`);
                        const job = await sr.json();

                        if (job.status === "done") {
                            clearInterval(pollInterval);
                            // Garante que os dados estão gravados ANTES de recarregar
                            localStorage.setItem("analysisData", JSON.stringify(job.result));
                            // Pequeno tick para garantir que o setItem foi concluído
                            setTimeout(() => window.location.reload(), 50);
                        } else if (job.status === "error") {
                            clearInterval(pollInterval);
                            alert(`Erro: ${job.error}`);
                            forceBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Update';
                        }
                    } catch {
                        clearInterval(pollInterval);
                        alert("Erro ao verificar status da atualização.");
                        forceBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Update';
                    }
                }, 1500);

            } catch {
                if (pollInterval) clearInterval(pollInterval);
                alert("Erro ao conectar com o servidor.");
                forceBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Update';
            }
        });
    }

    // Banner de cache info - removido

    bindSection("", data.geral_matchs, data);
    bindSection("champ-", data.champion_results, data);

    if (data.charts)        buildCharts(data.charts);
    if (data.match_history) buildMatchHistory(data.match_history);
});

// ================================================================
//  BIND SECTION — Unifica geral e campeão (prefixo "" ou "champ-")
// ================================================================

function bindSection(prefix, stats, data) {
    if (!stats) return;
    const p = prefix;

    // Hero card
    if (p === "") {
        setText("player-hero-name", `${data.player_info.name}#${data.player_info.tag}`);
        const img = document.getElementById("player-icon-img");
        if (img && data.player_icon_img) { img.src = data.player_icon_img; img.alt = data.player_info.name; }
    } else {
        setText("champion-name", stats.champion || "--");
        const img = document.getElementById("champion-img");
        if (img && data.champion_img) { img.src = data.champion_img; img.alt = stats.champion; }
    }

    // Insights
    const insightsEl = document.getElementById(p === "" ? "player-insights" : "champ-insights");
    if (insightsEl) insightsEl.innerHTML = buildInsights(stats);

    // KPI cards
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

    // Pings — card simples
    const pg = stats.pings;
    if (pg) {
        setText(`${p}total-pings`,        fmt(pg.total));
        setText(`${p}avg-pings-per-game`, pg.avg_per_game);
    }

    // KDA detalhado
    setText(`${p}total-kills`,   fmt(stats.kda.total_kills));
    setText(`${p}total-deaths`,  fmt(stats.kda.total_deaths));
    setText(`${p}total-assists`, fmt(stats.kda.total_assists));

    // Multikills
    setText(`${p}double-kills`, fmt(stats.multikills.double));
    setText(`${p}triple-kills`, fmt(stats.multikills.triple));
    setText(`${p}quadra-kills`, fmt(stats.multikills.quadra));
    setText(`${p}penta-kills`,  fmt(stats.multikills.penta));

    // Pings detalhados — somente na seção geral (Seção 1)
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

    // Objetivos — somente na seção geral (Seção 1)
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

// ================================================================
//  CHART HELPERS
// ================================================================

function toFloat(arr) {
    return (arr || []).map(v => parseFloat(v) || 0);
}

function defaultScales(yLabel = "") {
    return {
        x: {
            ticks:  { color: TICK_COLOR, font: BASE_FONT, maxRotation: 45 },
            grid:   { color: GRID_COLOR },
            border: { color: "transparent" },
        },
        y: {
            ticks:  { color: TICK_COLOR, font: BASE_FONT },
            grid:   { color: GRID_COLOR },
            border: { color: "transparent" },
            title:  yLabel
                ? { display: true, text: yLabel, color: TICK_COLOR, font: BASE_FONT }
                : { display: false },
        },
    };
}

function winrateYScale() {
    return {
        x: {
            ticks:  { color: TICK_COLOR, font: BASE_FONT, maxRotation: 45 },
            grid:   { color: GRID_COLOR },
            border: { color: "transparent" },
        },
        y: {
            min: 0, max: 100,
            ticks: {
                color: TICK_COLOR, font: BASE_FONT,
                stepSize: 20,
                callback: val => val + "%",
            },
            grid:   { color: GRID_COLOR },
            border: { color: "transparent" },
        },
    };
}

// Plugin — linha pontilhada em 50%
const FIFTY_LINE_PLUGIN = {
    id: "fiftyLine",
    afterDraw(chart) {
        const { ctx, chartArea: { left, right }, scales: { y } } = chart;
        if (!y) return;
        const yPos = y.getPixelForValue(50);
        ctx.save();
        ctx.setLineDash([6, 4]);
        ctx.strokeStyle = "rgba(255, 255, 255, 0.3)";
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(left, yPos);
        ctx.lineTo(right, yPos);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.restore();
    },
};

function lineDataset(label, data, color, fill) {
    return {
        label,
        data:                 toFloat(data),
        borderColor:          color,
        backgroundColor:      fill,
        borderWidth:          2.5,
        pointRadius:          4,
        pointHoverRadius:     6,
        pointBackgroundColor: color,
        tension:              0.4,
        fill:                 true,
    };
}

function barDataset(label, data, color, fill) {
    return {
        label,
        data:            toFloat(data),
        backgroundColor: fill,
        borderColor:     color,
        borderWidth:     2,
        borderRadius:    6,
        borderSkipped:   false,
    };
}

// Registro de instâncias Chart.js
const chartInstances = {};

function destroyChart(id) {
    if (chartInstances[id]) { chartInstances[id].destroy(); delete chartInstances[id]; }
}

function registerChart(id, instance) {
    chartInstances[id] = instance;
}

// ================================================================
//  CHART FACTORIES
// ================================================================

function makeLineChart(id, labels, dataset, yLabel) {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    registerChart(id, new Chart(canvas, {
        type: "line",
        data: { labels, datasets: [dataset] },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: DEFAULT_TOOLTIP },
            scales:  defaultScales(yLabel),
        },
    }));
}

function makeBarChart(id, labels, dataset, scales) {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    registerChart(id, new Chart(canvas, {
        type: "bar",
        data: { labels, datasets: [dataset] },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { ...DEFAULT_TOOLTIP, callbacks: { label: ctx => ` ${ctx.parsed.y}` } },
            },
            scales,
        },
    }));
}

function makeWinrateBarChart(id, labels, dataset, showLegend = false, compactTicks = false) {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    const xTicks = compactTicks
        ? { color: TICK_COLOR, font: { ...BASE_FONT, size: 10 }, maxRotation: 60, minRotation: 45 }
        : { color: TICK_COLOR, font: BASE_FONT, maxRotation: 45 };
    const scales = winrateYScale();
    scales.x.ticks = xTicks;
    registerChart(id, new Chart(canvas, {
        type: "bar",
        data: { labels, datasets: [dataset] },
        plugins: [FIFTY_LINE_PLUGIN],
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: showLegend,
                    labels: { color: "rgba(255,255,255,0.7)", font: { ...BASE_FONT, size: 13 }, boxWidth: 14, padding: 12 },
                },
                tooltip: { ...DEFAULT_TOOLTIP, callbacks: { label: ctx => ` ${ctx.parsed.y}%` } },
            },
            scales,
        },
    }));
}

function makeHorizontalBarChart(id, labels, dataset, matchesLabel = "Partidas") {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    registerChart(id, new Chart(canvas, {
        type: "bar",
        data: { labels, datasets: [dataset] },
        options: {
            indexAxis: "y",
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { ...DEFAULT_TOOLTIP, callbacks: { label: ctx => ` ${ctx.parsed.x} ${matchesLabel.toLowerCase()}` } },
            },
            scales: {
                x: { ticks: { color: TICK_COLOR, font: BASE_FONT }, grid: { color: GRID_COLOR }, border: { color: "transparent" } },
                y: { ticks: { color: TICK_COLOR, font: { ...BASE_FONT, size: 13 } }, grid: { color: "transparent" }, border: { color: "transparent" } },
            },
        },
    }));
}

// ── Tab switcher com lazy render ──────────────────────────────

function setupTabs(tabGroupId, chartBuilders) {
    const group = document.getElementById(tabGroupId);
    if (!group) return;

    group.querySelectorAll(".chart-tab").forEach(btn => {
        if (btn.classList.contains("active") && chartBuilders[btn.dataset.chart]) {
            chartBuilders[btn.dataset.chart]();
        }
    });

    group.querySelectorAll(".chart-tab").forEach(btn => {
        btn.addEventListener("click", () => {
            const currentActive = group.querySelector(".chart-tab.active");
            if (currentActive === btn) return;
            destroyChart(currentActive.dataset.chart);
            group.querySelectorAll(".chart-tab").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            const targetId = btn.dataset.chart;
            const card = btn.closest(".dashboard-section").querySelector(".chart-card");
            card.querySelectorAll(".chart-canvas").forEach(c => c.classList.remove("active-chart"));
            document.getElementById(targetId).classList.add("active-chart");
            if (chartBuilders[targetId]) chartBuilders[targetId]();
        });
    });
}

// ================================================================
//  FREQUENCY CHARTS (barras verticais com ícones)
// ================================================================

const LANE_META = [
    { key: "Top",     color: "rgba(201,170,113,0.8)", icon: "../static/img/roles/Top_icon.png" },
    { key: "Jungle",  color: "rgba(80,220,140,0.8)",  icon: "../static/img/roles/Jungle_icon.png" },
    { key: "Mid",     color: "rgba(100,180,255,0.8)", icon: "../static/img/roles/Middle_icon.png" },
    { key: "ADC",     color: "rgba(255,159,67,0.8)",  icon: "../static/img/roles/Bottom_icon.png" },
    { key: "Adc",     color: "rgba(255,159,67,0.8)",  icon: "../static/img/roles/Bottom_icon.png" },
    { key: "Support", color: "rgba(180,130,255,0.8)", icon: "../static/img/roles/Support_icon.png" },
];

// Mapa de tradução de dias da semana PT → EN
const DAY_LABELS_EN = {
    "Segunda": "Monday",
    "Terça":   "Tuesday",
    "Quarta":  "Wednesday",
    "Quinta":  "Thursday",
    "Sexta":   "Friday",
    "Sábado":  "Saturday",
    "Domingo": "Sunday",
};

// Mapa EN para CLASS_META (label PT já existe, adiciona EN)
const CLASS_META_EN = {
    Fighter:  "Fighter",
    Tank:     "Tank",
    Mage:     "Mage",
    Assassin: "Assassin",
    Marksman: "Marksman",
    Support:  "Support",
};

const CLASS_META = {
    Fighter:  { label: "Lutador",   icon: "../static/img/class/Fighter_icon.png"    },
    Tank:     { label: "Tank",      icon: "../static/img/class/Tank_icon.png"       },
    Mage:     { label: "Mago",      icon: "../static/img/class/Mage_icon.png"       },
    Assassin: { label: "Assassino", icon: "../static/img/class/Slayer_icon.png"     },
    Marksman: { label: "Atirador",  icon: "../static/img/class/Marksman_icon.png"   },
    Support:  { label: "Suporte",   icon: "../static/img/class/Controller_icon.png" },
};

const GAME_MODE_LABELS_EN = {
    CLASSIC:    "Summoner's Rift",
    ARAM:       "Aram",
    CHERRY:     "Arena",
    NEXUSBLITZ: "Nexus Blitz",
    URF:        "URF",
    ONEFORALL:  "Todos por Um",
    TUTORIAL:   "Tutorial",
};


const GAME_MODE_LABELS = {
    CLASSIC:    "Summoner's Rift",
    ARAM:       "Aram",
    CHERRY:     "Arena",
    NEXUSBLITZ: "Blitz do Nexus",
    URF:        "URF",
    ONEFORALL:  "Todos por Um",
    TUTORIAL:   "Tutorial",
};

// Função genérica para os dois gráficos de barras verticais com ícone
function buildFrequencyChart(containerId, items) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const max = Math.max(...items.map(i => i.value), 1);
    container.innerHTML = items.map(({ label, icon, color, value }) => {
        const barPct = value === 0 ? 0 : Math.max(Math.round((value / max) * 100), 2);
        return `
        <div class="lane-bar-col">
            <span class="lane-bar-value">${value}</span>
            <div class="lane-bar-track">
                <div class="lane-bar-fill" style="height:${barPct}%; background:${color};"></div>
            </div>
            <img class="lane-bar-icon" src="${icon}" alt="${label}" title="${label}">
            <span class="lane-bar-label">${label}</span>
        </div>`;
    }).join("");
}

// ================================================================
//  BUILD ALL CHARTS
// ================================================================

function buildCharts(charts) {
    const lang = (typeof getCurrentLang === "function") ? getCurrentLang() : "pt";
    const isPT = lang === "pt";

    const m = charts.monthly;
    const l = charts.lanes;
    const t = charts.time;
    const c = charts.classes    || { labels: [], games: [], winrate: [] };
    const g = charts.game_modes || { labels: [], games: [], percentages: [], winrate: [] };

    // Labels traduzíveis
    const LBL = {
        kills:      isPT ? "Kills"        : "Kills",
        deaths:     isPT ? "Mortes"       : "Deaths",
        assists:    isPT ? "Assistências" : "Assists",
        gold:       isPT ? "Gold"         : "Gold",
        damage:     isPT ? "Dano"         : "Damage",
        winrate:    isPT ? "Winrate"      : "Win Rate",
        avgKills:   isPT ? "Média de Kills"        : "Average Kills",
        avgDeaths:  isPT ? "Média de Mortes"       : "Average Deaths",
        avgAssists: isPT ? "Média de Assistências" : "Average Assists",
        avgGold:    isPT ? "Gold Médio"   : "Average Gold",
        avgDamage:  isPT ? "Dano Médio"   : "Average Damage",
        winratePct: isPT ? "Winrate %"    : "Win Rate %",
        hours:      isPT ? "Horas"        : "Hours",
        hoursPlayed:isPT ? "Horas Jogadas": "Hours Played",
        matches:    isPT ? "Partidas"     : "Matches",
    };

    // Traduz dias da semana se EN
    const translateDays = labels => isPT ? labels : labels.map(d => DAY_LABELS_EN[d] ?? d);

    // ── 1. EVOLUÇÃO MENSAL ───────────────────────────────────────
    setupTabs("monthly-tabs", {
        "monthly-kills":   () => makeLineChart("monthly-kills",   m.labels, lineDataset(LBL.kills,   m.avg_kills,  GOLD_COLOR,   GOLD_FILL),   LBL.avgKills),
        "monthly-deaths":  () => makeLineChart("monthly-deaths",  m.labels, lineDataset(LBL.deaths,  m.avg_deaths, RED_COLOR,    RED_FILL),    LBL.avgDeaths),
        "monthly-assists": () => makeLineChart("monthly-assists",  m.labels, lineDataset(LBL.assists, m.avg_assists, BLUE_COLOR,  BLUE_FILL),   LBL.avgAssists),
        "monthly-gold":    () => makeLineChart("monthly-gold",    m.labels, lineDataset(LBL.gold,    m.avg_gold,   PURPLE_COLOR, PURPLE_FILL), LBL.avgGold),
        "monthly-damage":  () => makeLineChart("monthly-damage",  m.labels, lineDataset(LBL.damage,  m.avg_damage, RED_COLOR,    RED_FILL),    LBL.avgDamage),
        "monthly-winrate": () => makeWinrateBarChart("monthly-winrate", m.labels, barDataset(LBL.winrate, m.win_rate, GREEN_COLOR, GREEN_FILL), true),
    });

    // ── 2. POSIÇÕES ──────────────────────────────────────────────
    buildFrequencyChart("lane-frequency-chart", l.labels.map((key, i) => {
        const meta = LANE_META.find(m => m.key === key) || { color: GOLD_COLOR, icon: "" };
        return { label: key, icon: meta.icon, color: meta.color, value: toFloat(l.games)[i] };
    }));
    makeWinrateBarChart("lane-winrate", l.labels, barDataset(LBL.winratePct, l.winrate, GOLD_COLOR, GOLD_FILL));

    // ── 3. PERÍODOS ──────────────────────────────────────────────
    const weekdayLabels = translateDays(t.weekday.labels);
    makeBarChart("time-weekday-hours", weekdayLabels, barDataset(LBL.hours, t.weekday.hours_played, GOLD_COLOR, GOLD_FILL), defaultScales(LBL.hoursPlayed));
    makeWinrateBarChart("time-weekday-wr", weekdayLabels, barDataset(LBL.winratePct, t.weekday.winrate, GREEN_COLOR, GREEN_FILL));
    makeWinrateBarChart("time-hourly-wr",  t.hourly.labels,  barDataset(LBL.winratePct, t.hourly.winrate,  BLUE_COLOR,  BLUE_FILL), false, true);

    // ── 4. CLASSES ───────────────────────────────────────────────
    buildFrequencyChart("class-frequency-chart", c.labels.map((key, i) => {
        const meta  = CLASS_META[key] || { label: key, icon: "" };
        const label = isPT ? meta.label : (CLASS_META_EN[key] ?? meta.label);
        return { label, icon: meta.icon, color: GOLD_COLOR, value: c.games[i] };
    }));
    makeWinrateBarChart("class-winrate",
        c.labels.map(k => isPT ? (CLASS_META[k]?.label ?? k) : (CLASS_META_EN[k] ?? k)),
        barDataset(LBL.winratePct, c.winrate, PURPLE_COLOR, PURPLE_FILL)
    );

    // ── 5. MODOS DE JOGO ────────────────────────────────────────
    const gLabelsPT = g.labels.map(k => isPT ? (GAME_MODE_LABELS[k] ?? k) : (GAME_MODE_LABELS_EN[k] ?? k));
    makeHorizontalBarChart("game-modes-chart",   gLabelsPT, barDataset(LBL.matches,    g.games,           BLUE_COLOR,  BLUE_FILL), LBL.matches);
    makeWinrateBarChart(   "game-modes-winrate", gLabelsPT, barDataset(LBL.winratePct, g.winrate || [],    GOLD_COLOR,  GOLD_FILL));
}
// ================================================================
//  MATCH HISTORY
// ================================================================

function buildMatchHistory(history) {
    const container = document.getElementById("match-history-list");
    if (!container || !history || !history.length) return;

    const lang = (typeof getCurrentLang === "function") ? getCurrentLang() : "pt";
    const isPT = lang === "pt";

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
            <div class="match-result-bar"></div>

            <img class="match-champ-img" src="${m.champion_img}" alt="${m.champion}"
                 onerror="this.src='https://ddragon.leagueoflegends.com/cdn/img/champion/tiles/Lux_0.jpg'">

            <div class="match-info">
                <span class="match-champ-name">${m.champion}</span>
                <span class="match-mode">${m.gameMode}</span>
            </div>

            <div class="match-result-label ${resultClass}">
                ${resultLabel}
            </div>

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