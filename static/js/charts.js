import { getCurrentLang } from './i18n.js';
import { fmt } from './ui.js';

// ── Color palette ─────────────────────────────────────────────────
// Consistent color tokens used across all Chart.js instances

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

const BASE_FONT  = { family: "Inter, sans-serif", size: 12 };
const GRID_COLOR = "rgba(255, 255, 255, 0.06)";
const TICK_COLOR = "rgba(255, 255, 255, 0.4)";

// Shared tooltip style applied to every chart
const DEFAULT_TOOLTIP = {
    backgroundColor: "rgba(10, 22, 40, 0.95)",
    titleColor:      GOLD_COLOR,
    bodyColor:       "rgba(255,255,255,0.8)",
    borderColor:     "rgba(201,170,113,0.3)",
    borderWidth:     1,
    padding:         10,
};

// ── Lane and class metadata ───────────────────────────────────────
// Ordered arrays used to build frequency bar charts with icons

const LANE_META = [
    { key: "Top",     color: "rgba(201,170,113,0.8)", icon: "/static/img/roles/Top_icon.png" },
    { key: "Jungle",  color: "rgba(80,220,140,0.8)",  icon: "/static/img/roles/Jungle_icon.png" },
    { key: "Mid",     color: "rgba(100,180,255,0.8)", icon: "/static/img/roles/Middle_icon.png" },
    { key: "Adc",     color: "rgba(255,159,67,0.8)",  icon: "/static/img/roles/Bottom_icon.png" },
    { key: "Support", color: "rgba(180,130,255,0.8)", icon: "/static/img/roles/Support_icon.png" },
];

// Maps Riot class keys to localised display labels and icon paths
const CLASS_META = {
    Fighter:  { label: "Lutador",   labelEn: "Fighter",  icon: "/static/img/class/Fighter_icon.png" },
    Tank:     { label: "Tank",      labelEn: "Tank",     icon: "/static/img/class/Tank_icon.png" },
    Mage:     { label: "Mago",      labelEn: "Mage",     icon: "/static/img/class/Mage_icon.png" },
    Assassin: { label: "Assassino", labelEn: "Assassin", icon: "/static/img/class/Slayer_icon.png" },
    Marksman: { label: "Atirador",  labelEn: "Marksman", icon: "/static/img/class/Marksman_icon.png" },
    Support:  { label: "Suporte",   labelEn: "Support",  icon: "/static/img/class/Controller_icon.png" },
};

// Localised display names for each game mode key returned by the API
const GAME_MODE_LABELS = {
    pt: { CLASSIC: "Summoner's Rift", ARAM: "Aram", CHERRY: "Arena", NEXUSBLITZ: "Blitz do Nexus", URF: "URF" },
    en: { CLASSIC: "Summoner's Rift", ARAM: "Aram", CHERRY: "Arena", NEXUSBLITZ: "Nexus Blitz",    URF: "URF" },
};

// Maps Portuguese day abbreviations to English equivalents for i18n
const DAY_LABELS_EN = {
    "Segunda": "Monday", "Terca": "Tuesday", "Quarta": "Wednesday",
    "Quinta": "Thursday", "Sexta": "Friday", "Sabado": "Saturday", "Domingo": "Sunday",
};

// ── Chart.js instance registry ────────────────────────────────────
// Tracks live instances by canvas ID so they can be destroyed before re-render

const _instances = {};

/** Destroys the Chart.js instance for the given canvas ID, if one exists. */
function _destroy(id) {
    if (_instances[id]) { _instances[id].destroy(); delete _instances[id]; }
}

/** Saves a Chart.js instance under its canvas ID for later cleanup. */
function _register(id, instance) {
    _instances[id] = instance;
}

// ── Scale builders ────────────────────────────────────────────────

/**
 * Returns a standard x/y scale config for line and bar charts.
 * @param {string} yLabel - Optional label for the Y axis.
 */
function defaultScales(yLabel = "") {
    return {
        x: { ticks: { color: TICK_COLOR, font: BASE_FONT, maxRotation: 45 }, grid: { color: GRID_COLOR }, border: { color: "transparent" } },
        y: {
            ticks:  { color: TICK_COLOR, font: BASE_FONT },
            grid:   { color: GRID_COLOR },
            border: { color: "transparent" },
            title:  yLabel ? { display: true, text: yLabel, color: TICK_COLOR, font: BASE_FONT } : { display: false },
        },
    };
}

