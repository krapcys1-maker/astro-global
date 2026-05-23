const form = document.querySelector("#connectionForm");
const searchForm = document.querySelector("#searchForm");
const compareButton = document.querySelector("#compareButton");
const runtimeBadges = document.querySelector("#runtimeBadges");
const requestState = document.querySelector("#requestState");
const summaryPanel = document.querySelector("#summaryPanel");
const episodesPanel = document.querySelector("#episodesPanel");
const jsonPanel = document.querySelector("#jsonPanel");

const endpointActions = {
  health: () => apiRequest("/health", { auth: false }),
  readiness: () => apiRequest("/readiness"),
  today: () => apiRequest("/today"),
  comparePresets: () => apiRequest("/resonance/compare/presets"),
  status: () => apiRequest("/data/status"),
};

function connection() {
  return {
    apiBase: form.apiBase.value.replace(/\/+$/, ""),
    token: form.sessionToken.value.trim(),
  };
}

function authHeaders() {
  const { token } = connection();
  return token ? { "x-astro-global-session": token } : {};
}

async function apiRequest(path, options = {}) {
  const { apiBase } = connection();
  const headers = {
    ...(options.body ? { "content-type": "application/json" } : {}),
    ...(options.auth === false ? {} : authHeaders()),
  };
  const response = await fetch(`${apiBase}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  return { ok: response.ok, status: response.status, payload };
}

function setState(label, kind = "muted") {
  requestState.className = `badge ${kind}`;
  requestState.textContent = label;
}

function showJson(payload) {
  jsonPanel.textContent = JSON.stringify(payload, null, 2);
}

function showError(result) {
  const detail = typeof result.payload === "object" ? result.payload.detail : result.payload;
  summaryPanel.innerHTML = `<span class="badge error">${result.status}</span><p class="summary-text">${escapeHtml(String(detail ?? "request failed"))}</p>`;
  episodesPanel.replaceChildren();
  showJson(result.payload);
}

function renderRuntimeStatus(payload) {
  const security = payload.security ?? {};
  const provider = payload.providers ?? {};
  runtimeBadges.replaceChildren(
    badge(security.runtime_environment ?? "runtime", "ok"),
    badge(provider.swiss_available ? "swiss ready" : "swiss unavailable", provider.swiss_available ? "ok" : "warn"),
    badge(security.rate_limit_enabled ? "rate limited" : "rate open", security.rate_limit_enabled ? "ok" : "warn"),
    badge(`${security.max_request_bytes ?? "?"} bytes`, "muted"),
  );
}

function renderToday(payload) {
  summaryPanel.replaceChildren(
    metricRow([
      [`today ${payload.snapshot_date_utc}`, "ok"],
      [payload.provider ?? "provider", "muted"],
      [payload.index_file ?? "index", "muted"],
      [payload.history_window_label ?? "history", "muted"],
    ]),
    paragraph(payload.warnings?.join(" ") ?? ""),
  );
  episodesPanel.replaceChildren();
  const request = payload.recommended_search_request ?? {};
  searchForm.dateUtc.value = request.date_utc ?? searchForm.dateUtc.value;
  searchForm.provider.value = request.provider ?? searchForm.provider.value;
  searchForm.indexFile.value = request.index_file ?? searchForm.indexFile.value;
  searchForm.lookbackYears.value = request.lookback_years ?? searchForm.lookbackYears.value;
  searchForm.lookaheadYears.value = request.lookahead_years ?? searchForm.lookaheadYears.value;
  searchForm.maxEpisodes.value = request.max_episodes ?? searchForm.maxEpisodes.value;
  showJson(payload);
}

function renderComparePresets(payload) {
  const presets = payload.presets ?? [];
  const firstPreset = presets[0];
  summaryPanel.replaceChildren(
    metricRow([
      [`presets ${presets.length}`, "ok"],
      [payload.provider ?? "provider", "muted"],
      [payload.date_policy ?? "date policy", "muted"],
    ]),
    paragraph(firstPreset ? `Loaded ${firstPreset.label}` : "No compare presets returned."),
  );
  episodesPanel.replaceChildren(...presets.map(renderComparePreset));
  if (firstPreset?.compare_request) {
    applyCompareRequest(firstPreset.compare_request);
  }
  showJson(payload);
}

function renderComparePreset(preset) {
  const article = document.createElement("article");
  article.className = "episode";
  article.append(
    heading(preset.label ?? preset.preset_id ?? "Preset"),
    metricRow([
      [preset.left_event?.event_id ?? "left", "muted"],
      [preset.right_event?.event_id ?? "right", "muted"],
      [preset.left_event?.date_precision ?? "precision", "warn"],
    ]),
    paragraph(preset.warnings?.join(" ") ?? ""),
  );
  article.addEventListener("click", () => applyCompareRequest(preset.compare_request ?? {}));
  return article;
}

function applyCompareRequest(request) {
  searchForm.dateUtc.value = request.left_date_utc ?? searchForm.dateUtc.value;
  searchForm.compareDateUtc.value = request.right_date_utc ?? searchForm.compareDateUtc.value;
  searchForm.provider.value = request.provider ?? searchForm.provider.value;
  searchForm.indexFile.value = request.index_file ?? searchForm.indexFile.value;
  searchForm.lookbackYears.value = request.lookback_years ?? searchForm.lookbackYears.value;
  searchForm.lookaheadYears.value = request.lookahead_years ?? searchForm.lookaheadYears.value;
  searchForm.maxEpisodes.value = request.max_episodes ?? searchForm.maxEpisodes.value;
}

function renderSearch(payload) {
  const summary = payload.deterministic_summary ?? {};
  const coverage = payload.index_coverage ?? {};
  const episodes = payload.episodes ?? [];

  summaryPanel.replaceChildren(
    metricRow([
      [payload.provider ?? "provider", "ok"],
      [payload.index_source ?? "index", "muted"],
      [coverage.history_window_label ?? "history", "muted"],
      [coverage.index_coverage_status ?? "coverage", coverage.index_coverage_status === "full" ? "ok" : "warn"],
    ]),
    paragraph(summary.summary ?? ""),
  );

  episodesPanel.replaceChildren(...episodes.map(renderEpisode));
  showJson(payload);
}

function renderCompare(payload) {
  const sharedEvents = payload.shared_matched_event_ids ?? [];
  const sharedCycles = payload.shared_primary_cycles ?? [];
  summaryPanel.replaceChildren(
    metricRow([
      [payload.provider ?? "provider", "ok"],
      [`similarity ${formatNumber(payload.query_vector_similarity)}`, "ok"],
      [`cycles ${sharedCycles.length}`, "muted"],
      [`events ${sharedEvents.length}`, sharedEvents.length ? "ok" : "muted"],
    ]),
    paragraph(payload.deterministic_summary ?? ""),
  );
  episodesPanel.replaceChildren(
    compareSide("Left", payload.left),
    compareSide("Right", payload.right),
  );
  showJson(payload);
}

function compareSide(title, search) {
  const article = document.createElement("article");
  article.className = "episode";
  const firstEpisode = search?.episodes?.[0];
  const score = firstEpisode?.score_breakdown ?? {};
  article.append(
    heading(`${title} ${search?.query_datetime_utc ?? ""}`),
    metricRow([
      [search?.index_coverage?.history_window_label ?? "history", "muted"],
      [search?.index_coverage?.index_coverage_status ?? "coverage", "muted"],
      [`episodes ${search?.episodes?.length ?? 0}`, "muted"],
      [`score ${formatNumber(score.planetary_resonance_score)}`, "ok"],
    ]),
    firstEpisode ? eventList("Matched events", firstEpisode.matched_events ?? []) : paragraph("No episodes."),
  );
  return article;
}

function renderEpisode(episode) {
  const article = document.createElement("article");
  article.className = "episode";
  const score = episode.score_breakdown ?? {};
  const matchedEvents = episode.matched_events ?? [];
  const contextEvents = episode.context_events ?? [];
  article.append(
    heading(`${episode.best_date ?? "episode"} · ${score.label ?? "score"}`),
    metricRow([
      [`score ${formatNumber(score.planetary_resonance_score)}`, "ok"],
      [`confidence ${formatNumber(episode.narrative_confidence?.narrative_confidence)}`, "muted"],
      [`matched ${matchedEvents.length}`, "muted"],
      [`context ${contextEvents.length}`, contextEvents.length ? "warn" : "muted"],
    ]),
    eventList("Matched events", matchedEvents),
    eventList("Context events", contextEvents),
  );
  return article;
}

function eventList(title, events) {
  const fragment = document.createDocumentFragment();
  fragment.append(heading(title));
  const list = document.createElement("ul");
  list.className = "event-list";
  for (const event of events) {
    const item = document.createElement("li");
    item.innerHTML = `${escapeHtml(event.title ?? event.event_id)} <small>${escapeHtml(event.event_id ?? "")}</small>`;
    list.append(item);
  }
  if (!events.length) {
    const item = document.createElement("li");
    item.innerHTML = "<small>none</small>";
    list.append(item);
  }
  fragment.append(list);
  return fragment;
}

function searchPayload() {
  const indexFile = searchForm.indexFile.value.trim();
  return {
    date_utc: searchForm.dateUtc.value.trim(),
    profile_id: "global_slow_v1",
    lookback_years: Number(searchForm.lookbackYears.value),
    lookahead_years: Number(searchForm.lookaheadYears.value),
    step_days: 7,
    top_k: 30,
    max_episodes: Number(searchForm.maxEpisodes.value),
    events_per_episode: 6,
    event_window_years: 1,
    provider: searchForm.provider.value,
    ...(indexFile ? { index_file: indexFile } : {}),
  };
}

function comparePayload() {
  const request = searchPayload();
  return {
    left_date_utc: request.date_utc,
    right_date_utc: searchForm.compareDateUtc.value.trim(),
    profile_id: request.profile_id,
    lookback_years: request.lookback_years,
    lookahead_years: request.lookahead_years,
    step_days: request.step_days,
    top_k: request.top_k,
    max_episodes: request.max_episodes,
    events_per_episode: request.events_per_episode,
    event_window_years: request.event_window_years,
    provider: request.provider,
    ...(request.index_file ? { index_file: request.index_file } : {}),
  };
}

function badge(text, kind = "muted") {
  const span = document.createElement("span");
  span.className = `badge ${kind}`;
  span.textContent = text;
  return span;
}

function metricRow(items) {
  const row = document.createElement("div");
  row.className = "metric-row";
  for (const [text, kind] of items) {
    row.append(badge(text, kind));
  }
  return row;
}

function heading(text) {
  const title = document.createElement("h3");
  title.textContent = text;
  return title;
}

function paragraph(text) {
  const p = document.createElement("p");
  p.className = "summary-text";
  p.textContent = text;
  return p;
}

function formatNumber(value) {
  if (typeof value !== "number") {
    return "n/a";
  }
  return value.toFixed(3);
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (char) => {
    const escapes = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
    return escapes[char];
  });
}

document.querySelectorAll("[data-action]").forEach((button) => {
  button.addEventListener("click", async () => {
    const action = button.dataset.action;
    setState("loading");
    try {
      const result = await endpointActions[action]();
      setState(String(result.status), result.ok ? "ok" : "error");
      if (!result.ok) {
        showError(result);
        return;
      }
      summaryPanel.innerHTML = "";
      episodesPanel.replaceChildren();
      showJson(result.payload);
      if (action === "status") {
        renderRuntimeStatus(result.payload);
      } else if (action === "today") {
        renderToday(result.payload);
      } else if (action === "comparePresets") {
        renderComparePresets(result.payload);
      } else {
        summaryPanel.innerHTML = "";
        episodesPanel.replaceChildren();
        showJson(result.payload);
      }
    } catch (error) {
      setState("network", "error");
      showError({ status: "network", payload: { detail: error.message } });
    }
  });
});

searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setState("searching");
  try {
    const result = await apiRequest("/resonance/search", {
      method: "POST",
      body: searchPayload(),
    });
    setState(String(result.status), result.ok ? "ok" : "error");
    if (!result.ok) {
      showError(result);
      return;
    }
    renderSearch(result.payload);
  } catch (error) {
    setState("network", "error");
    showError({ status: "network", payload: { detail: error.message } });
  }
});

compareButton.addEventListener("click", async () => {
  setState("comparing");
  try {
    const result = await apiRequest("/resonance/compare", {
      method: "POST",
      body: comparePayload(),
    });
    setState(String(result.status), result.ok ? "ok" : "error");
    if (!result.ok) {
      showError(result);
      return;
    }
    renderCompare(result.payload);
  } catch (error) {
    setState("network", "error");
    showError({ status: "network", payload: { detail: error.message } });
  }
});
