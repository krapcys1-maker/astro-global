const API_TOKEN_HEADER = "x-astro-global-session";
const DEFAULT_API_BASE = "http://127.0.0.1:8765";
const DEFAULT_SESSION_TOKEN = "dev-local-token";
const DEFAULT_INDEX_FILE = "swiss_1500_now_global_slow_v1.npz";
const API_REQUEST_TIMEOUT_MS = 20000;
const EXPLORER_DEFAULT_DATE = "1789-07-14";
const EXPLORER_EXAMPLES = ["1789-07-14", "1848-02-24", "2020-01-12", "2026-05-24"];
const PLANET_GLYPHS = {
  Pluto: "♇",
  Neptune: "♆",
  Uranus: "♅",
  Saturn: "♄",
  Jupiter: "♃",
};
const ORBIT_PLANET_ORDER = ["Neptune", "Uranus", "Pluto", "Saturn", "Jupiter"];
const ZODIAC_GLYPHS = {
  Aries: "♈",
  Taurus: "♉",
  Gemini: "♊",
  Cancer: "♋",
  Leo: "♌",
  Virgo: "♍",
  Libra: "♎",
  Scorpio: "♏",
  Sagittarius: "♐",
  Capricorn: "♑",
  Aquarius: "♒",
  Pisces: "♓",
};
const PRODUCT_NAV_ITEMS = [
  { view: "home", route: "/", label: "Start" },
  { view: "today", route: "/dzis", label: "Dziś" },
  { view: "chart", route: "/kosmogram", label: "Kosmogram" },
  { view: "explorer", route: "/cykle-historyczne", label: "Cykle historyczne" },
  { view: "compare", route: "/porownania", label: "Porównania" },
  { view: "blog", route: "/blog", label: "Blog" },
  { view: "engine", route: "/o-silniku", label: "O silniku" },
  { view: "contact", route: "/kontakt", label: "Kontakt" },
  { view: "login", route: "/logowanie", label: "Logowanie", accent: true },
];
const ROUTE_ALIASES = {
  home: "home",
  start: "home",
  today: "today",
  dzis: "today",
  "dziś": "today",
  kosmogram: "chart",
  chart: "chart",
  explorer: "explorer",
  "cykle-historyczne": "explorer",
  compare: "compare",
  porownania: "compare",
  "porównania": "compare",
  blog: "blog",
  "o-silniku": "engine",
  engine: "engine",
  transparency: "engine",
  contact: "contact",
  kontakt: "contact",
  login: "login",
  logowanie: "login",
};
const EXPLORER_RAIL_ITEMS = [
  ["Explorer", "explorer"],
  ["Compare", "epoch"],
  ["Calendar", "events"],
  ["Cycles", "structural"],
  ["Library", "map"],
  ["Reports", "analogues"],
];
const CATEGORY_GROUP_META = {
  hard_disruption: {
    label: "Hard disruption",
    description: "wars, revolutions, crises and shocks",
  },
  science_technology: {
    label: "Science & technology",
    description: "science, technology, medicine and standards",
  },
  institutions: {
    label: "Institutions",
    description: "law, diplomacy, governance and organizations",
  },
  society_culture: {
    label: "Society & culture",
    description: "rights, ideas, culture and social movements",
  },
  economy_infrastructure: {
    label: "Economy & infrastructure",
    description: "economic systems, finance, infrastructure and trade",
  },
  civilizational_background: {
    label: "Civilizational background",
    description: "long processes and broad historical background",
  },
};
const CATEGORY_GROUP_ORDER = [
  "hard_disruption",
  "science_technology",
  "institutions",
  "society_culture",
  "economy_infrastructure",
  "civilizational_background",
];
const THEME_LABELS = {
  hard_disruption: "power stress and social rupture",
  science_technology: "science and technology shifts",
  institutions: "institutional redesign",
  society_culture: "ideas, rights and social change",
  economy_infrastructure: "economic and infrastructure transformation",
  civilizational_background: "long civilizational background",
};
const CATEGORY_GROUP_BY_CATEGORY = {
  war: "hard_disruption",
  revolution: "hard_disruption",
  geopolitical_crisis: "hard_disruption",
  political_crisis: "hard_disruption",
  economic_crisis: "hard_disruption",
  epidemic: "hard_disruption",
  disaster: "hard_disruption",
  terrorism: "hard_disruption",
  genocide: "hard_disruption",
  cyber_crisis: "hard_disruption",
  science_technology: "science_technology",
  time_standard: "science_technology",
  institution: "institutions",
  constitutional_institution: "institutions",
  economic_institution: "institutions",
  diplomatic_settlement: "institutions",
  diplomatic_congress: "institutions",
  humanitarian_institution: "institutions",
  communications_institution: "institutions",
  geopolitical_transition: "institutions",
  political_transition: "institutions",
  political_integration: "institutions",
  civil_rights: "society_culture",
  religious_reformation: "society_culture",
  intellectual_movement: "society_culture",
  publishing_culture: "society_culture",
  cultural_movement: "society_culture",
  religious_political_revolution: "society_culture",
  political_ideology: "society_culture",
  political_reform: "society_culture",
  social_policy: "society_culture",
  environment: "society_culture",
  economic_transition: "economy_infrastructure",
  colonial_expansion: "economy_infrastructure",
  infrastructure: "economy_infrastructure",
  economic_infrastructure: "economy_infrastructure",
  economic_disruption: "economy_infrastructure",
  economic_ideology: "economy_infrastructure",
  political_referendum: "institutions",
  demographic_transition: "civilizational_background",
};

const appRoot = document.querySelector("#appRoot");
const apiBaseInput = document.querySelector("#apiBase");
const sessionTokenInput = document.querySelector("#sessionToken");
const connectButton = document.querySelector("#connectButton");
const connectionState = document.querySelector("#connectionState");
const navLinks = [...document.querySelectorAll("[data-view]")];

const state = {
  apiBase: DEFAULT_API_BASE,
  token: DEFAULT_SESSION_TOKEN,
  status: null,
  today: null,
  todaySearch: null,
  timelineSeeds: null,
  articleSeeds: null,
  currentSearch: null,
  selectedEpisodeIndex: 0,
  explorerCategoryFilter: "all",
  currentCompare: null,
  currentView: "home",
  initialApplied: false,
  initialDate: null,
  initialLeft: null,
  initialRight: null,
  lastError: null,
  lastApiSummaries: {},
};

const routeLabels = {
  home: "Start",
  today: "Dziś",
  chart: "Kosmogram",
  explorer: "Cykle historyczne",
  compare: "Porównania",
  blog: "Blog",
  engine: "O silniku",
  contact: "Kontakt",
  login: "Logowanie",
};