/**
 * Returns a Y scale fixed to 0–100% for win rate charts.
 * Tick steps are every 20% for readability.
 */
function winrateYScale() {
    return {
        x: { ticks: { color: TICK_COLOR, font: BASE_FONT, maxRotation: 45 }, grid: { color: GRID_COLOR }, border: { color: "transparent" } },
        y: {
            min: 0, max: 100,
            ticks:  { color: TICK_COLOR, font: BASE_FONT, stepSize: 20, callback: v => v + "%" },
            grid:   { color: GRID_COLOR },
            border: { color: "transparent" },
        },
    };
}

// Chart.js plugin: draws a dotted horizontal reference line at the 50% win rate mark
const FIFTY_LINE_PLUGIN = {
    id: "fiftyLine",
    afterDraw(chart) {
        const { ctx, chartArea: { left, right }, scales: { y } } = chart;
        if (!y) return;
        const yPos = y.getPixelForValue(50);
        ctx.save();
        ctx.setLineDash([6, 4]);
        ctx.strokeStyle = "rgba(255, 255, 255, 0.3)";
        ctx.lineWidth   = 1.5;
        ctx.beginPath();
        ctx.moveTo(left, yPos);
        ctx.lineTo(right, yPos);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.restore();
    },
};

// ── Dataset builders ──────────────────────────────────────────────

/** Coerces all array elements to floats, defaulting to 0 for invalid values. */
function toFloat(arr) {
    return (arr || []).map(v => parseFloat(v) || 0);
}

/** Creates a Chart.js line dataset config with area fill. */
function lineDataset(label, data, color, fill) {
    return {
        label, data: toFloat(data), borderColor: color, backgroundColor: fill,
        borderWidth: 2.5, pointRadius: 4, pointHoverRadius: 6,
        pointBackgroundColor: color, tension: 0.4, fill: true,
    };
}

/** Creates a Chart.js bar dataset config with rounded corners. */
function barDataset(label, data, color, fill) {
    return {
        label, data: toFloat(data), backgroundColor: fill,
        borderColor: color, borderWidth: 2, borderRadius: 6, borderSkipped: false,
    };
}

// ── Chart factories ───────────────────────────────────────────────

/**
 * Renders a single-dataset area line chart on the given canvas.
 * @param {string} id      - Canvas element ID.
 * @param {string[]} labels - X-axis labels.
 * @param {object} dataset  - Dataset config from lineDataset().
 * @param {string} yLabel   - Optional Y-axis title.
 */
function makeLineChart(id, labels, dataset, yLabel) {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    _register(id, new Chart(canvas, {
        type: "line",
        data: { labels, datasets: [dataset] },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: DEFAULT_TOOLTIP },
            scales: defaultScales(yLabel),
        },
    }));
}

/**
 * Renders a vertical bar chart with optional custom scale config.
 * @param {string} id      - Canvas element ID.
 * @param {string[]} labels - X-axis labels.
 * @param {object} dataset  - Dataset config from barDataset().
 * @param {object} scales   - Chart.js scales config object.
 */
