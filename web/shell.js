const API_TOKEN_HEADER = "x-astro-global-session";
const DEFAULT_API_BASE = "http://127.0.0.1:8765";
const DEFAULT_SESSION_TOKEN = "dev-local-token";
const DEFAULT_INDEX_FILE = "swiss_1500_now_global_slow_v1.npz";

const apiBaseInput = document.querySelector("#apiBase");
const sessionTokenInput = document.querySelector("#sessionToken");
const connectButton = document.querySelector("#connectButton");
const connectionState = document.querySelector("#connectionState");
const runtimeBadge = document.querySelector("#runtimeBadge");
const homeMetrics = document.querySelector("#homeMetrics");
const leftRail = document.querySelector("#leftRail");
const rightRail = document.querySelector("#rightRail");
const viewPanel = document.querySelector("#viewPanel");
const viewControls = document.querySelector("#viewControls");
const viewTitle = document.querySelector("#viewTitle");
const viewKicker = document.querySelector("#viewKicker");
const timelineModule = document.querySelector("#timelineModule");
const primarySummary = document.querySelector("#primarySummary");
const navLinks = [...document.querySelectorAll("[data-view]")];

const state = {
  apiBase: DEFAULT_API_BASE,
  token: DEFAULT_SESSION_TOKEN,
  status: null,
  today: null,
  timelineSeeds: null,
  articleSeeds: null,
  currentSearch: null,
  currentCompare: null,
  currentView: "home",
};

const routeMeta = {
  home: ["Home", "Historical resonance engine"],
  today: ["Today", "GET /today"],
  explorer: ["Explorer", "POST /resonance/search"],
  compare: ["Compare", "POST /resonance/compare"],
  calendar: ["Calendar", "GET /timeline/seeds"],
  insights: ["Insights", "GET /articles/seeds"],
  library: ["Library", "Knowledge base shell"],
  blog: ["Blog", "Human editorial space"],
  contact: ["Contact", "Request analysis shell"],
};

function initFromUrl() {
  const params = new URLSearchParams(window.location.search);
  state.apiBase = params.get("apiBase") || DEFAULT_API_BASE;
  state.token = params.get("token") || DEFAULT_SESSION_TOKEN;
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

async function connectBackend() {
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
    setConnection("ok", "backend connected");
    renderGlobalShell();
    await renderActiveView(state.currentView, { refresh: true });
  } catch (error) {
    setConnection("error", errorMessage(error));
    renderBackendUnavailable(error);
  }
}

function setConnection(kind, label) {
  connectionState.innerHTML = `<span class="status-pill ${kind}">${escapeHtml(label)}</span>`;
  runtimeBadge.textContent = label;
  runtimeBadge.className = `status-pill ${kind}`;
}

function renderGlobalShell() {
  const dataStore = state.status?.data_store;
  const security = state.status?.security;
  const providers = state.status?.providers;
  homeMetrics.innerHTML = `
    <span><strong>${escapeHtml(String(dataStore?.curated_events_count ?? "--"))}</strong> curated events</span>
    <span><strong>${escapeHtml(providers?.swiss_available ? "Swiss" : "Synthetic")}</strong> provider status</span>
    <span><strong>${escapeHtml(security?.runtime_environment ?? "--")}</strong> runtime</span>
  `;
  renderTimelineSeeds();
}

function renderBackendUnavailable(error) {
  const message = errorMessage(error);
  homeMetrics.innerHTML = `
    <span><strong>Offline</strong> backend unavailable</span>
    <span><strong>No fake data</strong> UI is waiting for API</span>
    <span><strong>Run</strong> python scripts/run_api.py --port 8765</span>
  `;
  leftRail.innerHTML = panelMessage("Backend unavailable", message);
  rightRail.innerHTML = panelMessage("No evidence loaded", "Matched events and sources require a successful API response.");
  primarySummary.innerHTML = `
    <p class="eyebrow">Backend unavailable</p>
    <h3>FastAPI did not answer</h3>
    <p class="resonance-type">No demo values rendered</p>
    <strong>--</strong>
    <dl>
      <div><dt>Reason</dt><dd>${escapeHtml(message)}</dd></div>
      <div><dt>Expected API</dt><dd>${escapeHtml(state.apiBase)}</dd></div>
      <div><dt>Health endpoint</dt><dd>GET /health</dd></div>
    </dl>
  `;
  timelineModule.innerHTML = `<div class="empty-state">Timeline seeds cannot load until the backend is available.</div>`;
  viewPanel.innerHTML = errorState("Backend unavailable", message);
}