function viewFromRoute(rawRoute) {
  const normalized = String(rawRoute || "home")
    .replace(/^#?\/?/, "")
    .replace(/^\/+/, "")
    .replace(/\/+$/, "")
    .toLowerCase();
  return ROUTE_ALIASES[normalized || "home"] || "home";
}

function routeForView(viewName) {
  return PRODUCT_NAV_ITEMS.find((item) => item.view === viewName)?.route || "/";
}

function renderProductNav({ className = "product-toolbar-nav" } = {}) {
  return `
    <nav class="${className}" aria-label="Nawigacja produktu">
      ${PRODUCT_NAV_ITEMS.map((item) => `
        <button
          class="product-nav-link ${item.accent ? "nav-login-link" : ""} ${state.currentView === item.view ? "active" : ""}"
          type="button"
          data-view="${item.view}"
          data-route="${item.route}"
        >${escapeHtml(item.label)}</button>
      `).join("")}
    </nav>
  `;
}

function initFromUrl() {
  const params = new URLSearchParams(window.location.search);
  state.apiBase = params.get("apiBase") || DEFAULT_API_BASE;
  state.token = params.get("token") || DEFAULT_SESSION_TOKEN;
  state.initialDate = params.get("date");
  state.initialLeft = params.get("left");
  state.initialRight = params.get("right");
  apiBaseInput.value = state.apiBase;
  sessionTokenInput.value = state.token;
}

function connection() {
  state.apiBase = apiBaseInput.value.trim().replace(/\/+$/, "");
  state.token = sessionTokenInput.value.trim();
  return { apiBase: state.apiBase, token: state.token };
}

async function apiRequest(path, options = {}) {
  const { apiBase, token } = connection();
  const headers = {
    ...(options.body ? { "content-type": "application/json" } : {}),
    ...(options.auth === false || !token ? {} : { [API_TOKEN_HEADER]: token }),
  };
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), options.timeoutMs || API_REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(`${apiBase}${path}`, {
      method: options.method || "GET",
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: controller.signal,
    });
    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json") ? await response.json() : await response.text();
    state.lastApiSummaries[path] = summarizeApiPayload(path, payload, response.status);
    if (!response.ok) {
      const detail = typeof payload === "object" ? payload.detail : payload;
      throw new ApiError(response.status, detail || response.statusText, payload);
    }
    return payload;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new ApiError(408, `Backend request timed out after ${Math.round((options.timeoutMs || API_REQUEST_TIMEOUT_MS) / 1000)}s: ${path}`, null);
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

class ApiError extends Error {
  constructor(status, detail, payload) {
    super(String(detail));
    this.status = status;
    this.payload = payload;
  }
}

async function connectBackend({ render = true } = {}) {
  setConnection("loading", "connecting");
  try {
    await apiRequest("/health", { auth: false });
    const [status, today, timelineSeeds, articleSeeds] = await Promise.all([
      apiRequest("/data/status"),
      apiRequest("/today"),
      apiRequest("/timeline/seeds"),
      apiRequest("/articles/seeds"),
    ]);
    state.status = status;
    state.today = today;
    state.timelineSeeds = timelineSeeds;
    state.articleSeeds = articleSeeds;
    state.lastError = null;
    setConnection("ok", "backend connected");
    if (render) {
      await renderActiveView();
      await applyInitialRouteRequest();
    }
  } catch (error) {
    state.lastError = error;
    setConnection("error", errorMessage(error));
    if (render) {
      await renderActiveView();
    }
  }
}

async function applyInitialRouteRequest() {
  if (state.initialApplied || !state.status) {
    return;
  }
  state.initialApplied = true;
  if (state.currentView === "explorer" && state.initialDate) {
    await runExplorerSearch(buildSearchRequest(state.initialDate));
  } else if (state.currentView === "compare" && state.initialLeft && state.initialRight) {
    await runCompare(buildCompareRequest(state.initialLeft, state.initialRight));
  }
}

function setConnection(kind, label) {
  connectionState.innerHTML = `<span class="status-pill ${kind}">${escapeHtml(label)}</span>`;
}

function setActiveView(viewName, options = {}) {
  state.currentView = routeLabels[viewName] ? viewName : viewFromRoute(viewName);
  document.body.dataset.currentView = state.currentView;
  for (const link of navLinks) {
    link.classList.toggle("active", link.dataset.view === state.currentView);
  }
  const route = routeForView(state.currentView);
  if (route && !options.skipHash) {
    history.replaceState({ view: state.currentView }, "", `#${route === "/" ? "home" : route.slice(1)}`);
  }
  return renderActiveView(options);
}

async function renderActiveView(options = {}) {
  if (state.currentView === "home") {
    renderHome();
  } else if (state.currentView === "today") {
    renderToday();
    if (state.today && !state.todaySearch && !options.skipAutoLoad) {
      await loadTodayResonance();
    }
  } else if (state.currentView === "chart") {
    renderChart();
  } else if (state.currentView === "explorer") {
    renderExplorer();
    if (!state.currentSearch && !state.initialDate && !options.skipAutoLoad) {
      await runExplorerSearch(buildSearchRequest(EXPLORER_DEFAULT_DATE));
    }
  } else if (state.currentView === "compare") {
    renderCompare();
  } else if (state.currentView === "blog") {
    renderBlog();
  } else if (state.currentView === "engine") {
    renderEngine();
  } else if (state.currentView === "contact") {
    renderContact();
  } else if (state.currentView === "login") {
    renderLogin();
  }
}

function renderHome() {
  appRoot.innerHTML = `
    <section class="hero-screen">
      <div class="hero-copy">
        <p class="eyebrow">Astrologia mundalna / research product</p>
        <h1>Astro Global</h1>
        <p class="hero-subtitle">Silnik rezonansu planetarno-historycznego</p>
        <p class="hero-text">
          Astro Global porównuje aktualne układy wolnych planet z podobnymi
          reżimami z historii. Wynik nie jest prognozą, tylko uporządkowanym
          badaniem cykli, analogii i kontekstu wydarzeń.
        </p>
        <div class="hero-actions">
          <button class="primary-action" type="button" data-view="today">Dziś</button>
          <button class="secondary-action" type="button" data-view="chart">Kosmogram</button>
          <button class="secondary-action" type="button" data-view="explorer">Cykle historyczne</button>
        </div>
      </div>
      <div class="hero-orbit" aria-hidden="true">
        <div class="orbital-map product-orbit">
          <span class="sun-core"></span>
          <span class="orbit orbit-one"></span>
          <span class="orbit orbit-two"></span>
          <span class="orbit orbit-three"></span>
          <span class="orbit orbit-four"></span>
          <span class="planet-marker saturn">S</span>
          <span class="planet-marker jupiter">J</span>
          <span class="planet-marker uranus">U</span>
          <span class="planet-marker neptune">N</span>
        </div>
      </div>
    </section>
    <section class="feature-grid product-section">
      ${featureCard("Astrologia mundalna", "Punktem wyjścia są wolne cykle planetarne, ich aspekty oraz reżimy znakowe.")}
      ${featureCard("Cykle historyczne", "Silnik szuka podobnych konfiguracji w indeksie historycznym i pokazuje okresy rezonansu.")}
      ${featureCard("Resonance search", "Wydarzenia są dowodem kontekstowym, a nie sztucznie dopisaną narracją czy predykcją.")}
    </section>
    ${renderConnectionNotice()}
  `;
}

function renderChart() {
  appRoot.innerHTML = `
    <section class="page-shell">
      <div class="page-heading compact-heading">
        <p class="eyebrow">Kosmogram</p>
        <h1>Astrologia osobista</h1>
        <p>Frontend formularza jest gotowy jako miejsce pod późniejszy pipeline pracy astrologa. Dane nie są jeszcze wysyłane do backendu.</p>
      </div>
      <form class="contact-form product-card" id="chartForm">
        <label>Data urodzenia <input name="birthDate" type="date" /></label>
        <label>Godzina <input name="birthTime" type="time" /></label>
        <label class="wide-field">Miejsce <input name="birthPlace" placeholder="Miasto, kraj" autocomplete="off" /></label>
        <p class="privacy-note wide-field">
          Docelowo ta sekcja wygeneruje kosmogram SVG, pozycje planet, aspekty, dominanty i interpretację.
          Na tym etapie nie zapisuje ani nie wysyła danych.
        </p>
        <button class="primary-action" type="submit">Przygotuj kosmogram</button>
        <span class="form-state" id="chartState" aria-live="polite"></span>
      </form>
    </section>
  `;
}

function renderToday() {
  const today = state.today;
  if (!today) {
    appRoot.innerHTML = productErrorPage(
      "Today",
      "Today uses GET /today, but the backend snapshot is not available.",
      state.lastError
    );
    return;
  }
  const request = today.recommended_search_request;
  const primaryCycles = state.todaySearch?.primary_cycles || [];
  const supportingCycles = state.todaySearch?.supporting_cycles || [];
  appRoot.innerHTML = `
    <section class="page-shell">
      <div class="page-heading">
        <p class="eyebrow">Today</p>
        <h1>${escapeHtml(today.snapshot_date_utc)}</h1>
        <p>Today's backend snapshot, recommended search request and active cycle evidence.</p>
      </div>
      <div class="status-card-grid">
        ${statCard("Provider", today.provider)}
        ${statCard("Index", today.index_file)}
        ${statCard("Reliable range", `${today.reliable_history_start}-${today.reliable_history_end}`)}
      </div>
      <article class="product-card">
        <div class="section-head">
          <div>
            <p class="card-label">Recommended search request</p>
            <h2>${escapeHtml(shortDate(request.date_utc))}</h2>
          </div>
          <button class="primary-action" type="button" data-action="run-today-resonance">
            Run today resonance
          </button>
        </div>
        <div class="request-summary">
          <span>Lookback: ${escapeHtml(String(request.lookback_years))} years</span>
          <span>Episodes: ${escapeHtml(String(request.max_episodes))}</span>
          <span>Provider: ${escapeHtml(request.provider)}</span>
          <span>Profile: ${escapeHtml(request.profile_id)}</span>
        </div>
      </article>
      ${renderWarnings(today.warnings)}
      <section class="product-card">
        <p class="card-label">Active cycles</p>
        ${
          primaryCycles.length
            ? renderCycleSummary(primaryCycles, supportingCycles)
            : noPrimaryCycleMessage(supportingCycles)
        }
      </section>
    </section>
  `;
}

async function loadTodayResonance() {
  if (!state.today?.recommended_search_request) {
    return;
  }
  const holder = document.querySelector(".product-card:last-child");
  if (holder) {
    holder.innerHTML = loadingState("Loading today's resonance from POST /resonance/search");
  }
  try {
    state.todaySearch = await apiRequest("/resonance/search", {
      method: "POST",
      body: state.today.recommended_search_request,
    });
    if (state.currentView === "today") {
      renderToday();
    }
  } catch (error) {
    if (state.currentView === "today") {
      appRoot.insertAdjacentHTML("beforeend", errorState("Today resonance failed", errorMessage(error)));
    }
  }
}

function renderExplorer() {
  appRoot.innerHTML = `
    <section class="explorer-observatory-page reference-explorer-page">
      <div class="explorer-reference-frame">
        ${renderExplorerTopBar()}
        ${renderExplorerSideRail()}
        <div class="explorer-main-area">
          <div id="explorerResult" class="explorer-result-stage">
            ${state.currentSearch ? renderSearchResult(state.currentSearch) : renderExplorerLoading()}
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderExplorerTopBar() {
  return `
    <form class="explorer-top-bar" id="explorerForm">
      <div class="explorer-brand-lockup" aria-label="Astro Global Explorer">
        <span class="explorer-brand-mark" aria-hidden="true">
          <span></span>
        </span>
        <span>
          <strong>Astro Global</strong>
          <small>Silnik rezonansu<br />historycznego</small>
        </span>
      </div>
      ${renderProductNav({ className: "mode-tabs product-mode-tabs" })}
      <label class="explorer-date-control" aria-label="Analyze date">
        <input name="date" value="${escapeHtml(defaultExplorerDate())}" placeholder="dd-mm-rrrr" autocomplete="off" inputmode="numeric" />
        <span>${renderExplorerModeIcon("events")}</span>
      </label>
      <button class="explorer-help-button" type="button" aria-label="Help">?</button>
      <div class="example-row explorer-examples" aria-label="Explorer examples">
        ${EXPLORER_EXAMPLES.map((date) => `<button type="button" data-example-date="${date}">${date}</button>`).join("")}
      </div>
    </form>
  `;
}

function renderExplorerModeIcon(icon) {
  const icons = {
    overview: `
      <svg class="nav-line-icon" viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12" r="3.2"></circle>
        <circle cx="12" cy="12" r="8.2"></circle>
        <path d="M12 2.8v3.1M12 18.1v3.1M2.8 12h3.1M18.1 12h3.1"></path>
      </svg>
    `,
    epoch: `
      <svg class="nav-line-icon" viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="6" cy="6" r="1.7"></circle>
        <circle cx="17.5" cy="5.2" r="1.7"></circle>
        <circle cx="10.3" cy="13" r="1.7"></circle>
        <circle cx="18.5" cy="17.6" r="1.7"></circle>
        <path d="M7.4 7.1l2.1 4.4M11.9 12.3l4.3-5.7M11.9 13.8l5.1 2.9M6.8 6.9l10.7 10.7"></path>
      </svg>
    `,
    structural: `
      <svg class="nav-line-icon" viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12.5" r="7.2"></circle>
        <circle cx="12" cy="6.2" r="1.5"></circle>
        <path d="M12 3.2v3M15.8 10.8l-3.8 1.7"></path>
      </svg>
    `,
    short: `
      <svg class="nav-line-icon" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M7.2 5.2c1.4 4.1 3 6.4 4.8 6.4s3.4-2.3 4.8-6.4"></path>
        <path d="M8.4 8.3c.3 4.7 1.5 7 3.6 7s3.3-2.3 3.6-7"></path>
        <path d="M12 11.6v8.1M8.7 19.7h6.6"></path>
      </svg>
    `,
    analogues: `
      <svg class="nav-line-icon" viewBox="0 0 24 24" aria-hidden="true">
        <rect x="5.3" y="4" width="13.4" height="16" rx="1.1"></rect>
        <path d="M8.2 8h7.6M8.2 12h7.6M8.2 16h3M13.7 16h2.1"></path>
      </svg>
    `,
    events: `
      <svg class="nav-line-icon" viewBox="0 0 24 24" aria-hidden="true">
        <rect x="4.5" y="6.3" width="15" height="13" rx="1.2"></rect>
        <path d="M4.5 10h15M8.1 4.3v3.9M15.9 4.3v3.9M8 13.5h2.2M13.8 13.5H16M8 16.6h2.2"></path>
      </svg>
    `,
    map: `
      <svg class="nav-line-icon" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M6 5.2l4.2 2.1 3.6-2.1 4.2 2.1v11.5l-4.2-2.1-3.6 2.1L6 16.7z"></path>
        <path d="M10.2 7.3v11.5M13.8 5.2v11.5"></path>
      </svg>
    `,
    settings: `
      <svg class="nav-line-icon" viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12" r="3"></circle>
        <path d="M12 3.8v2.1M12 18.1v2.1M5.8 5.8l1.5 1.5M16.7 16.7l1.5 1.5M3.8 12h2.1M18.1 12h2.1M5.8 18.2l1.5-1.5M16.7 7.3l1.5-1.5"></path>
      </svg>
    `,
    explorer: `
      <svg class="nav-line-icon" viewBox="0 0 24 24" aria-hidden="true">
        <ellipse cx="12" cy="12" rx="8" ry="3.4" transform="rotate(-35 12 12)"></ellipse>
        <circle cx="12" cy="12" r="2.1"></circle>
      </svg>
    `,
  };
  return icons[icon] || icons.overview;
}

async function runExplorerSearch(request, options = {}) {
  const explorerRequest = historicalAnalogueRequest(request);
  if (options.navigate) {
    state.currentView = "explorer";
    syncNav();
    renderExplorer();
  }
  (document.querySelector("#explorerResult") || appRoot).innerHTML = loadingState(
    "Analyzing date with POST /resonance/search"
  );
  try {
    const payload = await apiRequest("/resonance/search", {
      method: "POST",
      body: explorerRequest,
    });
    state.currentSearch = payload;
    state.selectedEpisodeIndex = 0;
    state.explorerCategoryFilter = "all";
    const dateInput = document.querySelector("#explorerForm input[name='date']");
    if (dateInput) {
      dateInput.value = shortDate(payload.query_datetime_utc);
    }
    if (state.currentView === "explorer") {
      (document.querySelector("#explorerResult") || appRoot).innerHTML =
        renderSearchResult(payload);
    }
  } catch (error) {
    (document.querySelector("#explorerResult") || appRoot).innerHTML = errorState(
      "Analysis failed",
      errorMessage(error)
    );
  }
}

function historicalAnalogueRequest(request) {
  return {
    ...request,
    historical_analogue_mode: true,
    exclude_same_calendar_year: true,
    local_resonance_window_days: 365,
    historical_analogue_min_year_gap: 5,
    historical_exclude_active_regime_windows: true,
  };
}

function renderSearchResult(payload) {
  const queryDate = shortDate(payload.query_datetime_utc);
  const episodes = historicalAnalogues(payload);
  const selectedIndex = clampEpisodeIndex(state.selectedEpisodeIndex, episodes);
  const selectedEpisode = episodes[selectedIndex];
  return `
    <section class="reference-explorer-shell">
      ${renderReferenceCurrentRegime(payload, queryDate)}
      <div class="reference-content-grid">
        ${renderReferenceAnalogueSection(payload, episodes, selectedEpisode, selectedIndex)}
        ${renderReferenceCycleLayers(payload)}
      </div>
      ${renderReferenceTimelineOverlay(payload, selectedEpisode)}
      ${
        selectedEpisode
          ? renderSimpleNarrativeSection(payload, selectedEpisode, selectedIndex)
          : emptyState("Few strong historical analogues detected", "The backend returned no independent historical analogue periods after excluding current active regime and local resonance windows.")
      }
      ${renderAdvancedExplorerDetails(payload, selectedEpisode)}
    </section>
  `;
}

function renderExplorerLoading() {
  return `
    <section class="explorer-loading-panel">
      ${loadingState(`Loading Explorer resonance for ${defaultExplorerDate()}`)}
      <p class="human-note">Explorer uses POST /resonance/search only. No local scoring or fake data is rendered.</p>
    </section>
  `;
}

function renderExplorerSideRail() {
  return `
    <aside class="explorer-side-rail" aria-label="Explorer workspace">
      ${EXPLORER_RAIL_ITEMS.map(([item, icon], index) => `
        <button class="${index === 0 ? "active" : ""}" type="button">
          <span>${renderExplorerModeIcon(icon)}</span>
          ${escapeHtml(item)}
        </button>
      `).join("")}
      <div class="side-rail-spacer"></div>
      <button type="button"><span>?</span>Help</button>
    </aside>
  `;
}

function renderReferenceCurrentRegime(payload, queryDate) {
  const regimes = activeRegimeWindows(payload);
  const cycleWindows = activeCycleWindows(payload);
  const range = activeCycleRange(cycleWindows) || activeRegimeRange(regimes) || queryDate;
  const dominantCycles = dominantRegimeLabels(payload).slice(0, 4);
  const themes = conciseThemes(payload, historicalAnalogues(payload)[0]).slice(0, 5);
  return `
    <section class="reference-regime-panel" aria-label="Current regime">
      <div class="reference-regime-copy">
        <p class="eyebrow">Current Regime</p>
        <h1>${escapeHtml(regimeYearRange(range))}</h1>
        <p>This is the active planetary regime detected for the selected date. It describes the dominant long-term energies shaping the world.</p>
      </div>
      <div class="reference-divider"></div>
      <div class="reference-cycle-column">
        <p class="card-label">Dominant structural cycles</p>
        <div class="reference-cycle-list">
          ${
            dominantCycles.length
              ? dominantCycles.map((label, index) => renderReferenceCycleRow(label, windowForDominantLabel(label, cycleWindows, regimes, index), index)).join("")
              : `<p class="empty-copy">No dominant cycle returned by backend.</p>`
          }
        </div>
      </div>
      <div class="reference-divider reference-divider-soft"></div>
      <div class="reference-theme-column">
        <p class="card-label">Key themes</p>
        <div class="reference-theme-list">
          ${
            themes.length
              ? themes.map((theme, index) => renderReferenceTheme(theme, index)).join("")
              : `<p class="empty-copy">Theme evidence is limited for this query.</p>`
          }
        </div>
      </div>
      ${renderReferenceOrbit(payload)}
    </section>
  `;
}

function renderReferenceCycleRow(label, window, index) {
  const hasWindow = Boolean(window?.start_date || window?.end_date);
  const closeness = typeof window?.closeness_at_query === "number" ? window.closeness_at_query : hasWindow ? 0.82 : 0;
  const width = Math.round(Math.max(0.18, Math.min(1, closeness)) * 100);
  const range = cycleWindowDisplayRange(window);
  return `
    <article class="reference-cycle-row">
      <span class="reference-cycle-icon tone-${index % 4}">${renderPlanetGlyphIcon(label)}</span>
      <strong>${escapeHtml(label)}</strong>
      <span class="cycle-strength tone-${index % 4} ${hasWindow ? "" : "unavailable"}"><i style="width:${hasWindow ? width : 0}%"></i></span>
      <em>${range.map((part) => `<span>${escapeHtml(part)}</span>`).join("")}</em>
    </article>
  `;
}

function renderReferenceTheme(theme, index) {
  return `
    <span class="reference-theme">
      <i>${renderReferenceThemeIcon(index)}</i>
      ${escapeHtml(theme)}
    </span>
  `;
}

function renderReferenceThemeIcon(index) {
  const icons = [
    `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="6.2" r="2.3"></circle><path d="M12 8.7v8.9M7.2 11.5l4.8 3.1 4.8-3.1M7.5 18.2l4.5-3.6 4.5 3.6"></path><circle cx="6" cy="18.3" r="1.7"></circle><circle cx="18" cy="18.3" r="1.7"></circle></svg>`,
    `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8.1 5.2c2.8 1.5 5 3.7 6.5 6.5M15.9 18.8c-2.8-1.5-5-3.7-6.5-6.5"></path><path d="M15.9 5.2c-2.8 1.5-5 3.7-6.5 6.5M8.1 18.8c2.8-1.5 5-3.7 6.5-6.5"></path><circle cx="12" cy="12" r="2"></circle></svg>`,
    `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6.2 15.8c2.8-2.8 8.8-2.8 11.6 0"></path><path d="M7.3 8.5c2.2 2.4 7.2 2.4 9.4 0"></path><circle cx="7" cy="8.3" r="1.7"></circle><circle cx="17" cy="8.3" r="1.7"></circle><circle cx="6.2" cy="15.8" r="1.7"></circle><circle cx="17.8" cy="15.8" r="1.7"></circle></svg>`,
    `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="2"></circle><path d="M12 4.2v4M12 15.8v4M4.2 12h4M15.8 12h4M6.5 6.5l2.8 2.8M14.7 14.7l2.8 2.8"></path></svg>`,
    `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4.4v15.2M7.2 7.2c0 3.2 1.6 4.8 4.8 4.8s4.8-1.6 4.8-4.8"></path><path d="M8.2 18.4h7.6M5.8 14.4h12.4"></path></svg>`,
  ];
  return icons[index % icons.length];
}

function renderReferenceOrbit(payload) {
  const cycleWindows = activeCycleWindows(payload).slice(0, 6);
  const nodes = orbitNodesFromCycles(cycleWindows, dominantRegimeLabels(payload)).slice(0, 4);
  const points = orbitLayoutPoints(nodes.length);
  const positionedNodes = nodes.map((node, index) => ({ ...node, point: points[index] })).filter((node) => node.point);
  return `
    <div class="reference-orbit" aria-label="Cycle map">
      <div class="orbit-ring ring-one"></div>
      <div class="orbit-ring ring-two"></div>
      <div class="orbit-ring ring-three"></div>
      <svg class="orbit-aspect-lines" viewBox="0 0 228 228" aria-hidden="true">
        ${renderOrbitAspectLines(positionedNodes, cycleWindows)}
      </svg>
      ${positionedNodes.map((node, index) => renderOrbitPoint(node.label, node.point, index)).join("")}
      <span class="orbit-sun"></span>
      ${cycleWindows.map((window, index) => `
        <span class="orbit-window-label orbit-window-label-${index}">
          ${escapeHtml(yearRangeFromDates(window.start_date, window.end_date) || window.aspect || "")}
        </span>
      `).join("")}
    </div>
  `;
}

function renderReferenceAnalogueSection(payload, episodes, selectedEpisode, selectedIndex) {
  const visibleEpisodes = episodes.slice(0, 3);
  const countClass = `analogue-count-${Math.max(1, Math.min(visibleEpisodes.length || 1, 3))}`;
  return `
    <section class="reference-analogue-panel ${countClass}">
      <div class="reference-panel-heading">
        <div>
          <p class="eyebrow">Most similar historical regimes</p>
        </div>
        <span class="info-dot" title="Same-regime and nearby dates are kept in Advanced.">i</span>
      </div>
      <div class="reference-analogue-cards">
        ${
          visibleEpisodes.length
            ? visibleEpisodes.map((episode, index) => renderReferenceAnalogueCard(episode, index, selectedIndex)).join("")
            : emptyState("No historical analogues", "The backend found no independent periods outside the current regime.")
        }
      </div>
      ${
        visibleEpisodes.length
          ? `<button class="show-more-analogues" type="button" data-action="open-analysis">Show more analogues</button>`
          : ""
      }
    </section>
  `;
}

function orbitNodesFromCycles(cycleWindows = [], fallbackLabels = []) {
  const nodes = [];
  const seen = new Set();
  const addPlanet = (planet) => {
    if (!planet || seen.has(planet) || !PLANET_GLYPHS[planet]) {
      return;
    }
    seen.add(planet);
    nodes.push({ label: planet, planet });
  };
  for (const cycle of cycleWindows) {
    for (const planet of cyclePair(cycle)) {
      addPlanet(planet);
    }
  }
  for (const label of fallbackLabels) {
    for (const planet of planetsFromText(label)) {
      addPlanet(planet);
    }
  }
  return nodes.sort((left, right) => orbitPlanetRank(left.planet) - orbitPlanetRank(right.planet));
}

function orbitPlanetRank(planet) {
  const index = ORBIT_PLANET_ORDER.indexOf(planet);
  return index === -1 ? ORBIT_PLANET_ORDER.length : index;
}

function renderOrbitPoint(label, point, index) {
  if (!label || !point) {
    return "";
  }
  return `
    <span
      class="orbit-point tone-${index % 4}"
      style="left:${num(point.x - 19, 1)}px; top:${num(point.y - 19, 1)}px"
      title="${escapeHtml(label)}"
    >${renderPlanetGlyphIcon(label)}</span>
  `;
}

function renderOrbitAspectLines(nodes, cycleWindows = []) {
  if (nodes.length < 2) {
    return "";
  }
  const pointByPlanet = new Map(nodes.map((node) => [node.planet, node.point]));
  const lines = [];
  const seen = new Set();
  for (const cycle of cycleWindows) {
    const [left, right] = cyclePair(cycle);
    const leftPoint = pointByPlanet.get(left);
    const rightPoint = pointByPlanet.get(right);
    if (!leftPoint || !rightPoint) {
      continue;
    }
    const key = [left, right].sort().join(":");
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    const tone = orbitAspectTone(cycle.aspect, lines.length, left, right);
    lines.push(`<line class="aspect ${tone}" x1="${leftPoint.x}" y1="${leftPoint.y}" x2="${rightPoint.x}" y2="${rightPoint.y}"></line>`);
  }
  if (!lines.length) {
    nodes.forEach((node, index) => {
      const next = nodes[(index + 1) % nodes.length];
      const tone = index % 2 === 0 ? "cyan" : "violet";
      lines.push(`<line class="aspect ${tone}" x1="${node.point.x}" y1="${node.point.y}" x2="${next.point.x}" y2="${next.point.y}"></line>`);
    });
  }
  const anchor = nodes[0]?.point;
  if (anchor) {
    lines.push(`<line class="aspect gold" x1="${anchor.x}" y1="${anchor.y}" x2="108" y2="122"></line>`);
  }
  return lines.join("");
}