function makeBarChart(id, labels, dataset, scales) {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    _register(id, new Chart(canvas, {
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

/**
 * Renders a win rate bar chart with a fixed 0–100% Y axis and 50% reference line.
 * @param {string}  id            - Canvas element ID.
 * @param {string[]} labels        - X-axis labels.
 * @param {object}  dataset        - Dataset config from barDataset().
 * @param {boolean} showLegend     - Whether to display the chart legend.
 * @param {boolean} compactTicks   - Use smaller, rotated tick labels (for dense data).
 */
function makeWinrateBarChart(id, labels, dataset, showLegend = false, compactTicks = false) {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    const xTicks = compactTicks
        ? { color: TICK_COLOR, font: { ...BASE_FONT, size: 10 }, maxRotation: 60, minRotation: 45 }
        : { color: TICK_COLOR, font: BASE_FONT, maxRotation: 45 };
    const scales   = winrateYScale();
    scales.x.ticks = xTicks;
    _register(id, new Chart(canvas, {
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

/**
 * Renders a horizontal bar chart (indexAxis: "y"), used for game mode counts.
 * @param {string}  id            - Canvas element ID.
 * @param {string[]} labels        - Y-axis (category) labels.
 * @param {object}  dataset        - Dataset config from barDataset().
 * @param {string}  matchesLabel   - Tooltip unit label (e.g. "Matches").
 */
function makeHorizontalBarChart(id, labels, dataset, matchesLabel = "Matches") {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    _register(id, new Chart(canvas, {
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

// ── Custom frequency chart ────────────────────────────────────────

/**
 * Renders a custom vertical bar chart with icon labels below each bar.
 * Used for lane and champion class frequency displays.
 *
 * Bar heights are proportional to the highest value in the dataset.
 * Bars with a value of 0 are rendered at a minimum of 2% height for visibility.
 *
 * @param {string} containerId - ID of the container <div>.
 * @param {Array<{label, icon, color, value}>} items - Data items to render.
 */
function buildFrequencyChart(containerId, items) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const max = Math.max(...items.map(i => i.value), 1);
    container.innerHTML = items.map(({ label, icon, color, value }) => {
        const pct = value === 0 ? 0 : Math.max(Math.round((value / max) * 100), 2);
        return `
        <div class="lane-bar-col">
            <span class="lane-bar-value">${value}</span>
            <div class="lane-bar-track">
                <div class="lane-bar-fill" style="height:${pct}%; background:${color};"></div>
            </div>
            <img class="lane-bar-icon" src="${icon}" alt="${label}" title="${label}">
            <span class="lane-bar-label">${label}</span>
        </div>`;
    }).join("");
}

// ── Tab switcher with lazy rendering ─────────────────────────────

/**
 * Wires up tab buttons within a tab group to lazily render charts on demand.
 *
 * The active tab's chart is rendered immediately on setup.
 * When the user clicks another tab, the previous chart is destroyed first
 * to free Canvas memory, then the new chart is built.
 *
 * @param {string} tabGroupId    - ID of the element containing .chart-tab buttons.
 * @param {Object} chartBuilders - Map of chart canvas ID → builder function.
 */
function setupTabs(tabGroupId, chartBuilders) {
    const group = document.getElementById(tabGroupId);
    if (!group) return;

    // Immediately render the initially-active tab
    group.querySelectorAll(".chart-tab").forEach(btn => {
        if (btn.classList.contains("active") && chartBuilders[btn.dataset.chart]) {
            chartBuilders[btn.dataset.chart]();
        }
    });

    group.querySelectorAll(".chart-tab").forEach(btn => {
        btn.addEventListener("click", () => {
            const active = group.querySelector(".chart-tab.active");
            if (active === btn) return;

            // Destroy the outgoing chart to release the Canvas context
            _destroy(active.dataset.chart);

            group.querySelectorAll(".chart-tab").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            // Show the correct canvas within the card
            const card = btn.closest(".dashboard-section").querySelector(".chart-card");
            card.querySelectorAll(".chart-canvas").forEach(c => c.classList.remove("active-chart"));
            document.getElementById(btn.dataset.chart).classList.add("active-chart");

            if (chartBuilders[btn.dataset.chart]) chartBuilders[btn.dataset.chart]();
        });
    });
}

// ── Public entry point ────────────────────────────────────────────

/**
 * Builds all dashboard charts from the analytics payload returned by the API.
 *
 * Called once after the analysis result is loaded from localStorage.
 * All chart sections use lazy tab rendering to avoid building hidden canvases.
 *
 * @param {object} charts - The `charts` key from the analysis result payload.
 */
export function buildCharts(charts) {
    const lang = getCurrentLang();
    const isPT = lang === "pt";
    const gml  = GAME_MODE_LABELS[isPT ? "pt" : "en"];

    // Destructure chart data sections with safe fallbacks
    const m = charts.daily;
    const l = charts.lanes;
    const t = charts.time;
    const c = charts.classes    || { labels: [], games: [], winrate: [] };
    const g = charts.game_modes || { labels: [], games: [], percentages: [], winrate: [] };

    // Localised axis and tooltip labels
    const LBL = {
        kills:        isPT ? "Kills"                : "Kills",
        deaths:       isPT ? "Mortes"               : "Deaths",
        assists:      isPT ? "Assistencias"         : "Assists",
        gold:         isPT ? "Gold"                 : "Gold",
        damage:       isPT ? "Dano"                 : "Damage",
        winrate:      isPT ? "Winrate"              : "Win Rate",
        avgKills:     isPT ? "Media de Kills"       : "Average Kills",
        avgDeaths:    isPT ? "Media de Mortes"      : "Average Deaths",
        avgAssists:   isPT ? "Media de Assistencias": "Average Assists",
        avgGold:      isPT ? "Gold Medio"           : "Average Gold",
        avgDamage:    isPT ? "Dano Medio"           : "Average Damage",
        winratePct:   isPT ? "Winrate %"            : "Win Rate %",
        hours:        isPT ? "Horas"                : "Hours",
        hoursPlayed:  isPT ? "Horas Jogadas"        : "Hours Played",
        matches:      isPT ? "Partidas"             : "Matches",
    };

    // Converts Portuguese weekday labels to English when needed
    const translateDays = labels =>
        isPT ? labels : labels.map(d => DAY_LABELS_EN[d] ?? d);

    // 1. Daily evolution — tab group with one chart per metric
    setupTabs("daily-tabs", {
        "daily-kills":   () => makeLineChart("daily-kills",   m.labels, lineDataset(LBL.kills,   m.avg_kills,   GOLD_COLOR,   GOLD_FILL),   LBL.avgKills),
        "daily-deaths":  () => makeLineChart("daily-deaths",  m.labels, lineDataset(LBL.deaths,  m.avg_deaths,  RED_COLOR,    RED_FILL),    LBL.avgDeaths),
        "daily-assists": () => makeLineChart("daily-assists",  m.labels, lineDataset(LBL.assists, m.avg_assists, BLUE_COLOR,   BLUE_FILL),   LBL.avgAssists),
        "daily-gold":    () => makeLineChart("daily-gold",    m.labels, lineDataset(LBL.gold,    m.avg_gold,    PURPLE_COLOR, PURPLE_FILL), LBL.avgGold),
        "daily-damage":  () => makeLineChart("daily-damage",  m.labels, lineDataset(LBL.damage,  m.avg_damage,  RED_COLOR,    RED_FILL),    LBL.avgDamage),
        "daily-winrate": () => makeWinrateBarChart("daily-winrate", m.labels, barDataset(LBL.winrate, m.win_rate, GREEN_COLOR, GREEN_FILL), true),
    });

    // 2. Lane positions — frequency bars and win rate chart
    buildFrequencyChart("lane-frequency-chart", l.labels.map((key, i) => {
        const meta = LANE_META.find(m => m.key === key) || { color: GOLD_COLOR, icon: "" };
        return { label: key, icon: meta.icon, color: meta.color, value: toFloat(l.games)[i] };
    }));
    makeWinrateBarChart("lane-winrate", l.labels, barDataset(LBL.winratePct, l.winrate, GOLD_COLOR, GOLD_FILL));

    // 3. Time patterns — hours played by weekday, win rate by weekday and by hour
    const weekdayLabels = translateDays(t.weekday.labels);
    makeBarChart("time-weekday-hours", weekdayLabels, barDataset(LBL.hours, t.weekday.hours_played, GOLD_COLOR, GOLD_FILL), defaultScales(LBL.hoursPlayed));
    makeWinrateBarChart("time-weekday-wr",  weekdayLabels,   barDataset(LBL.winratePct, t.weekday.winrate, GREEN_COLOR, GREEN_FILL));
    // Compact ticks for 24-hour labels to avoid overlap
    makeWinrateBarChart("time-hourly-wr",   t.hourly.labels, barDataset(LBL.winratePct, t.hourly.winrate,  BLUE_COLOR,  BLUE_FILL), false, true);

    // 4. Champion classes — frequency bars and win rate chart
    buildFrequencyChart("class-frequency-chart", c.labels.map((key, i) => {
        const meta  = CLASS_META[key] || { label: key, labelEn: key, icon: "" };
        const label = isPT ? meta.label : meta.labelEn;
        return { label, icon: meta.icon, color: GOLD_COLOR, value: c.games[i] };
    }));
    makeWinrateBarChart("class-winrate",
        c.labels.map(k => {
            const meta = CLASS_META[k];
            return meta ? (isPT ? meta.label : meta.labelEn) : k;
        }),
        barDataset(LBL.winratePct, c.winrate, PURPLE_COLOR, PURPLE_FILL),
    );

    // 5. Game modes — horizontal match count bars and win rate chart
    const gLabels = g.labels.map(k => gml[k] ?? k);
    makeHorizontalBarChart("game-modes-chart",   gLabels, barDataset(LBL.matches,    g.games,        BLUE_COLOR,  BLUE_FILL), LBL.matches);
    makeWinrateBarChart(   "game-modes-winrate", gLabels, barDataset(LBL.winratePct, g.winrate || [], GOLD_COLOR,  GOLD_FILL));
}