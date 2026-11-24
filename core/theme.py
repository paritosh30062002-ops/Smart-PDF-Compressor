"""Glass theme: static stylesheet, instant theme switch, and the smooth first-load reveal."""
import streamlit as st

_THEME_DARK = {
    "bg-1": "#04060d", "bg-2": "#0a1020", "bg-3": "#05080f",
    "blob-a": "rgba(56, 189, 248, 0.20)", "blob-b": "rgba(168, 85, 247, 0.22)", "blob-c": "rgba(16, 185, 129, 0.13)",
    "fg": "#f8fafc", "fg-muted": "#a8b4c7",
    "surface": "rgba(15, 23, 42, 0.62)", "surface-hover": "rgba(22, 32, 54, 0.78)",
    "border": "rgba(148, 163, 184, 0.20)", "border-hover": "rgba(125, 211, 252, 0.45)",
    "highlight": "rgba(255, 255, 255, 0.06)",
    "shadow-c": "rgba(0, 0, 0, 0.60)", "lift-c": "rgba(56, 189, 248, 0.28)",
    "input-bg": "rgba(10, 16, 32, 0.85)",
    "btn-bg": "rgba(30, 41, 59, 0.70)", "btn-hover": "rgba(51, 65, 85, 0.90)", "btn-fg": "#f8fafc",
    "acc-1": "#38bdf8", "acc-2": "#a855f7", "pbtn-1": "#0284c7", "pbtn-2": "#7c3aed",
    "term-1": "rgba(8, 13, 27, 0.92)", "term-2": "rgba(4, 8, 16, 0.96)", "term-border": "rgba(125, 211, 252, 0.26)",
    "succ-bg": "rgba(16, 185, 129, 0.14)", "succ-border": "rgba(52, 211, 153, 0.40)", "succ-fg": "#ecfdf5",
    "err-bg": "rgba(248, 113, 113, 0.14)", "err-border": "rgba(248, 113, 113, 0.45)", "err-fg": "#fee2e2",
    "warn-bg": "rgba(251, 191, 36, 0.13)", "warn-border": "rgba(251, 191, 36, 0.45)", "warn-fg": "#fef3c7",
    "info-bg": "rgba(56, 189, 248, 0.13)", "info-border": "rgba(56, 189, 248, 0.42)", "info-fg": "#e0f2fe",
    "delta-bg": "rgba(16, 185, 129, 0.18)", "delta-fg": "#6ee7b7",
    "chip-bg": "rgba(30, 41, 59, 0.80)", "chip-fg": "#f8fafc",
    "ring": "#64748b", "active": "#38bdf8", "active-bg": "rgba(56, 189, 248, 0.14)",
    "code-bg": "rgba(8, 13, 27, 0.92)", "code-fg": "#f8fafc",
    "toolbar-bg": "rgba(30, 41, 59, 0.92)", "toolbar-fg": "#f8fafc",
    "track": "rgba(148, 163, 184, 0.16)", "scroll": "rgba(148, 163, 184, 0.30)",
}

_THEME_LIGHT = {
    "bg-1": "#eef2ff", "bg-2": "#f8fafc", "bg-3": "#e2e8f0",
    "blob-a": "rgba(59, 130, 246, 0.16)", "blob-b": "rgba(139, 92, 246, 0.15)", "blob-c": "rgba(16, 185, 129, 0.10)",
    "fg": "#0f172a", "fg-muted": "#475569",
    "surface": "rgba(255, 255, 255, 0.70)", "surface-hover": "rgba(255, 255, 255, 0.92)",
    "border": "rgba(15, 23, 42, 0.12)", "border-hover": "rgba(37, 99, 235, 0.40)",
    "highlight": "rgba(255, 255, 255, 0.70)",
    "shadow-c": "rgba(15, 23, 42, 0.20)", "lift-c": "rgba(37, 99, 235, 0.28)",
    "input-bg": "rgba(255, 255, 255, 0.92)",
    "btn-bg": "rgba(255, 255, 255, 0.85)", "btn-hover": "#ffffff", "btn-fg": "#0f172a",
    "acc-1": "#2563eb", "acc-2": "#7c3aed", "pbtn-1": "#2563eb", "pbtn-2": "#6d28d9",
    "term-1": "rgba(15, 23, 42, 0.95)", "term-2": "rgba(9, 13, 24, 0.98)", "term-border": "rgba(99, 102, 241, 0.32)",
    "succ-bg": "rgba(16, 185, 129, 0.12)", "succ-border": "rgba(5, 150, 105, 0.32)", "succ-fg": "#064e3b",
    "err-bg": "rgba(254, 226, 226, 0.85)", "err-border": "rgba(220, 38, 38, 0.35)", "err-fg": "#7f1d1d",
    "warn-bg": "rgba(254, 243, 199, 0.85)", "warn-border": "rgba(217, 119, 6, 0.35)", "warn-fg": "#78350f",
    "info-bg": "rgba(224, 242, 254, 0.85)", "info-border": "rgba(37, 99, 235, 0.32)", "info-fg": "#1e3a8a",
    "delta-bg": "rgba(16, 185, 129, 0.14)", "delta-fg": "#047857",
    "chip-bg": "rgba(255, 255, 255, 0.92)", "chip-fg": "#0f172a",
    "ring": "#94a3b8", "active": "#2563eb", "active-bg": "rgba(37, 99, 235, 0.10)",
    "code-bg": "rgba(15, 23, 42, 0.92)", "code-fg": "#f8fafc",
    "toolbar-bg": "rgba(255, 255, 255, 0.95)", "toolbar-fg": "#0f172a",
    "track": "rgba(15, 23, 42, 0.08)", "scroll": "rgba(15, 23, 42, 0.22)",
}


def _build_theme_css() -> str:
    # Every colour is a registered custom property (@property), so the browser can
    # interpolate it. The stylesheet itself never changes between reruns; switching
    # theme only flips a tiny flag element, and :root:has(.theme-flag-light) swaps
    # the variable values -> colours (even inside gradients) glide instead of blinking.
    # (No @property registrations: colours switch instantly now, and a "<" inside the CSS
    #  would make st.html's sanitizer drop the whole stylesheet.)
    props = ""
    dark_vars = "\n".join(f"    --{k}: {v};" for k, v in _THEME_DARK.items())
    light_vars = "\n".join(f"    --{k}: {v};" for k, v in _THEME_LIGHT.items())

    return (
        "<style>\n"
        "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=optional');\n"
        + props
        + "\n:root {\n"
        + dark_vars
        + "\n    --slider-hue: -155deg;\n"
        + "    --ease: cubic-bezier(0.22, 1, 0.36, 1);\n"
        + "    interpolate-size: allow-keywords;\n"
        + "}\n"
        # Instant: react to the Theme radio itself (no wait for the server rerun).
        + ":root:has([role='radiogroup'][aria-label='Theme'] > :nth-child(2) input:checked),\n"
        # Fallback for Streamlit versions whose radio DOM differs: server-side flag.
        + ":root:not(:has([role='radiogroup'][aria-label='Theme'] input)):has(.theme-flag-light) {\n"
        + light_vars
        + "\n    --slider-hue: -133deg;\n}\n"
        + _STATIC_CSS
        + "\n</style>"
    )


