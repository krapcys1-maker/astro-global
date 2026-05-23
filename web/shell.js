const form = document.querySelector("#connectionForm");
const searchForm = document.querySelector("#searchForm");
const runtimeBadges = document.querySelector("#runtimeBadges");
const requestState = document.querySelector("#requestState");
const summaryPanel = document.querySelector("#summaryPanel");
const episodesPanel = document.querySelector("#episodesPanel");
const jsonPanel = document.querySelector("#jsonPanel");

const endpointActions = {
  health: () => apiRequest("/health", { auth: false }),
  readiness: () => apiRequest("/readiness"),
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