function orbitAspectTone(aspect = "", index = 0, left = "", right = "") {
  const pairKey = [left, right].sort().join(":");
  if (pairKey === "Neptune:Uranus") {
    return "cyan";
  }
  if (pairKey === "Pluto:Uranus" || pairKey === "Neptune:Pluto") {
    return "violet";
  }
  const normalized = String(aspect || "").toLowerCase();
  if (normalized.includes("trine")) {
    return "violet";
  }
  if (normalized.includes("sextile")) {
    return index % 2 === 0 ? "cyan" : "gold";
  }
  return index % 2 === 0 ? "cyan" : "violet";
}

function orbitLayoutPoints(count) {
  if (count >= 4) {
    return [
      { x: 82, y: 58 },
      { x: 184, y: 104 },
      { x: 116, y: 169 },
      { x: 66, y: 132 },
    ];
  }
  if (count === 3) {
    return [
      { x: 82, y: 60 },
      { x: 184, y: 106 },
      { x: 116, y: 169 },
    ];
  }
  if (count === 2) {
    return [
      { x: 82, y: 60 },
      { x: 184, y: 106 },
    ];
  }
  return [{ x: 114, y: 62 }];
}

function renderReferenceAnalogueCard(episode, index, selectedIndex) {
  const exactEvents = (episode.matched_events || []).slice(0, 4);
  const contextEvents = (episode.context_events || []).slice(0, 4);
  const matchScore = typeof episode.best_score === "number"
    ? episode.best_score
    : episode.narrative_confidence?.narrative_confidence;
  return `
    <article class="reference-analogue-card ${index === selectedIndex ? "selected" : ""}">
      <span class="match-ribbon">${percent(matchScore)} match</span>
      <div class="analogue-period-heading">
        <span>Resonance period</span>
        <h3>${escapeHtml(analogueCardYears(episode))}</h3>
      </div>
      <p class="analogue-window-label">Exact resonance window:<span>${escapeHtml(compactPeriod(episodePeriod(episode)))}</span></p>
      ${renderAnalogueResonanceBasis(episode)}
      ${renderAnalogueSignal(episode)}
      <div class="analogue-events-block">
        <p class="card-label">Exact window events</p>
        <ul>
          ${
            exactEvents.length
              ? exactEvents.map(renderAnalogueEventItem).join("")
              : '<li class="empty-window-events">No major precisely dated events found in this resonance window.</li>'
          }
        </ul>
        ${
          contextEvents.length
            ? `
              <p class="card-label context-label">Broader historical context</p>
              <ul class="context-event-list">
                ${contextEvents.map(renderAnalogueEventItem).join("")}
              </ul>
            `
            : ""
        }
      </div>
      <button class="ghost-action" type="button" data-episode-index="${index}">View details</button>
    </article>
  `;
}

function renderAnalogueResonanceBasis(episode = {}) {
  const basis = episode.resonance_basis || {};
  const current = (basis.current_drivers || []).slice(0, 3).map((driver) => driver.label).filter(Boolean);
  const historical = (basis.historical_drivers || []).slice(0, 3).map((driver) => driver.label).filter(Boolean);
  if (!current.length && !historical.length) {
    return "";
  }
  return `
    <div class="analogue-basis" aria-label="Resonance basis">
      <p>Resonance basis</p>
      <div><span>Now</span><strong>${escapeHtml(current.join(" · ") || "not available")}</strong></div>
      <div><span>Then</span><strong>${escapeHtml(historical.join(" · ") || "not available")}</strong></div>
    </div>
  `;
}

function renderAnalogueEventItem(event = {}) {
  const dateLabel = analogueEventDateLabel(event);
  return `
    <li>
      <span class="analogue-event-date">${escapeHtml(dateLabel)}</span>
      <span>${escapeHtml(analogueEventTitle(event, dateLabel))}</span>
    </li>
  `;
}

function analogueEventDateLabel(event = {}) {
  const displayDate = String(event.display_date || "").trim();
  if (displayDate) {
    return displayDate;
  }
  const startYear = Number(event.start_astro_year);
  const endYear = Number(event.end_astro_year);
  if (Number.isFinite(startYear) && Number.isFinite(endYear)) {
    return startYear === endYear ? String(startYear) : `${startYear}-${endYear}`;
  }
  if (Number.isFinite(startYear)) {
    return String(startYear);
  }
  if (Number.isFinite(endYear)) {
    return String(endYear);
  }
  return "date n/a";
}

function analogueEventTitle(event = {}, dateLabel = "") {
  const title = String(event.title || "Untitled event").trim();
  const date = String(dateLabel || "").trim();
  if (date && title.toLowerCase().startsWith(`${date.toLowerCase()} `)) {
    return title.slice(date.length).trim();
  }
  return title;
}

function renderReferenceCycleLayers(payload) {
  const regimes = activeRegimeWindows(payload);
  const cycleWindows = activeCycleWindows(payload);
  const background = regimes.find((item) => item.driver_type === "sign_regime") || regimes[0];
  const structural = cycleWindows.slice(0, 2);
  const supporting = (payload.supporting_cycles || []).slice(0, 2);
  const shortTermRows = supporting.length
    ? supporting.map((cycle) => cycleLayerRowFromCycle(cycle, cycleWindows))
    : [
        {
          label: "Non-fixed resonance support",
          range: "continuous supporting layer",
          detail: "no fixed window",
        },
      ];
  return `
    <section class="reference-layers-panel">
      <div class="reference-panel-heading">
        <div>
          <p class="eyebrow">Cycle layers (what you are seeing)</p>
        </div>
        <span class="info-dot" title="Layer labels are derived from backend cycle windows.">i</span>
      </div>
      <div class="cycle-layer-stack">
        ${renderReferenceLayerCard({
          tone: "epoch",
          title: "Epoch Background",
          scale: "20+ years",
          rows: background
            ? [cycleLayerRowFromWindow(background, "Long planetary era")]
            : [{ label: "Active long-term field", range: "not fixed", detail: "background layer" }],
          copy: "The long-term atmosphere setting the world stage.",
        })}
        ${renderReferenceLayerCard({
          tone: "structural",
          title: "Structural Cycles",
          scale: "2-10 years",
          rows: structural.length
            ? structural.map((item) => cycleLayerRowFromWindow(item, "active chapter"))
            : [{ label: "Structural resonance layer", range: "not fixed", detail: "cycle window pending" }],
          copy: "The main active chapter shaping the strongest themes.",
        })}
        ${renderReferenceLayerCard({
          tone: "short",
          title: "Short-Term Cycles",
          scale: "days-2 years",
          rows: shortTermRows,
          copy: "Faster activators that support, trigger, or color the regime.",
        })}
      </div>
    </section>
  `;
}

function renderReferenceLayerCard({ tone, title, scale, rows, copy }) {
  const iconLabel = layerIconSource(tone, title, rows);
  return `
    <article class="cycle-layer-card ${tone}">
      <div class="cycle-layer-body">
        <span class="cycle-layer-icon">${renderPlanetGlyphIcon(iconLabel)}</span>
        <div class="cycle-layer-main">
          <p class="card-label">${escapeHtml(title)} (${escapeHtml(scale)})</p>
          <div class="cycle-layer-cycles">
            ${rows.map((row) => `<strong>${escapeLayerLabel(row.label)}</strong>`).join("")}
          </div>
          <p class="cycle-layer-copy">${escapeHtml(copy)}</p>
        </div>
        <div class="cycle-layer-dates">
          ${
            rows
              .map(
                (row) => `
                  <span>
                    <em>${escapeHtml(row.range)}</em>
                    <small>${escapeHtml(row.detail)}</small>
                  </span>
                `
              )
              .join("")
          }
        </div>
      </div>
    </article>
  `;
}

function layerIconSource(tone, title, rows) {
  if (tone === "short") {
    return "Jupiter";
  }
  const joined = rows.map((row) => row.label).join(" ");
  if (joined) {
    return joined;
  }
  return title;
}

function cycleLayerRowFromWindow(window = {}, fallbackDetail = "backend-derived window") {
  return {
    label: window.label || cycleTitle(window) || "Active cycle window",
    range: fullDateRangeFromDates(window.start_date, window.end_date) || "continuous layer",
    detail: peakDateLine(window.peak_date) || fallbackDetail,
  };
}

function cycleLayerRowFromCycle(cycle = {}, cycleWindows = []) {
  const window = windowForCycle(cycle, cycleWindows);
  if (window) {
    return cycleLayerRowFromWindow(window, "supporting window");
  }
  return {
    label: cycleLabel(cycle) || "Supporting resonance",
    range: "continuous support",
    detail: "non-fixed layer",
  };
}

function yearRangeFromDates(startDate, endDate) {
  const start = yearFromDate(startDate);
  const end = yearFromDate(endDate);
  if (start && end) {
    return start === end ? String(start) : `${start}-${end}`;
  }
  if (start || end) {
    return String(start || end);
  }
  return "";
}

function fullDateRangeFromDates(startDate, endDate) {
  const start = formatDisplayDate(startDate);
  const end = formatDisplayDate(endDate);
  if (start && end) {
    return start === end ? start : `${start} - ${end}`;
  }
  return start || end || "";
}

function peakDateLine(peakDate) {
  const value = String(peakDate || "").slice(0, 10);
  return value ? `peak ${value}` : "";
}

function escapeLayerLabel(label) {
  return escapeHtml(label).replace(/-/g, "&#8209;");
}

function renderReferenceTimelineOverlay(payload, selectedEpisode) {
  const cycles = activeCycleWindows(payload);
  const currentRange = activeCycleRange(cycles) || activeRegimeRange(activeRegimeWindows(payload));
  const matchRange = selectedEpisode ? episodePeriod(selectedEpisode) : "";
  const currentMarkers = regimeTimelineMarkers(payload);
  const matchMarkers = selectedEpisode ? episodeTimelineMarkers(selectedEpisode) : [];
  const queryDate = String(payload.query_datetime_utc || "").slice(0, 10);
  const currentLabel = regimeYearRange(currentRange) || "current";
  const matchLabel = selectedEpisode ? periodYears(selectedEpisode) : "match";
  return `
    <section class="reference-timeline-panel">
      <div class="reference-panel-heading compact">
        <div>
          <p class="eyebrow">Timeline overlay — current regime vs best match</p>
        </div>
        <div class="timeline-legend" aria-hidden="true">
          <span class="current">Current regime (${escapeHtml(currentLabel)})</span>
          <span class="match">Best match (${escapeHtml(selectedEpisode ? matchLabel : "none")})</span>
        </div>
        <span class="tool-chip readout-chip">Best match: ${escapeHtml(selectedEpisode ? matchLabel : "none")}</span>
      </div>
      ${renderResonanceTimelineSvg({
        currentRange,
        matchRange,
        currentLabel,
        matchLabel,
        currentMarkers,
        matchMarkers,
        currentFocusDate: queryDate,
        matchFocusDate: selectedEpisode?.best_date || selectedEpisode?.period_start || "",
      })}
    </section>
  `;
}

function renderSimpleCurrentRegime(payload) {
  const regimes = activeRegimeWindows(payload);
  const cycleWindows = activeCycleWindows(payload);
  const range = activeCycleRange(cycleWindows) || activeRegimeRange(regimes) || shortDate(payload.query_datetime_utc);
  const dominantCycles = dominantRegimeLabels(payload).slice(0, 4);
  const themes = conciseThemes(payload, historicalAnalogues(payload)[0]).slice(0, 4);
  return `
    <section class="simple-regime-panel">
      <div>
        <p class="eyebrow">1. Current Regime</p>
        <h2>${escapeHtml(regimeYearRange(range))}</h2>
        <p>Current planetary regime detected by the backend around the query date.</p>
      </div>
      <div class="simple-regime-column">
        <p class="card-label">Dominant cycles</p>
        <ul class="simple-list">
          ${
            dominantCycles.length
              ? dominantCycles.map((label) => `<li>${escapeHtml(label)}</li>`).join("")
              : "<li>No dominant cycle returned.</li>"
          }
        </ul>
      </div>
      <div class="simple-regime-column">
        <p class="card-label">Common themes</p>
        <ul class="simple-list">
          ${
            themes.length
              ? themes.map((theme) => `<li>${escapeHtml(theme)}</li>`).join("")
              : "<li>Not enough event evidence to summarize themes.</li>"
          }
        </ul>
      </div>
      <details class="simple-inline-advanced">
        <summary>Show exact cycle windows</summary>
        ${
          cycleWindows.length
            ? `<div class="cycle-window-list compact">${cycleWindows.map(renderCycleWindowCard).join("")}</div>`
            : `<p class="empty-copy">Cycle window metadata was not returned.</p>`
        }
      </details>
    </section>
  `;
}

function renderSimpleAnalogueSection(payload, episodes, selectedEpisode, selectedIndex) {
  const primaryCycles = payload.primary_cycles || [];
  const supportingCycles = payload.supporting_cycles || [];
  return `
    <section class="simple-analogue-panel">
      <div class="simple-panel-head">
        <div>
          <p class="eyebrow">2. Similar Historical Periods</p>
          <h2>Independent historical analogues</h2>
          <p>Nearby same-regime dates are excluded from this list and kept in Advanced.</p>
        </div>
        <span class="tool-chip readout-chip">${escapeHtml(selectedEpisode ? `Selected: ${episodePeriod(selectedEpisode)}` : "No selection")}</span>
      </div>
      <div class="simple-sky-stage">
        <div class="star-field" aria-hidden="true"></div>
        ${renderResonanceWheel(primaryCycles, supportingCycles)}
      </div>
      <div class="simple-analogue-grid">
        ${
          episodes.length
            ? episodes.map((episode, index) => renderSimpleAnalogueCard(episode, index, selectedIndex)).join("")
            : emptyState("No historical analogues", "The backend found no independent periods outside the current regime.")
        }
      </div>
    </section>
  `;
}

function renderSimpleAnalogueCard(episode, index, selectedIndex) {
  const events = (episode.matched_events || []).slice(0, 4);
  const themes = conciseThemes(null, episode).slice(0, 3);
  return `
    <button class="simple-analogue-card ${index === selectedIndex ? "selected" : ""}" type="button" data-episode-index="${index}">
      <span class="analogue-period">${escapeHtml(episodePeriod(episode))}</span>
      <strong>${escapeHtml(analogueLabel(episode))}</strong>
      <span class="subtle-line">Peak match: ${escapeHtml(episode.best_date || "--")}</span>
      <span class="confidence-pill">${percent(episode.narrative_confidence?.narrative_confidence)} confidence</span>
      <div class="theme-row">
        ${themes.map((theme) => `<span>${escapeHtml(theme)}</span>`).join("") || "<span>theme evidence limited</span>"}
      </div>
      <ul>
        ${
          events.length
            ? events.map((event) => `<li>${escapeHtml(event.title)}</li>`).join("")
            : "<li>No matched events returned.</li>"
        }
      </ul>
    </button>
  `;
}

function renderSimpleNarrativeSection(payload, episode, selectedIndex) {
  const themes = conciseThemes(payload, episode).slice(0, 5);
  return `
    <details class="simple-narrative-panel" id="analysis-detail">
      <summary>
        <span>What happened during ${escapeHtml(periodYears(episode))}?</span>
        <span>${percent(episode.narrative_confidence?.narrative_confidence)} confidence</span>
      </summary>
      <div class="simple-panel-head">
        <div>
          <p class="eyebrow">3. What Happened During Those Periods?</p>
          <h2>${escapeHtml(episodePeriod(episode))}</h2>
          <p class="subtle-line">Peak match: ${escapeHtml(episode.best_date || "--")} | selected analogue ${selectedIndex + 1}</p>
        </div>
        <span class="confidence-pill">${percent(episode.narrative_confidence?.narrative_confidence)} confidence</span>
      </div>
      <div class="narrative-grid">
        <article>
          <p class="card-label">Why this match?</p>
          <p>${escapeHtml(whyMatchLine(payload, episode))}</p>
          <div class="theme-row narrative-themes">
            ${themes.map((theme) => `<span>${escapeHtml(theme)}</span>`).join("")}
          </div>
        </article>
        <article>
          <p class="card-label">Key matched events</p>
          ${renderSimpleEventList(episode.matched_events, "matched")}
        </article>
        <article>
          <p class="card-label">Broader context</p>
          ${renderSimpleEventList(episode.context_events, "context")}
        </article>
      </div>
    </details>
  `;
}

function renderSimpleEventList(events = [], bucket) {
  if (!events.length) {
    return `<p class="empty-copy">No ${bucket === "context" ? "context" : "matched"} events returned.</p>`;
  }
  return `
    <div class="simple-event-list">
      ${events.slice(0, 5).map((event) => renderSimpleEvent(event, bucket)).join("")}
    </div>
  `;
}

