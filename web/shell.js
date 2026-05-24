const API_TOKEN_HEADER = "x-astro-global-session";
const DEFAULT_API_BASE = "http://127.0.0.1:8765";
const DEFAULT_SESSION_TOKEN = "dev-local-token";
const DEFAULT_INDEX_FILE = "swiss_1500_now_global_slow_v1.npz";
const EXPLORER_DEFAULT_DATE = "1789-07-14";
const EXPLORER_EXAMPLES = ["1789-07-14", "1848-02-24", "2020-01-12", "2026-05-24"];

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
  home: "Home",
  today: "Today",
  explorer: "Explorer",
  compare: "Compare",
  calendar: "Calendar",
  insights: "Insights",
  library: "Library",
  blog: "Blog",
  contact: "Contact",
};

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
  const response = await fetch(`${apiBase}${path}`, {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  state.lastApiSummaries[path] = summarizeApiPayload(path, payload, response.status);
  if (!response.ok) {
    const detail = typeof payload === "object" ? payload.detail : payload;
    throw new ApiError(response.status, detail || response.statusText, payload);
  }
  return payload;
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
  state.currentView = routeLabels[viewName] ? viewName : "home";
  document.body.dataset.currentView = state.currentView;
  for (const link of navLinks) {
    link.classList.toggle("active", link.dataset.view === state.currentView);
  }
  const route = document.querySelector(`[data-view="${state.currentView}"]`)?.dataset.route;
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
  } else if (state.currentView === "explorer") {
    renderExplorer();
    if (!state.currentSearch && !state.initialDate && !options.skipAutoLoad) {
      await runExplorerSearch(buildSearchRequest(EXPLORER_DEFAULT_DATE));
    }
  } else if (state.currentView === "compare") {
    renderCompare();
  } else if (state.currentView === "calendar") {
    renderCalendar();
  } else if (state.currentView === "insights") {
    renderInsights();
  } else if (state.currentView === "library") {
    renderLibrary();
  } else if (state.currentView === "blog") {
    renderBlog();
  } else if (state.currentView === "contact") {
    renderContact();
  }
}

function renderHome() {
  appRoot.innerHTML = `
    <section class="hero-screen">
      <div class="hero-copy">
        <p class="eyebrow">Historical planetary resonance explorer</p>
        <h1>Astro Global</h1>
        <p class="hero-subtitle">Historical planetary resonance explorer</p>
        <p class="hero-text">
          Explore how planetary cycles align with historical periods, sourced events,
          confidence and context.
        </p>
        <div class="hero-actions">
          <button class="primary-action" type="button" data-view="explorer">Open Explorer</button>
          <button class="secondary-action" type="button" data-view="today">View Today</button>
          <a class="secondary-action" href="./transparency/">Read Transparency</a>
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
      ${featureCard("Planetary cycles", "Slow-cycle configurations are calculated by the backend and surfaced as primary and supporting drivers.")}
      ${featureCard("Historical resonance", "Explorer compares dates against historical periods and keeps direct events apart from broad context.")}
      ${featureCard("Sources & confidence", "Every event can expose curated source links, confidence, coverage and clear limitations.")}
    </section>
    ${renderConnectionNotice()}
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
    <section class="explorer-observatory-page">
      <form class="explorer-command-bar" id="explorerForm">
        <label>
          Analyze date
          <input name="date" value="${escapeHtml(defaultExplorerDate())}" autocomplete="off" />
        </label>
        <button class="primary-action" type="submit">Analyze date</button>
        <div class="example-row" aria-label="Explorer examples">
          ${EXPLORER_EXAMPLES.map((date) => `<button type="button" data-example-date="${date}">${date}</button>`).join("")}
        </div>
      </form>
      <div id="explorerResult" class="explorer-result-stage">
        ${state.currentSearch ? renderSearchResult(state.currentSearch) : renderExplorerLoading()}
      </div>
    </section>
  `;
}

async function runExplorerSearch(request, options = {}) {
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
      body: request,
    });
    state.currentSearch = payload;
    state.selectedEpisodeIndex = 0;
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