function panelMessage(title, message) {
  return `
    <div class="sub-panel">
      <p class="eyebrow">${escapeHtml(title)}</p>
      <p class="panel-note">${escapeHtml(message)}</p>
    </div>
  `;
}

function setActiveView(viewName, options = {}) {
  state.currentView = routeMeta[viewName] ? viewName : "home";
  const [title, kicker] = routeMeta[state.currentView];
  viewTitle.textContent = title;
  viewKicker.textContent = kicker;
  document.body.dataset.view = state.currentView;

  for (const link of navLinks) {
    link.classList.toggle("active", link.dataset.view === state.currentView);
  }

  const route = document.querySelector(`[data-view="${state.currentView}"]`)?.dataset.route;
  if (route) {
    history.replaceState({ view: state.currentView }, "", `#${route === "/" ? "home" : route.slice(1)}`);
  }

  return renderActiveView(state.currentView, options);
}

async function renderActiveView(viewName, options = {}) {
  if (!state.status && viewName !== "contact" && viewName !== "blog" && viewName !== "library") {
    renderStaticOrOfflineView(viewName);
    return;
  }
  if (viewName === "home") {
    renderHomeView();
  } else if (viewName === "today") {
    await renderTodayView(options);
  } else if (viewName === "explorer") {
    renderExplorerView();
    if (!options.skipAutoSearch && (!state.currentSearch || options.refresh)) {
      await runExplorerSearch(defaultSearchRequest());
    }
  } else if (viewName === "compare") {
    renderCompareView();
  } else if (viewName === "calendar") {
    renderCalendarView();
  } else if (viewName === "insights") {
    renderInsightsView();
  } else if (viewName === "library") {
    renderLibraryView();
  } else if (viewName === "blog") {
    renderBlogView();
  } else if (viewName === "contact") {
    renderContactView();
  }
}

function renderStaticOrOfflineView(viewName) {
  if (viewName === "library") {
    renderLibraryView();
  } else if (viewName === "blog") {
    renderBlogView();
  } else if (viewName === "contact") {
    renderContactView();
  } else {
    viewControls.innerHTML = `<button class="tool-chip active" type="button" id="retryConnect">Connect backend</button>`;
    document.querySelector("#retryConnect")?.addEventListener("click", connectBackend);
    viewPanel.innerHTML = emptyState(
      "Backend required",
      "This route renders real Astro Global API data. Start the backend or update API base/token."
    );
  }
}

function renderHomeView() {
  viewControls.innerHTML = `
    <button class="tool-chip active" type="button" data-view="explorer">Open Explorer</button>
    <button class="tool-chip" type="button" data-view="today">Today</button>
    <button class="tool-chip" type="button" data-view="compare">Compare</button>
  `;
  const timelineCount = state.timelineSeeds?.seeds?.length ?? 0;
  const articleCount = state.articleSeeds?.seeds?.length ?? 0;
  viewPanel.innerHTML = `
    <div class="view-intro">
      <p class="eyebrow">Live API overview</p>
      <p>
        The shell is connected to FastAPI. Explorer and Compare now use backend
        resonance responses; Timeline and Insights use backend-authored seeds.
      </p>
    </div>
    <div class="research-grid">
      <article class="research-card">
        <p class="card-label">Today snapshot</p>
        <h3>${escapeHtml(state.today?.snapshot_date_utc ?? "not loaded")}</h3>
        <p>${escapeHtml(state.today?.history_window_label ?? "No snapshot loaded.")}</p>
        ${badgeRow([state.today?.provider, state.today?.profile_id, state.today?.index_file].filter(Boolean))}
      </article>
      <article class="research-card">
        <p class="card-label">Timeline seeds</p>
        <h3>${timelineCount} backend seeds</h3>
        <p>Featured event anchors from GET /timeline/seeds. Clicking a seed can run a real search request.</p>
        ${badgeRow([state.timelineSeeds?.date_policy, state.timelineSeeds?.selection_policy].filter(Boolean))}
      </article>
      <article class="research-card">
        <p class="card-label">Insights seeds</p>
        <h3>${articleCount} article seeds</h3>
        <p>Seed-only research topics from GET /articles/seeds. No live AI generation runs in this UI.</p>
        ${badgeRow([state.articleSeeds?.content_policy, "human review required"].filter(Boolean))}
      </article>
    </div>
  `;
}

