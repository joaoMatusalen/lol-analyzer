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
//  INIT
// ================================================================

document.addEventListener("DOMContentLoaded", () => {

    document.getElementById("logo").addEventListener("click", e => {
        e.stopPropagation();
        window.location.href = "/";
    });

    const data = JSON.parse(localStorage.getItem("analysisData"));
    if (!data) {
        console.warn("Nenhum dado encontrado. Redirecionando...");
        window.location.href = "/";
        return;
    }

    // Banner — nome do jogador
    const bannerName = document.getElementById("banner-player-name");
    if (bannerName && data.player_info) {
        bannerName.textContent = `${data.player_info.name}#${data.player_info.tag}`;
    }

    // Header search form — submete para o backend igual ao index
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
                const resp = await fetch("/analyze", {
                    method:  "POST",
                    headers: { "Content-Type": "application/json" },
                    body:    JSON.stringify({ name, tag, region }),
                });
                const result = await resp.json();
                if (result.error) {
                    alert(`Erro: ${result.error}`);
                } else {
                    localStorage.setItem("analysisData", JSON.stringify(result));
                    window.location.reload();
                }
            } catch (err) {
                alert("Erro ao conectar com o servidor.");
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-search"></i>';
            }
        });
    }

    bindGeneral(data);
    bindChampion(data);

    if (data.charts) buildCharts(data.charts);
});

// ================================================================
//  SECTION 1 — ESTATÍSTICAS GERAIS
// ================================================================

