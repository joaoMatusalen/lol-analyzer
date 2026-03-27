// ================================================================
//  i18n — Troca de idioma PT-BR / EN
//  Uso:  data-pt="Texto PT"  data-en="Text EN"  em qualquer elemento
//        data-pt-placeholder  data-en-placeholder  em inputs
//        data-pt-tooltip      data-en-tooltip      em .classic-info-icon
// ================================================================

const I18N_KEY = "lolanalyzer_lang";

const ERROR_STRINGS = {
    pt: {
        "error.no_match":       "Nenhuma partida encontrada. Verifique se a região está correta.",
        "error.account_not_found":"Conta não encontrada. Verifique o nome e a tag.",
        "error.internal":         "Erro interno no servidor. Tente novamente.",
    },
    en: {
        "error.no_match":       "No matches found. Please check if the region is correct.",
        "error.account_not_found":"Account not found. Please check the name and tag.",
        "error.internal":         "Internal server error. Please try again.",
    },
};

const PROGRESS_STRINGS = {
    pt: {
        "progress.starting":   "Iniciando...",
        "progress.account":    "Buscando conta...",
        "progress.collecting": "Analisando partidas...",
        "progress.processing": "Processando estatísticas...",
        "progress.done":       "Concluído!",
    },
    en: {
        "progress.starting":   "Starting...",
        "progress.account":    "Fetching account...",
        "progress.collecting": "Analyzing matches...",
        "progress.processing": "Processing statistics...",
        "progress.done":       "Done!",
    },
};

export function translateError(key) {
    const lang   = getCurrentLang();
    const strings = ERROR_STRINGS[lang] || ERROR_STRINGS.pt;
    return strings[key] || key; // fallback: mostra a chave se não encontrar
}

export function translateProgress(key) {
    const lang    = getCurrentLang();
    const strings = PROGRESS_STRINGS[lang] || PROGRESS_STRINGS.pt;
    return strings[key] || key;
}

export function setLanguage(lang) {
    const previous = localStorage.getItem(I18N_KEY);
    localStorage.setItem(I18N_KEY, lang);
    document.documentElement.lang = lang === "pt" ? "pt-BR" : "en";

    // Textos estáticos
    document.querySelectorAll("[data-pt]").forEach(el => {
        el.textContent = lang === "pt" ? el.dataset.pt : el.dataset.en;
    });

    // Placeholders
    document.querySelectorAll("[data-pt-placeholder]").forEach(el => {
        el.placeholder = lang === "pt" ? el.dataset.ptPlaceholder : el.dataset.enPlaceholder;
    });

    // Tooltips dos ícones ?
    document.querySelectorAll("[data-pt-tooltip]").forEach(el => {
        el.dataset.tooltip = lang === "pt" ? el.dataset.ptTooltip : el.dataset.enTooltip;
    });

    // Marca o botão ativo dentro do dropdown
    document.querySelectorAll(".lang-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.lang === lang);
    });

    // No dashboard, recarrega quando o idioma é trocado pelo usuário
    // (gráficos e insights dinâmicos precisam ser reconstruídos)
    const isDashboard = !!document.getElementById("section-general");
    const isUserAction = previous !== null && previous !== lang;
    if (isDashboard && isUserAction) {
        window.location.reload();
    }
}

export function getCurrentLang() {
    return localStorage.getItem(I18N_KEY) || "pt";
}

export function initI18n() {
    const globeBtn = document.getElementById("langGlobeBtn");
    const dropdown = document.getElementById("langDropdown");

    // Abre/fecha dropdown ao clicar no globo
    if (globeBtn && dropdown) {
        globeBtn.addEventListener("click", e => {
            e.stopPropagation();
            dropdown.classList.toggle("open");
        });

        // Fecha ao clicar fora
        document.addEventListener("click", () => dropdown.classList.remove("open"));
    }

    // Listeners nos botões de idioma
    document.querySelectorAll(".lang-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            setLanguage(btn.dataset.lang);
            if (dropdown) dropdown.classList.remove("open");
        });
    });

    // Aplica o idioma salvo
    setLanguage(getCurrentLang());
}