import { initI18n, translateError, translateProgress } from './i18n.js';

document.addEventListener("DOMContentLoaded", () => {
    initI18n();

    // Clicking the logo always navigates to the root search page
    document.getElementById("logo").addEventListener("click", e => {
        e.stopPropagation();
        window.location.href = "/";
    });

    // ── Mobile hamburger menu ─────────────────────────────────────
    const hamburger = document.getElementById("hamburguerBtn");
    const nav       = document.getElementById("nav-header");
    const overlay   = document.getElementById("menuOverlay");

    const openMenu  = () => { nav.classList.add("active");    overlay.classList.add("active"); };
    const closeMenu = () => { nav.classList.remove("active"); overlay.classList.remove("active"); };

    hamburger.addEventListener("click", e => {
        e.stopPropagation();
        nav.classList.contains("active") ? closeMenu() : openMenu();
    });
    // Close the menu when tapping the overlay, scrolling or following a nav link
    overlay.addEventListener("click", closeMenu);
    window.addEventListener("scroll", closeMenu);
    document.querySelectorAll(".nav-link").forEach(l => l.addEventListener("click", closeMenu));
});

// Reset form state when navigating back via browser history (bfcache restore)
window.addEventListener("pageshow", () => {
    const form = document.getElementById("playerForm");
    const btn  = document.getElementById("analyzeBtn");
    if (form) form.reset();
    if (btn)  btn.disabled = false;
    hideProgress();
});

// ── Progress bar helpers ──────────────────────────────────────────

/**
 * Shows the progress bar with an optional percentage indicator.
 * When total is 0 (indeterminate), the bar animates without a percentage.
 *
 * @param {string} message - Human-readable progress message to display.
 * @param {number} current - Matches processed so far.
 * @param {number} total   - Total matches to process (0 = indeterminate).
 */
function showProgress(message, current, total) {
    const wrap = document.getElementById("progressWrap");
    const bar  = document.getElementById("progressBar");
    const msg  = document.getElementById("progressMsg");
    const pct  = document.getElementById("progressPct");
    if (!wrap) return;

    wrap.style.display = "block";
    if (msg) msg.textContent = message || "Processing...";

    const percent = total > 0 ? Math.round((current / total) * 100) : null;
    if (bar) {
        // Toggle CSS animation class for indeterminate state
        bar.classList.toggle("indeterminate", percent === null);
        bar.style.width = percent !== null ? percent + "%" : "100%";
    }
    if (pct) pct.textContent = percent !== null ? `${percent}%` : "";
}

/** Hides the progress bar wrapper. */
function hideProgress() {
    const wrap = document.getElementById("progressWrap");
    if (wrap) wrap.style.display = "none";
}

/**
 * Shows an inline error message below the search form.
 *
 * @param {string} message - Error text to display.
 */
function showError(message) {
    const box = document.getElementById("errorBox");
    const msg = document.getElementById("errorMsg");
    if (!box) return;
    if (msg) msg.textContent = message;
    box.style.display = "flex";
}

// Exposed globally so the inline onclick in index.html can call it
window.hideError = function () {
    const box = document.getElementById("errorBox");
    if (box) box.style.display = "none";
};

// ── Job polling ───────────────────────────────────────────────────

/**
 * Polls the /status/<jobId> endpoint every 1.5 seconds until the job
 * completes or fails. Updates the progress bar on each tick.
 *
 * @param {string} jobId - Job UUID returned by /analyze.
 * @returns {Promise<object>} Resolves with the result payload when done.
 */
async function pollJob(jobId) {
    return new Promise((resolve, reject) => {
        const interval = setInterval(async () => {
            try {
                const resp = await fetch(`/status/${jobId}`);
                const data = await resp.json();

                showProgress(translateProgress(data.step), data.current, data.total);

                if (data.status === "done")  { clearInterval(interval); resolve(data.result); }
                else if (data.status === "error") { clearInterval(interval); reject(new Error(translateError(data.error))); }
            } catch (err) { clearInterval(interval); reject(err); }
        }, 1500);
    });
}

// ── Search form submit ────────────────────────────────────────────

document.getElementById("playerForm").addEventListener("submit", async e => {
    e.preventDefault();
    window.hideError();

    const playerName = document.getElementById("playerName").value.trim();
    const playerTag  = document.getElementById("playerTag").value.trim();
    const region     = document.getElementById("region").value;
    const btn        = document.getElementById("analyzeBtn");
    if (!playerName || !playerTag || !region) return;

    btn.disabled = true;
    showProgress(translateProgress("progress.starting"), 0, 0);

    try {
        // Kick off the background analysis job
        const resp = await fetch("/analyze", {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify({ playerName, playerTag, region }),
        });
        const init = await resp.json();

        if (init.error) {
            hideProgress();
            showError(init.error);
            btn.disabled = false;
            return;
        }

        // Poll until done, then persist result and navigate to the dashboard
        const result = await pollJob(init.job_id);
        hideProgress();
        localStorage.setItem("analysisData", JSON.stringify(result));
        window.location.href = "/dashboard";

    } catch (err) {
        hideProgress();
        showError(err.message || "Could not connect to the server.");
        btn.disabled = false;
    }
});