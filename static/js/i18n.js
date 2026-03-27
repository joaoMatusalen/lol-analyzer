// ================================================================
//  i18n — Language switching: Portuguese (PT-BR) / English (EN)
//
//  Usage in HTML:
//    data-pt="Texto PT"  data-en="Text EN"       → static text nodes
//    data-pt-placeholder  data-en-placeholder     → input placeholders
//    data-pt-tooltip      data-en-tooltip         → .classic-info-icon tooltips
// ================================================================

// localStorage key used to persist the user's language preference
const I18N_KEY = "lolanalyzer_lang";

// Localised strings for API/job error codes returned as i18n keys
const ERROR_STRINGS = {
    pt: {
        "error.no_match":          "Nenhuma partida encontrada. Verifique se a região está correta.",
        "error.account_not_found": "Conta não encontrada. Verifique o nome e a tag.",
        "error.internal":          "Erro interno no servidor. Tente novamente.",
    },
    en: {
        "error.no_match":          "No matches found. Please check if the region is correct.",
        "error.account_not_found": "Account not found. Please check the name and tag.",
        "error.internal":          "Internal server error. Please try again.",
    },
};

// Localised strings for job progress step keys sent by the backend
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

/**
 * Translates an error i18n key to the user's current language.
 * Falls back to the raw key string if no translation is found.
 *
 * @param {string} key - Error key (e.g. "error.no_match").
 * @returns {string} Localised error message.
 */
export function translateError(key) {
    const lang    = getCurrentLang();
    const strings = ERROR_STRINGS[lang] || ERROR_STRINGS.pt;
    return strings[key] || key;
}

/**
 * Translates a progress step i18n key to the user's current language.
 * Falls back to the raw key string if no translation is found.
 *
 * @param {string} key - Progress key (e.g. "progress.collecting").
 * @returns {string} Localised progress message.
 */
export function translateProgress(key) {
    const lang    = getCurrentLang();
    const strings = PROGRESS_STRINGS[lang] || PROGRESS_STRINGS.pt;
    return strings[key] || key;
}

/**
 * Applies the given language to all localised DOM elements and persists
 * the choice to localStorage.
 *
 * On the dashboard, a language change triggers a full page reload so that
 * dynamically rendered charts and text blocks are rebuilt in the new locale.
 *
 * @param {string} lang - Language code: "pt" or "en".
 */
export function setLanguage(lang) {
    const previous = localStorage.getItem(I18N_KEY);
    localStorage.setItem(I18N_KEY, lang);
    document.documentElement.lang = lang === "pt" ? "pt-BR" : "en";

    // Update static text nodes with data-pt / data-en attributes
    document.querySelectorAll("[data-pt]").forEach(el => {
        el.textContent = lang === "pt" ? el.dataset.pt : el.dataset.en;
    });

    // Update input placeholders
    document.querySelectorAll("[data-pt-placeholder]").forEach(el => {
        el.placeholder = lang === "pt" ? el.dataset.ptPlaceholder : el.dataset.enPlaceholder;
    });

    // Update tooltip text on info icons
    document.querySelectorAll("[data-pt-tooltip]").forEach(el => {
        el.dataset.tooltip = lang === "pt" ? el.dataset.ptTooltip : el.dataset.enTooltip;
    });

    // Highlight the active language button in the dropdown
    document.querySelectorAll(".lang-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.lang === lang);
    });

    // Reload the dashboard when the user actively switches language,
    // so all dynamic content (charts, insights) is rebuilt in the new locale
    const isDashboard  = !!document.getElementById("section-general");
    const isUserAction = previous !== null && previous !== lang;
    if (isDashboard && isUserAction) {
        window.location.reload();
    }
}

/**
 * Returns the active language code from localStorage.
 * Defaults to "pt" if no preference has been saved yet.
 *
 * @returns {"pt" | "en"}
 */
export function getCurrentLang() {
    return localStorage.getItem(I18N_KEY) || "pt";
}

/**
 * Initialises the language switcher UI and applies the saved language preference.
 *
 * Wires up the globe button to toggle the dropdown, closes it on outside clicks,
 * and attaches click handlers to each language button.
 */
export function initI18n() {
    const globeBtn = document.getElementById("langGlobeBtn");
    const dropdown = document.getElementById("langDropdown");

    // Toggle the dropdown when the globe icon is clicked
    if (globeBtn && dropdown) {
        globeBtn.addEventListener("click", e => {
            e.stopPropagation();
            dropdown.classList.toggle("open");
        });

        // Close the dropdown when clicking anywhere outside it
        document.addEventListener("click", () => dropdown.classList.remove("open"));
    }

    // Attach language-switch handlers to each button in the dropdown
    document.querySelectorAll(".lang-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            setLanguage(btn.dataset.lang);
            if (dropdown) dropdown.classList.remove("open");
        });
    });

    // Apply the persisted (or default) language on page load
    setLanguage(getCurrentLang());
}