_STATIC_CSS = """
/* ---------- Keyframes ---------- */
@keyframes fadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes slideInLog { from { opacity: 0; transform: translateX(-8px); } to { opacity: 1; transform: none; } }
@keyframes blobDrift {
    0%   { transform: translate3d(0, 0, 0) scale(1); }
    33%  { transform: translate3d(3%, -2%, 0) scale(1.05); }
    66%  { transform: translate3d(-2%, 3%, 0) scale(0.97); }
    100% { transform: translate3d(0, 0, 0) scale(1); }
}
@keyframes shimmerText { 0% { background-position: 0% 50%; } 100% { background-position: 200% 50%; } }
@keyframes pulseDot {
    0%   { box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.65); }
    70%  { box-shadow: 0 0 0 8px rgba(52, 211, 153, 0); }
    100% { box-shadow: 0 0 0 0 rgba(52, 211, 153, 0); }
}
@keyframes progressStripes { from { background-position: 0 0, 0 0; } to { background-position: 40px 0, 0 0; } }
@keyframes popIn { 0% { opacity: 0; transform: scale(0.96) translateY(6px); } 100% { opacity: 1; transform: none; } }
@keyframes checkPop { 0% { transform: scale(0.3); opacity: 0; } 100% { transform: scale(1); opacity: 1; } }

/* ---------- Base / Background ---------- */
html, body, .stApp {
    background: linear-gradient(145deg, var(--bg-1) 0%, var(--bg-2) 55%, var(--bg-3) 100%) !important;
    color: var(--fg) !important;
    font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif !important;
    -webkit-font-smoothing: antialiased;
}
.stApp::before {
    content: "";
    position: fixed;
    inset: -10%;
    pointer-events: none;
    z-index: 0;
    background:
        radial-gradient(circle at 12% 14%, var(--blob-a), transparent 36%),
        radial-gradient(circle at 86% 12%, var(--blob-b), transparent 40%),
        radial-gradient(circle at 50% 96%, var(--blob-c), transparent 45%);
}
[data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: transparent !important;
    position: relative;
    z-index: 1;
}
[data-testid="stHeader"] { background: transparent !important; height: 2rem !important; }
.block-container, [data-testid="stMainBlockContainer"] {
    padding-top: 2.2rem !important;
    padding-bottom: 2rem !important;
}

/* ---------- Load: everything appears together ----------
   Content stays invisible while Streamlit streams the first run element by element.
   signal_app_ready() (last line of the script) adds .app-ready -> one smooth fade-in.
   Safety net: if that signal never arrives, content reveals itself after 2.5s anyway. */
@keyframes safetyReveal { to { opacity: 1; transform: none; } }
html:not(.app-ready) .block-container,
html:not(.app-ready) [data-testid="stMainBlockContainer"] {
    opacity: 0;
    transform: translateY(6px);
    animation: safetyReveal 0.35s ease-out 2.5s forwards;
}
html.app-ready .block-container,
html.app-ready [data-testid="stMainBlockContainer"] {
    opacity: 1;
    transform: none;
    transition: opacity 0.35s ease-out, transform 0.35s var(--ease) !important;
}

/* ---------- No "stale" dimming during reruns (main cause of flicker) ---------- */
[data-stale="true"], .stale-element,
[data-testid="stElementContainer"][data-stale="true"],
.element-container[data-stale="true"] {
    opacity: 1 !important;
    filter: none !important;
    transition: none !important;
}

/* ---------- Instant theme switch ----------
   Colours (incl. Streamlit's own widget transitions) never animate, so one click = whole UI
   switches in the same frame. Only motion properties keep their smooth transitions. */
.stApp *, .stApp *::before, .stApp *::after {
    transition-property: transform, opacity, background-position, width, block-size, content-visibility !important;
}

/* ---------- Helper elements (style / theme flag / script iframe) take no space ---------- */
[data-testid="stElementContainer"]:has(.glass-css-anchor),
[data-testid="stElementContainer"]:has(> [data-testid="stHtml"] .glass-css-anchor),
[data-testid="stElementContainer"]:has(.theme-flag),
[data-testid="stElementContainer"]:has(.app-ready-signal),
[data-testid="stElementContainer"]:has(iframe[height="0"]),
.element-container:has(.glass-css-anchor),
.element-container:has(.theme-flag),
.element-container:has(iframe[height="0"]) {
    position: absolute !important;
    width: 0 !important;
    height: 0 !important;
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* ---------- Mount animation for elements that appear after an action ---------- */
html.app-settled [data-testid="stElementContainer"]:has(> [data-testid="stTextInput"]),
html.app-settled [data-testid="stElementContainer"]:has(> .stTextInput),
html.app-settled [data-testid="stElementContainer"]:has(> [data-testid="stCheckbox"]),
html.app-settled [data-testid="stElementContainer"]:has(> .stCheckbox),
html.app-settled [data-testid="stElementContainer"]:has(.glass-selection-strip),
html.app-settled [data-testid="stElementContainer"]:has(> [data-testid="stAlert"]),
html.app-settled [data-testid="stElementContainer"]:has(> .stAlert),
html.app-settled [data-testid="stElementContainer"]:has(> [data-testid="stDownloadButton"]),
html.app-settled [data-testid="stElementContainer"]:has(> .stDownloadButton) {
    animation: fadeUp 0.4s var(--ease) backwards;
}

/* Custom scrollbars */
.stApp ::-webkit-scrollbar { width: 8px; height: 8px; }
.stApp ::-webkit-scrollbar-track { background: transparent; }
.stApp ::-webkit-scrollbar-thumb { background: var(--scroll); border-radius: 999px; }
.stApp ::-webkit-scrollbar-thumb:hover { background: var(--acc-1); }

/* ---------- Hero title ---------- */

.hero-title {
    margin: 0;
    font-size: 1.9rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    line-height: 1.15;
    background: linear-gradient(90deg, var(--fg) 0%, var(--acc-1) 35%, var(--acc-2) 65%, var(--fg) 100%);
    background-size: 200% auto;
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: shimmerText 8s linear infinite;
}
.hero-badge {
    display: inline-flex;
    align-items: center;
    margin-left: 10px;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    vertical-align: middle;
    background: var(--active-bg);
    border: 1px solid var(--border-hover);
    color: var(--acc-1) !important;
    -webkit-text-fill-color: var(--acc-1);
}

/* ---------- Text contrast ---------- */
.stApp h1, .stApp h2, .stApp h3, .stApp h4,
.stApp label, .stApp p, .stApp span, .stApp .stMarkdown { color: var(--fg) !important; }
.stApp .hero-title { color: transparent !important; }
.stApp .stCaption, .stApp [data-testid="stCaptionContainer"] * { color: var(--fg-muted) !important; }
.stApp [data-testid="stWidgetLabel"], .stApp [data-testid="stWidgetLabel"] * {
    color: var(--fg) !important;
    font-weight: 600 !important;
    letter-spacing: -0.005em;
}

/* ---------- Radio pills ---------- */
.stApp [data-testid="stRadio"] [role="radiogroup"] { gap: 8px !important; flex-wrap: wrap !important; }
.stApp [data-testid="stRadio"] [role="radiogroup"] label {
    color: var(--fg) !important;
    background-color: var(--surface) !important;
    border: 1px solid var(--border) !important;
    padding: 6px 12px !important;
    border-radius: 12px !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    cursor: pointer;
    transition: transform 0.2s var(--ease) !important;
}
.stApp [data-testid="stRadio"] [role="radiogroup"] label:hover {
    border-color: var(--border-hover) !important;
    transform: translateY(-1px);
}
.stApp [data-testid="stRadio"] [role="radiogroup"] label:active { transform: scale(0.97); }
.stApp [data-testid="stRadio"] [role="radiogroup"] label p,
.stApp [data-testid="stRadio"] [role="radiogroup"] label span { color: var(--fg) !important; font-weight: 500 !important; }
.stApp [data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) {
    background-color: var(--active-bg) !important;
    border-color: var(--active) !important;
    box-shadow: 0 0 0 3px var(--active-bg), 0 6px 18px -8px var(--active) !important;
}
.stApp [data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) p,
.stApp [data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) span { font-weight: 700 !important; }

/* Radio ring + animated inner dot (new DOM: label > div > div:first-child; older: label > div:first-child) */
.stApp [data-testid="stRadioOption"] > div > div:first-child,
.stApp [data-testid="stRadio"] [role="radiogroup"] label > div:first-child:not(:has(p)) {
    background-color: transparent !important;
    border: 2px solid var(--ring) !important;
    border-radius: 50% !important;
    width: 16px !important; height: 16px !important;
    min-width: 16px !important; min-height: 16px !important;
    box-sizing: border-box !important;
    display: flex !important; align-items: center !important; justify-content: center !important;
    
}
.stApp [data-testid="stRadioOption"] > div > div:first-child > div {
    background: #ffffff !important;
    width: 6px !important; height: 6px !important;
    border-radius: 50% !important;
    transform: scale(0);
    transition: transform 0.3s var(--ease) !important;
}
.stApp [data-testid="stRadioOption"]:has(input:checked) > div > div:first-child,
.stApp [data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) > div:first-child:not(:has(p)) {
    background-color: var(--acc-1) !important;
    border-color: var(--acc-1) !important;
    box-shadow: 0 0 10px -2px var(--active) !important;
}
.stApp [data-testid="stRadioOption"]:has(input:checked) > div > div:first-child > div { transform: scale(1); }

/* ---------- Checkbox ---------- */
.stApp [data-testid="stCheckbox"] label,
.stApp [data-testid="stCheckbox"] label div,
.stApp [data-testid="stCheckbox"] label span { color: var(--fg) !important; background-color: transparent !important; }
.stApp [data-testid="stCheckbox"] label > span + div {
    border: 1.5px solid var(--ring) !important;
    border-radius: 6px !important;
    background-color: var(--input-bg) !important;
    transition: transform 0.15s var(--ease) !important;
}
.stApp [data-testid="stCheckbox"] label:hover > span + div { border-color: var(--acc-1) !important; }
.stApp [data-testid="stCheckbox"] label:active > span + div { transform: scale(0.9); }
.stApp [data-testid="stCheckbox"] label:has(input:checked) > span + div {
    background-color: var(--acc-1) !important;
    border-color: var(--acc-1) !important;
    box-shadow: 0 0 10px -2px var(--active) !important;
}
.stApp [data-testid="stCheckbox"] label:has(input:checked) > span + div svg {
    animation: checkPop 0.25s var(--ease) both;
}

/* ---------- Inputs ---------- */
.stApp input, .stApp textarea,
.stApp [data-baseweb="input"], .stApp [data-baseweb="input"] > div, .stApp [data-baseweb="base-input"] {
    background-color: var(--input-bg) !important;
    color: var(--fg) !important;
    border-color: var(--border) !important;
    border-radius: 11px !important;
}
.stApp [data-baseweb="input"], .stApp [data-testid="stNumberInputContainer"], .stApp [data-testid="stTextInputRootElement"] {
    
}
.stApp [data-baseweb="input"]:focus-within,
.stApp [data-testid="stTextInputRootElement"]:focus-within,
.stApp [data-testid="stNumberInputContainer"]:focus-within {
    border-color: var(--acc-1) !important;
    box-shadow: 0 0 0 3px var(--active-bg) !important;
}
.stApp [data-testid="stNumberInputContainer"] {
    background-color: var(--input-bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 11px !important;
    overflow: hidden;
}
.stApp [data-testid="stNumberInputContainer"] input { background-color: transparent !important; border: none !important; }
.stApp [data-testid="stNumberInput"] button {
    background-color: var(--btn-bg) !important;
    color: var(--btn-fg) !important;
    border-color: var(--border) !important;
    
}
.stApp [data-testid="stNumberInput"] button * { background: transparent !important; color: var(--btn-fg) !important; }
.stApp [data-testid="stNumberInput"] button:hover { background-color: var(--btn-hover) !important; }

/* Text input container (also neutralises Streamlit's dark-base border) */
.stApp [data-testid="stTextInputRootElement"] {
    background-color: var(--input-bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 11px !important;
    overflow: hidden;
}
.stApp [data-testid="stTextInputRootElement"] > div,
.stApp [data-testid="stTextInputRootElement"] input { background-color: transparent !important; border: none !important; }

/* Slider: re-tint Streamlit's red to the accent hue (angle animates on theme switch) */
.stApp [data-testid="stSlider"] [role="group"],
.stApp [data-testid="stSlider"] [data-baseweb="slider"] { filter: hue-rotate(var(--slider-hue)) saturate(1.15); }
.stApp [data-testid="stSlider"] [role="group"] [style*="translate(-50%"],
.stApp [data-testid="stSlider"] [role="slider"] {
    box-shadow: 0 0 0 4px rgba(197, 57, 72, 0.18), 0 4px 12px rgba(0, 0, 0, 0.25) !important;
    
}
.stApp [data-testid="stSlider"] [role="group"] [style*="translate(-50%"]:hover,
.stApp [data-testid="stSlider"] [role="slider"]:hover {
    box-shadow: 0 0 0 8px rgba(197, 57, 72, 0.22), 0 4px 14px rgba(0, 0, 0, 0.3) !important;
}

/* ---------- File uploader ---------- */
.stApp [data-testid="stFileUploader"],
.stApp [data-testid="stFileUploader"] section,
.stApp [data-testid="stFileUploaderDropzone"],
.stApp [data-testid="stFileUploaderDropzone"] > div {
    background-color: var(--surface) !important;
    color: var(--fg) !important;
    border-radius: 16px !important;
}
.stApp [data-testid="stFileUploaderDropzone"] {
    border: 1.5px dashed var(--border) !important;
    padding: 20px !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    box-shadow: inset 0 1px 0 var(--highlight), 0 10px 30px -14px var(--shadow-c) !important;
    transition: transform 0.3s var(--ease) !important;
}
.stApp [data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--acc-1) !important;
    background-color: var(--surface-hover) !important;
    box-shadow: inset 0 1px 0 var(--highlight), 0 18px 40px -16px var(--lift-c) !important;
    transform: translateY(-2px);
}
.stApp [data-testid="stFileUploaderDropzone"] * { color: var(--fg) !important; }
.stApp [data-testid="stFileUploaderDropzone"] button {
    background: var(--btn-bg) !important;
    color: var(--btn-fg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    transition: transform 0.2s var(--ease) !important;
}
.stApp [data-testid="stFileUploaderDropzone"] button * { background: transparent !important; border: none !important; color: var(--btn-fg) !important; }
.stApp [data-testid="stFileUploaderDropzone"] button:hover { border-color: var(--acc-1) !important; transform: translateY(-1px); }

.stApp [data-testid="stFileUploaderFile"],
.stApp [data-testid="stFileUploaderFile"] > div,
.stApp [data-testid="stFileUploaderFile"] > div > div,
.stApp [data-testid="stFileUploaderFileData"],
.stApp [data-testid="stFileUploaderFileData"] > div {
    background-color: var(--chip-bg) !important;
    color: var(--chip-fg) !important;
    border-color: var(--border) !important;
}
.stApp [data-testid="stFileUploaderFile"] { border-radius: 12px !important; animation: popIn 0.35s var(--ease) both; }
.stApp [data-testid="stFileUploaderFile"] div,
.stApp [data-testid="stFileUploaderFile"] span,
.stApp [data-testid="stFileUploaderFile"] small,
.stApp [data-testid="stFileUploaderFileName"], .stApp [data-testid="stFileUploaderFileName"] *,
.stApp [data-testid="stFileUploaderFileSize"], .stApp [data-testid="stFileUploaderFileSize"] * {
    background-color: transparent !important;
    color: var(--chip-fg) !important;
    opacity: 1 !important;
}

/* File chips (newer Streamlit) */
.stApp [data-testid="stFileChip"] {
    background-color: var(--chip-bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    animation: popIn 0.35s var(--ease) both;
    transition: transform 0.2s var(--ease) !important;
}
.stApp [data-testid="stFileChip"]:hover {
    border-color: var(--border-hover) !important;
    transform: translateY(-1px);
    box-shadow: 0 10px 24px -14px var(--lift-c) !important;
}
.stApp [data-testid="stFileChip"] > div:first-child {
    background-color: var(--active-bg) !important;
    border-radius: 8px !important;
}
.stApp [data-testid="stFileChip"] > div:first-child,
.stApp [data-testid="stFileChip"] > div:first-child * { color: var(--acc-1) !important; }

/* ---------- Code block ---------- */
.stApp [data-testid="stCode"], .stApp [data-testid="stCode"] > div, .stApp [data-testid="stCode"] pre, .stApp [data-testid="stCode"] code,
.stApp [data-testid="stCodeBlock"], .stApp [data-testid="stCodeBlock"] > div, .stApp [data-testid="stCodeBlock"] pre, .stApp [data-testid="stCodeBlock"] code {
    background-color: var(--code-bg) !important;
    color: var(--code-fg) !important;
    border-color: var(--border) !important;
    font-family: 'JetBrains Mono', ui-monospace, monospace !important;
    border-radius: 12px !important;
}
.stApp [data-testid="stCode"] span, .stApp [data-testid="stCodeBlock"] span { color: var(--code-fg) !important; }
.stApp [data-testid="stCode"] button, .stApp [data-testid="stCodeBlock"] button {
    background-color: var(--btn-bg) !important;
    color: var(--btn-fg) !important;
    border-color: var(--border) !important;
}
.stApp [data-testid="stCode"] button *, .stApp [data-testid="stCodeBlock"] button * { background: transparent !important; color: var(--btn-fg) !important; }

/* ---------- Dataframe & toolbar ---------- */
.stApp [data-testid="stDataFrame"] { border-radius: 12px !important; overflow: hidden; border: 1px solid var(--border) !important; }
.stApp [data-testid="stElementToolbar"], .stApp [data-testid="stElementToolbar"] > div {
    background-color: var(--toolbar-bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
}
.stApp [data-testid="stElementToolbar"] button, .stApp [data-testid="stElementToolbar"] button *,
.stApp [data-testid="stElementToolbar"] a, .stApp [data-testid="stElementToolbar"] a * { color: var(--toolbar-fg) !important; opacity: 1 !important; }

/* ---------- Selection strip ---------- */
.glass-selection-strip {
    margin-top: 8px;
    padding: 10px 14px;
    border-radius: 12px;
    background: var(--chip-bg);
    border: 1px solid var(--border);
    border-left: 3px solid var(--acc-1);
    color: var(--chip-fg) !important;
    font-size: 0.88rem;
    line-height: 1.45;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: 0 10px 30px -14px var(--shadow-c);
}
.glass-selection-strip strong { color: var(--fg) !important; }

/* ---------- Alerts ---------- */
.stApp [data-testid="stAlert"], .stApp [data-testid="stAlert"] > div {
    background-color: var(--succ-bg) !important;
    backdrop-filter: blur(14px) !important;
    -webkit-backdrop-filter: blur(14px) !important;
    border: 1px solid var(--succ-border) !important;
    border-radius: 14px !important;
    color: var(--succ-fg) !important;
}
.stApp [data-testid="stAlert"] * { color: var(--succ-fg) !important; }
.stApp [data-testid="stAlert"]:has([data-testid="stAlertContentError"]),
.stApp [data-testid="stAlert"]:has([data-testid="stAlertContentError"]) > div { background-color: var(--err-bg) !important; border-color: var(--err-border) !important; }
.stApp [data-testid="stAlert"]:has([data-testid="stAlertContentError"]) * { color: var(--err-fg) !important; }
.stApp [data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]),
.stApp [data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]) > div { background-color: var(--warn-bg) !important; border-color: var(--warn-border) !important; }
.stApp [data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]) * { color: var(--warn-fg) !important; }
.stApp [data-testid="stAlert"]:has([data-testid="stAlertContentInfo"]),
.stApp [data-testid="stAlert"]:has([data-testid="stAlertContentInfo"]) > div { background-color: var(--info-bg) !important; border-color: var(--info-border) !important; }
.stApp [data-testid="stAlert"]:has([data-testid="stAlertContentInfo"]) * { color: var(--info-fg) !important; }
.stApp [data-testid="stAlert"] code { background: rgba(127, 127, 127, 0.18) !important; border-radius: 6px !important; padding: 1px 6px !important; }

/* ---------- Buttons ---------- */
.stApp .stButton > button, .stApp .stDownloadButton > button {
    background-color: var(--btn-bg) !important;
    color: var(--btn-fg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em;
    min-height: 2.6rem;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    box-shadow: inset 0 1px 0 var(--highlight), 0 10px 30px -14px var(--shadow-c) !important;
    transition: transform 0.2s var(--ease), opacity 0.3s var(--ease) !important;
}
.stApp .stButton > button *, .stApp .stDownloadButton > button * { color: var(--btn-fg) !important; }
.stApp .stButton > button:hover, .stApp .stDownloadButton > button:hover {
    background-color: var(--btn-hover) !important;
    border-color: var(--border-hover) !important;
    transform: translateY(-2px);
    box-shadow: inset 0 1px 0 var(--highlight), 0 18px 40px -16px var(--lift-c) !important;
}
.stApp .stButton > button:active, .stApp .stDownloadButton > button:active { transform: translateY(0) scale(0.98); transition-duration: 0.08s !important; }
.stApp .stButton > button[kind="primary"], .stApp .stDownloadButton > button[kind="primary"] {
    background-image: linear-gradient(120deg, var(--pbtn-1) 0%, var(--pbtn-2) 50%, var(--pbtn-1) 100%) !important;
    background-size: 200% auto !important;
    background-position: left center !important;
    color: #ffffff !important;
    border: 1px solid rgba(255, 255, 255, 0.22) !important;
    min-height: 3rem;
    font-size: 1rem !important;
    box-shadow: 0 10px 28px -10px var(--acc-2), inset 0 1px 0 rgba(255, 255, 255, 0.25) !important;
    transition: background-position 0.6s var(--ease), transform 0.2s var(--ease), opacity 0.3s var(--ease) !important;
}
.stApp .stButton > button[kind="primary"]:hover, .stApp .stDownloadButton > button[kind="primary"]:hover {
    background-position: right center !important;
    transform: translateY(-2px);
    box-shadow: 0 16px 36px -10px var(--acc-2), 0 0 0 3px var(--active-bg), inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
}
.stApp .stButton > button[kind="primary"] *, .stApp .stDownloadButton > button[kind="primary"] * { color: #ffffff !important; }
.stApp .stButton > button:disabled { opacity: 0.45 !important; transform: none !important; cursor: not-allowed !important; box-shadow: none !important; }

/* ---------- Progress bar ---------- */
.stApp [data-testid="stProgress"] [role="progressbar"] > div {
    background: var(--track) !important;
    border-radius: 999px !important;
    height: 8px !important;
    overflow: hidden;
}
.stApp [data-testid="stProgress"] [role="progressbar"] > div > div {
    background-color: var(--acc-1) !important;
    background-image:
        linear-gradient(45deg, rgba(255,255,255,0.18) 25%, transparent 25%, transparent 50%, rgba(255,255,255,0.18) 50%, rgba(255,255,255,0.18) 75%, transparent 75%, transparent),
        linear-gradient(90deg, var(--acc-1), var(--acc-2)) !important;
    background-size: 40px 40px, 100% 100% !important;
    border-radius: 999px !important;
    box-shadow: 0 0 14px var(--acc-1);
    animation: progressStripes 1s linear infinite;
    transition: width 0.45s var(--ease) !important;
}

/* ---------- Expander (smooth open / close) ---------- */
.stApp [data-testid="stExpander"], .stApp [data-testid="stExpander"] details, .stApp [data-testid="stExpander"] summary {
    background-color: var(--surface) !important;
    color: var(--fg) !important;
    border-color: var(--border) !important;
    border-radius: 14px !important;
}
.stApp [data-testid="stExpander"] details {
    backdrop-filter: blur(14px) !important;
    -webkit-backdrop-filter: blur(14px) !important;
    box-shadow: inset 0 1px 0 var(--highlight), 0 10px 30px -14px var(--shadow-c);
    
}
.stApp [data-testid="stExpander"] details:hover { border-color: var(--border-hover) !important; }
.stApp [data-testid="stExpander"] summary {  }
.stApp [data-testid="stExpander"] summary:hover { background-color: var(--surface-hover) !important; }
.stApp [data-testid="stExpander"] summary svg { transition: transform 0.3s var(--ease) !important; }
.stApp [data-testid="stExpander"] details::details-content {
    block-size: 0;
    overflow: hidden;
    opacity: 0;
    transition: block-size 0.4s var(--ease), opacity 0.3s var(--ease), content-visibility 0.4s allow-discrete !important;
}
.stApp [data-testid="stExpander"] details[open]::details-content { block-size: auto; opacity: 1; }
.stApp [data-testid="stExpander"] * { color: var(--fg) !important; }

/* ---------- Metrics ---------- */
.stApp [data-testid="stMetric"] {
    background-color: var(--surface) !important;
    backdrop-filter: blur(14px) !important;
    -webkit-backdrop-filter: blur(14px) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    padding: 14px 16px !important;
    box-shadow: inset 0 1px 0 var(--highlight), 0 10px 30px -14px var(--shadow-c);
    position: relative;
    overflow: hidden;
    animation: fadeUp 0.55s var(--ease) backwards;
    transition: transform 0.3s var(--ease) !important;
}
.stApp [data-testid="stMetric"]::after {
    content: "";
    position: absolute;
    left: 0; top: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--acc-1), var(--acc-2));
    opacity: 0.8;
}
.stApp [data-testid="stMetric"]:hover {
    transform: translateY(-3px);
    border-color: var(--border-hover) !important;
    box-shadow: inset 0 1px 0 var(--highlight), 0 18px 40px -16px var(--lift-c);
}
.stApp [data-testid="stColumn"]:nth-child(2) [data-testid="stMetric"] { animation-delay: 0.06s; }
.stApp [data-testid="stColumn"]:nth-child(3) [data-testid="stMetric"] { animation-delay: 0.12s; }
.stApp [data-testid="stColumn"]:nth-child(4) [data-testid="stMetric"] { animation-delay: 0.18s; }
.stApp [data-testid="stMetric"] [data-testid="stMetricLabel"], .stApp [data-testid="stMetric"] [data-testid="stMetricLabel"] * {
    color: var(--fg-muted) !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    font-size: 0.74rem !important;
    letter-spacing: 0.06em;
}
.stApp [data-testid="stMetric"] [data-testid="stMetricValue"], .stApp [data-testid="stMetric"] [data-testid="stMetricValue"] * {
    color: var(--fg) !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em;
}
.stApp [data-testid="stMetricDelta"], .stApp [data-testid="stMetricDelta"] * {
    background-color: var(--delta-bg) !important;
    color: var(--delta-fg) !important;
    border-radius: 8px !important;
    padding: 2px 6px !important;
    font-weight: 600 !important;
}

.stApp hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, var(--border-hover), transparent) !important;
    opacity: 0.6 !important;
}

/* ---------- Live Terminal ---------- */
.glass-term-topbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.glass-term-label { font-size: 0.95rem; font-weight: 700; color: var(--fg) !important; display: flex; align-items: center; gap: 9px; }
.live-dot { width: 8px; height: 8px; border-radius: 50%; background: #34d399; display: inline-block; animation: pulseDot 1.8s ease-out infinite; }
.live-pill {
    font-size: 11px; font-weight: 700; letter-spacing: 0.06em;
    padding: 3px 10px; border-radius: 999px;
    background: rgba(56, 189, 248, 0.16);
    border: 1px solid rgba(56, 189, 248, 0.36);
    color: var(--acc-1) !important;
    font-family: 'JetBrains Mono', ui-monospace, monospace;
}
.glass-terminal {
    position: relative;
    display: flex;
    flex-direction: column;
    background: linear-gradient(180deg, var(--term-1) 0%, var(--term-2) 100%) !important;
    border: 1px solid var(--term-border) !important;
    border-radius: 18px !important;
    padding: 40px 6px 10px 15px !important;
    font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace !important;
    font-size: 12.3px !important;
    line-height: 1.6 !important;
    height: 445px !important;
    overflow: hidden !important;
    color: #f8fafc !important;
    box-shadow: 0 20px 50px -18px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.07) !important;
}
.glass-terminal::before {
    content: "";
    position: absolute;
    top: 15px; left: 16px;
    width: 10px; height: 10px;
    border-radius: 50%;
    background: #f87171;
    box-shadow: 16px 0 0 #fbbf24, 32px 0 0 #34d399;
}
/* column-reverse keeps the newest log in view automatically */
.glass-terminal .term-scroll {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column-reverse;
    padding-right: 9px;
}
/* few logs -> stay at the top; many logs -> stay pinned to the newest one */
.glass-terminal .term-inner { margin-bottom: auto; }
.glass-terminal .log-row {
    padding: 7px 10px !important;
    margin-bottom: 6px !important;
    border-radius: 10px !important;
    background: rgba(255, 255, 255, 0.04) !important;
    border-left: 3px solid rgba(148, 163, 184, 0.45) !important;
    color: #f8fafc !important;
    word-break: break-word !important;
    transition: transform 0.2s var(--ease) !important;
}
.glass-terminal .log-row:hover { background-color: rgba(255, 255, 255, 0.08) !important; transform: translateX(2px); }
.glass-terminal .log-row:last-child { animation: slideInLog 0.35s var(--ease) both; }
.glass-terminal .log-msg { color: #f1f5f9 !important; }
.glass-terminal .log-row-more { color: #94a3b8 !important; font-style: italic; text-align: center; border-left-color: transparent !important; background: transparent !important; }
/* st.html wrapper: no extra spacing, isolate terminal repaints from the rest of the page */
.glass-terminal { contain: layout paint; }
.glass-terminal .term-scroll { overscroll-behavior: contain; }
.glass-terminal .log-row-INFO { border-left-color: #38bdf8 !important; }
.glass-terminal .log-row-OK { border-left-color: #34d399 !important; background: rgba(16, 185, 129, 0.10) !important; }
.glass-terminal .log-row-DONE { border-left-color: #c084fc !important; background: rgba(168, 85, 247, 0.13) !important; box-shadow: 0 0 18px -6px rgba(192, 132, 252, 0.6); }
.glass-terminal .log-row-WARN { border-left-color: #fbbf24 !important; background: rgba(251, 191, 36, 0.10) !important; }
.glass-terminal .log-row-ERROR { border-left-color: #f87171 !important; background: rgba(248, 113, 113, 0.12) !important; }
.glass-terminal .log-ts { color: #94a3b8 !important; font-size: 11.5px !important; }
.glass-terminal .log-badge { display: inline-block; padding: 1px 7px; border-radius: 6px; font-size: 10.5px; font-weight: 700; margin: 0 7px; letter-spacing: 0.04em; }
.glass-terminal .badge-INFO { background: rgba(56, 189, 248, 0.22); color: #e0f2fe !important; }
.glass-terminal .badge-OK { background: rgba(52, 211, 153, 0.22); color: #d1fae5 !important; }
.glass-terminal .badge-DONE { background: rgba(192, 132, 252, 0.26); color: #f3e8ff !important; }
.glass-terminal .badge-WARN { background: rgba(251, 191, 36, 0.24); color: #fef3c7 !important; }
.glass-terminal .badge-ERROR { background: rgba(248, 113, 113, 0.26); color: #fee2e2 !important; }

/* ===================== Shared app chrome (nav, user chip) ===================== */
.st-key-topnav [data-testid="stPageLink"] a,
.st-key-topnav [data-testid="stPageLink-NavLink"] {
    background-color: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 6px 14px !important;
    justify-content: center !important;
    transition: transform 0.2s var(--ease) !important;
}
.st-key-topnav [data-testid="stPageLink"] a:hover,
.st-key-topnav [data-testid="stPageLink-NavLink"]:hover { transform: translateY(-1px); border-color: var(--border-hover) !important; }
.st-key-topnav [data-testid="stPageLink"] a[aria-current="page"],
.st-key-topnav [data-testid="stPageLink-NavLink"][aria-current="page"] {
    background-color: var(--active-bg) !important;
    border-color: var(--active) !important;
}
.st-key-topnav [data-testid="stPageLink"] a[aria-current="page"] p,
.st-key-topnav [data-testid="stPageLink-NavLink"][aria-current="page"] p { font-weight: 700 !important; color: var(--acc-1) !important; }
.user-chip {
    display: flex; align-items: center; justify-content: flex-end; gap: 8px;
    font-size: 0.86rem; color: var(--fg-muted) !important; white-space: nowrap; overflow: hidden;
}
.user-chip b { color: var(--fg) !important; font-weight: 600; overflow: hidden; text-overflow: ellipsis; }
.plan-badge {
    display: inline-flex; align-items: center; padding: 2px 9px; border-radius: 999px;
    font-size: 0.7rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
    background: var(--active-bg); border: 1px solid var(--border-hover); color: var(--acc-1) !important;
}
.plan-badge.pro {
    background-image: linear-gradient(120deg, var(--pbtn-1), var(--pbtn-2));
    border-color: transparent; color: #ffffff !important;
}
.demo-banner {
    padding: 8px 14px; border-radius: 12px; margin-bottom: 10px; font-size: 0.85rem;
    background: var(--warn-bg); border: 1px solid var(--warn-border); color: var(--warn-fg) !important;
}

/* ===================== Glass cards (auth, pricing, account) ===================== */
[class*="st-key-glasscard"],
[class*="st-key-price_"] {
    background-color: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 18px !important;
    padding: 22px 22px 18px 22px !important;
    backdrop-filter: blur(14px) !important;
    -webkit-backdrop-filter: blur(14px) !important;
    box-shadow: inset 0 1px 0 var(--highlight), 0 14px 36px -18px var(--shadow-c) !important;
}
[class*="st-key-price_"] { height: 100%; transition: transform 0.25s var(--ease) !important; }
[class*="st-key-price_"]:hover { transform: translateY(-4px); border-color: var(--border-hover) !important; }
.st-key-price_pro_3k {
    border: 1.5px solid var(--acc-2) !important;
    box-shadow: 0 0 0 3px var(--active-bg), 0 18px 44px -18px var(--acc-2) !important;
}
.price-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 26px; }
.price-name { font-size: 1.15rem; font-weight: 800; color: var(--fg) !important; letter-spacing: -0.01em; }
.price-tag-pop {
    font-size: 0.68rem; font-weight: 700; letter-spacing: 0.06em; padding: 3px 9px; border-radius: 999px;
    background-image: linear-gradient(120deg, var(--pbtn-1), var(--pbtn-2)); color: #ffffff !important;
}
.price-tagline { font-size: 0.85rem; color: var(--fg-muted) !important; margin-top: 2px; }
.price-amount { margin-top: 14px; font-size: 2.3rem; font-weight: 800; letter-spacing: -0.03em; color: var(--fg) !important; line-height: 1.1; }
.price-amount small { font-size: 0.9rem; font-weight: 500; color: var(--fg-muted) !important; letter-spacing: 0; }
.price-inr { font-size: 0.92rem; font-weight: 600; color: var(--acc-1) !important; margin-top: 4px; }
.price-features { list-style: none; padding: 0; margin: 16px 0 6px 0; }
.price-features li { padding: 5px 0 5px 24px; position: relative; font-size: 0.9rem; color: var(--fg) !important; }
.price-features li::before {
    content: ""; position: absolute; left: 2px; top: 10px; width: 12px; height: 7px;
    border-left: 2px solid var(--acc-1); border-bottom: 2px solid var(--acc-1); transform: rotate(-45deg);
}
.rate-note { font-size: 0.78rem; color: var(--fg-muted) !important; text-align: center; margin-top: 6px; }

/* Usage meter */
.usage-box { margin: 2px 0 10px 0; }
.usage-head { display: flex; justify-content: space-between; font-size: 0.84rem; color: var(--fg-muted) !important; margin-bottom: 6px; }
.usage-head b { color: var(--fg) !important; }
.usage-track { height: 8px; border-radius: 999px; background: var(--track); overflow: hidden; }
.usage-fill { height: 100%; border-radius: 999px; background-image: linear-gradient(90deg, var(--acc-1), var(--acc-2)); transition: width 0.5s var(--ease) !important; }
.usage-fill.full { background-image: linear-gradient(90deg, #f59e0b, #ef4444); }
.quota-strip {
    display: flex; align-items: center; justify-content: space-between; gap: 12px;
    padding: 10px 14px; border-radius: 12px; margin-bottom: 12px;
    background: var(--chip-bg); border: 1px solid var(--border); border-left: 3px solid var(--acc-2);
    font-size: 0.88rem; color: var(--chip-fg) !important;
}
.quota-strip b { color: var(--fg) !important; }

/* Auth page */
.auth-hero { text-align: center; margin: 6px 0 18px 0; }
.auth-hero h2 { margin: 0 !important; font-size: 1.5rem !important; font-weight: 800 !important; letter-spacing: -0.02em; }
.auth-hero p { margin: 6px 0 0 0 !important; color: var(--fg-muted) !important; font-size: 0.92rem; }
.or-divider { display: flex; align-items: center; gap: 12px; margin: 14px 0 6px 0; font-size: 0.8rem; color: var(--fg-muted) !important; }
.or-divider::before, .or-divider::after { content: ""; flex: 1; height: 1px; background: var(--border); }
.st-key-google_login button {
    background-color: #ffffff !important;
    color: #1f2937 !important;
    border: 1px solid rgba(15, 23, 42, 0.16) !important;
    min-height: 2.9rem !important;
}
.st-key-google_login button * { color: #1f2937 !important; }
.st-key-google_login button p::before {
    content: ""; display: inline-block; width: 18px; height: 18px; margin-right: 10px; vertical-align: -3px;
    background: url("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'%3E%3Cpath fill='%23FFC107' d='M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z'/%3E%3Cpath fill='%23FF3D00' d='M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z'/%3E%3Cpath fill='%234CAF50' d='M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z'/%3E%3Cpath fill='%231976D2' d='M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z'/%3E%3C/svg%3E") no-repeat center / contain;
}

/* Tabs */
.stApp [data-baseweb="tab-list"] { gap: 6px !important; background: transparent !important; }
.stApp [data-baseweb="tab"] {
    background-color: var(--surface) !important; border: 1px solid var(--border) !important;
    border-radius: 10px !important; padding: 6px 16px !important; height: auto !important;
}
.stApp [data-baseweb="tab"][aria-selected="true"] { background-color: var(--active-bg) !important; border-color: var(--active) !important; }
.stApp [data-baseweb="tab-highlight"], .stApp [data-baseweb="tab-border"] { display: none !important; }

/* Forms */
.stApp [data-testid="stForm"] { border: none !important; padding: 0 !important; background: transparent !important; }
.stApp [data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background-color: var(--input-bg) !important; border-color: var(--border) !important; border-radius: 11px !important;
}

/* Form submit buttons + tabs (newer Streamlit DOM) */
.stApp .stFormSubmitButton > button {
    background-color: var(--btn-bg) !important; color: var(--btn-fg) !important;
    border: 1px solid var(--border) !important; border-radius: 12px !important; font-weight: 600 !important;
    min-height: 2.6rem; transition: transform 0.2s var(--ease) !important;
}
.stApp .stFormSubmitButton > button:hover { transform: translateY(-2px); border-color: var(--border-hover) !important; }
.stApp .stFormSubmitButton > button * { color: var(--btn-fg) !important; }
.stApp .stFormSubmitButton > button[kind="primaryFormSubmit"] {
    background-image: linear-gradient(120deg, var(--pbtn-1) 0%, var(--pbtn-2) 50%, var(--pbtn-1) 100%) !important;
    background-size: 200% auto !important; background-position: left center !important;
    color: #ffffff !important; border: 1px solid rgba(255, 255, 255, 0.22) !important;
    box-shadow: 0 10px 28px -10px var(--acc-2), inset 0 1px 0 rgba(255, 255, 255, 0.25) !important;
    transition: background-position 0.6s var(--ease), transform 0.2s var(--ease) !important;
}
.stApp .stFormSubmitButton > button[kind="primaryFormSubmit"]:hover { background-position: right center !important; }
.stApp .stFormSubmitButton > button[kind="primaryFormSubmit"] * { color: #ffffff !important; }
.stApp .stFormSubmitButton > button:disabled { opacity: 0.45 !important; transform: none !important; }
.stApp [data-testid="stTab"] {
    background-color: var(--surface) !important; border: 1px solid var(--border) !important;
    border-radius: 10px !important; padding: 6px 16px !important; margin-right: 6px !important;
}
.stApp [data-testid="stTab"][aria-selected="true"] { background-color: var(--active-bg) !important; border-color: var(--active) !important; }
.stApp [data-testid="stTab"][aria-selected="true"] p { font-weight: 700 !important; color: var(--acc-1) !important; }
.stApp [data-testid="stTab"] .react-aria-SelectionIndicator { display: none !important; }
.stApp [data-testid="stTabs"] [role="tablist"] { border-bottom: none !important; box-shadow: none !important; }
/* Active nav pill (we mark it with a keyed container) */
[class*="st-key-navon_"] [data-testid="stPageLink-NavLink"],
[class*="st-key-navon_"] [data-testid="stPageLink"] a {
    background-color: var(--active-bg) !important; border-color: var(--active) !important;
}
[class*="st-key-navon_"] [data-testid="stPageLink-NavLink"] p,
[class*="st-key-navon_"] [data-testid="stPageLink-NavLink"] span { font-weight: 700 !important; color: var(--acc-1) !important; }

/* Checkout */
.order-meta { margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--border); font-size: 0.82rem; color: var(--fg-muted) !important; }
.order-meta b { color: var(--fg) !important; font-family: 'JetBrains Mono', ui-monospace, monospace; }
.pay-title { font-size: 1.15rem; font-weight: 800; color: var(--fg) !important; letter-spacing: -0.01em; }
.pay-amount { text-align: center; font-size: 2rem; font-weight: 800; letter-spacing: -0.02em; color: var(--fg) !important; margin-top: 4px; }
.st-key-qrbox { display: flex !important; justify-content: center !important; margin: 14px 0 4px 0; }
.st-key-qrbox [data-testid="stImage"], .st-key-qrbox [data-testid="stImageContainer"] { display: flex; justify-content: center; }
.st-key-qrbox img {
    background: #ffffff !important; padding: 10px !important; border-radius: 16px !important;
    box-shadow: 0 14px 36px -16px var(--lift-c) !important;
}
.waiting {
    display: flex; align-items: center; justify-content: center; gap: 9px; margin-top: 10px;
    font-size: 0.88rem; color: var(--fg-muted) !important;
}

/* Multiselect tags */
.stApp [data-baseweb="tag"] {
    background-color: var(--active-bg) !important; border: 1px solid var(--active) !important; border-radius: 8px !important;
}
.stApp [data-baseweb="tag"] span, .stApp [data-baseweb="tag"] svg { color: var(--acc-1) !important; fill: var(--acc-1) !important; }
.stApp [data-baseweb="select"] > div { background-color: var(--input-bg) !important; border-color: var(--border) !important; border-radius: 11px !important; }

/* Accessibility: respect reduced motion */
@media (prefers-reduced-motion: reduce) {
    .stApp *, .stApp *::before, .stApp *::after, .stApp::before {
        animation: none !important;
        transition: none !important;
    }
}
"""

