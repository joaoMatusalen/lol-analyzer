import { initI18n } from './i18n.js';
import { initTooltip, bindSection } from './ui.js';
import { buildCharts } from './charts.js';
import { buildMatchHistory } from './history.js';

// ── Erro inline ───────────────────────────────────────────────────

function showError(message) {
    let box = document.getElementById("dashErrorBox");
    if (!box) {
        box = document.createElement("div");
        box.id = "dashErrorBox";
        box.className = "dash-error-box";
        box.innerHTML = `
            <i class="fas fa-exclamation-circle"></i>
            <p id="dashErrorMsg"></p>
            <button class="error-close" onclick="document.getElementById('dashErrorBox').style.display='none'">
                <i class="fas fa-times"></i> Fechar
            </button>`;
        const banner = document.querySelector(".dashboard-banner-simple");
        if (banner) banner.insertAdjacentElement("afterend", box);
        else document.querySelector(".container").prepend(box);
    }
    document.getElementById("dashErrorMsg").textContent = message;
    box.style.display = "flex";
}

document.addEventListener("DOMContentLoaded", () => {

    initI18n();
    initTooltip();

    document.getElementById("logo").addEventListener("click", e => {
        e.stopPropagation();
        window.location.href = "/";
    });

    const nameInput = document.getElementById("header-playerName");
    const tagInput  = document.getElementById("header-playerTag");
    if (nameInput) nameInput.value = "";
    if (tagInput)  tagInput.value  = "";

    let data;
    try {
        data = JSON.parse(localStorage.getItem("analysisData"));
    } catch {
        console.warn("Dados corrompidos. Redirecionando...");
        window.location.href = "/";
        return;
    }
    if (!data) {
        console.warn("Sem dados. Redirecionando...");
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
                const resp = await fetch("/analyze", {
                    method:  "POST",
                    headers: { "Content-Type": "application/json" },
                    body:    JSON.stringify({ playerName: name, playerTag: tag, region }),
                });
                const init = await resp.json();
                if (init.error) { showError(init.error); return; }

                const result = await _pollJob(init.job_id);
                localStorage.setItem("analysisData", JSON.stringify(result));
                window.location.reload();
            } catch {
                showError("Erro ao conectar com o servidor.");
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-search"></i>';
            }
        });
    }

    // Botão Update com cooldown
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
                const remaining = Math.max(0, Math.ceil((COOLDOWN_MS - (Date.now() - startedAt)) / 1000));
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

        const savedAt = parseInt(localStorage.getItem(COOLDOWN_KEY), 10);
        if (savedAt && Date.now() - savedAt < COOLDOWN_MS) startCooldown(savedAt);

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
                if (init.error) { showError(init.error); forceBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Update'; return; }

                pollInterval = setInterval(async () => {
                    try {
                        const sr  = await fetch(`/status/${init.job_id}`);
                        const job = await sr.json();
                        if (job.status === "done") {
                            clearInterval(pollInterval);
                            localStorage.setItem("analysisData", JSON.stringify(job.result));
                            setTimeout(() => window.location.reload(), 50);
                        } else if (job.status === "error") {
                            clearInterval(pollInterval);
                            showError(job.error);
                            forceBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Update';
                        }
                    } catch {
                        clearInterval(pollInterval);
                        showError("Erro ao verificar status da atualização.");
                        forceBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Update';
                    }
                }, 1500);
            } catch {
                if (pollInterval) clearInterval(pollInterval);
                showError("Erro ao conectar com o servidor.");
                forceBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Update';
            }
        });
    }

    bindSection("", data.geral_matchs, data);
    bindSection("champ-", data.champion_results, data);
    if (data.charts)        buildCharts(data.charts);
    if (data.match_history) buildMatchHistory(data.match_history);
});

async function _pollJob(jobId) {
    return new Promise((resolve, reject) => {
        const interval = setInterval(async () => {
            try {
                const resp = await fetch(`/status/${jobId}`);
                const job  = await resp.json();
                if (job.status === "done")  { clearInterval(interval); resolve(job.result); }
                else if (job.status === "error") { clearInterval(interval); reject(new Error(job.error || "Erro.")); }
            } catch (err) { clearInterval(interval); reject(err); }
        }, 1500);
    });
}