function renderSimpleEvent(event, bucket) {
  return `
    <article class="simple-event">
      <div>
        <strong>${escapeHtml(event.title)}</strong>
        <span>${escapeHtml(event.display_date)} · ${escapeHtml(scopeLabel(event, bucket))}</span>
      </div>
      ${renderEventSources(event)}
    </article>
  `;
}

function renderAdvancedExplorerDetails(payload, episode) {
  const primaryCycles = payload.primary_cycles || [];
  const supportingCycles = payload.supporting_cycles || [];
  const local = payload.local_resonance;
  const localWindow = localResonanceWindow(payload);
  return `
    <details class="advanced-explorer-details">
      <summary>Advanced / technical details</summary>
      <div class="advanced-grid">
        <article>
          <p class="card-label">Local resonance window</p>
          ${
            local
              ? `<p>Nearest local peak: <strong>${escapeHtml(local.best_date || "--")}</strong></p>
                 <p>${escapeHtml(episodePeriod(local))}</p>
                 <p>${escapeHtml(localWindow.length ? `${localWindow.length} nearby/same-regime episodes returned.` : "No additional local episodes returned.")}</p>`
              : `<p>No local resonance window returned.</p>`
          }
        </article>
        <article>
          <p class="card-label">Exact active cycles</p>
          ${renderEpisodeCycles(primaryCycles, supportingCycles)}
        </article>
        <article>
          <p class="card-label">Backend diagnostics</p>
          ${renderCoverage(payload.index_coverage)}
          ${episode ? renderScoreBreakdown(episode.score_breakdown) : ""}
          ${episode ? renderConfidenceBreakdown(episode.narrative_confidence) : ""}
        </article>
        <article>
          <p class="card-label">Event category metrics</p>
          ${episode ? renderCategoryMixSummary(episode) : `<p class="empty-copy">No selected episode.</p>`}
        </article>
        <article>
          <p class="card-label">Query state</p>
          ${renderAdvancedQueryState(payload)}
        </article>
      </div>
    </details>
  `;
}

function renderAdvancedQueryState(payload) {
  return `
    <div class="query-state-list compact">
      <span><strong>Date</strong>${escapeHtml(shortDate(payload.query_datetime_utc))}</span>
      <span><strong>Profile</strong>${escapeHtml(payload.profile_id || "global_slow_v1")}</span>
      <span><strong>Index</strong>${escapeHtml(payload.index_artifact || DEFAULT_INDEX_FILE)}</span>
      <span><strong>Provider</strong>${escapeHtml(payload.provider || "backend")}</span>
    </div>
  `;
}

function renderCurrentSkyCard(payload) {
  const positions = getQueryPositions(payload);
  return `
    <article class="observatory-card current-sky-card">
      <div class="observatory-card-title">
        <p class="eyebrow">Current Sky</p>
        <span class="status-pill live">Live backend</span>
      </div>
      <p class="panel-note">${escapeHtml(shortDate(payload.query_datetime_utc))}</p>
      ${
        positions.length
          ? `<ul class="planet-list">${positions.map(renderPositionRow).join("")}</ul>`
          : `<div class="query-state-list">
              <span><strong>Date</strong>${escapeHtml(shortDate(payload.query_datetime_utc))}</span>
              <span><strong>Profile</strong>${escapeHtml(payload.profile_id || "global_slow_v1")}</span>
              <span><strong>Index</strong>${escapeHtml(payload.index_artifact || DEFAULT_INDEX_FILE)}</span>
              <span><strong>Provider</strong>${escapeHtml(payload.provider || "backend")}</span>
            </div>`
      }
    </article>
  `;
}

function renderActiveRegimeSection(payload) {
  const regimes = activeRegimeWindows(payload);
  const cycleWindows = activeCycleWindows(payload);
  const range = activeRegimeRange(regimes);
  const backgroundCycles = regimes.filter((item) => item.driver_type === "sign_regime");
  return `
    <section class="explorer-semantic-section current-regime-section">
      <div class="semantic-section-heading">
        <div>
          <p class="eyebrow">Section 1 - Current Active Regime</p>
          <h2>Current planetary regime detected by the engine</h2>
          <p>These are active cycle windows around the query date. They describe the current regime, not historical analogues.</p>
        </div>
        <span class="tool-chip readout-chip">${escapeHtml(range || "No active regime range")}</span>
      </div>
      <div class="regime-grid">
        <article class="semantic-card">
          <p class="card-label">Regime date range</p>
          <h3>${escapeHtml(range || shortDate(payload.query_datetime_utc))}</h3>
          <p>${escapeHtml(regimes.length ? `${regimes.length} active regime windows returned by backend.` : "No active regime windows returned by backend.")}</p>
        </article>
        <article class="semantic-card">
          <p class="card-label">Active cycle windows</p>
          ${cycleWindows.length ? `<div class="compact-list">${cycleWindows.map(renderCycleChip).join("")}</div>` : `<p>No cycle-window data returned for this date.</p>`}
        </article>
        <article class="semantic-card">
          <p class="card-label">Active background cycles</p>
          ${backgroundCycles.length ? `<div class="compact-list">${backgroundCycles.slice(0, 5).map(renderRegimeChip).join("")}</div>` : `<p>No slow-body background regimes returned.</p>`}
        </article>
      </div>
      ${
        cycleWindows.length
          ? `<div class="cycle-window-list">${cycleWindows.map(renderCycleWindowCard).join("")}</div>`
          : `<div class="empty-state compact">Cycle window unavailable. Backend returned active cycles without start/end window metadata.</div>`
      }
      ${regimes.length ? `<div class="regime-window-list">${regimes.map(renderRegimeWindowCard).join("")}</div>` : ""}
    </section>
  `;
}

function renderLocalResonanceSection(payload) {
  const local = payload.local_resonance;
  const policy = payload.analogue_policy || {};
  const localWindow = localResonanceWindow(payload);
  const regimes = activeRegimeWindows(payload);
  const count = policy.excluded_local_episodes_count || localWindow.length || 1;
  const topEvent = local?.matched_events?.[0];
  const nearbyDates = localWindow
    .map((episode) => episode.best_date)
    .filter(Boolean)
    .slice(0, 4);
  const additionalLocalEpisodes = localWindow
    .filter((episode) => episode.best_date !== local?.best_date)
    .slice(0, 4);
  return `
    <section class="explorer-semantic-section local-window-section">
      <div class="semantic-section-heading">
        <div>
          <p class="eyebrow">Section 2 - Local Resonance Window</p>
          <h2>Current cycle continuity</h2>
          <p>Nearby resonance inside the same active regime. Valid engine data, but not historical analogues.</p>
        </div>
        <span class="tool-chip readout-chip">${escapeHtml(local ? `Peak match: ${local.best_date}` : "No nearby match")}</span>
      </div>
      ${
        local
          ? `<div class="local-window-grid">
              <article class="semantic-card local-summary-card">
                <p class="card-label">Current-cycle continuity</p>
                <h3>${escapeHtml(episodePeriod(local))}</h3>
                <p>Kept separate from historical analogues because it sits inside the same active regime or local exclusion window.</p>
                <div class="query-state-list compact">
                  <span><strong>Peak match</strong>${escapeHtml(local.best_date || "--")}</span>
                  <span><strong>Top local event</strong>${escapeHtml(topEvent?.title || "none returned")}</span>
                  <span><strong>Score</strong>${escapeHtml(num(local.best_score, 3))}</span>
                  <span><strong>Nearby episodes</strong>${escapeHtml(String(count))}</span>
                  ${nearbyDates.length ? `<span><strong>Window dates</strong>${escapeHtml(nearbyDates.join(", "))}</span>` : ""}
                  ${regimes.length ? `<span><strong>Active regimes</strong>${escapeHtml(regimes.slice(0, 3).map((item) => item.label).join(", "))}</span>` : ""}
                </div>
              </article>
              ${
                additionalLocalEpisodes.length
                  ? additionalLocalEpisodes.map(renderLocalWindowEpisode).join("")
                  : `<article class="semantic-card local-window-episode"><p class="card-label">Nearby resonance</p><h3>No additional local episode</h3><p>The nearest local resonance is the only nearby episode returned.</p></article>`
              }
            </div>`
          : emptyState("No local resonance window", "The backend returned no same-regime nearby matches for this query.")
      }
    </section>
  `;
}

function renderKeyResonancesCard(primaryCycles = [], supportingCycles = [], cycleWindows = []) {
  return `
    <article class="observatory-card key-resonance-card">
      <p class="eyebrow">Key Resonances</p>
      ${cycleStack(primaryCycles, "Primary cycles", "No dominant primary cycle returned.", cycleWindows)}
      ${cycleStack(supportingCycles, "Supporting cycles", "No supporting cycles returned.", cycleWindows)}
    </article>
  `;
}

function renderPrimaryCyclesCard(primaryCycles = []) {
  return `
    <article class="observatory-card primary-cycles-card">
      <p class="eyebrow">Primary Cycles</p>
      ${
        primaryCycles.length
          ? primaryCycles.slice(0, 4).map(renderCycleBar).join("")
          : `<p class="empty-copy">No dominant primary cycle returned by backend for this date.</p>`
      }
    </article>
  `;
}

function renderConfidenceIndexCard(episode) {
  const confidence = episode?.narrative_confidence?.narrative_confidence;
  const score = episode?.score_breakdown || {};
  return `
    <article class="observatory-card confidence-index-card">
      <p class="eyebrow">Confidence Index</p>
      <div class="confidence-orbit" style="--confidence-deg: ${confidenceDegrees(confidence)}deg">
        <span>${percent(confidence)}</span>
        <small>${escapeHtml(score.label || "backend")}</small>
      </div>
      <ul class="confidence-metrics">
        <li><span>Event coverage</span><strong>${percent(episode?.narrative_confidence?.event_coverage_score)}</strong></li>
        <li><span>Source quality</span><strong>${percent(episode?.narrative_confidence?.source_quality_score)}</strong></li>
        <li><span>Evidence</span><strong>${percent(episode?.narrative_confidence?.evidence_confidence)}</strong></li>
        <li><span>Resonance</span><strong>${num(score.planetary_resonance_score, 3)}</strong></li>
      </ul>
    </article>
  `;
}

function renderHistoricalContextCard(episode) {
  const contextEvents = episode?.context_events || [];
  return `
    <article class="observatory-card context-observatory-card">
      <p class="eyebrow">Historical Context</p>
      ${
        contextEvents.length
          ? `<div class="context-timeline-list">${contextEvents.slice(0, 4).map(renderContextMini).join("")}</div>`
          : `<p class="empty-copy">No context events returned for the selected episode.</p>`
      }
    </article>
  `;
}

function renderAspectChips(primaryCycles = [], supportingCycles = []) {
  const aspects = [...primaryCycles, ...supportingCycles].map((cycle) => cycle.aspect).filter(Boolean);
  const uniqueAspects = [...new Set(aspects)].slice(0, 5);
  if (!uniqueAspects.length) {
    return `<span class="aspect-chip muted">No cycle aspects returned</span>`;
  }
  return uniqueAspects.map((aspect) => `<span class="aspect-chip">${escapeHtml(aspect)}</span>`).join("");
}

function renderCategoryFilterRow(episode) {
  const counts = categoryGroupCountsForEpisode(episode);
  const total = Object.values(counts).reduce((sum, count) => sum + count, 0);
  if (!total) {
    return "";
  }
  const buttons = [
    categoryFilterButton("all", `All evidence (${total})`),
    ...CATEGORY_GROUP_ORDER
      .filter((group) => counts[group])
      .map((group) => categoryFilterButton(group, `${CATEGORY_GROUP_META[group].label} (${counts[group]})`)),
  ];
  return `
    <div class="category-filter-row" aria-label="Event category filters">
      <span>Event lens</span>
      ${buttons.join("")}
    </div>
  `;
}

function categoryFilterButton(group, label) {
  return `
    <button
      class="category-filter-chip ${state.explorerCategoryFilter === group ? "active" : ""}"
      type="button"
      data-category-filter="${escapeHtml(group)}"
    >
      ${escapeHtml(label)}
    </button>
  `;
}

function renderCategoryMixSummary(episode) {
  const counts = categoryGroupCountsForEpisode(episode);
  const total = Object.values(counts).reduce((sum, count) => sum + count, 0);
  if (!total) {
    return "";
  }
  const rows = CATEGORY_GROUP_ORDER
    .filter((group) => counts[group])
    .map((group) => {
      const share = counts[group] / total;
      return `
        <span class="category-mix-item" data-category-group="${escapeHtml(group)}">
          <strong>${escapeHtml(CATEGORY_GROUP_META[group].label)}</strong>
          <meter min="0" max="1" value="${share}"></meter>
          <em>${counts[group]}/${total}</em>
        </span>
      `;
    })
    .join("");
  return `
    <div class="category-mix-summary">
      <p class="card-label">Civilizational event mix</p>
      ${rows}
    </div>
  `;
}

function categoryMixHeadline(episode) {
  const counts = categoryGroupCountsForEpisode(episode);
  const entries = Object.entries(counts).sort((left, right) => right[1] - left[1]);
  if (!entries.length) {
    return "No event mix";
  }
  const [group, count] = entries[0];
  return `${CATEGORY_GROUP_META[group]?.label || "Event mix"} x${count}`;
}

function renderResonanceWheel(primaryCycles = [], supportingCycles = []) {
  const cycles = [...primaryCycles, ...supportingCycles].slice(0, 8);
  return `
    <div class="resonance-wheel" aria-label="Backend cycle resonance visual">
      <span class="wheel-sun"></span>
      <span class="wheel-orbit orbit-a"></span>
      <span class="wheel-orbit orbit-b"></span>
      <span class="wheel-orbit orbit-c"></span>
      <span class="wheel-orbit orbit-d"></span>
      <span class="wheel-ray ray-a"></span>
      <span class="wheel-ray ray-b"></span>
      <span class="wheel-ray ray-c"></span>
      ${
        cycles.length
          ? cycles.map((cycle, index) => renderWheelMarker(cycle, index, cycles.length)).join("")
          : `<span class="wheel-empty">No cycle markers</span>`
      }
    </div>
  `;
}

function renderWheelMarker(cycle, index, total) {
  const angle = Math.round((360 / Math.max(total, 1)) * index - 82);
  const radius = 38 + (index % 3) * 8;
  const radians = (angle * Math.PI) / 180;
  const x = 50 + Math.cos(radians) * radius;
  const y = 50 + Math.sin(radians) * radius;
  return `
    <span class="wheel-marker" style="--x: ${x}%; --y: ${y}%">
      ${escapeHtml(cycleInitials(cycle))}
    </span>
  `;
}

function renderActiveResonanceCard(cycle, episode, confidence) {
  const cycleName = cycle?.label || cycleTitle(cycle);
  return `
    <article class="active-resonance-card">
      <p class="eyebrow">Active resonance</p>
      <h2>${escapeHtml(cycle ? cycleName : "No dominant cycle")}</h2>
      <span class="resonance-type">${escapeHtml(cycle?.aspect || episode?.score_breakdown?.label || "backend result")}</span>
      <strong>${percent(confidence)}</strong>
      <dl>
        <div>
          <dt>Matching resonance window</dt>
          <dd>${escapeHtml(episodePeriod(episode))}</dd>
        </div>
        <div>
          <dt>Peak match</dt>
          <dd>${escapeHtml(episode?.best_date || "--")}</dd>
        </div>
      </dl>
      <button class="text-action" type="button" data-action="open-analysis">Open analysis</button>
    </article>
  `;
}

function renderEpisodeTimeline(episodes = [], selectedIndex = 0) {
  if (!episodes.length) {
    return `<section class="observatory-timeline">${emptyState("No timeline", "The backend returned no episodes.")}</section>`;
  }
  const years = episodes.map((episode) => yearFromDate(episode.best_date)).filter((year) => year !== null);
  const minYear = years.length ? Math.min(...years) : 0;
  const maxYear = years.length ? Math.max(...years) : minYear;
  return `
    <section class="observatory-timeline">
      <div class="timeline-rule">
        ${episodes.map((episode, index) => renderTimelineMarker(episode, index, selectedIndex, minYear, maxYear)).join("")}
      </div>
      <div class="timeline-episode-cards">
        ${episodes.map((episode, index) => renderTimelineEpisodeCard(episode, index, selectedIndex)).join("")}
      </div>
    </section>
  `;
}

function renderTimelineMarker(episode, index, selectedIndex, minYear, maxYear) {
  const year = yearFromDate(episode.best_date);
  const span = Math.max(maxYear - minYear, 1);
  const left = year === null ? 50 : ((year - minYear) / span) * 84 + 8;
  return `
    <button
      class="timeline-marker ${index === selectedIndex ? "selected" : ""}"
      type="button"
      data-episode-index="${index}"
      style="left: ${left}%"
      aria-label="Select episode ${index + 1}"
    >
      <span>${escapeHtml(year || episode.best_date || index + 1)}</span>
    </button>
  `;
}

function renderTimelineEpisodeCard(episode, index, selectedIndex) {
  const mainEvent = episode.matched_events?.[0];
  const categoryGroup = eventCategoryGroup(mainEvent);
  return `
    <button class="timeline-episode-card ${index === selectedIndex ? "selected" : ""}" type="button" data-episode-index="${index}">
      <strong>${escapeHtml(episodePeriod(episode))}</strong>
      ${mainEvent ? categoryBadge(categoryGroup) : ""}
      <em>Peak match: ${escapeHtml(episode.best_date || "--")}</em>
      <span>${escapeHtml(mainEvent?.title || "No matched event")}</span>
      <p>${escapeHtml(compactEpisodeLine(episode))}</p>
    </button>
  `;
}