async function renderTodayView() {
  viewControls.innerHTML = `
    <button class="tool-chip active" type="button" id="runTodaySearch">Run recommended search</button>
    <button class="tool-chip" type="button" id="refreshToday">Refresh today</button>
  `;
  document.querySelector("#refreshToday")?.addEventListener("click", async () => {
    await refreshToday();
    renderTodayView();
  });
  document.querySelector("#runTodaySearch")?.addEventListener("click", async () => {
    await runExplorerSearch(state.today.recommended_search_request);
    setActiveView("explorer");
  });
  primarySummary.innerHTML = renderTodaySummary(state.today);
  viewPanel.innerHTML = `
    <div class="view-intro">
      <p class="eyebrow">Backend daily snapshot</p>
      <p>
        Today is not generated by the browser. It is GET /today plus a backend-authored
        recommended_search_request for POST /resonance/search.
      </p>
    </div>
    ${renderRequestCard("Recommended search", state.today?.recommended_search_request)}
    ${renderWarnings(state.today?.warnings)}
  `;
}

async function refreshToday() {
  viewPanel.innerHTML = loadingState("Refreshing GET /today");
  state.today = await apiRequest("/today");
  renderGlobalShell();
}

function renderExplorerView() {
  viewControls.innerHTML = `
    <form class="inline-form" id="explorerForm">
      <label>Date or year <input name="date" value="${escapeHtml(defaultDateValue())}" /></label>
      <label>Lookback <input name="lookback" type="number" min="1" max="600" value="120" /></label>
      <label>Episodes <input name="episodes" type="number" min="1" max="20" value="5" /></label>
      <button class="primary-action" type="submit">Search</button>
    </form>
  `;
  document.querySelector("#explorerForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const request = {
      ...defaultSearchRequest(),
      date_utc: normalizeDateInput(form.date.value),
      lookback_years: Number(form.lookback.value),
      max_episodes: Number(form.episodes.value),
    };
    await runExplorerSearch(request);
  });
  if (state.currentSearch) {
    renderSearchResult(state.currentSearch);
  } else {
    viewPanel.innerHTML = loadingState("Loading recommended Explorer search");
  }
}

async function runExplorerSearch(request) {
  viewPanel.innerHTML = loadingState("Running POST /resonance/search");
  try {
    const payload = await apiRequest("/resonance/search", {
      method: "POST",
      body: request,
    });
    state.currentSearch = payload;
    renderSearchResult(payload);
  } catch (error) {
    viewPanel.innerHTML = errorState("Search failed", errorMessage(error));
  }
}

function renderSearchResult(payload) {
  const episodes = payload.episodes || [];
  const firstEpisode = episodes[0];
  leftRail.innerHTML = renderCycleRail(payload);
  rightRail.innerHTML = renderEvidenceRail(payload);
  primarySummary.innerHTML = renderSearchSummary(payload, firstEpisode);
  timelineModule.innerHTML = renderEpisodeTimeline(episodes);
  viewPanel.innerHTML = `
    <div class="view-intro">
      <p class="eyebrow">Why this match?</p>
      <p>${escapeHtml(summaryText(payload.deterministic_summary))}</p>
    </div>
    ${renderCoverage(payload.index_coverage)}
    ${renderCycleGrid(payload.primary_cycles, payload.supporting_cycles)}
    <div class="episode-list">
      ${episodes.length ? episodes.map(renderEpisode).join("") : emptyState("No episodes", "The backend returned no episodes for this request.")}
    </div>
  `;
}

function renderCompareView() {
  viewControls.innerHTML = `
    <form class="inline-form" id="compareForm">
      <label>Left date <input name="left" value="1789" /></label>
      <label>Right date <input name="right" value="1848" /></label>
      <button class="primary-action" type="submit">Compare</button>
    </form>
  `;
  document.querySelector("#compareForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    await runCompare({
      ...defaultCompareRequest(),
      left_date_utc: normalizeDateInput(form.left.value),
      right_date_utc: normalizeDateInput(form.right.value),
    });
  });
  if (state.currentCompare) {
    renderCompareResult(state.currentCompare);
  } else {
    viewPanel.innerHTML = `
      <div class="view-intro">
        <p class="eyebrow">Real compare endpoint</p>
        <p>Submit two dates to POST /resonance/compare, or open an article seed in Insights.</p>
      </div>
      ${renderCompareSeedCards()}
    `;
  }
}

async function runCompare(request) {
  viewPanel.innerHTML = loadingState("Running POST /resonance/compare");
  try {
    const payload = await apiRequest("/resonance/compare", {
      method: "POST",
      body: request,
    });
    state.currentCompare = payload;
    renderCompareResult(payload);
  } catch (error) {
    viewPanel.innerHTML = errorState("Compare failed", errorMessage(error));
  }
}

