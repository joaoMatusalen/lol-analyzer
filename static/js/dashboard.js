import { initI18n, translateError } from './i18n.js';
import { initTooltip, bindSection } from './ui.js';
import { buildCharts } from './charts.js';
import { buildMatchHistory } from './history.js';

// ── Inline error banner ───────────────────────────────────────────

/**
 * Displays an error message banner below the dashboard header.
 * Creates the DOM element on first call and reuses it on subsequent calls.
 *
 * @param {string} message - Human-readable error text to display.
 */
function showError(message) {
    let box = document.getElementById("dashErrorBox");
    if (!box) {
        box = document.createElement("div");
        box.id        = "dashErrorBox";
        box.className = "dash-error-box";
        box.innerHTML = `
            <i class="fas fa-exclamation-circle"></i>
            <p id="dashErrorMsg"></p>
            <button class="error-close" onclick="document.getElementById('dashErrorBox').style.display='none'">
                <i class="fas fa-times"></i> Close
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

    // Clicking the logo always navigates back to the search page
    document.getElementById("logo").addEventListener("click", e => {
        e.stopPropagation();
        window.location.href = "/";
    });

    // Clear header search inputs so they don't carry over stale values on reload
    const nameInput = document.getElementById("header-playerName");
    const tagInput  = document.getElementById("header-playerTag");
    if (nameInput) nameInput.value = "";
    if (tagInput)  tagInput.value  = "";

    // Load the analysis result that was saved to localStorage by the search page
    let data;
    try {
        data = JSON.parse(localStorage.getItem("analysisData"));
    } catch {
        console.warn("Corrupted analysis data. Redirecting...");
        window.location.href = "/";
        return;
    }
    if (!data) {
        console.warn("No analysis data found. Redirecting...");
        window.location.href = "/";
        return;
    }

    // ── Header search form ────────────────────────────────────────
    // Allows searching for a different player without leaving the dashboard
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
                if (init.error) { showError(translateError(init.error)); return; }

                const result = await _pollJob(init.job_id);
                localStorage.setItem("analysisData", JSON.stringify(result));
                window.location.reload();
            } catch {
                showError("Could not connect to the server.");
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-search"></i>';
            }
        });
    }

    // ── Update button with client-side cooldown ───────────────────
    // Prevents the user from spamming incremental refreshes.
    // A 2-minute cooldown is enforced via localStorage so it persists across reloads.
    const updateBtn  = document.getElementById("updateBtn");
    const timerLabel = document.getElementById("updateTimer");
    const COOLDOWN_KEY = "lolanalyzer_update_cooldown";
    const COOLDOWN_MS  = 2 * 60 * 1000; // 2 minutes in milliseconds

    if (updateBtn && data.player_info) {
        let countdownInterval = null;

        /**
         * Starts the cooldown countdown, disabling the update button
         * and showing a live timer until the cooldown expires.
         *
         * @param {number} startedAt - Unix timestamp (ms) when the cooldown began.
         */
        function startCooldown(startedAt) {
            localStorage.setItem(COOLDOWN_KEY, startedAt);
            updateBtn.disabled       = true;
            timerLabel.style.display = "inline";

            countdownInterval = setInterval(() => {
                const remaining = Math.max(0, Math.ceil((COOLDOWN_MS - (Date.now() - startedAt)) / 1000));
                const m = Math.floor(remaining / 60);
                const s = String(remaining % 60).padStart(2, "0");
                timerLabel.textContent = `${m}:${s}`;

                if (remaining <= 0) {
                    clearInterval(countdownInterval);
                    localStorage.removeItem(COOLDOWN_KEY);
                    updateBtn.disabled       = false;
                    timerLabel.style.display = "none";
                    updateBtn.innerHTML      = '<i class="fas fa-sync-alt"></i> Update';
                }
            }, 1000);
        }

        // Restore a cooldown that was active before the page was reloaded
        const savedAt = parseInt(localStorage.getItem(COOLDOWN_KEY), 10);
        if (savedAt && Date.now() - savedAt < COOLDOWN_MS) startCooldown(savedAt);

        updateBtn.addEventListener("click", async () => {
            if (updateBtn.disabled) return;
            updateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Update';
            startCooldown(Date.now());

            let pollInterval = null;
            try {
                // Request a forced incremental update for the currently displayed player
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
                    showError(init.error);
                    updateBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Update';
                    return;
                }

                // Poll the job status endpoint until the update completes or fails
                pollInterval = setInterval(async () => {
                    try {
                        const sr  = await fetch(`/status/${init.job_id}`);
                        const job = await sr.json();
                        if (job.status === "done") {
                            clearInterval(pollInterval);
                            localStorage.setItem("analysisData", JSON.stringify(job.result));
                            // Small delay before reload to ensure localStorage write completes
                            setTimeout(() => window.location.reload(), 50);
                        } else if (job.status === "error") {
                            clearInterval(pollInterval);
                            showError(translateError(job.error));
                            updateBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Update';
                        }
                    } catch {
                        clearInterval(pollInterval);
                        showError("Error checking update status.");
                        updateBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Update';
                    }
                }, 1500);
            } catch {
                if (pollInterval) clearInterval(pollInterval);
                showError("Could not connect to the server.");
                updateBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Update';
            }
        });
    }

    // ── Render dashboard sections ─────────────────────────────────
    bindSection("",       data.geral_matchs,     data);  // General stats
    bindSection("champ-", data.champion_results, data);  // Most-played champion stats
    if (data.charts)        buildCharts(data.charts);
    if (data.match_history) buildMatchHistory(data.match_history);
});

// ── Job polling helper ────────────────────────────────────────────

/**
 * Polls /status/<jobId> every 1.5 seconds until the job finishes or fails.
 *
 * @param {string} jobId - Job UUID returned by the /analyze endpoint.
 * @returns {Promise<object>} Resolves with the result payload on success.
 */
async function _pollJob(jobId) {
    return new Promise((resolve, reject) => {
        const interval = setInterval(async () => {
            try {
                const resp = await fetch(`/status/${jobId}`);
                const job  = await resp.json();
                if (job.status === "done")  { clearInterval(interval); resolve(job.result); }
                else if (job.status === "error") { clearInterval(interval); reject(new Error(job.error || "Error.")); }
            } catch (err) { clearInterval(interval); reject(err); }
        }, 1500);
    });
}