function renderExplorerAnalysis(payload, episode, selectedIndex) {
  return `
    <section class="explorer-analysis-detail" id="analysis-detail">
      <div class="analysis-summary-card">
        <p class="eyebrow">Selected episode ${selectedIndex + 1}</p>
        <h2>${escapeHtml(episodePeriod(episode))} historical analogue window</h2>
        <p class="panel-note">Peak match: ${escapeHtml(episode.best_date || "--")}</p>
        <p>${escapeHtml(shortSummary(payload.deterministic_summary, 360))}</p>
        ${renderCategoryMixSummary(episode)}
      </div>
      <div class="analysis-grid">
        <article class="analysis-card why-card">
          <p class="eyebrow">Why this match?</p>
          <p>${escapeHtml(whyMatchLine(payload, episode))}</p>
          ${renderEpisodeCycles(payload.primary_cycles, payload.supporting_cycles)}
        </article>
        <article class="analysis-card">
          <p class="eyebrow">Matched events</p>
          ${renderGroupedEvents(episode.matched_events, { bucket: "matched" })}
        </article>
        <article class="analysis-card">
          <p class="eyebrow">Context events</p>
          ${renderGroupedEvents(episode.context_events, { bucket: "context" })}
        </article>
      </div>
      <details class="technical-details analysis-technical">
        <summary>Technical details</summary>
        ${renderCoverage(payload.index_coverage)}
        ${renderScoreBreakdown(episode.score_breakdown)}
        ${renderConfidenceBreakdown(episode.narrative_confidence)}
      </details>
    </section>
  `;
}

function renderCompare() {
  appRoot.innerHTML = `
    <section class="page-shell compare-page">
      <div class="page-heading compact-heading">
        <p class="eyebrow">Compare</p>
        <h1>Compare two dates</h1>
        <p>Send both dates to the deterministic backend and inspect shared cycles and event evidence.</p>
      </div>
      <form class="analysis-form compare-form" id="compareForm">
        <label>Date A <input name="left" value="1789-07-14" autocomplete="off" /></label>
        <label>Date B <input name="right" value="1848-02-24" autocomplete="off" /></label>
        <button class="primary-action" type="submit">Compare</button>
        <div class="example-row">
          <button type="button" data-compare-left="1789-07-14" data-compare-right="1848-02-24">1789 vs 1848</button>
          <button type="button" data-compare-left="1989-11-09" data-compare-right="2020-01-12">1989 vs 2020</button>
        </div>
      </form>
      <div id="compareResult">
        ${state.currentCompare ? renderCompareResult(state.currentCompare) : emptyState("No comparison yet", "Choose two dates and run Compare.")}
      </div>
    </section>
  `;
}

async function runCompare(request, options = {}) {
  if (options.navigate) {
    state.currentView = "compare";
    syncNav();
    renderCompare();
  }
  (document.querySelector("#compareResult") || appRoot).innerHTML = loadingState(
    "Comparing dates with POST /resonance/compare"
  );
  try {
    const payload = await apiRequest("/resonance/compare", {
      method: "POST",
      body: request,
    });
    state.currentCompare = payload;
    if (state.currentView === "compare") {
      (document.querySelector("#compareResult") || appRoot).innerHTML =
        renderCompareResult(payload);
    }
  } catch (error) {
    (document.querySelector("#compareResult") || appRoot).innerHTML = errorState(
      "Compare failed",
      errorMessage(error)
    );
  }
}

function renderCompareResult(payload) {
  return `
    <section class="result-header">
      <div>
        <p class="eyebrow">Similarity score</p>
        <h2>${percent(payload.query_vector_similarity)} similarity</h2>
        <p>${escapeHtml(payload.deterministic_summary)}</p>
      </div>
      <div class="result-meta">
        <span>${escapeHtml(String(payload.shared_primary_cycles?.length || 0))} common cycles</span>
        <span>${escapeHtml(String(payload.shared_matched_event_ids?.length || 0))} shared matched events</span>
        <span>${escapeHtml(String(payload.shared_context_event_ids?.length || 0))} shared context events</span>
      </div>
    </section>
    <section class="product-card">
      <p class="card-label">Common cycles</p>
      <div class="compact-list">${eventIdChips(payload.shared_primary_cycles)}</div>
    </section>
    <section class="product-card">
      <p class="card-label">Shared motifs and events returned by backend</p>
      <div class="compact-list">${eventIdChips(payload.shared_matched_event_ids)}</div>
      <div class="compact-list">${eventIdChips(payload.shared_context_event_ids)}</div>
    </section>
    ${renderWarnings(payload.warnings)}
    <div class="compare-grid">
      ${renderCompareSide("Date A", payload.left)}
      ${renderCompareSide("Date B", payload.right)}
    </div>
  `;
}

function renderCalendar() {
  const seeds = state.timelineSeeds?.seeds || [];
  appRoot.innerHTML = `
    <section class="page-shell">
      <div class="page-heading compact-heading">
        <p class="eyebrow">Calendar</p>
        <h1>Timeline seeds</h1>
        <p>Backend-authored historical anchors from GET /timeline/seeds. These are research starts, not predictions.</p>
      </div>
      <div class="seed-grid timeline-seed-grid">
        ${seeds.length ? seeds.map(renderTimelineSeed).join("") : emptyState("No timeline seeds", "GET /timeline/seeds returned no seeds or the backend is unavailable.")}
      </div>
    </section>
  `;
}

function renderInsights() {
  const seeds = state.articleSeeds?.seeds || [];
  appRoot.innerHTML = `
    <section class="page-shell">
      <div class="page-heading compact-heading">
        <p class="eyebrow">Insights</p>
        <h1>AI-assisted article seeds</h1>
        <p>Seed-only research topics from GET /articles/seeds. No live AI text is generated here.</p>
      </div>
      <div class="seed-grid">
        ${seeds.length ? seeds.map(renderArticleSeed).join("") : emptyState("No article seeds", "GET /articles/seeds returned no seeds or the backend is unavailable.")}
      </div>
    </section>
  `;
}

function renderLibrary() {
  appRoot.innerHTML = `
    <section class="page-shell">
      <div class="page-heading compact-heading">
        <p class="eyebrow">Library</p>
        <h1>Knowledge base</h1>
        <p>Static educational shell for the concepts users need before reading engine results.</p>
      </div>
      <div class="feature-grid">
        ${featureCard("Planetary cycles", "Slow cycles are the primary symbolic drivers in the resonance engine.")}
        ${featureCard("Aspects", "Conjunctions, squares, trines, sextiles and oppositions describe geometric relationships.")}
        ${featureCard("Matched vs context events", "Matched events are direct evidence; context events are broad historical background.")}
        ${featureCard("Confidence", "Confidence combines event coverage, source quality and evidence strength returned by the backend.")}
        ${featureCard("Sources", "Curated source links stay attached to events so claims remain inspectable.")}
      </div>
    </section>
  `;
}

function renderBlog() {
  appRoot.innerHTML = `
    <section class="page-shell">
      <div class="page-heading compact-heading">
        <p class="eyebrow">Blog</p>
        <h1>Magazyn analityczny</h1>
        <p>Miejsce na wpisy, komentarze do cykli, analizy astrologiczne i teksty autorskie.</p>
      </div>
      <div class="feature-grid">
        ${articlePlaceholder("Analiza", "Komentarz do bieżących cykli", "Tekst autorski, nie live AI.")}
        ${articlePlaceholder("Edukacja", "Jak czytać rezonanse historyczne", "Manualny materiał wyjaśniający.")}
        ${articlePlaceholder("Notatnik", "Obserwacje astrologiczne", "Przestrzeń redakcyjna na kolejne wpisy.")}
      </div>
    </section>
  `;
}

function renderEngine() {
  appRoot.innerHTML = `
    <section class="page-shell">
      <div class="page-heading compact-heading">
        <p class="eyebrow">O silniku</p>
        <h1>Metodologia i ograniczenia</h1>
        <p>Transparentność projektu: Swiss Ephemeris, resonance engine, curated historical data, matching historyczny i granice użycia AI.</p>
      </div>
      <div class="feature-grid">
        ${featureCard("Swiss Ephemeris", "Pozycje planet pochodzą z deterministycznej warstwy ephemeris, a nie z modelu językowego.")}
        ${featureCard("Historical matching", "Podobieństwo liczone jest na wektorach cykli i konfiguracji, a wydarzenia są osobną warstwą evidence.")}
        ${featureCard("No prediction policy", "Astro Global nie sprzedaje pewnych prognoz. Pokazuje analogie, źródła i ograniczenia danych.")}
        ${featureCard("Reliable range", "Główny indeks historyczny obejmuje zakres od 1500 roku, z jawną informacją o pokryciu danych.")}
      </div>
      <div class="hero-actions">
        <a class="secondary-action" href="./transparency/">Pełna transparentność</a>
      </div>
    </section>
  `;
}

function renderContact() {
  appRoot.innerHTML = `
    <section class="page-shell contact-page">
      <div class="page-heading compact-heading">
        <p class="eyebrow">Kontakt</p>
        <h1>Skontaktuj się</h1>
        <p>Formularz kontaktowy jest na razie lokalnym placeholderem. Nie wysyła danych do backendu.</p>
      </div>
      <form class="contact-form product-card" id="contactForm">
        <label>Imię <input name="name" autocomplete="name" /></label>
        <label>Email <input name="email" type="email" autocomplete="email" /></label>
        <label class="wide-field">Wiadomość <textarea name="message" rows="5"></textarea></label>
        <label>Social media <input name="social" placeholder="opcjonalnie" /></label>
        <label>Temat <input name="topic" placeholder="analiza, współpraca, pytanie" /></label>
        <label>Email publiczny <input name="publicEmail" placeholder="kontakt@astro.global" disabled /></label>
        <p class="privacy-note wide-field">
          Dane kontaktowe i social media zostaną docelowo podpięte po decyzji właściciela projektu.
        </p>
        <button class="primary-action" type="submit">Przygotuj wiadomość</button>
        <span class="form-state" id="contactState" aria-live="polite"></span>
      </form>
    </section>
  `;
}

function renderLogin() {
  appRoot.innerHTML = `
    <section class="page-shell">
      <div class="page-heading compact-heading">
        <p class="eyebrow">Logowanie</p>
        <h1>Panel w przygotowaniu</h1>
        <p>Tu trafi panel administratora, workflow wpisów, pipeline interpretacji i drafty AI dla astrologa.</p>
      </div>
      <div class="feature-grid">
        ${featureCard("Admin", "Zarządzanie treściami i ustawieniami projektu.")}
        ${featureCard("Draft AI", "Pomocnicze szkice wymagające kontroli człowieka.")}
        ${featureCard("Workflow astrologa", "Przyszły pipeline prywatnych interpretacji i publikacji.")}
      </div>
    </section>
  `;
}

function renderTimelineSeed(seed) {
  return `
    <article class="research-card seed-card">
      <p class="card-label">${escapeHtml(seed.display_date)}</p>
      <h3>${escapeHtml(seed.title)}</h3>
      <p>${escapeHtml(seed.category)} in ${escapeHtml(seed.region)}. Date policy: ${escapeHtml(seed.date_precision)}.</p>
      ${badgeRow([seed.event_kind, seed.geo_scope, percent(seed.confidence_score)])}
      <button class="text-action" type="button" data-seed-id="${escapeHtml(seed.seed_id)}">Recommended search</button>
    </article>
  `;
}

function renderArticleSeed(seed) {
  return `
    <article class="research-card seed-card">
      <p class="card-label">Draft only / human review required</p>
      <h3>${escapeHtml(seed.title)}</h3>
      <p>${escapeHtml(seed.summary)}</p>
      ${badgeRow(["Draft only / human review required", seed.seed_kind, seed.compare_preset_id])}
      <div class="compact-list">
        ${(seed.source_event_ids || []).map((eventId) => `<span>${escapeHtml(eventId)}</span>`).join("")}
      </div>
      <button class="text-action" type="button" data-article-id="${escapeHtml(seed.seed_id)}">Run related compare</button>
    </article>
  `;
}

function renderCompareSide(label, search) {
  const first = historicalAnalogues(search)[0];
  return `
    <article class="episode-card product-episode">
      <p class="card-label">${escapeHtml(label)}</p>
      <h3>${escapeHtml(shortDate(search?.query_datetime_utc))}</h3>
      <p>${escapeHtml(summaryText(search?.deterministic_summary))}</p>
      ${first ? renderMiniEpisode(first) : emptyState("No episode", "No episode returned for this side.")}
    </article>
  `;
}

function renderMiniEpisode(episode) {
  return `
    <div class="metric-grid">
      <span><strong>${escapeHtml(episodePeriod(episode))}</strong> window</span>
      <span><strong>${escapeHtml(episode.best_date)}</strong> peak match</span>
      <span><strong>${percent(episode.narrative_confidence?.narrative_confidence)}</strong> confidence</span>
      <span><strong>${escapeHtml(episode.score_breakdown?.label || "score")}</strong> label</span>
    </div>
    <div class="event-columns">
      <section>
        <p class="eyebrow">Matched events</p>
        ${renderEvents(episode.matched_events)}
      </section>
      <section>
        <p class="eyebrow">Context events</p>
        ${renderEvents(episode.context_events)}
      </section>
    </div>
  `;
}

function clampEpisodeIndex(index, episodes = []) {
  if (!episodes.length) {
    return 0;
  }
  const parsed = Number(index);
  if (!Number.isFinite(parsed)) {
    return 0;
  }
  return Math.min(Math.max(parsed, 0), episodes.length - 1);
}

function getQueryPositions(payload) {
  const candidates = [
    payload?.query_planetary_positions,
    payload?.planetary_positions,
    payload?.query_positions,
  ];
  return candidates.find((value) => Array.isArray(value)) || [];
}

function historicalAnalogues(payload) {
  return payload?.historical_analogues || payload?.episodes || [];
}

function localResonanceWindow(payload) {
  return payload?.local_resonance_window || payload?.nearby_matches || [];
}

function activeRegimeWindows(payload) {
  const windows = payload?.active_regime_windows;
  if (Array.isArray(windows) && windows.length) {
    return windows;
  }
  return payload?.active_background_cycles || [];
}

function activeCycleWindows(payload) {
  const windows = payload?.active_cycle_windows;
  if (Array.isArray(windows) && windows.length) {
    return windows;
  }
  return payload?.regime_cycle_windows || [];
}

function activeRegimeRange(regimes = []) {
  const starts = regimes.map((item) => item.start_date).filter(Boolean).sort();
  const ends = regimes.map((item) => item.end_date).filter(Boolean).sort();
  if (!starts.length || !ends.length) {
    return "";
  }
  return `${starts[0]} to ${ends[ends.length - 1]}`;
}

function activeCycleRange(cycleWindows = []) {
  const starts = cycleWindows.map((item) => item.start_date).filter(Boolean).sort();
  const ends = cycleWindows.map((item) => item.end_date).filter(Boolean).sort();
  if (!starts.length || !ends.length) {
    return "";
  }
  return `${starts[0]} to ${ends[ends.length - 1]}`;
}

function regimeYearRange(range) {
  const years = String(range || "").match(/\d{4}/g) || [];
  if (years.length >= 2) {
    return years[0] === years[years.length - 1] ? years[0] : `${years[0]}–${years[years.length - 1]}`;
  }
  return range || "--";
}

function dominantRegimeLabels(payload) {
  const cycleLabels = activeCycleWindows(payload)
    .map((window) => window.label || cycleTitle(window))
    .filter(Boolean);
  const backgroundLabels = activeRegimeWindows(payload)
    .filter((window) => window.driver_type === "sign_regime")
    .map((window) => window.label)
    .filter(Boolean);
  return [...cycleLabels, ...backgroundLabels].slice(0, 4);
}

function windowForDominantLabel(label, cycleWindows, regimeWindows, index) {
  const normalized = String(label || "").toLowerCase();
  const cycleWindow = cycleWindows.find((window) =>
    String(window.label || cycleTitle(window)).toLowerCase() === normalized
  );
  if (cycleWindow) {
    return cycleWindow;
  }
  const regimeWindow = regimeWindows.find((window) =>
    String(window.label || "").toLowerCase() === normalized
  );
  return regimeWindow || cycleWindows[index];
}

function cycleWindowDisplayRange(window = {}) {
  if (!window?.start_date && !window?.end_date) {
    return ["window unavailable"];
  }
  const start = String(window.start_date || window.end_date || "").slice(0, 10);
  const end = String(window.end_date || window.start_date || "").slice(0, 10);
  const startLabel = formatDisplayDate(start);
  const endLabel = formatDisplayDate(end);
  if (startLabel && endLabel) {
    return startLabel === endLabel ? [startLabel] : [startLabel, endLabel];
  }
  return [startLabel || endLabel || start || end || "--"];
}

function conciseThemes(payload, episode) {
  const events = [
    ...(episode?.matched_events || []),
    ...(episode?.context_events || []),
  ];
  const groups = categoryGroupCounts(events);
  const themes = Object.entries(groups)
    .sort((left, right) => right[1] - left[1])
    .map(([group]) => THEME_LABELS[group] || CATEGORY_GROUP_META[group]?.label)
    .filter(Boolean);
  if (payload) {
    const background = activeRegimeWindows(payload)
      .filter((window) => window.driver_type === "sign_regime")
      .map((window) => signTheme(window.label))
      .filter(Boolean);
    themes.push(...background);
  }
  return [...new Set(themes)].slice(0, 5);
}

