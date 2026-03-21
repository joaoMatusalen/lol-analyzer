import { initI18n } from './i18n.js';

document.addEventListener("DOMContentLoaded", () => {
    initI18n();

    document.getElementById("logo").addEventListener("click", e => {
        e.stopPropagation();
        window.location.href = "/";
    });

    const hamburger = document.getElementById("hamburguerBtn");
    const nav       = document.getElementById("nav-header");
    const overlay   = document.getElementById("menuOverlay");

    const openMenu  = () => { nav.classList.add("active");    overlay.classList.add("active"); };
    const closeMenu = () => { nav.classList.remove("active"); overlay.classList.remove("active"); };

    hamburger.addEventListener("click", e => {
        e.stopPropagation();
        nav.classList.contains("active") ? closeMenu() : openMenu();
    });
    overlay.addEventListener("click", closeMenu);
    window.addEventListener("scroll", closeMenu);
    document.querySelectorAll(".nav-link").forEach(l => l.addEventListener("click", closeMenu));
});

window.addEventListener("pageshow", () => {
    const form    = document.getElementById("playerForm");
    const btn     = document.getElementById("analyzeBtn");
    if (form) form.reset();
    if (btn)  btn.disabled = false;
    hideProgress();
});

// ── Progress & error ──────────────────────────────────────────────

function showProgress(message, current, total) {
    const wrap = document.getElementById("progressWrap");
    const bar  = document.getElementById("progressBar");
    const msg  = document.getElementById("progressMsg");
    const pct  = document.getElementById("progressPct");
    if (!wrap) return;

    wrap.style.display = "block";
    if (msg) msg.textContent = message || "Processando...";

    const percent = total > 0 ? Math.round((current / total) * 100) : null;
    if (bar) {
        bar.classList.toggle("indeterminate", percent === null);
        bar.style.width = percent !== null ? percent + "%" : "100%";
    }
    if (pct) pct.textContent = percent !== null ? `${percent}%` : "";
}

function hideProgress() {
    const wrap = document.getElementById("progressWrap");
    if (wrap) wrap.style.display = "none";
}

function showError(message) {
    const box = document.getElementById("errorBox");
    const msg = document.getElementById("errorMsg");
    if (!box) return;
    if (msg) msg.textContent = message;
    box.style.display = "flex";
}

window.hideError = function () {
    const box = document.getElementById("errorBox");
    if (box) box.style.display = "none";
};

// ── Polling ───────────────────────────────────────────────────────

async function pollJob(jobId) {
    return new Promise((resolve, reject) => {
        const interval = setInterval(async () => {
            try {
                const resp = await fetch(`/status/${jobId}`);
                const data = await resp.json();

                showProgress(data.step, data.current, data.total);

                if (data.status === "done")  { clearInterval(interval); resolve(data.result); }
                else if (data.status === "error") { clearInterval(interval); reject(new Error(data.error || "Erro.")); }
            } catch (err) { clearInterval(interval); reject(err); }
        }, 1500);
    });
}

// ── Form submit ───────────────────────────────────────────────────

document.getElementById("playerForm").addEventListener("submit", async e => {
    e.preventDefault();
    window.hideError();

    const playerName = document.getElementById("playerName").value.trim();
    const playerTag  = document.getElementById("playerTag").value.trim();
    const region     = document.getElementById("region").value;
    const btn        = document.getElementById("analyzeBtn");
    if (!playerName || !playerTag || !region) return;

    btn.disabled = true;
    showProgress("Iniciando...", 0, 0);

    try {
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

        const result = await pollJob(init.job_id);
        hideProgress();
        localStorage.setItem("analysisData", JSON.stringify(result));
        window.location.href = "/dashboard";

    } catch (err) {
        hideProgress();
        showError(err.message || "Erro ao conectar com o servidor.");
        btn.disabled = false;
    }
});