# Blank lines would end the HTML block in Streamlit's markdown parser, so strip them.
_THEME_CSS = "\n".join(line for line in _build_theme_css().splitlines() if line.strip())

def apply_glass_theme(theme_mode: str) -> None:
    is_dark = theme_mode == "Dark Glass"

    # 1) Static stylesheet: identical on every rerun, so Streamlit never re-inserts it
    #    (re-inserting a <style> block is what caused the blink + replayed animations).
    # st.html skips markdown parsing, so the stylesheet lands before anything is shown.
    if hasattr(st, "html"):
        st.html(_THEME_CSS)  # style-only content is kept by st.html (mixed content would be stripped)
    else:
        st.markdown(_THEME_CSS + '<div class="glass-css-anchor"></div>', unsafe_allow_html=True)

    # 2) Tiny theme flag: the only thing that changes when the theme switches.
    #    :root:has(.theme-flag-light) swaps the colour variables, which animate.
    flag_html = f'<div class="theme-flag theme-flag-{"dark" if is_dark else "light"}"></div>'
    if hasattr(st, "html"):
        st.html(flag_html)
    else:
        st.markdown(flag_html, unsafe_allow_html=True)


_READY_JS = """
<div class="app-ready-signal"></div>
<script>
(function () {
    const doc = (window.parent && window.parent.document) ? window.parent.document : document;
    const root = doc.documentElement;
    if (root.classList.contains('app-ready')) return;
    const t0 = performance.now();
    let lastChange = performance.now();
    const mo = new MutationObserver(() => { lastChange = performance.now(); });
    mo.observe(doc.body, { childList: true, subtree: true });
    function reveal() {
        mo.disconnect();
        requestAnimationFrame(() => requestAnimationFrame(() => {
            root.classList.add('app-ready');
            setTimeout(() => root.classList.add('app-settled'), 450);
        }));
    }
    (function wait() {
        const now = performance.now();
        const titleThere = !!doc.querySelector('.hero-title');
        const skeletons = doc.querySelectorAll('[data-testid="stMain"] [data-testid="stSkeleton"]').length;
        const quiet = now - lastChange > 150;
        if ((titleThere && skeletons === 0 && quiet) || now - t0 > 2000) {
            (doc.fonts && doc.fonts.ready ? Promise.race([doc.fonts.ready, new Promise(r => setTimeout(r, 300))]) : Promise.resolve()).then(reveal);
        } else {
            requestAnimationFrame(wait);
        }
    })();
})();
</script>
"""


def signal_app_ready() -> None:
    # Call once at the very end of the script: reveals the whole UI in one smooth fade.
    try:
        st.html(_READY_JS, unsafe_allow_javascript=True)
    except TypeError:
        # Older Streamlit without unsafe_allow_javascript: the CSS safety reveal (2.5s) takes over.
        st.markdown('<div class="app-ready-signal"></div>', unsafe_allow_html=True)