function signTheme(label = "") {
  if (label.includes("Gemini")) {
    return "communication and network acceleration";
  }
  if (label.includes("Aquarius")) {
    return "technological and institutional redesign";
  }
  if (label.includes("Aries")) {
    return "new cycle initiation";
  }
  if (label.includes("Capricorn")) {
    return "state and institutional pressure";
  }
  return "";
}

function analogueLabel(episode = {}) {
  const event = episode.matched_events?.[0];
  if (event?.title) {
    return event.title;
  }
  const label = episode.score_breakdown?.label;
  return label ? `${label} resonance period` : "Historical resonance period";
}

function renderRegimeChip(regime) {
  return `<span>${escapeHtml(regime.label || "Active regime")}</span>`;
}

function renderCycleChip(cycle) {
  return `<span>${escapeHtml(`${cycleTitle(cycle)} ${cycle.aspect || ""}`.trim())}</span>`;
}

function renderCycleWindowCard(window) {
  return `
    <article class="cycle-window-card">
      <div>
        <p class="card-label">${escapeHtml(window.role || "cycle")}</p>
        <strong>${escapeHtml(window.label || cycleTitle(window))}</strong>
        <span>${escapeHtml(window.aspect || "cycle aspect")}</span>
      </div>
      <div class="window-axis">
        <span><em>Start</em>${escapeHtml(window.start_date || "window unavailable")}</span>
        <span><em>Peak</em>${escapeHtml(window.peak_date || "window unavailable")}</span>
        <span><em>End</em>${escapeHtml(window.end_date || "window unavailable")}</span>
      </div>
      <p>${escapeHtml(cycleWindowMetrics(window))}</p>
    </article>
  `;
}

function renderRegimeWindowCard(regime) {
  return `
    <article class="regime-window-card">
      <strong>${escapeHtml(regime.label || "Active regime")}</strong>
      <span>${escapeHtml(regime.start_date || "--")} - ${escapeHtml(regime.end_date || "--")}</span>
      <em>${escapeHtml(regime.driver_type || "regime")}</em>
    </article>
  `;
}

function renderLocalWindowEpisode(episode) {
  const topEvent = episode?.matched_events?.[0];
  return `
    <article class="semantic-card local-window-episode">
      <p class="card-label">Nearby resonance</p>
      <h3>${escapeHtml(episodePeriod(episode))}</h3>
      <p>Peak match: ${escapeHtml(episode.best_date || "nearby date")}</p>
      <div class="metric-grid compact-metrics">
        <span><strong>${escapeHtml(num(episode.best_score, 3))}</strong> score</span>
        <span><strong>${escapeHtml(topEvent?.title || "none")}</strong> top event</span>
      </div>
    </article>
  `;
}

function renderPositionRow(position) {
  const name = position.name || position.planet || position.body || "Planet";
  const value = position.formatted || position.longitude_label || position.sign || position.longitude_deg || "--";
  return `<li><span>${escapeHtml(name)}</span><strong>${escapeHtml(value)}</strong></li>`;
}

function cycleStack(cycles = [], label, emptyMessage, cycleWindows = []) {
  return `
    <section class="cycle-stack">
      <h3>${escapeHtml(label)}</h3>
      ${
        cycles.length
          ? cycles.slice(0, 4).map((cycle) => renderCycleLine(cycle, cycleWindows)).join("")
          : `<p class="empty-copy">${escapeHtml(emptyMessage)}</p>`
      }
    </section>
  `;
}

function renderCycleLine(cycle, cycleWindows = []) {
  const window = windowForCycle(cycle, cycleWindows);
  return `
    <article class="cycle-line">
      <span class="cycle-symbol">${escapeHtml(cycleInitials(cycle))}</span>
      <div>
        <h4>${escapeHtml(cycleTitle(cycle))}</h4>
        <p>${escapeHtml(cycleMeta(cycle))}</p>
        <small>${escapeHtml(window ? cycleWindowRange(window) : "window unavailable")}</small>
      </div>
      <strong>${escapeHtml(orbText(cycle))}</strong>
    </article>
  `;
}

function renderCycleBar(cycle) {
  const closeness = typeof cycle.closeness === "number" ? Math.max(0, Math.min(1, cycle.closeness)) : 0;
  return `
    <article class="cycle-bar">
      <div>
        <strong>${escapeHtml(cycleTitle(cycle))}</strong>
        <span>${escapeHtml(cycle.aspect || "cycle")}</span>
      </div>
      <meter min="0" max="1" value="${closeness}"></meter>
      <p>${escapeHtml(cycleMeta(cycle))}</p>
    </article>
  `;
}

function renderContextMini(event) {
  return `
    <article class="context-mini">
      <span>${escapeHtml(event.display_date || "--")}</span>
      <div>
        <h4>${escapeHtml(event.title || "Context event")}</h4>
        <p>${escapeHtml([event.category, event.event_kind].filter(Boolean).join(" | "))}</p>
      </div>
    </article>
  `;
}

function confidenceDegrees(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return 0;
  }
  return Math.round(Math.max(0, Math.min(1, value)) * 360);
}

function cycleInitials(cycle = {}) {
  const pair = cyclePair(cycle);
  if (!pair.length) {
    return "?";
  }
  return pair.map((item) => String(item).trim().charAt(0).toUpperCase()).join("");
}

function cycleInitialsFromLabel(label = "") {
  const matches = String(label).match(/[A-Z][a-z]+/g) || [];
  if (!matches.length) {
    return "--";
  }
  return matches.slice(0, 2).map((item) => item.charAt(0)).join("");
}

function cycleTitle(cycle = {}) {
  const pair = cyclePair(cycle).join(" - ");
  return pair || "Unknown cycle";
}

function cyclePair(cycle = {}) {
  if (Array.isArray(cycle.pair)) {
    return cycle.pair;
  }
  if (Array.isArray(cycle.planets)) {
    return cycle.planets;
  }
  return [];
}

function cycleMeta(cycle = {}) {
  const parts = [];
  if (cycle.aspect) {
    parts.push(cycle.aspect);
  }
  if (cycle.phase_role) {
    parts.push(cycle.phase_role);
  }
  if (cycle.tier) {
    parts.push(cycle.tier);
  }
  if (typeof cycle.cycle_years === "number") {
    parts.push(`${num(cycle.cycle_years, 1)}y cycle`);
  }
  return parts.join(" | ") || "cycle";
}

function orbText(cycle = {}) {
  const orb = typeof cycle.orb_deg === "number" ? cycle.orb_deg : cycle.orb_at_query;
  return typeof orb === "number" ? `${num(orb, 2)} deg` : "--";
}

function windowForCycle(cycle = {}, cycleWindows = []) {
  const pair = cyclePair(cycle).join("|");
  const aspect = cycle.aspect || "";
  return cycleWindows.find((window) => {
    const windowPair = cyclePair(window).join("|");
    return windowPair === pair && (window.aspect || "") === aspect;
  });
}

function cycleWindowRange(window = {}) {
  if (!window.start_date || !window.end_date) {
    return "window unavailable";
  }
  return `${window.start_date} to ${window.end_date}`;
}

function cycleWindowMetrics(window = {}) {
  const parts = [];
  if (typeof window.orb_at_query === "number") {
    parts.push(`orb at query ${num(window.orb_at_query, 2)} deg`);
  }
  if (typeof window.closeness_at_query === "number") {
    parts.push(`closeness ${percent(window.closeness_at_query)}`);
  }
  parts.push(window.confidence_scope || "backend-derived window");
  return parts.join(" | ");
}

function episodePeriod(episode) {
  if (!episode) {
    return "--";
  }
  if (episode.period_start && episode.period_end && episode.period_start !== episode.period_end) {
    return `${episode.period_start} to ${episode.period_end}`;
  }
  return episode.period_start || episode.period_end || "--";
}

function periodYears(episode = {}) {
  return regimeYearRange(episodePeriod(episode));
}

function analogueCardYears(episode = {}) {
  return periodYears(episode);
  const bestYear = yearFromDate(episode.best_date || episode.period_start);
  const eventYears = (episode.matched_events || [])
    .slice(0, 4)
    .map((event) => Number(event.start_astro_year) || yearFromDate(event.display_date))
    .filter((year) => Number.isFinite(year))
    .filter((year) => !bestYear || Math.abs(year - bestYear) <= 3)
    .sort((left, right) => left - right);
  if (eventYears.length >= 2) {
    return eventYears[0] === eventYears[eventYears.length - 1]
      ? String(eventYears[0])
      : `${eventYears[0]}–${eventYears[eventYears.length - 1]}`;
  }
  return analogueEvidenceYears(episode);
}

function analogueEvidenceYears(episode = {}) {
  return analogueEvidenceYearsFromEvidence(episode);
  const years = (episode.matched_events || [])
    .slice(0, 4)
    .map((event) => Number(event.start_astro_year) || yearFromDate(event.display_date))
    .filter((year) => Number.isFinite(year))
    .sort((left, right) => left - right);
  if (years.length >= 2) {
    return years[0] === years[years.length - 1] ? String(years[0]) : `${years[0]}–${years[years.length - 1]}`;
  }
  return periodYears(episode);
}

function analogueCardYearsFromEvidence(episode = {}) {
  const bestYear = yearFromDate(episode.best_date || episode.period_start);
  const eventYears = analogueEvidenceEventsForHeading(episode)
    .flatMap(analogueEventYearsForHeading)
    .filter((year) => Number.isFinite(year))
    .filter((year) => !bestYear || Math.abs(year - bestYear) <= 3)
    .sort((left, right) => left - right);
  if (eventYears.length >= 2) {
    return eventYears[0] === eventYears[eventYears.length - 1]
      ? String(eventYears[0])
      : `${eventYears[0]}-${eventYears[eventYears.length - 1]}`;
  }
  return analogueEvidenceYearsFromEvidence(episode);
}

function analogueEvidenceYearsFromEvidence(episode = {}) {
  const years = analogueEvidenceEventsForHeading(episode)
    .flatMap(analogueEventYearsForHeading)
    .filter((year) => Number.isFinite(year))
    .sort((left, right) => left - right);
  if (years.length >= 2) {
    return years[0] === years[years.length - 1] ? String(years[0]) : `${years[0]}-${years[years.length - 1]}`;
  }
  return periodYears(episode);
}

function analogueEvidenceEventsForHeading(episode = {}) {
  return [...(episode.matched_events || []), ...(episode.context_events || [])]
    .filter((event) => {
      const startYear = Number(event.start_astro_year);
      const endYear = Number(event.end_astro_year);
      if (!Number.isFinite(startYear) || !Number.isFinite(endYear)) {
        return true;
      }
      return endYear - startYear <= 6;
    })
    .slice(0, 6);
}

function analogueEventYearsForHeading(event = {}) {
  const startYear = Number(event.start_astro_year) || yearFromDate(event.display_date);
  const endYear = Number(event.end_astro_year) || startYear;
  if (!Number.isFinite(startYear)) {
    return [];
  }
  if (!Number.isFinite(endYear) || endYear === startYear) {
    return [startYear];
  }
  return [startYear, endYear];
}

function compactPeriod(value = "") {
  return String(value)
    .split(/\s+to\s+/)
    .map((part) => formatDisplayDate(part) || part)
    .join(" - ");
}

function yearFromDate(value) {
  const match = String(value || "").match(/^-?\d{1,4}/);
  if (!match) {
    return null;
  }
  const parsed = Number(match[0]);
  return Number.isFinite(parsed) ? parsed : null;
}

function dateValue(value) {
  const text = String(value || "").slice(0, 10);
  const parsed = Date.parse(`${text}T00:00:00Z`);
  return Number.isFinite(parsed) ? parsed : null;
}

function rangeDates(range = "") {
  const parts = String(range).split(/\s+to\s+|\s+-\s+/).map((item) => item.trim()).filter(Boolean);
  const start = dateValue(parts[0]);
  const end = dateValue(parts[1] || parts[0]);
  if (start === null || end === null) {
    return null;
  }
  return { start: Math.min(start, end), end: Math.max(start, end) };
}

function markerPosition(date, range) {
  const value = dateValue(date);
  if (value === null || !range) {
    return 50;
  }
  const span = Math.max(1, range.end - range.start);
  return Math.max(4, Math.min(96, ((value - range.start) / span) * 100));
}

function eventPointDate(event = {}) {
  if (event.display_date && /^\d{4}-\d{2}-\d{2}/.test(event.display_date)) {
    return event.display_date.slice(0, 10);
  }
  const year = event.start_astro_year || yearFromDate(event.display_date);
  return Number.isFinite(Number(year)) ? `${String(year).padStart(4, "0")}-01-01` : "";
}

function glyphForCycleLabel(label = "") {
  const text = String(label || "");
  for (const [sign, glyph] of Object.entries(ZODIAC_GLYPHS)) {
    if (text.includes(sign)) {
      return glyph;
    }
  }
  const glyphs = Object.entries(PLANET_GLYPHS)
    .filter(([planet]) => text.includes(planet))
    .map(([, glyph]) => glyph);
  return glyphs.slice(0, 2).join("") || cycleInitialsFromLabel(text);
}

function planetsFromText(label = "") {
  const text = String(label || "").toLowerCase();
  return Object.keys(PLANET_GLYPHS).filter((planet) => text.includes(planet.toLowerCase()));
}

function primaryPlanetGlyphForCycle(label = "") {
  const text = String(label || "");
  const normalized = text.toLowerCase();
  const key = primaryPlanetKeyForCycle(normalized);
  return key ? PLANET_GLYPHS[key] : glyphForCycleLabel(text);
}

function primaryPlanetKeyForCycle(label = "") {
  const normalized = String(label || "").toLowerCase();
  if (normalized.includes("neptune") && normalized.includes("pluto")) {
    return "Neptune";
  }
  if (normalized.includes("neptune") && normalized.includes("uranus")) {
    return "Uranus";
  }
  if (normalized.includes("pluto")) {
    return "Pluto";
  }
  if (normalized.includes("uranus")) {
    return "Uranus";
  }
  if (normalized.includes("neptune")) {
    return "Neptune";
  }
  if (normalized.includes("saturn")) {
    return "Saturn";
  }
  if (normalized.includes("jupiter")) {
    return "Jupiter";
  }
  return "";
}

function renderPlanetGlyphIcon(label = "") {
  const key = primaryPlanetKeyForCycle(label);
  const fallback = escapeHtml(primaryPlanetGlyphForCycle(label));
  const icons = {
    Neptune: `<svg class="planet-glyph planet-neptune" viewBox="0 0 32 32" aria-hidden="true"><path d="M9 7c1.1 5.1 3.4 7.7 7 7.7s5.9-2.6 7-7.7"></path><path d="M11.2 8.7c.2 6.5 1.8 9.7 4.8 9.7s4.6-3.2 4.8-9.7"></path><path d="M16 14.5v12.2M10.8 26.7h10.4"></path></svg>`,
    Uranus: `<svg class="planet-glyph planet-uranus" viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="21.2" r="3.9"></circle><path d="M16 4.8v12.5M11 8.4h10M11 8.4v7.3M21 8.4v7.3M7.5 13.4h5M19.5 13.4h5"></path></svg>`,
    Pluto: `<svg class="planet-glyph planet-pluto" viewBox="0 0 32 32" aria-hidden="true"><path d="M12.2 5.5v21.2"></path><path d="M12.2 5.5h5.1c4 0 6.5 2.4 6.5 6s-2.5 6-6.5 6h-5.1"></path><path d="M8.8 24.5h12.4"></path></svg>`,
    Saturn: `<svg class="planet-glyph planet-saturn" viewBox="0 0 32 32" aria-hidden="true"><path d="M15 5v21M10 9h10"></path><path d="M15 16c5-1.9 9.3-1.6 10.1.4.9 2.3-3.3 5.5-9.3 7.1-4.2 1.1-7.7 1-8.9-.3"></path></svg>`,
    Jupiter: `<svg class="planet-glyph planet-jupiter" viewBox="0 0 32 32" aria-hidden="true"><path d="M9 8c6.5 0 9.5 3.2 9.5 9V26"></path><path d="M8 18h16M20 6v20"></path></svg>`,
  };
  return icons[key] || `<span class="planet-glyph-fallback">${fallback}</span>`;
}

function glyphForLayer(title = "", rows = []) {
  const rowLabel = rows.map((row) => row.label).join(" ");
  if (title.includes("Short")) {
    return PLANET_GLYPHS.Jupiter;
  }
  return glyphForCycleLabel(rowLabel);
}

function signalPath(points = []) {
  if (!points.length) {
    return "M16 42 L304 42";
  }
  const sorted = [...points].sort((left, right) => left.x - right.x);
  return smoothPath(sorted);
}