function renderCompareResult(payload) {
  leftRail.innerHTML = renderCompareRail(payload);
  rightRail.innerHTML = renderCompareEvidence(payload);
  primarySummary.innerHTML = `
    <p class="eyebrow">Query vector similarity</p>
    <h3>${escapeHtml(shortDate(payload.left?.query_datetime_utc))} vs ${escapeHtml(shortDate(payload.right?.query_datetime_utc))}</h3>
    <p class="resonance-type">POST /resonance/compare</p>
    <strong>${percent(payload.query_vector_similarity)}</strong>
    <dl>
      <div><dt>Shared primary cycles</dt><dd>${escapeHtml(String(payload.shared_primary_cycles?.length ?? 0))}</dd></div>
      <div><dt>Shared matched events</dt><dd>${escapeHtml(String(payload.shared_matched_event_ids?.length ?? 0))}</dd></div>
      <div><dt>Shared context events</dt><dd>${escapeHtml(String(payload.shared_context_event_ids?.length ?? 0))}</dd></div>
    </dl>
  `;
  timelineModule.innerHTML = renderCompareTimeline(payload);
  viewPanel.innerHTML = `
    <div class="view-intro">
      <p class="eyebrow">Compare summary</p>
      <p>${escapeHtml(payload.deterministic_summary)}</p>
    </div>
    ${renderWarnings(payload.warnings)}
    <div class="compare-grid">
      ${renderCompareSide("Left", payload.left)}
      ${renderCompareSide("Right", payload.right)}
    </div>
  `;
}

function renderCalendarView() {
  viewControls.innerHTML = `
    <button class="tool-chip active" type="button" id="refreshTimeline">Refresh seeds</button>
  `;
  document.querySelector("#refreshTimeline")?.addEventListener("click", async () => {
    state.timelineSeeds = await apiRequest("/timeline/seeds");
    renderCalendarView();
  });
  renderTimelineSeeds();
  viewPanel.innerHTML = `
    <div class="view-intro">
      <p class="eyebrow">Backend timeline seeds</p>
      <p>
        These are backend-authored event anchors from GET /timeline/seeds. They are
        not a prediction calendar and do not add events in the browser.
      </p>
    </div>
    <div class="seed-grid">
      ${(state.timelineSeeds?.seeds || []).map(renderTimelineSeed).join("")}
    </div>
  `;
  bindSeedButtons();
}

function renderInsightsView() {
  viewControls.innerHTML = `
    <button class="tool-chip active" type="button" id="refreshArticles">Refresh article seeds</button>
  `;
  document.querySelector("#refreshArticles")?.addEventListener("click", async () => {
    state.articleSeeds = await apiRequest("/articles/seeds");
    renderInsightsView();
  });
  viewPanel.innerHTML = `
    <div class="view-intro">
      <p class="eyebrow">AI-assisted seeds only</p>
      <p>
        Insights loads seed-only topics from GET /articles/seeds. It does not generate
        articles or call an AI model in the browser.
      </p>
    </div>
    <div class="seed-grid">
      ${(state.articleSeeds?.seeds || []).map(renderArticleSeed).join("")}
    </div>
  `;
  bindArticleButtons();
}

function renderLibraryView() {
  viewControls.innerHTML = "";
  viewPanel.innerHTML = `
    <div class="view-intro">
      <p class="eyebrow">Knowledge base</p>
      <p>Library remains a static education shell until dedicated backend endpoints exist.</p>
    </div>
    <div class="research-grid">
      ${renderInfoCard("Cycles", "Planetary cycle dictionary", ["primary cycles", "supporting cycles", "orb"])}
      ${renderInfoCard("Sources", "Source archive and confidence notes", ["source links", "quality", "precision"])}
      ${renderInfoCard("Explain", "Aspect and scoring explainers", ["score breakdown", "coverage", "limits"])}
    </div>
  `;
}

function renderBlogView() {
  viewControls.innerHTML = "";
  viewPanel.innerHTML = `
    <div class="view-intro">
      <p class="eyebrow">Human essays</p>
      <p>Blog is kept separate from backend article seeds and AI-assisted research notes.</p>
    </div>
    <div class="research-grid">
      ${renderInfoCard("Manual", "Personal observation", ["human written", "editorial", "separate from AI"])}
      ${renderInfoCard("Education", "How to read cycles", ["manual text", "learning", "voice"])}
      ${renderInfoCard("Journal", "Field notes", ["drafts", "observations", "review"])}
    </div>
  `;
}