function bindGeneral(data) {
    const info  = data.player_info;
    const stats = data.geral_matchs;

    // Hero card
    setText("player-name",         `${info.name}#${info.tag}`);
    setText("player-hero-name",     `${info.name}#${info.tag}`);
    setText("player-winrate-badge", `${stats.matchResult.win_rate}% WR`);
    setText("player-kda-badge",     `${stats.kda.kda_ratio.toFixed(1)} KDA`);
    setText("player-games-badge",   `${stats.sizePlayed.total_matchs} Partidas`);

    const playerIconImg = document.getElementById("player-icon-img");
    if (playerIconImg && data.player_icon_img) {
        playerIconImg.src = data.player_icon_img;
        playerIconImg.alt = info.name;
    }

    // KPI cards
    setText("winrate",           `${stats.matchResult.win_rate}%`);
    setText("win-loss",          `${stats.matchResult.total_win} / ${stats.matchResult.total_loss}`);
    setText("kda",               stats.kda.kda_ratio.toFixed(1));
    setText("kda-detail",        `${stats.kda.avg_kills.toFixed(1)} / ${stats.kda.avg_deaths.toFixed(1)} / ${stats.kda.avg_assists.toFixed(1)}`);
    setText("total-games",       stats.sizePlayed.total_matchs);
    setText("total-time-played", stats.sizePlayed.total_time_played);
    setText("avg-gold",          fmt(stats.economy.avg_gold));
    setText("total-gold",        fmt(stats.economy.total_gold));
    setText("avg-damage",        fmt(stats.damage.avg));
    setText("total-damage",      fmt(stats.damage.total));
    setText("avg-farm",          stats.farm.avg);
    setText("total-farm",        fmt(stats.farm.total));
    setText("avg-vision",        stats.vision.avg);
    setText("total-vision",      fmt(stats.vision.total));

    // Pings — card simples
    const pg = stats.pings;
    if (pg) {
        setText("total-pings",        fmt(pg.total));
        setText("avg-pings-per-game", pg.avg_per_game);
    }

    // Wide cards — KDA detalhado
    setText("total-kills",   fmt(stats.kda.total_kills));
    setText("total-deaths",  fmt(stats.kda.total_deaths));
    setText("total-assists", fmt(stats.kda.total_assists));

    // Wide cards — Multikills
    setText("double-kills", fmt(stats.multikills.double));
    setText("triple-kills", fmt(stats.multikills.triple));
    setText("quadra-kills", fmt(stats.multikills.quadra));
    setText("penta-kills",  fmt(stats.multikills.penta));

    // Wide cards — Pings detalhados
    if (pg) {
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

    // Wide cards — Objetivos
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

// ================================================================
//  SECTION 2 — CAMPEÃO DESTAQUE
// ================================================================

function bindChampion(data) {
    const champ = data.champion_results;
    if (!champ?.champion) return;

    setText("champion-name", champ.champion);

    const img = document.getElementById("champion-img");
    if (img && data.champion_img) {
        img.src = data.champion_img;
        img.alt = champ.champion;
    }

    setText("champ-winrate-badge", `${champ.matchResult.win_rate}% WR`);
    setText("champ-kda-badge",     `${champ.kda.kda_ratio.toFixed(1)} KDA`);
    setText("champ-games-badge",   `${champ.sizePlayed.total_matchs} Partidas`);

    // KPI cards
    setText("champ-winrate",           `${champ.matchResult.win_rate}%`);
    setText("champ-win-loss",          `${champ.matchResult.total_win} / ${champ.matchResult.total_loss}`);
    setText("champ-kda",               champ.kda.kda_ratio.toFixed(1));
    setText("champ-kda-detail",        `${champ.kda.avg_kills.toFixed(1)} / ${champ.kda.avg_deaths.toFixed(1)} / ${champ.kda.avg_assists.toFixed(1)}`);
    setText("champ-total-games",       champ.sizePlayed.total_matchs);
    setText("champ-total-time-played", champ.sizePlayed.total_time_played);
    setText("champ-avg-gold",          fmt(champ.economy.avg_gold));
    setText("champ-total-gold",        fmt(champ.economy.total_gold));
    setText("champ-avg-damage",        fmt(champ.damage.avg));
    setText("champ-total-damage",      fmt(champ.damage.total));
    setText("champ-avg-farm",          champ.farm.avg);
    setText("champ-total-farm",        fmt(champ.farm.total));
    setText("champ-avg-vision",        champ.vision.avg);
    setText("champ-total-vision",      fmt(champ.vision.total));

    // Wide cards — KDA detalhado + Multikills
    setText("champ-total-kills",   fmt(champ.kda.total_kills));
    setText("champ-total-deaths",  fmt(champ.kda.total_deaths));
    setText("champ-total-assists", fmt(champ.kda.total_assists));
    setText("champ-double-kills",  fmt(champ.multikills.double));
    setText("champ-triple-kills",  fmt(champ.multikills.triple));
    setText("champ-quadra-kills",  fmt(champ.multikills.quadra));
    setText("champ-penta-kills",   fmt(champ.multikills.penta));

    // Pings — card simples + detalhados
    const pg = champ.pings;
    if (pg) {
        setText("champ-total-pings",        fmt(pg.total));
        setText("champ-avg-pings-per-game", pg.avg_per_game);
    }

    // Objetivos
    const obj = champ.objectives;
    if (obj) {
        setText("champ-total-towers",       fmt(obj.total_towers));
        setText("champ-avg-towers",         obj.avg_towers);
        setText("champ-total-inhibitors",   fmt(obj.total_inhibitor_kills));
        setText("champ-avg-inhibitors",     obj.avg_inhibitor_kills);
        setText("champ-total-barons",       fmt(obj.total_barons));
        setText("champ-avg-barons",         obj.avg_barons);
        setText("champ-total-rift-heralds", fmt(obj.total_rift_heralds));
        setText("champ-avg-rift-heralds",   obj.avg_rift_heralds);
        setText("champ-total-horde",        fmt(obj.total_horde_heralds));
        setText("champ-avg-horde",          obj.avg_horde_heralds);
        setText("champ-total-dragons",      fmt(obj.total_dragons));
        setText("champ-avg-dragons",        obj.avg_dragons);
    }

    // Pings detalhados
    if (pg) {
        setText("champ-ping-all-in",         fmt(pg.all_in));
        setText("champ-ping-enemy-missing",  fmt(pg.enemy_missing));
        setText("champ-ping-danger",         fmt(pg.danger));
        setText("champ-ping-get-back",       fmt(pg.get_back));
        setText("champ-ping-enemy-vision",   fmt(pg.enemy_vision));
        setText("champ-ping-vision-cleared", fmt(pg.vision_cleared));
        setText("champ-ping-command",        fmt(pg.command));
        setText("champ-ping-on-my-way",      fmt(pg.on_my_way));
        setText("champ-ping-assist-me",      fmt(pg.assist_me));
        setText("champ-ping-push",           fmt(pg.push));
        setText("champ-ping-need-vision",    fmt(pg.need_vision));
        setText("champ-ping-hold",           fmt(pg.hold));
    }
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

// Plugin de linha pontilhada em 50%
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
        data: toFloat(data),
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

// ── Chart instances registry ──────────────────────────────────
const chartInstances = {};

function destroyChart(id) {
    if (chartInstances[id]) {
        chartInstances[id].destroy();
        delete chartInstances[id];
    }
}

function registerChart(id, instance) {
    chartInstances[id] = instance;
}

// ── Factory functions ─────────────────────────────────────────

function makeLineChart(id, labels, dataset, yLabel) {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    registerChart(id, new Chart(canvas, {
        type: "line",
        data: { labels, datasets: [dataset] },
        options: {
            responsive: true,
            maintainAspectRatio: false,
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
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { ...DEFAULT_TOOLTIP, callbacks: { label: ctx => ` ${ctx.parsed.y}` } },
            },
            scales,
        },
    }));
}

// ── Mapa de classes EN → PT-BR e ícones ──────────────────────
const CLASS_META = {
    Fighter:  { label: "Lutador",   icon: "../static/img/class/Fighter_icon.png"    },
    Tank:     { label: "Tank",      icon: "../static/img/class/Tank_icon.png"       },
    Mage:     { label: "Mago",      icon: "../static/img/class/Mage_icon.png"       },
    Assassin: { label: "Assassino", icon: "../static/img/class/Slayer_icon.png"     },
    Marksman: { label: "Atirador",  icon: "../static/img/class/Marksman_icon.png"   },
    Support:  { label: "Suporte",   icon: "../static/img/class/Controller_icon.png" },
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

function buildClassFrequencyChart(containerId, labelsEN, values) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const max = Math.max(...values, 1);

    container.innerHTML = labelsEN.map((key, i) => {
        const meta   = CLASS_META[key] || { label: key, icon: "" };
        const barPct = values[i] === 0 ? 0 : Math.max(Math.round((values[i] / max) * 100), 2);
        const color  = GOLD_COLOR;

        return `
        <div class="lane-bar-col">
            <span class="lane-bar-value">${values[i]}</span>
            <div class="lane-bar-track">
                <div class="lane-bar-fill" style="height:${barPct}%; background:${color};"></div>
            </div>
            <img class="lane-bar-icon" src="${meta.icon}" alt="${meta.label}" title="${meta.label}">
            <span class="lane-bar-label">${meta.label}</span>
        </div>`;
    }).join("");
}

function makeHorizontalBarChart(id, labels, dataset) {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    registerChart(id, new Chart(canvas, {
        type: "bar",
        data: { labels, datasets: [dataset] },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { ...DEFAULT_TOOLTIP, callbacks: { label: ctx => ` ${ctx.parsed.x} partidas` } },
            },
            scales: {
                x: {
                    ticks:  { color: TICK_COLOR, font: BASE_FONT },
                    grid:   { color: GRID_COLOR },
                    border: { color: "transparent" },
                },
                y: {
                    ticks:  { color: TICK_COLOR, font: { ...BASE_FONT, size: 13 } },
                    grid:   { color: "transparent" },
                    border: { color: "transparent" },
                },
            },
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
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: showLegend,
                    labels: {
                        color:     "rgba(255,255,255,0.7)",
                        font:      { ...BASE_FONT, size: 13 },
                        boxWidth:  14,
                        padding:   12,
                    },
                },
                tooltip: { ...DEFAULT_TOOLTIP, callbacks: { label: ctx => ` ${ctx.parsed.y}%` } },
            },
            scales,
        },
    }));
}