function renderAnalogueSignal(episode = {}) {
  const range = rangeDates(episodePeriod(episode));
  const events = (episode.matched_events || []).slice(0, 5);
  const best = episode.best_date;
  const signalId = `signalLine-${stableHash(`${episode.period_start}-${episode.period_end}-${best}`).toString(36)}`;
  const points = analogueSignaturePoints(episode, range);
  const path = signalPath(points);
  const peakX = 16 + (markerPosition(best || episode.period_start, range) / 100) * 288;
  const eventNodes = events.map((event) => ({
    x: 16 + (markerPosition(eventPointDate(event), range) / 100) * 288,
    y: signalYAt(points, 16 + (markerPosition(eventPointDate(event), range) / 100) * 288),
    label: event.title,
  }));
  return `
    <div class="analogue-signal" aria-label="Backend resonance window">
      <svg viewBox="0 0 320 82" role="img" aria-label="Episode period, peak match and matched event positions">
        <defs>
          <linearGradient id="${signalId}" x1="0" x2="1">
            <stop offset="0" stop-color="rgba(75, 180, 207, 0)" />
            <stop offset="0.18" stop-color="rgba(75, 180, 207, 0.72)" />
            <stop offset="0.62" stop-color="rgba(75, 180, 207, 0.66)" />
            <stop offset="1" stop-color="rgba(214, 165, 107, 0)" />
          </linearGradient>
        </defs>
        <rect class="signal-window" x="${num(Math.max(12, Math.min(256, peakX - 26)), 1)}" y="12" width="52" height="52" rx="1" />
        <line class="signal-peak-line" x1="${num(peakX, 1)}" y1="16" x2="${num(peakX, 1)}" y2="64" />
        <path class="signal-haze" d="${path}" />
        <path class="signal-line" style="stroke:url(#${signalId})" d="${path}" />
        ${eventNodes.map((node) => `<circle class="signal-node event" cx="${num(node.x, 1)}" cy="${num(node.y, 1)}" r="2"><title>${escapeHtml(node.label)}</title></circle>`).join("")}
        <circle class="signal-node peak" cx="${num(peakX, 1)}" cy="${num(signalYAt(points, peakX), 1)}" r="3.8"><title>${escapeHtml(best ? `Peak match ${best}` : "Peak match")}</title></circle>
      </svg>
    </div>
  `;
}

function analogueSignaturePoints(episode = {}, range) {
  const seed = stableHash([
    episode.period_start,
    episode.period_end,
    episode.best_date,
    episode.best_score,
    ...(episode.row_indices || []),
    ...(episode.matched_events || []).map((event) => event.event_id || event.title),
  ].join("|"));
  const confidence =
    episode.narrative_confidence?.narrative_confidence ??
    episode.best_percentile ??
    episode.best_score ??
    0.65;
  const peakT = markerPosition(episode.best_date || episode.period_start, range) / 100;
  const eventPositions = (episode.matched_events || [])
    .slice(0, 7)
    .map((event) => markerPosition(eventPointDate(event), range) / 100);
  const count = 36;
  return Array.from({ length: count }, (_, index) => {
    const t = index / (count - 1);
    const wobble =
      Math.sin(t * Math.PI * 5.4 + (seed % 11)) * 4.2 +
      Math.sin(t * Math.PI * 12.5 + (seed % 17)) * 1.9 +
      (((stableHash(`${seed}-${index}`) % 100) / 100) - 0.5) * 2.3;
    const peakLift = gaussian(t, peakT, 0.013) * (13 + confidence * 6);
    const eventLift = eventPositions.reduce((sum, position, eventIndex) => {
      return sum + gaussian(t, position, 0.007 + eventIndex * 0.0006) * (4.2 + (eventIndex % 3) * 1.1);
    }, 0);
    const y = Math.max(17, Math.min(66, 46 + wobble - peakLift - eventLift));
    return { x: 16 + t * 288, y };
  });
}

function signalYAt(points, x) {
  if (!points.length) {
    return 46;
  }
  return points.reduce((closest, point) => {
    return Math.abs(point.x - x) < Math.abs(closest.x - x) ? point : closest;
  }, points[0]).y;
}

function gaussian(value, center, spread) {
  const safeSpread = Math.max(0.0001, spread);
  return Math.exp(-((value - center) ** 2) / safeSpread);
}

function stableHash(value = "") {
  let hash = 2166136261;
  for (const char of String(value)) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function regimeTimelineMarkers(payload) {
  return [
    ...activeCycleWindows(payload).flatMap((window) => [
      { date: window.start_date, label: `${window.label} start`, type: "edge" },
      { date: window.peak_date, label: `${window.label} peak`, type: "peak" },
      { date: window.end_date, label: `${window.label} end`, type: "edge" },
    ]),
    ...activeRegimeWindows(payload)
      .filter((window) => window.driver_type === "sign_regime")
      .map((window) => ({ date: window.start_date, label: window.label, type: "sign" })),
  ].filter((marker) => marker.date);
}

function episodeTimelineMarkers(episode = {}) {
  return [
    { date: episode.period_start, label: "Analogue start", type: "edge" },
    { date: episode.best_date, label: "Peak match", type: "peak" },
    { date: episode.period_end, label: "Analogue end", type: "edge" },
    ...(episode.matched_events || []).slice(0, 8).map((event) => ({
      date: eventPointDate(event),
      label: event.title,
      type: "event",
    })),
  ].filter((marker) => marker.date);
}

function renderResonanceTimelineSvg({
  currentRange,
  matchRange,
  currentLabel,
  matchLabel,
  currentMarkers,
  matchMarkers,
  currentFocusDate,
  matchFocusDate,
}) {
  const current = rangeDates(currentRange);
  const match = rangeDates(matchRange);
  const currentNodes = currentMarkers.slice(0, 18);
  const matchNodes = matchMarkers.slice(0, 18);
  const currentFocusX = timelineX(currentFocusDate || currentMarkers.find((node) => node.type === "peak")?.date, current);
  const focusX = Number.isFinite(currentFocusX) ? currentFocusX : timelineX(matchFocusDate || matchMarkers.find((node) => node.type === "peak")?.date, match);
  const matchFocusX = focusX;
  const currentPath = timelineWavePath(currentNodes, current, "current");
  const matchPath = timelineWavePath(matchNodes, match, "match");
  const currentYears = timelineYearTicks(currentRange, current);
  const matchYears = timelineYearTicks(matchRange, match);
  const currentRowLabel = timelineStartLabel(current, currentLabel);
  const matchRowLabel = timelineStartLabel(match, matchLabel);
  const currentFocusLabel = String(currentFocusDate || "").slice(0, 4);
  const matchFocusLabel = String(matchFocusDate || "").slice(0, 4);
  const visibleCurrentYears = currentYears.filter((tick) => tick.label !== currentFocusLabel);
  const visibleMatchYears = matchYears.filter((tick) => tick.label !== matchFocusLabel);
  return `
    <div class="resonance-timeline-svg">
      <svg viewBox="0 0 1180 122" role="img" aria-label="Current regime and selected historical analogue timeline">
        <defs>
          <linearGradient id="currentBand" x1="0" x2="1">
            <stop offset="0" stop-color="rgba(75,180,207,0)" />
            <stop offset="0.18" stop-color="rgba(75,180,207,0.36)" />
            <stop offset="0.76" stop-color="rgba(75,180,207,0.22)" />
            <stop offset="1" stop-color="rgba(75,180,207,0)" />
          </linearGradient>
          <linearGradient id="matchBand" x1="0" x2="1">
            <stop offset="0" stop-color="rgba(214,165,107,0)" />
            <stop offset="0.16" stop-color="rgba(214,165,107,0.42)" />
            <stop offset="0.78" stop-color="rgba(214,165,107,0.22)" />
            <stop offset="1" stop-color="rgba(214,165,107,0)" />
          </linearGradient>
        </defs>
        <line class="timeline-dashed current" x1="142" y1="42" x2="1114" y2="42"></line>
        <line class="timeline-dashed match" x1="142" y1="84" x2="1114" y2="84"></line>
        <rect class="timeline-focus-window" x="${num(Math.max(142, Math.min(1030, focusX - 28)), 1)}" y="16" width="56" height="92" rx="0"></rect>
        <text class="timeline-label" x="24" y="46">${escapeHtml(currentRowLabel)}</text>
        <text class="timeline-label" x="24" y="89">${escapeHtml(matchRowLabel)}</text>
        <path class="timeline-band current" d="${currentPath}" />
        <path class="timeline-band match" d="${matchPath}" />
        <path class="timeline-thread current" d="${currentPath}" />
        <path class="timeline-thread match" d="${matchPath}" />
        ${currentNodes.map((node) => renderTimelineNode(node, current, 42, "current")).join("")}
        ${matchNodes.map((node) => renderTimelineNode(node, match, 84, "match")).join("")}
        <circle class="timeline-focus current" cx="${num(currentFocusX, 1)}" cy="42" r="3"></circle>
        <circle class="timeline-focus match" cx="${num(matchFocusX, 1)}" cy="84" r="4.3"></circle>
        ${visibleCurrentYears.map((tick) => `<text class="timeline-year current" x="${num(tick.x, 1)}" y="63">${escapeHtml(tick.label)}</text>`).join("")}
        ${visibleMatchYears.map((tick) => `<text class="timeline-year match" x="${num(tick.x, 1)}" y="107">${escapeHtml(tick.label)}</text>`).join("")}
        ${currentFocusLabel ? `<text class="timeline-focus-year current" x="${num(focusX, 1)}" y="63">${escapeHtml(currentFocusLabel)}</text>` : ""}
        ${matchFocusLabel ? `<text class="timeline-focus-year match" x="${num(focusX, 1)}" y="107">${escapeHtml(matchFocusLabel)}</text>` : ""}
      </svg>
    </div>
  `;
}

function timelineStartLabel(range, fallback) {
  const startYear = range?.start instanceof Date && !Number.isNaN(range.start.getTime()) ? range.start.getUTCFullYear() : null;
  return startYear ? String(startYear) : String(fallback || "").match(/\d{4}/)?.[0] || fallback || "";
}

function renderTimelineNode(node, range, y, tone) {
  const x = timelineX(node.date, range);
  const radius = node.type === "peak" ? 2.6 : node.type === "event" ? 2 : 2.1;
  return `
    <g class="timeline-node ${tone} ${escapeHtml(node.type)}">
      <circle cx="${num(x, 1)}" cy="${y}" r="${radius}">
        <title>${escapeHtml(node.label || node.date)}</title>
      </circle>
    </g>
  `;
}

function timelineX(date, range) {
  return 142 + (markerPosition(date, range) / 100) * 972;
}

function timelineWavePath(markers, range, tone) {
  const seed = stableHash(markers.map((marker) => `${marker.date}:${marker.type}`).join("|") || tone);
  const yBase = tone === "current" ? 42 : 84;
  const points = Array.from({ length: 22 }, (_, index) => {
    const t = index / 21;
    const x = 142 + t * 972;
    const wobble =
      Math.sin(t * Math.PI * 4.6 + (seed % 13)) * 2.2 +
      Math.sin(t * Math.PI * 10.8 + (seed % 19)) * 1.15;
    const markerLift = markers.slice(0, 10).reduce((sum, marker) => {
      const markerT = markerPosition(marker.date, range) / 100;
      const direction = marker.type === "peak" ? -1 : 1;
      return sum + gaussian(t, markerT, 0.01) * direction * 2.2;
    }, 0);
    return { x, y: yBase + wobble + markerLift };
  });
  return smoothPath(points);
}

function smoothPath(points = []) {
  if (!points.length) {
    return "";
  }
  if (points.length === 1) {
    return `M${num(points[0].x, 1)} ${num(points[0].y, 1)}`;
  }
  return points.reduce((path, point, index) => {
    if (index === 0) {
      return `M${num(point.x, 1)} ${num(point.y, 1)}`;
    }
    const previous = points[index - 1];
    const midX = (previous.x + point.x) / 2;
    return `${path} C${num(midX, 1)} ${num(previous.y, 1)} ${num(midX, 1)} ${num(point.y, 1)} ${num(point.x, 1)} ${num(point.y, 1)}`;
  }, "");
}

function timelineYearTicks(rangeText, range) {
  const years = String(rangeText || "").match(/\d{4}/g)?.map(Number).filter(Number.isFinite) || [];
  if (!years.length) {
    return [];
  }
  const startYear = years[0];
  const endYear = years[years.length - 1];
  const span = Math.max(1, endYear - startYear);
  const step = span <= 3 ? 1 : span <= 8 ? 2 : Math.ceil(span / 4);
  const ticks = [];
  for (let year = startYear; year <= endYear; year += step) {
    ticks.push({
      label: String(year),
      x: timelineX(`${year}-01-01`, range),
    });
  }
  if (!ticks.some((tick) => tick.label === String(endYear))) {
    ticks.push({ label: String(endYear), x: timelineX(`${endYear}-12-31`, range) });
  }
  return ticks.slice(0, 6);
}

function compactEpisodeLine(episode = {}) {
  const event = episode.matched_events?.[0];
  const label = episode.score_breakdown?.label;
  const confidence = percent(episode.narrative_confidence?.narrative_confidence);
  return [event?.category, label, confidence].filter(Boolean).join(" | ") || "Backend episode";
}

function shortSummary(summary, maxLength = 280) {
  const text = stripEventIds(summaryText(summary)).replace(/\s+/g, " ").trim();
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength - 1).trim()}...`;
}

function stripEventIds(text) {
  return String(text || "")
    .replace(/\s*\(evt_[^)]+\)/g, "")
    .replace(/\bevt_[a-z0-9_]+\b/gi, "")
    .replace(/\s+([.;,])/g, "$1")
    .replace(/\s{2,}/g, " ");
}

function whyMatchLine(payload, episode) {
  const cycles = [...(payload.primary_cycles || []), ...(payload.supporting_cycles || [])]
    .slice(0, 3)
    .map(cycleLabel)
    .join(", ");
  const score = num(episode.score_breakdown?.planetary_resonance_score, 3);
  const period = episodePeriod(episode);
  const best = episode.best_date || "the selected period";
  const eventCount = episode.matched_events?.length || 0;
  return `The backend found an independent resonance window ${period}, with peak match ${best}, after separating current active regime and local continuity from historical analogues. Resonance score: ${score}. ${eventCount} matched events are attached as direct evidence. ${cycles ? `Active cycles: ${cycles}.` : "No cycle list was returned."}`;
}

function renderGroupedEvents(events = [], options = {}) {
  const filteredEvents = filterEventsByCategory(events, options.bucket);
  if (!filteredEvents.length) {
    const message = state.explorerCategoryFilter === "all"
      ? "No events in this bucket."
      : "No events in the selected event lens. Switch back to All evidence to see the full backend result.";
    return `<div class="empty-state compact">${escapeHtml(message)}</div>`;
  }
  const grouped = new Map();
  for (const event of filteredEvents) {
    const group = options.bucket === "context" ? "civilizational_background" : eventCategoryGroup(event);
    if (!grouped.has(group)) {
      grouped.set(group, []);
    }
    grouped.get(group).push(event);
  }
  return [...grouped.entries()]
    .sort(
      ([left], [right]) =>
        CATEGORY_GROUP_ORDER.indexOf(left) - CATEGORY_GROUP_ORDER.indexOf(right)
    )
    .map(([group, groupEvents]) => `
      <section class="event-category-group" data-category-group="${escapeHtml(group)}">
        <div class="event-category-heading">
          ${categoryBadge(group)}
          <span>${escapeHtml(CATEGORY_GROUP_META[group]?.description || "backend category group")}</span>
        </div>
        ${groupEvents.map((event) => renderEvent(event, { bucket: options.bucket })).join("")}
      </section>
    `)
    .join("");
}

function renderEvents(events = []) {
  if (!events.length) {
    return `<div class="empty-state compact">No events in this bucket.</div>`;
  }
  return events.map((event) => renderEvent(event)).join("");
}

function renderEvent(event, options = {}) {
  const categoryGroup = options.bucket === "context"
    ? "civilizational_background"
    : eventCategoryGroup(event);
  return `
    <article class="event-card">
      <div>
        <h4>${escapeHtml(event.title)}</h4>
        <p>${escapeHtml(event.display_date)} | ${escapeHtml(scopeLabel(event, options.bucket))}</p>
        <div class="event-badge-row">
          ${categoryBadge(categoryGroup)}
          <span class="event-raw-category">${escapeHtml(humanizeCategory(event.category))}</span>
        </div>
      </div>
      <span class="status-pill">${percent(event.confidence_score)}</span>
      ${renderEventSources(event)}
    </article>
  `;
}

function filterEventsByCategory(events = [], bucket) {
  if (state.explorerCategoryFilter === "all") {
    return events;
  }
  if (state.explorerCategoryFilter === "civilizational_background") {
    return events.filter(
      (event) => bucket === "context" || eventCategoryGroup(event) === "civilizational_background"
    );
  }
  if (bucket === "context") {
    return [];
  }
  return events.filter((event) => eventCategoryGroup(event) === state.explorerCategoryFilter);
}

function categoryGroupCountsForEpisode(episode) {
  const counts = categoryGroupCounts(episode?.matched_events || []);
  for (const _event of episode?.context_events || []) {
    counts.civilizational_background = (counts.civilizational_background || 0) + 1;
  }
  return counts;
}

function categoryGroupCounts(events = []) {
  return events.reduce((counts, event) => {
    const group = eventCategoryGroup(event);
    counts[group] = (counts[group] || 0) + 1;
    return counts;
  }, {});
}

function eventCategoryGroup(event = {}) {
  if (!event || !event.category) {
    return "civilizational_background";
  }
  if (event.event_kind === "long_process") {
    return CATEGORY_GROUP_BY_CATEGORY[event.category] || "civilizational_background";
  }
  return CATEGORY_GROUP_BY_CATEGORY[event.category] || "civilizational_background";
}

function categoryBadge(group) {
  const meta = CATEGORY_GROUP_META[group] || CATEGORY_GROUP_META.civilizational_background;
  return `
    <span class="event-category-badge" data-category-group="${escapeHtml(group)}">
      ${escapeHtml(meta.label)}
    </span>
  `;
}

function scopeLabel(event = {}, bucket) {
  if (bucket === "context") {
    return "context event";
  }
  if (event.event_kind === "long_process") {
    return "civilizational background";
  }
  if (event.event_kind === "war" || event.event_kind === "revolution" || event.event_kind === "crisis") {
    return "hard event";
  }
  return humanizeCategory(event.event_kind || "event");
}

function humanizeCategory(value) {
  return String(value || "event").replaceAll("_", " ");
}

function renderEventSources(event) {
  const sources = Array.isArray(event.sources) ? event.sources : [];
  const fallbackSource = !sources.length && event.source_url
    ? [{ source_name: sourceLabel(event.source_url), source_url: event.source_url }]
    : null;
  const visibleSources = fallbackSource || sources;
  if (!visibleSources.length) {
    return `<div class="source-row"><span>No sources returned</span></div>`;
  }
  return `
    <div class="source-row">
      ${visibleSources.slice(0, 4).map((source) => {
        const url = safeUrl(source.source_url);
        return url
          ? `<a href="${url}" target="_blank" rel="noreferrer">${escapeHtml(source.source_name)}</a>`
          : `<span>${escapeHtml(source.source_name)}</span>`;
      }).join("")}
    </div>
  `;
}

function sourceLabel(value) {
  try {
    const hostname = new URL(value).hostname.replace(/^www\./, "");
    if (hostname.includes("wikidata")) {
      return "Wikidata";
    }
    if (hostname.includes("britannica")) {
      return "Encyclopaedia Britannica";
    }
    return hostname || "Source";
  } catch {
    return "Source";
  }
}

function renderEpisodeCycles(primaryCycles = [], supportingCycles = []) {
  const primaryText = primaryCycles.length
    ? primaryCycles.slice(0, 4).map(cycleLabel).join(", ")
    : "No dominant primary cycle returned for this query.";
  const supportingText = supportingCycles.length
    ? supportingCycles.slice(0, 4).map(cycleLabel).join(", ")
    : "No supporting cycles returned.";
  return `
    <div class="cycle-explain-grid">
      <span><strong>Primary cycles</strong>${escapeHtml(primaryText)}</span>
      <span><strong>Supporting cycles</strong>${escapeHtml(supportingText)}</span>
    </div>
  `;
}

function renderCycleSummary(primaryCycles = [], supportingCycles = []) {
  return `
    <div class="cycle-explain-grid">
      <span><strong>Primary cycles</strong>${escapeHtml(primaryCycles.slice(0, 5).map(cycleLabel).join(", "))}</span>
      <span><strong>Supporting cycles</strong>${escapeHtml(supportingCycles.slice(0, 5).map(cycleLabel).join(", ") || "none")}</span>
    </div>
  `;
}

function noPrimaryCycleMessage(supportingCycles = []) {
  return `
    <p class="human-note">
      No dominant primary cycle returned for today; supporting cycles are shown below.
    </p>
    <div class="compact-list">
      ${supportingCycles.length ? supportingCycles.map((cycle) => `<span>${escapeHtml(cycleLabel(cycle))}</span>`).join("") : "<span>No supporting cycles loaded yet.</span>"}
    </div>
  `;
}

function renderScoreBreakdown(score = {}) {
  const rows = [
    ["Structural similarity", score.structural_similarity],
    ["Cycle power", score.cycle_power_score],
    ["Rarity percentile", score.rarity_adjusted_percentile],
    ["Planetary resonance", score.planetary_resonance_score],
    ["Strongest primary", score.strongest_primary_contribution],
  ];
  return `<ul class="score-list">${rows.map(([label, value]) => `<li><span>${label}</span><strong>${num(value, 3)}</strong></li>`).join("")}</ul>`;
}

function renderConfidenceBreakdown(confidence = {}) {
  const rows = [
    ["Event coverage", confidence.event_coverage_score],
    ["Source quality", confidence.source_quality_score],
    ["Evidence", confidence.evidence_confidence],
    ["Narrative confidence", confidence.narrative_confidence],
  ];
  return `<ul class="score-list">${rows.map(([label, value]) => `<li><span>${label}</span><strong>${percent(value)}</strong></li>`).join("")}</ul>`;
}

function renderCoverage(coverage) {
  if (!coverage) {
    return "";
  }
  return `
    <section class="coverage-strip">
      <span>${escapeHtml(coverage.history_window_label)}</span>
      <span>${escapeHtml(coverage.index_coverage_status)}</span>
      <span>${escapeHtml(shortDate(coverage.request_window_start))} to ${escapeHtml(shortDate(coverage.request_window_end))}</span>
      ${coverage.warning ? `<span class="warn-text">${escapeHtml(coverage.warning)}</span>` : ""}
    </section>
  `;
}

function renderWarnings(warnings = []) {
  if (!warnings?.length) {
    return "";
  }
  return `<div class="warning-box">${warnings.map((warning) => `<p>${escapeHtml(warning)}</p>`).join("")}</div>`;
}

function productErrorPage(title, message, error) {
  return `
    <section class="page-shell">
      <div class="page-heading compact-heading">
        <p class="eyebrow">${escapeHtml(title)}</p>
        <h1>Backend unavailable</h1>
        <p>${escapeHtml(message)}</p>
      </div>
      ${errorState("Backend unavailable", errorMessage(error))}
      <button class="secondary-action" type="button" data-action="open-dev-settings">Open Developer settings</button>
    </section>
  `;
}

function renderConnectionNotice() {
  if (!state.lastError) {
    return "";
  }
  return `
    <section class="product-section">
      ${errorState("Live backend unavailable", "Open Developer settings to check API base and token. Public pages stay readable without fake data.")}
    </section>
  `;
}

function featureCard(title, body) {
  return `
    <article class="research-card feature-card">
      <p class="card-label">${escapeHtml(title)}</p>
      <h3>${escapeHtml(title)}</h3>
      <p>${escapeHtml(body)}</p>
    </article>
  `;
}

function articlePlaceholder(label, title, body) {
  return `
    <article class="research-card feature-card">
      <p class="card-label">${escapeHtml(label)}</p>
      <h3>${escapeHtml(title)}</h3>
      <p>${escapeHtml(body)}</p>
    </article>
  `;
}

function statCard(label, value) {
  return `
    <article class="stat-card">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value || "--")}</strong>
    </article>
  `;
}

function badgeRow(items = []) {
  return `<div class="badge-row">${items.map((item) => `<span class="status-pill">${escapeHtml(String(item))}</span>`).join("")}</div>`;
}

function eventIdChips(ids = []) {
  return ids?.length ? ids.map((id) => `<span>${escapeHtml(id)}</span>`).join("") : "<span>none</span>";
}

function emptyState(title, message) {
  return `<div class="empty-state"><strong>${escapeHtml(title)}</strong><p>${escapeHtml(message)}</p></div>`;
}

function loadingState(message) {
  return `<div class="loading-state"><span></span><p>${escapeHtml(message)}</p></div>`;
}

function errorState(title, message) {
  return `<div class="error-state"><strong>${escapeHtml(title)}</strong><p>${escapeHtml(message)}</p></div>`;
}

function buildSearchRequest(dateValue) {
  const recommended = state.today?.recommended_search_request;
  return {
    date_utc: normalizeDateInput(dateValue),
    profile_id: recommended?.profile_id || "global_slow_v1",
    lookback_years: recommended?.lookback_years ?? 120,
    lookahead_years: recommended?.lookahead_years ?? 0,
    step_days: recommended?.step_days ?? 7,
    top_k: recommended?.top_k ?? 30,
    max_episodes: recommended?.max_episodes ?? 5,
    events_per_episode: recommended?.events_per_episode ?? 6,
    event_window_years: recommended?.event_window_years ?? 1,
    provider: recommended?.provider || "swiss",
    index_file: recommended?.index_file || DEFAULT_INDEX_FILE,
    historical_analogue_mode: true,
    exclude_same_calendar_year: true,
    local_resonance_window_days: 365,
    historical_analogue_min_year_gap: 5,
    historical_exclude_active_regime_windows: true,
  };
}

function buildCompareRequest(leftValue, rightValue) {
  const seed = state.articleSeeds?.seeds?.[0]?.compare_request;
  return {
    left_date_utc: normalizeDateInput(leftValue),
    right_date_utc: normalizeDateInput(rightValue),
    profile_id: seed?.profile_id || "global_slow_v1",
    lookback_years: seed?.lookback_years ?? 120,
    lookahead_years: seed?.lookahead_years ?? 0,
    step_days: seed?.step_days ?? 7,
    top_k: seed?.top_k ?? 30,
    max_episodes: seed?.max_episodes ?? 5,
    events_per_episode: seed?.events_per_episode ?? 6,
    event_window_years: seed?.event_window_years ?? 1,
    provider: seed?.provider || "swiss",
    index_file: seed?.index_file || DEFAULT_INDEX_FILE,
  };
}

function defaultExplorerDate() {
  return shortDate(state.currentSearch?.query_datetime_utc || state.initialDate || EXPLORER_DEFAULT_DATE);
}

function normalizeDateInput(value) {
  const trimmed = String(value || "").trim();
  if (/^-?\d{1,4}$/.test(trimmed)) {
    return `${trimmed.padStart(4, "0")}-01-01T00:00:00Z`;
  }
  const dateOnly = isoDateFromInput(trimmed);
  if (dateOnly) {
    return `${dateOnly}T00:00:00Z`;
  }
  const parsed = new Date(trimmed);
  if (Number.isNaN(parsed.getTime())) {
    throw new Error("Use date format dd-mm-yyyy, for example 25-05-2026.");
  }
  return parsed.toISOString();
}

function summaryText(summary) {
  if (!summary) {
    return "No backend summary returned.";
  }
  if (typeof summary === "string") {
    return summary;
  }
  return summary.summary || (summary.key_points || []).join(" ");
}

function cycleLabel(cycle = {}) {
  const pair = cyclePair(cycle).join("-") || "unknown";
  return `${pair}:${cycle.aspect || "cycle"}`;
}

function percent(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return `${Math.round(value * 100)}%`;
}

function num(value, digits) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return value.toFixed(digits);
}

function shortDate(value) {
  if (!value) {
    return "--";
  }
  return formatDisplayDate(value) || String(value).slice(0, 16);
}

function formatDisplayDate(value) {
  const isoDate = isoDateFromInput(value);
  if (!isoDate) {
    return "";
  }
  const [, year, month, day] = isoDate.match(/^(\d{4})-(\d{2})-(\d{2})$/) || [];
  return year ? `${day}-${month}-${year}` : "";
}

function isoDateFromInput(value) {
  const raw = String(value || "").trim();
  const isoMatch = raw.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T\s].*)?$/);
  if (isoMatch) {
    return validIsoDate(isoMatch[1], isoMatch[2], isoMatch[3]);
  }
  const localMatch = raw.match(/^(\d{1,2})[./-](\d{1,2})[./-](\d{4})$/);
  if (localMatch) {
    return validIsoDate(localMatch[3], localMatch[2].padStart(2, "0"), localMatch[1].padStart(2, "0"));
  }
  return "";
}

function validIsoDate(year, month, day) {
  const normalized = `${year}-${month}-${day}`;
  const parsed = new Date(`${normalized}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }
  const roundTrip = parsed.toISOString().slice(0, 10);
  return roundTrip === normalized ? normalized : "";
}