function renderContactView() {
  viewControls.innerHTML = "";
  viewPanel.innerHTML = `
    <div class="view-intro">
      <p class="eyebrow">Request analysis</p>
      <p>This is only a contact shell. It does not send private data anywhere yet.</p>
    </div>
    <form class="contact-form" id="contactForm">
      <label>Name <input name="name" autocomplete="name" /></label>
      <label>Email <input name="email" type="email" autocomplete="email" /></label>
      <label>Topic
        <select name="topic">
          <option>Private analysis</option>
          <option>Research question</option>
          <option>Editorial contact</option>
        </select>
      </label>
      <label class="wide-field">Message <textarea name="message" rows="4"></textarea></label>
      <label>Birth date <input name="birthDate" type="date" /></label>
      <label>Birth time <input name="birthTime" type="time" /></label>
      <label class="wide-field">Birth place <input name="birthPlace" /></label>
      <label class="consent-field wide-field">
        <input name="consent" type="checkbox" />
        <span>I consent to processing this request.</span>
      </label>
      <button class="primary-action" type="submit">Prepare request</button>
      <span class="form-state" id="contactState" aria-live="polite"></span>
    </form>
  `;
  document.querySelector("#contactForm")?.addEventListener("submit", (event) => {
    event.preventDefault();
    document.querySelector("#contactState").textContent = "Draft prepared locally. No API request sent.";
  });
}

