const API_TOKEN_HEADER = "x-astro-global-session";
const DEFAULT_API_BASE = "http://127.0.0.1:8765";
const DEFAULT_SESSION_TOKEN = "dev-local-token";
const DEFAULT_INDEX_FILE = "swiss_1500_now_global_slow_v1.npz";
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
  document.body.dataset.view = state.currentView;
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
    <section class="page-shell explorer-page">
      <div class="page-heading compact-heading">
        <p class="eyebrow">Explorer</p>
        <h1>Date to resonance result</h1>
        <p>Analyze a date, inspect the strongest historical episodes, and see why the engine matched them.</p>
      </div>
      <form class="analysis-form" id="explorerForm">
        <label>
          Date
          <input name="date" value="${escapeHtml(defaultExplorerDate())}" autocomplete="off" />
        </label>
        <button class="primary-action" type="submit">Analyze date</button>
        <div class="example-row" aria-label="Explorer examples">
          ${EXPLORER_EXAMPLES.map((date) => `<button type="button" data-example-date="${date}">${date}</button>`).join("")}
        </div>
      </form>
      <div id="explorerResult">
        ${state.currentSearch ? renderSearchResult(state.currentSearch) : emptyState("No analysis yet", "Choose a date and run Analyze date.")}
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
  const target = document.querySelector("#explorerResult") || appRoot;
  target.innerHTML = loadingState("Analyzing date with POST /resonance/search");
  try {
    const payload = await apiRequest("/resonance/search", {
      method: "POST",
      body: request,
    });
    state.currentSearch = payload;
    const dateInput = document.querySelector("#explorerForm input[name='date']");
    if (dateInput) {
      dateInput.value = shortDate(payload.query_datetime_utc);
    }
    if (state.currentView === "explorer") {
      target.innerHTML = renderSearchResult(payload);
    }
  } catch (error) {
    target.innerHTML = errorState("Analysis failed", errorMessage(error));
  }
}

function renderSearchResult(payload) {
  const queryDate = shortDate(payload.query_datetime_utc);
  const episodes = payload.episodes || [];
  return `
    <section class="result-header">
      <div>
        <p class="eyebrow">Resonance result</p>
        <h2>Resonance result for ${escapeHtml(queryDate)}</h2>
        <p>${escapeHtml(summaryText(payload.deterministic_summary))}</p>
      </div>
      <div class="result-meta">
        <span>${escapeHtml(payload.provider)}</span>
        <span>${escapeHtml(payload.index_coverage?.history_window_label || "coverage")}</span>
        <span>${escapeHtml(String(payload.index_rows))} index rows</span>
      </div>
    </section>
    ${renderCoverage(payload.index_coverage)}
    <section class="episode-list">
      ${episodes.length ? episodes.map((episode, index) => renderEpisodeCard(episode, index, payload)).join("") : emptyState("No episodes", "The backend returned no episodes for this date.")}
    </section>
  `;
}

function renderEpisodeCard(episode, index, payload) {
  return `
    <article class="episode-card product-episode">
      <div class="episode-head">
        <div>
          <p class="card-label">Episode ${index + 1}</p>
          <h3>${escapeHtml(episode.best_date)} within ${escapeHtml(episode.period_start)} to ${escapeHtml(episode.period_end)}</h3>
        </div>
        <span class="status-pill ok">${escapeHtml(episode.score_breakdown?.label || "resonance")}</span>
      </div>
      <div class="metric-grid">
        <span><strong>${escapeHtml(episode.best_date)}</strong> best date</span>
        <span><strong>${percent(episode.narrative_confidence?.narrative_confidence)}</strong> confidence</span>
        <span><strong>${num(episode.score_breakdown?.planetary_resonance_score, 3)}</strong> resonance score</span>
      </div>
      <section class="why-card">
        <p class="eyebrow">Why this match</p>
        <p>
          The backend found a similar planetary vector in this period, then attached
          historical evidence from the curated event layer. Direct evidence is shown as
          matched events; broad background is shown as context events.
        </p>
        ${renderEpisodeCycles(payload.primary_cycles, payload.supporting_cycles)}
      </section>
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
      <details class="technical-details">
        <summary>Technical details</summary>
        ${renderScoreBreakdown(episode.score_breakdown)}
        ${renderConfidenceBreakdown(episode.narrative_confidence)}
      </details>
    </article>
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
  const target = document.querySelector("#compareResult") || appRoot;
  target.innerHTML = loadingState("Comparing dates with POST /resonance/compare");
  try {
    const payload = await apiRequest("/resonance/compare", {
      method: "POST",
      body: request,
    });
    state.currentCompare = payload;
    if (state.currentView === "compare") {
      target.innerHTML = renderCompareResult(payload);
    }
  } catch (error) {
    target.innerHTML = errorState("Compare failed", errorMessage(error));
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
  const sources = event.sources || [];
  if (!sources.length) {
    return `<div class="source-row"><span>No sources returned</span></div>`;
  }
  return `
    <div class="source-row">
      ${sources.slice(0, 4).map((source) => {
        const url = safeUrl(source.source_url);
        return url
          ? `<a href="${url}" target="_blank" rel="noreferrer">${escapeHtml(source.source_name)}</a>`
          : `<span>${escapeHtml(source.source_name)}</span>`;
      }).join("")}
    </div>
  `;
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
  return shortDate(state.currentSearch?.query_datetime_utc || state.today?.recommended_search_request?.date_utc || "2026-05-24");
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
  document.body.dataset.view = state.currentView;
}

document.addEventListener("click", async (event) => {
  const viewTrigger = event.target.closest("[data-view]");
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
connectBackend();