function safeUrl(value) {
  try {
    const url = new URL(value);
    if (url.protocol === "http:" || url.protocol === "https:") {
      return escapeHtml(url.href);
    }
  } catch {
    return "";
  }
  return "";
}

function errorMessage(error) {
  if (error instanceof ApiError) {
    return `${error.status}: ${error.message}`;
  }
  return error?.message || String(error);
}

function summarizeApiPayload(path, payload, status) {
  if (path === "/today" && typeof payload === "object") {
    return `${status}: snapshot ${payload.snapshot_date_utc}, provider ${payload.provider}`;
  }
  if (path === "/resonance/search" && typeof payload === "object") {
    return `${status}: ${historicalAnalogues(payload).length} historical analogues for ${shortDate(payload.query_datetime_utc)}`;
  }
  if (path === "/resonance/compare" && typeof payload === "object") {
    return `${status}: similarity ${num(payload.query_vector_similarity, 3)}`;
  }
  if (path === "/timeline/seeds" && typeof payload === "object") {
    return `${status}: ${payload.seeds?.length || 0} timeline seeds`;
  }
  if (path === "/articles/seeds" && typeof payload === "object") {
    return `${status}: ${payload.seeds?.length || 0} article seeds`;
  }
  return `${status}: ${path}`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => {
    const escapes = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
    return escapes[char];
  });
}

function syncNav() {
  for (const link of navLinks) {
    link.classList.toggle("active", link.dataset.view === state.currentView);
  }
  const route = routeForView(state.currentView);
  if (route) {
    history.replaceState({ view: state.currentView }, "", `#${route === "/" ? "home" : route.slice(1)}`);
  }
  document.body.dataset.currentView = state.currentView;
}

document.addEventListener("click", async (event) => {
  const viewTrigger = event.target.closest("button[data-view], a[data-view]");
  if (viewTrigger) {
    event.preventDefault();
    await setActiveView(viewTrigger.dataset.view);
    return;
  }

  const action = event.target.closest("[data-action]")?.dataset.action;
  if (action === "refresh-view") {
    await renderActiveView({ skipAutoLoad: false });
  } else if (action === "open-dev-settings") {
    document.querySelector("#developerSettings").open = true;
  } else if (action === "run-today-resonance") {
    const request = state.today?.recommended_search_request;
    if (request) {
      await runExplorerSearch(request, { navigate: true });
    }
  } else if (action === "open-analysis") {
    document.querySelector("#analysis-detail")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  const exampleDate = event.target.closest("[data-example-date]")?.dataset.exampleDate;
  if (exampleDate) {
    const input = document.querySelector("#explorerForm input[name='date']");
    if (input) {
      input.value = exampleDate;
    }
    await runExplorerSearch(buildSearchRequest(exampleDate));
  }

  const categoryFilter = event.target.closest("[data-category-filter]")?.dataset.categoryFilter;
  if (categoryFilter && state.currentSearch) {
    state.explorerCategoryFilter = categoryFilter;
    const target = document.querySelector("#explorerResult");
    if (target) {
      target.innerHTML = renderSearchResult(state.currentSearch);
    }
  }

  const compareExample = event.target.closest("[data-compare-left]");
  if (compareExample) {
    const form = document.querySelector("#compareForm");
    if (form) {
      form.left.value = compareExample.dataset.compareLeft;
      form.right.value = compareExample.dataset.compareRight;
    }
    await runCompare(buildCompareRequest(compareExample.dataset.compareLeft, compareExample.dataset.compareRight));
  }

  const episodeIndex = event.target.closest("[data-episode-index]")?.dataset.episodeIndex;
  if (episodeIndex !== undefined && state.currentSearch) {
    state.selectedEpisodeIndex = clampEpisodeIndex(episodeIndex, historicalAnalogues(state.currentSearch));
    const target = document.querySelector("#explorerResult");
    if (target) {
      target.innerHTML = renderSearchResult(state.currentSearch);
    }
  }

  const seedId = event.target.closest("[data-seed-id]")?.dataset.seedId;
  if (seedId) {
    const seed = state.timelineSeeds?.seeds?.find((item) => item.seed_id === seedId);
    if (seed) {
      await runExplorerSearch(seed.search_request, { navigate: true });
    }
  }

  const articleId = event.target.closest("[data-article-id]")?.dataset.articleId;
  if (articleId) {
    const seed = state.articleSeeds?.seeds?.find((item) => item.seed_id === articleId);
    if (seed) {
      await runCompare(seed.compare_request, { navigate: true });
    }
  }
});

document.addEventListener("submit", async (event) => {
  if (event.target.id === "explorerForm") {
    event.preventDefault();
    await runExplorerSearch(buildSearchRequest(event.target.date.value));
  } else if (event.target.id === "compareForm") {
    event.preventDefault();
    await runCompare(buildCompareRequest(event.target.left.value, event.target.right.value));
  } else if (event.target.id === "contactForm") {
    event.preventDefault();
    document.querySelector("#contactState").textContent = "Draft prepared locally. No request sent.";
  } else if (event.target.id === "chartForm") {
    event.preventDefault();
    document.querySelector("#chartState").textContent = "Kosmogram zostanie podpięty w kolejnym etapie.";
  }
});

connectButton.addEventListener("click", () => connectBackend());
window.addEventListener("hashchange", () => {
  const nextView = viewFromRoute(window.location.hash);
  setActiveView(nextView, { skipHash: true });
});

initFromUrl();
state.currentView = viewFromRoute(window.location.hash);
syncNav();
renderActiveView({ skipAutoLoad: true });
window.__ASTRO_SHELL_READY = true;
connectBackend();