function renderSearchResult(payload) {
  const queryDate = shortDate(payload.query_datetime_utc);
  const episodes = payload.episodes || [];
  const selectedIndex = clampEpisodeIndex(state.selectedEpisodeIndex, episodes);
  const selectedEpisode = episodes[selectedIndex];
  const primaryCycles = payload.primary_cycles || [];
  const supportingCycles = payload.supporting_cycles || [];
  const activeCycle = primaryCycles[0] || supportingCycles[0];
  const confidence = selectedEpisode?.narrative_confidence?.narrative_confidence;
  return `
    <div class="observatory-layout">
      <aside class="observatory-column left-observatory">
        ${renderCurrentSkyCard(payload)}
        ${renderKeyResonancesCard(primaryCycles, supportingCycles)}
      </aside>

      <section class="timeline-observatory-panel">
        <div class="observatory-panel-head">
          <div>
            <p class="eyebrow">Historical Resonance Timeline</p>
            <h1>Resonance result for ${escapeHtml(queryDate)}</h1>
          </div>
          <button class="tool-chip" type="button" disabled>Filters</button>
        </div>
        <div class="aspect-filter-row" aria-label="Cycle filters">
          ${renderAspectChips(primaryCycles, supportingCycles)}
        </div>
        <div class="sky-map-stage">
          <div class="star-field" aria-hidden="true"></div>
          ${renderResonanceWheel(primaryCycles, supportingCycles)}
          ${renderActiveResonanceCard(activeCycle, selectedEpisode, confidence)}
        </div>
        ${renderEpisodeTimeline(episodes, selectedIndex)}
      </section>

      <aside class="observatory-column right-observatory">
        ${renderPrimaryCyclesCard(primaryCycles)}
        ${renderConfidenceIndexCard(selectedEpisode)}
        ${renderHistoricalContextCard(selectedEpisode)}
      </aside>
    </div>
    ${selectedEpisode ? renderExplorerAnalysis(payload, selectedEpisode, selectedIndex) : emptyState("No episodes", "The backend returned no episodes for this date.")}
  `;
}