// ── Tab switcher com lazy render ──────────────────────────────

function setupTabs(tabGroupId, chartBuilders) {
    const group = document.getElementById(tabGroupId);
    if (!group) return;

    // Renderiza a tab ativa inicial imediatamente
    group.querySelectorAll(".chart-tab").forEach(btn => {
        if (btn.classList.contains("active")) {
            const id = btn.dataset.chart;
            if (chartBuilders[id]) chartBuilders[id]();
        }
    });

    group.querySelectorAll(".chart-tab").forEach(btn => {
        btn.addEventListener("click", () => {
            const currentActive = group.querySelector(".chart-tab.active");
            if (currentActive === btn) return;

            // Destrói o gráfico da tab anterior
            destroyChart(currentActive.dataset.chart);

            // Troca tab ativa
            group.querySelectorAll(".chart-tab").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            // Troca canvas visível
            const targetId = btn.dataset.chart;
            const card = btn.closest(".dashboard-section").querySelector(".chart-card");
            card.querySelectorAll(".chart-canvas").forEach(c => c.classList.remove("active-chart"));
            document.getElementById(targetId).classList.add("active-chart");

            // Cria o gráfico no canvas agora visível
            if (chartBuilders[targetId]) chartBuilders[targetId]();
        });
    });
}

// ================================================================
//  LANE FREQUENCY — BARRAS VERTICAIS COM ÍCONES
// ================================================================

const LANE_META = [
    { key: "Top",     color: "rgba(201,170,113,0.8)", icon: "../static/img/roles/Top_icon.png" },
    { key: "Jungle",  color: "rgba(80,220,140,0.8)",  icon: "../static/img/roles/Jungle_icon.png" },
    { key: "Mid",     color: "rgba(100,180,255,0.8)", icon: "../static/img/roles/Middle_icon.png" },
    { key: "ADC",     color: "rgba(255,159,67,0.8)",  icon: "../static/img/roles/Bottom_icon.png" },
    { key: "Adc",     color: "rgba(255,159,67,0.8)",  icon: "../static/img/roles/Bottom_icon.png" },
    { key: "Support", color: "rgba(180,130,255,0.8)", icon: "../static/img/roles/Support_icon.png" },
];