function defaultSearchRequest() {
  const recommended = state.today?.recommended_search_request;
  return {
    date_utc: recommended?.date_utc || new Date().toISOString(),
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

function defaultCompareRequest() {
  const seed = state.articleSeeds?.seeds?.[0]?.compare_request;
  return {
    left_date_utc: seed?.left_date_utc || "1789-01-01T00:00:00Z",
    right_date_utc: seed?.right_date_utc || "1848-01-01T00:00:00Z",
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

function renderCycleRail(payload) {
  return `
    <div class="panel-heading">
      <p class="eyebrow">Primary cycles</p>
      <span class="status-pill ok">${escapeHtml(payload.provider)}</span>
    </div>
    <p class="panel-note">${escapeHtml(shortDate(payload.query_datetime_utc))} via ${escapeHtml(payload.index_source)}</p>
    <div class="resonance-list">
      ${(payload.primary_cycles || []).slice(0, 5).map(renderCycleItem).join("") || emptyState("No primary cycles", "Backend returned no primary cycles.")}
    </div>
    <div class="sub-panel">
      <p class="eyebrow">Supporting cycles</p>
      <div class="compact-list">
        ${(payload.supporting_cycles || []).slice(0, 6).map((cycle) => `<span>${escapeHtml(cycleLabel(cycle))}</span>`).join("") || "<span>none</span>"}
      </div>
    </div>
  `;
}

function renderCycleItem(cycle) {
  return `
    <article>
      <span class="cycle-icon">${escapeHtml(String(cycle.aspect || "?").slice(0, 1).toUpperCase())}</span>
      <div>
        <h3>${escapeHtml(cycleLabel(cycle))}</h3>
        <p>orb ${num(cycle.orb_deg, 2)} deg, contribution ${num(cycle.contribution, 3)}</p>
      </div>
      <strong>${escapeHtml(String(cycle.tier || cycle.role || ""))}</strong>
    </article>
  `;
}

function renderEvidenceRail(payload) {
  const first = payload.episodes?.[0];
  if (!first) {
    return panelMessage("Evidence", "No episodes returned.");
  }
  return `
    <div class="sub-panel confidence-panel">
      <p class="eyebrow">Confidence index</p>
      <div class="confidence-ring" aria-label="Narrative confidence ${percent(first.narrative_confidence?.narrative_confidence)}">
        <span>${percent(first.narrative_confidence?.narrative_confidence)}</span>
        <small>${escapeHtml(first.score_breakdown?.label || "score")}</small>
      </div>
      <ul class="score-list">
        <li><span>Event coverage</span><strong>${percent(first.narrative_confidence?.event_coverage_score)}</strong></li>
        <li><span>Source quality</span><strong>${percent(first.narrative_confidence?.source_quality_score)}</strong></li>
        <li><span>Evidence</span><strong>${percent(first.narrative_confidence?.evidence_confidence)}</strong></li>
        <li><span>Resonance</span><strong>${num(first.score_breakdown?.planetary_resonance_score, 3)}</strong></li>
      </ul>
    </div>
    <div class="sub-panel">
      <p class="eyebrow">Score breakdown</p>
      ${renderScoreBreakdown(first.score_breakdown)}
    </div>
    <div class="sub-panel">
      <p class="eyebrow">Sources</p>
      ${renderSourceList(first)}
    </div>
  `;
}

function renderCompareRail(payload) {
  return `
    <div class="panel-heading">
      <p class="eyebrow">Shared cycles</p>
      <span class="status-pill ok">${percent(payload.query_vector_similarity)}</span>
    </div>
    <div class="compact-list">
      ${(payload.shared_primary_cycles || []).map((label) => `<span>${escapeHtml(label)}</span>`).join("") || "<span>none</span>"}
    </div>
    ${renderWarnings(payload.warnings)}
  `;
}

function renderCompareEvidence(payload) {
  return `
    <div class="sub-panel">
      <p class="eyebrow">Shared matched events</p>
      <div class="compact-list">${eventIdChips(payload.shared_matched_event_ids)}</div>
    </div>
    <div class="sub-panel">
      <p class="eyebrow">Shared context events</p>
      <div class="compact-list">${eventIdChips(payload.shared_context_event_ids)}</div>
    </div>
    <div class="sub-panel">
      <p class="eyebrow">Different evidence</p>
      <p class="panel-note">Left only: ${escapeHtml(String(payload.left_only_matched_event_ids?.length ?? 0))}</p>
      <p class="panel-note">Right only: ${escapeHtml(String(payload.right_only_matched_event_ids?.length ?? 0))}</p>
    </div>
  `;
}

function renderSearchSummary(payload, episode) {
  const score = episode?.score_breakdown;
  return `
    <p class="eyebrow">Active backend result</p>
    <h3>${escapeHtml(shortDate(payload.query_datetime_utc))}</h3>
    <p class="resonance-type">${escapeHtml(score?.label || "resonance search")}</p>
    <strong>${num(score?.planetary_resonance_score, 3)}</strong>
    <dl>
      <div><dt>Best episode</dt><dd>${escapeHtml(episode?.best_date || "--")}</dd></div>
      <div><dt>Matched events</dt><dd>${escapeHtml(String(episode?.matched_events?.length ?? 0))}</dd></div>
      <div><dt>Context events</dt><dd>${escapeHtml(String(episode?.context_events?.length ?? 0))}</dd></div>
    </dl>
  `;
}

function renderTodaySummary(today) {
  return `
    <p class="eyebrow">Today snapshot</p>
    <h3>${escapeHtml(today?.snapshot_date_utc || "--")}</h3>
    <p class="resonance-type">GET /today</p>
    <strong>${escapeHtml(today?.provider || "--")}</strong>
    <dl>
      <div><dt>History window</dt><dd>${escapeHtml(today?.history_window_label || "--")}</dd></div>
      <div><dt>Index file</dt><dd>${escapeHtml(today?.index_file || "--")}</dd></div>
      <div><dt>Expires</dt><dd>${escapeHtml(shortDate(today?.expires_at_utc))}</dd></div>
    </dl>
  `;
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

function renderCycleGrid(primaryCycles = [], supportingCycles = []) {
  return `
    <div class="cycle-data-grid">
      <article class="research-card">
        <p class="card-label">Primary cycles</p>
        <h3>${primaryCycles.length} drivers</h3>
        <p>${primaryCycles.slice(0, 3).map(cycleLabel).join(", ") || "No primary cycles returned."}</p>
        ${badgeRow(primaryCycles.slice(0, 4).map((cycle) => cycle.aspect || "cycle"))}
      </article>
      <article class="research-card">
        <p class="card-label">Supporting cycles</p>
        <h3>${supportingCycles.length} supporting</h3>
        <p>${supportingCycles.slice(0, 4).map(cycleLabel).join(", ") || "No supporting cycles returned."}</p>
        ${badgeRow(supportingCycles.slice(0, 4).map((cycle) => cycle.aspect || "cycle"))}
      </article>
    </div>
  `;
}

function renderEpisode(episode, index) {
  return `
    <article class="episode-card">
      <div class="episode-head">
        <div>
          <p class="card-label">Episode ${index + 1}</p>
          <h3>${escapeHtml(episode.period_start)} to ${escapeHtml(episode.period_end)}</h3>
        </div>
        <span class="status-pill ok">${escapeHtml(episode.score_breakdown?.label || "score")}</span>
      </div>
      <div class="metric-grid">
        <span><strong>${escapeHtml(episode.best_date)}</strong> best date</span>
        <span><strong>${num(episode.best_score, 3)}</strong> structural score</span>
        <span><strong>${percent(episode.narrative_confidence?.narrative_confidence)}</strong> confidence</span>
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
    </article>
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
    return "";
  }
  return `
    <div class="source-row">
      ${sources.slice(0, 3).map((source) => {
        const url = safeUrl(source.source_url);
        return url
          ? `<a href="${url}" target="_blank" rel="noreferrer">${escapeHtml(source.source_name)}</a>`
          : `<span>${escapeHtml(source.source_name)}</span>`;
      }).join("")}
    </div>
  `;
}

function renderScoreBreakdown(score = {}) {
  const rows = [
    ["Structural similarity", score.structural_similarity],
    ["Cycle power", score.cycle_power_score],
    ["Rarity percentile", score.rarity_adjusted_percentile],
    ["Strongest primary", score.strongest_primary_contribution],
  ];
  return `<ul class="score-list">${rows.map(([label, value]) => `<li><span>${label}</span><strong>${num(value, 3)}</strong></li>`).join("")}</ul>`;
}

function renderSourceList(episode) {
  const sources = [];
  for (const event of [...(episode.matched_events || []), ...(episode.context_events || [])]) {
    for (const source of event.sources || []) {
      if (!sources.some((item) => item.source_id === source.source_id)) {
        sources.push(source);
      }
    }
  }
  if (!sources.length) {
    return `<p class="panel-note">No sources returned.</p>`;
  }
  return `
    <div class="source-list">
      ${sources.slice(0, 10).map((source) => {
        const url = safeUrl(source.source_url);
        return `<a href="${url}" target="_blank" rel="noreferrer">${escapeHtml(source.source_name)} <small>${escapeHtml(source.source_quality)}</small></a>`;
      }).join("")}
    </div>
  `;
}

function renderEpisodeTimeline(episodes = []) {
  if (!episodes.length) {
    return `<div class="empty-state">No episodes returned.</div>`;
  }
  return `
    <div class="timeline-scale">
      ${episodes.map((episode) => `<span>${escapeHtml(episode.best_date)}</span>`).join("")}
    </div>
    <div class="timeline-track">
      ${episodes.map((_, index) => `<span style="left: ${episodePoint(index, episodes.length)}%"></span>`).join("")}
    </div>
    <div class="era-cards">
      ${episodes.map((episode) => `
        <article>
          <strong>${escapeHtml(episode.best_date)}</strong>
          <span>${escapeHtml(episode.score_breakdown?.label || "episode")}</span>
          <p>${escapeHtml(String(episode.matched_events?.length ?? 0))} matched, ${escapeHtml(String(episode.context_events?.length ?? 0))} context</p>
        </article>
      `).join("")}
    </div>
  `;
}

function renderTimelineSeeds() {
  const seeds = state.timelineSeeds?.seeds || [];
  if (!seeds.length) {
    timelineModule.innerHTML = `<div class="empty-state">Timeline seeds load from GET /timeline/seeds.</div>`;
    return;
  }
  timelineModule.innerHTML = `
    <div class="timeline-scale">
      ${seeds.slice(0, 7).map((seed) => `<span>${escapeHtml(String(seed.start_astro_year))}</span>`).join("")}
    </div>
    <div class="timeline-track">
      ${seeds.slice(0, 7).map((_, index) => `<span style="left: ${episodePoint(index, Math.min(seeds.length, 7))}%"></span>`).join("")}
    </div>
    <div class="era-cards">
      ${seeds.slice(0, 5).map((seed) => `
        <article>
          <strong>${escapeHtml(seed.display_date)}</strong>
          <span>${escapeHtml(seed.title)}</span>
          <p>${escapeHtml(seed.category)} | ${escapeHtml(seed.date_precision)}</p>
        </article>
      `).join("")}
    </div>
  `;
}

function renderTimelineSeed(seed) {
  return `
    <article class="research-card">
      <p class="card-label">${escapeHtml(seed.display_date)}</p>
      <h3>${escapeHtml(seed.title)}</h3>
      <p>${escapeHtml(seed.category)} | ${escapeHtml(seed.region)} | ${escapeHtml(seed.date_precision)}</p>
      ${badgeRow([seed.event_kind, seed.geo_scope, percent(seed.confidence_score)])}
      <button class="text-action seed-search" type="button" data-seed-id="${escapeHtml(seed.seed_id)}">Run search</button>
    </article>
  `;
}

function renderArticleSeed(seed) {
  return `
    <article class="research-card">
      <p class="card-label">${escapeHtml(seed.editorial_status)}</p>
      <h3>${escapeHtml(seed.title)}</h3>
      <p>${escapeHtml(seed.summary)}</p>
      ${badgeRow(["Generated/Assisted by Astro Global", "Human reviewed", "Sources included"])}
      <button class="text-action article-compare" type="button" data-seed-id="${escapeHtml(seed.seed_id)}">Run compare</button>
    </article>
  `;
}

function renderCompareSeedCards() {
  const seeds = state.articleSeeds?.seeds || [];
  if (!seeds.length) {
    return emptyState("No article seeds", "GET /articles/seeds returned no seeds.");
  }
  return `<div class="seed-grid">${seeds.map(renderArticleSeed).join("")}</div>`;
}

function bindSeedButtons() {
  document.querySelectorAll(".seed-search").forEach((button) => {
    button.addEventListener("click", async () => {
      const seed = state.timelineSeeds.seeds.find((item) => item.seed_id === button.dataset.seedId);
      if (seed) {
        await setActiveView("explorer", { skipAutoSearch: true });
        await runExplorerSearch(seed.search_request);
      }
    });
  });
}

function bindArticleButtons() {
  document.querySelectorAll(".article-compare").forEach((button) => {
    button.addEventListener("click", async () => {
      const seed = state.articleSeeds.seeds.find((item) => item.seed_id === button.dataset.seedId);
      if (seed) {
        await setActiveView("compare", { skipAutoSearch: true });
        await runCompare(seed.compare_request);
      }
    });
  });
}

function renderCompareSide(label, search) {
  const first = search?.episodes?.[0];
  return `
    <article class="episode-card">
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
      <span><strong>${num(episode.score_breakdown?.planetary_resonance_score, 3)}</strong> resonance</span>
      <span><strong>${percent(episode.narrative_confidence?.narrative_confidence)}</strong> confidence</span>
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

function renderCompareTimeline(payload) {
  return `
    <div class="era-cards">
      <article><strong>${escapeHtml(shortDate(payload.left?.query_datetime_utc))}</strong><span>Left side</span><p>${escapeHtml(String(payload.left?.episodes?.length ?? 0))} episodes</p></article>
      <article class="selected"><strong>${percent(payload.query_vector_similarity)}</strong><span>Vector similarity</span><p>${escapeHtml(String(payload.shared_primary_cycles?.length ?? 0))} shared cycles</p></article>
      <article><strong>${escapeHtml(shortDate(payload.right?.query_datetime_utc))}</strong><span>Right side</span><p>${escapeHtml(String(payload.right?.episodes?.length ?? 0))} episodes</p></article>
    </div>
  `;
}

function renderRequestCard(title, request) {
  if (!request) {
    return emptyState(title, "No request returned.");
  }
  return `
    <article class="episode-card">
      <p class="card-label">${escapeHtml(title)}</p>
      <h3>${escapeHtml(shortDate(request.date_utc || request.left_date_utc))}</h3>
      <pre class="request-preview">${escapeHtml(JSON.stringify(request, null, 2))}</pre>
    </article>
  `;
}

function renderInfoCard(label, title, badges) {
  return `
    <article class="research-card">
      <p class="card-label">${escapeHtml(label)}</p>
      <h3>${escapeHtml(title)}</h3>
      <p>This route is intentionally separate from live resonance search.</p>
      ${badgeRow(badges)}
    </article>
  `;
}

function renderWarnings(warnings = []) {
  if (!warnings?.length) {
    return "";
  }
  return `<div class="warning-box">${warnings.map((warning) => `<p>${escapeHtml(warning)}</p>`).join("")}</div>`;
}

function badgeRow(items = []) {
  return `<div class="badge-row">${items.map((item) => `<span class="status-pill">${escapeHtml(String(item))}</span>`).join("")}</div>`;
}

function eventIdChips(ids = []) {
  return ids.length ? ids.map((id) => `<span>${escapeHtml(id)}</span>`).join("") : "<span>none</span>";
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

function errorMessage(error) {
  if (error instanceof ApiError) {
    return `${error.status}: ${error.message}`;
  }
  return error?.message || String(error);
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

function defaultDateValue() {
  const date = state.currentSearch?.query_datetime_utc || state.today?.recommended_search_request?.date_utc;
  return date ? shortDate(date) : "2026-05-23";
}

function shortDate(value) {
  if (!value) {
    return "--";
  }
  return String(value).replace("T00:00:00+00:00", "").replace("T00:00:00Z", "").slice(0, 16);
}

function cycleLabel(cycle = {}) {
  const pair = Array.isArray(cycle.pair) ? cycle.pair.join("-") : "unknown";
  return `${pair}:${cycle.aspect || "cycle"}`;
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

function episodePoint(index, total) {
  if (total <= 1) {
    return 50;
  }
  return 6 + (index * 88) / (total - 1);
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

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => {
    const escapes = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
    return escapes[char];
  });
}

document.addEventListener("click", (event) => {
  const trigger = event.target.closest("[data-view]");
  if (!trigger) {
    return;
  }
  event.preventDefault();
  setActiveView(trigger.dataset.view);
});

connectButton.addEventListener("click", connectBackend);
document.querySelector('[data-action="refresh-view"]')?.addEventListener("click", () => {
  renderActiveView(state.currentView, { refresh: true });
});
window.addEventListener("hashchange", () => setActiveView(window.location.hash.replace(/^#\/?/, "") || "home"));

initFromUrl();
setActiveView(window.location.hash.replace(/^#\/?/, "") || "home");
connectBackend();