function renderExplorerLoading() {
  return `
    <section class="explorer-loading-panel">
      ${loadingState(`Loading default Explorer resonance for ${EXPLORER_DEFAULT_DATE}`)}
      <p class="human-note">Explorer uses POST /resonance/search only. No local scoring or fake data is rendered.</p>
    </section>
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

function renderKeyResonancesCard(primaryCycles = [], supportingCycles = []) {
  return `
    <article class="observatory-card key-resonance-card">
      <p class="eyebrow">Key Resonances</p>
      ${cycleStack(primaryCycles, "Primary cycles", "No dominant primary cycle returned.")}
      ${cycleStack(supportingCycles, "Supporting cycles", "No supporting cycles returned.")}
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
  return `
    <article class="active-resonance-card">
      <p class="eyebrow">Active resonance</p>
      <h2>${escapeHtml(cycle ? cycleTitle(cycle) : "No dominant cycle")}</h2>
      <span class="resonance-type">${escapeHtml(cycle?.aspect || episode?.score_breakdown?.label || "backend result")}</span>
      <strong>${percent(confidence)}</strong>
      <dl>
        <div>
          <dt>Best matched date</dt>
          <dd>${escapeHtml(episode?.best_date || "--")}</dd>
        </div>
        <div>
          <dt>Period</dt>
          <dd>${escapeHtml(episodePeriod(episode))}</dd>
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
  return `
    <button class="timeline-episode-card ${index === selectedIndex ? "selected" : ""}" type="button" data-episode-index="${index}">
      <strong>${escapeHtml(episode.best_date || "--")}</strong>
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
        <h2>${escapeHtml(episode.best_date)} historical resonance</h2>
        <p>${escapeHtml(shortSummary(payload.deterministic_summary, 360))}</p>
      </div>
      <div class="analysis-grid">
        <article class="analysis-card why-card">
          <p class="eyebrow">Why this match?</p>
          <p>${escapeHtml(whyMatchLine(payload, episode))}</p>
          ${renderEpisodeCycles(payload.primary_cycles, payload.supporting_cycles)}
        </article>
        <article class="analysis-card">
          <p class="eyebrow">Matched events</p>
          ${renderEvents(episode.matched_events)}
        </article>
        <article class="analysis-card">
          <p class="eyebrow">Context events</p>
          ${renderEvents(episode.context_events)}
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
        <h1>Human-authored astrology notes</h1>
        <p>Separate space for manual essays, observations and educational writing.</p>
      </div>
      <div class="feature-grid">
        ${articlePlaceholder("Field note", "Personal observation draft", "Human-authored, not generated.")}
        ${articlePlaceholder("Education", "Reading cycles with care", "Manual explainer placeholder.")}
        ${articlePlaceholder("Journal", "Current sky notes", "Editorial space for future posts.")}
      </div>
    </section>
  `;
}

function renderContact() {
  appRoot.innerHTML = `
    <section class="page-shell contact-page">
      <div class="page-heading compact-heading">
        <p class="eyebrow">Contact</p>
        <h1>Request private analysis</h1>
        <p>Contact shell only. No real submission is sent from this frontend yet.</p>
      </div>
      <form class="contact-form product-card" id="contactForm">
        <label>Name <input name="name" autocomplete="name" /></label>
        <label>Email <input name="email" type="email" autocomplete="email" /></label>
        <label class="wide-field">Message <textarea name="message" rows="5"></textarea></label>
        <label>Birth date <input name="birthDate" type="date" disabled /></label>
        <label>Birth time <input name="birthTime" type="time" disabled /></label>
        <label>Birth place <input name="birthPlace" placeholder="coming soon" disabled /></label>
        <p class="privacy-note wide-field">
          Birth details are optional and disabled until a safe private-analysis workflow exists.
          Do not send sensitive data here yet.
        </p>
        <button class="primary-action" type="submit">Prepare request</button>
        <span class="form-state" id="contactState" aria-live="polite"></span>
      </form>
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
  const first = search?.episodes?.[0];
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
      <span><strong>${escapeHtml(episode.best_date)}</strong> best date</span>
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

function renderPositionRow(position) {
  const name = position.name || position.planet || position.body || "Planet";
  const value = position.formatted || position.longitude_label || position.sign || position.longitude_deg || "--";
  return `<li><span>${escapeHtml(name)}</span><strong>${escapeHtml(value)}</strong></li>`;
}

function cycleStack(cycles = [], label, emptyMessage) {
  return `
    <section class="cycle-stack">
      <h3>${escapeHtml(label)}</h3>
      ${
        cycles.length
          ? cycles.slice(0, 4).map(renderCycleLine).join("")
          : `<p class="empty-copy">${escapeHtml(emptyMessage)}</p>`
      }
    </section>
  `;
}

function renderCycleLine(cycle) {
  return `
    <article class="cycle-line">
      <span class="cycle-symbol">${escapeHtml(cycleInitials(cycle))}</span>
      <div>
        <h4>${escapeHtml(cycleTitle(cycle))}</h4>
        <p>${escapeHtml(cycleMeta(cycle))}</p>
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
  const pair = Array.isArray(cycle.pair) ? cycle.pair : [];
  if (!pair.length) {
    return "?";
  }
  return pair.map((item) => String(item).trim().charAt(0).toUpperCase()).join("");
}

function cycleTitle(cycle = {}) {
  const pair = Array.isArray(cycle.pair) ? cycle.pair.join(" - ") : "Unknown cycle";
  return pair || "Unknown cycle";
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
  return typeof cycle.orb_deg === "number" ? `${num(cycle.orb_deg, 2)} deg` : "--";
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

function yearFromDate(value) {
  const match = String(value || "").match(/^-?\d{1,4}/);
  if (!match) {
    return null;
  }
  const parsed = Number(match[0]);
  return Number.isFinite(parsed) ? parsed : null;
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
  const best = episode.best_date || "the selected period";
  const eventCount = episode.matched_events?.length || 0;
  return `The backend found a similar planetary vector around ${best}, with resonance score ${score}. ${eventCount} matched events are attached as direct evidence. ${cycles ? `Active cycles: ${cycles}.` : "No cycle list was returned."}`;
}

function renderEvents(events = []) {
  if (!events.length) {
    return `<div class="empty-state compact">No events in this bucket.</div>`;
  }
  return events.map(renderEvent).join("");
}

function renderEvent(event) {
  return `
    <article class="event-card">
      <div>
        <h4>${escapeHtml(event.title)}</h4>
        <p>${escapeHtml(event.display_date)} | ${escapeHtml(event.category)} | ${escapeHtml(event.event_kind)}</p>
      </div>
      <span class="status-pill">${percent(event.confidence_score)}</span>
      ${renderEventSources(event)}
    </article>
  `;
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
  const trimmed = value.trim();
  if (/^-?\d{1,4}$/.test(trimmed)) {
    return `${trimmed.padStart(4, "0")}-01-01T00:00:00Z`;
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
    return `${trimmed}T00:00:00Z`;
  }
  return new Date(trimmed).toISOString();
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
  const pair = Array.isArray(cycle.pair) ? cycle.pair.join("-") : "unknown";
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
  return String(value).replace("T00:00:00+00:00", "").replace("T00:00:00Z", "").slice(0, 16);
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
    return `${status}: ${payload.episodes?.length || 0} episodes for ${shortDate(payload.query_datetime_utc)}`;
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
  const route = document.querySelector(`[data-view="${state.currentView}"]`)?.dataset.route;
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
    state.selectedEpisodeIndex = clampEpisodeIndex(episodeIndex, state.currentSearch.episodes || []);
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
  }
});

connectButton.addEventListener("click", () => connectBackend());
window.addEventListener("hashchange", () => {
  const nextView = window.location.hash.replace(/^#\/?/, "") || "home";
  setActiveView(nextView, { skipHash: true });
});

initFromUrl();
state.currentView = window.location.hash.replace(/^#\/?/, "") || "home";
syncNav();
renderActiveView({ skipAutoLoad: true });
window.__ASTRO_SHELL_READY = true;
connectBackend();