function buildLaneFrequencyChart(containerId, labels, values) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const max = Math.max(...values, 1);

    container.innerHTML = labels.map((lane, i) => {
        const meta   = LANE_META.find(m => m.key === lane) || { color: GOLD_COLOR, icon: "" };
        const barPct = values[i] === 0 ? 0 : Math.max(Math.round((values[i] / max) * 100), 2);

        return `
        <div class="lane-bar-col">
            <span class="lane-bar-value">${values[i]}</span>
            <div class="lane-bar-track">
                <div class="lane-bar-fill" style="height:${barPct}%; background:${meta.color};"></div>
            </div>
            <img class="lane-bar-icon" src="${meta.icon}" alt="${lane}" title="${lane}">
            <span class="lane-bar-label">${lane}</span>
        </div>`;
    }).join("");
}

// ================================================================
//  BUILD ALL CHARTS
// ================================================================

function buildCharts(charts) {
    const m = charts.monthly;
    const l = charts.lanes;
    const t = charts.time;
    const c = charts.classes    || { labels: [], games: [], winrate: [] };
    const g = charts.game_modes || { labels: [], games: [], percentages: [], winrate: [] };

    // ── 1. EVOLUÇÃO MENSAL ───────────────────────────────────────
    setupTabs("monthly-tabs", {
        "monthly-kills":   () => makeLineChart("monthly-kills",   m.labels, lineDataset("Kills",        m.avg_kills,  GOLD_COLOR,   GOLD_FILL),   "Média de Kills"),
        "monthly-deaths":  () => makeLineChart("monthly-deaths",  m.labels, lineDataset("Mortes",       m.avg_deaths, RED_COLOR,    RED_FILL),    "Média de Mortes"),
        "monthly-assists": () => makeLineChart("monthly-assists",  m.labels, lineDataset("Assistências", m.avg_assists,BLUE_COLOR,   BLUE_FILL),   "Média de Assistências"),
        "monthly-gold":    () => makeLineChart("monthly-gold",    m.labels, lineDataset("Gold",         m.avg_gold,   PURPLE_COLOR, PURPLE_FILL), "Gold Médio"),
        "monthly-damage":  () => makeLineChart("monthly-damage",  m.labels, lineDataset("Dano",         m.avg_damage, RED_COLOR,    RED_FILL),    "Dano Médio"),
        "monthly-winrate": () => makeWinrateBarChart("monthly-winrate", m.labels, barDataset("Winrate", m.win_rate, GREEN_COLOR, GREEN_FILL), true),
    });

    // ── 2. POSIÇÕES ──────────────────────────────────────────────
    buildLaneFrequencyChart("lane-frequency-chart", l.labels, toFloat(l.games));
    makeWinrateBarChart("lane-winrate", l.labels, barDataset("Winrate %", l.winrate, GOLD_COLOR, GOLD_FILL));

    // ── 3. PERÍODOS ──────────────────────────────────────────────
    makeBarChart("time-weekday-hours", t.weekday.labels, barDataset("Horas", t.weekday.hours_played, GOLD_COLOR, GOLD_FILL), defaultScales("Horas Jogadas"));
    makeWinrateBarChart("time-weekday-wr", t.weekday.labels, barDataset("Winrate %", t.weekday.winrate, GREEN_COLOR, GREEN_FILL));
    makeWinrateBarChart("time-hourly-wr",  t.hourly.labels,  barDataset("Winrate %", t.hourly.winrate,  BLUE_COLOR,  BLUE_FILL), false, true);

    // ── 4. CLASSES ───────────────────────────────────────────────
    const cLabelsPT = c.labels.map(k => CLASS_META[k]?.label ?? k);
    buildClassFrequencyChart("class-frequency-chart", c.labels, c.games);
    makeWinrateBarChart("class-winrate", cLabelsPT, barDataset("Winrate %", c.winrate, PURPLE_COLOR, PURPLE_FILL));

    // ── 5. MODOS DE JOGO ────────────────────────────────────────
    const gLabelsPT = g.labels.map(k => GAME_MODE_LABELS[k] ?? k);
    makeHorizontalBarChart("game-modes-chart",   gLabelsPT, barDataset("Partidas",   g.games,   BLUE_COLOR,   BLUE_FILL));
    makeWinrateBarChart("game-modes-winrate", gLabelsPT, barDataset("Winrate %", g.winrate || [], GOLD_COLOR, GOLD_FILL));
}