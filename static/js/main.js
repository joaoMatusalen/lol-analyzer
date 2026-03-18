document.addEventListener("DOMContentLoaded", () => {

    // Logo — volta para home
    document.getElementById("logo").addEventListener("click", e => {
        e.stopPropagation();
        window.location.href = "/";
    });

    // Menu hamburguer
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

// pageshow dispara tanto no carregamento normal quanto ao voltar pelo histórico (bfcache).
// Garante que o form está sempre limpo e o spinner escondido quando a página é exibida.
window.addEventListener("pageshow", () => {
    const form    = document.getElementById("playerForm");
    const btn     = document.getElementById("analyzeBtn");
    const loading = document.getElementById("loading");

    if (form)    form.reset();
    if (btn)     btn.disabled = false;
    if (loading) loading.style.display = "none";
});

// Formulário de busca
document.getElementById("playerForm").addEventListener("submit", async e => {
    e.preventDefault();

    const playerName = document.getElementById("playerName").value.trim();
    const playerTag  = document.getElementById("playerTag").value.trim();
    const region     = document.getElementById("region").value;
    const btn        = document.getElementById("analyzeBtn");
    const loading    = document.getElementById("loading");

    if (!playerName || !playerTag || !region) return;

    btn.disabled = true;
    loading.style.display = "flex";

    try {
        const resp = await fetch("/analyze", {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify({playerName, playerTag, region}),
        });

        const data = await resp.json();

        if (data.error) {
            alert(`Erro: ${data.error}`);
            btn.disabled = false;
            loading.style.display = "none";
            return;
        }

        localStorage.setItem("analysisData", JSON.stringify(data));
        window.location.href = "/dashboard";

    } catch {
        alert("Erro ao conectar com o servidor.");
        btn.disabled = false;
        loading.style.display = "none";
    }
});