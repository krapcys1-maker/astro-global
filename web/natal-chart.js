const PLANET_GLYPHS = {
  Sun: "☉",
  Moon: "☽",
  Mercury: "☿",
  Venus: "♀",
  Mars: "♂",
  Jupiter: "♃",
  Saturn: "♄",
  Uranus: "♅",
  Neptune: "♆",
  Pluto: "♇",
};

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

const SIGN_ORDER = [
  "Aries",
  "Taurus",
  "Gemini",
  "Cancer",
  "Leo",
  "Virgo",
  "Libra",
  "Scorpio",
  "Sagittarius",
  "Capricorn",
  "Aquarius",
  "Pisces",
];

export function normalizeAngle(value) {
  const normalized = value % 360;
  return normalized < 0 ? normalized + 360 : normalized;
}

export function longitudeToWheelAngle(longitudeDeg) {
  return normalizeAngle(longitudeDeg - 90);
}

export function polarPoint(center, radius, angleDeg) {
  const angleRad = (angleDeg * Math.PI) / 180;
  return {
    x: center + Math.cos(angleRad) * radius,
    y: center + Math.sin(angleRad) * radius,
  };
}

export function aspectLineForPlanets(planetsByBody, aspect, center, radius) {
  const left = planetsByBody.get(aspect.body_a);
  const right = planetsByBody.get(aspect.body_b);
  if (!left || !right) {
    return null;
  }
  const start = polarPoint(center, radius, longitudeToWheelAngle(left.longitude_deg));
  const end = polarPoint(center, radius, longitudeToWheelAngle(right.longitude_deg));
  return { start, end };
}

export function axisPairsAreOpposite(axes) {
  const byName = new Map(axes.map((axis) => [axis.name, axis.longitude_deg]));
  return (
    isOpposite(byName.get("ASC"), byName.get("DSC")) &&
    isOpposite(byName.get("MC"), byName.get("IC"))
  );
}

export function isOpposite(left, right) {
  if (typeof left !== "number" || typeof right !== "number") {
    return false;
  }
  const distance = Math.abs(normalizeAngle(left - right));
  return Math.abs(distance - 180) < 0.001 || Math.abs(distance - 180) > 359.999;
}

export function renderNatalChartWheel(chart) {
  const size = 720;
  const center = size / 2;
  const radii = {
    outer: 330,
    zodiac: 302,
    tickOuter: 318,
    tickInner: 309,
    houses: 258,
    planets: 226,
    aspects: 174,
    core: 14,
  };
  const planetsByBody = new Map((chart.planets || []).map((planet) => [planet.body, planet]));
  return `
    <svg class="natal-wheel" viewBox="0 0 ${size} ${size}" role="img" aria-label="Natal chart wheel">
      <defs>
        <radialGradient id="natalWheelGlow" cx="50%" cy="50%" r="52%">
          <stop offset="0%" stop-color="rgba(218, 171, 103, 0.20)" />
          <stop offset="38%" stop-color="rgba(45, 169, 189, 0.09)" />
          <stop offset="100%" stop-color="rgba(4, 12, 20, 0)" />
        </radialGradient>
      </defs>
      <circle class="natal-wheel-atmosphere" cx="${center}" cy="${center}" r="${radii.outer}" />
      <circle class="natal-wheel-glow" cx="${center}" cy="${center}" r="${radii.outer}" fill="url(#natalWheelGlow)" />
      ${renderZodiacLayer(center, radii)}
      ${renderHouseLayer(chart.houses || [], center, radii)}
      ${renderAspectLayer(chart.aspects || [], planetsByBody, center, radii)}
      ${renderAxisLayer(chart.axes || [], center, radii)}
      ${renderPlanetLayer(chart.planets || [], center, radii)}
      <circle class="natal-wheel-core" cx="${center}" cy="${center}" r="${radii.core}" />
    </svg>
  `;
}

function renderZodiacLayer(center, radii) {
  const rings = [radii.outer, radii.zodiac, radii.houses, radii.aspects];
  const ringMarkup = rings.map((radius) => (
    `<circle class="natal-ring" cx="${center}" cy="${center}" r="${radius}" />`
  )).join("");
  const divisions = Array.from({ length: 12 }, (_, index) => {
    const angle = longitudeToWheelAngle(index * 30);
    const outer = polarPoint(center, radii.outer, angle);
    const inner = polarPoint(center, radii.houses, angle);
    const label = polarPoint(center, radii.zodiac + 2, longitudeToWheelAngle(index * 30 + 15));
    const sign = SIGN_ORDER[index];
    return `
      <line class="natal-sign-division" x1="${inner.x}" y1="${inner.y}" x2="${outer.x}" y2="${outer.y}" />
      <text class="natal-zodiac-glyph" x="${label.x}" y="${label.y}">${ZODIAC_GLYPHS[sign]}</text>
    `;
  }).join("");
  const ticks = Array.from({ length: 72 }, (_, index) => {
    const angle = longitudeToWheelAngle(index * 5);
    const outer = polarPoint(center, radii.tickOuter, angle);
    const inner = polarPoint(center, index % 6 === 0 ? radii.tickInner - 7 : radii.tickInner, angle);
    return `<line class="natal-degree-tick" x1="${inner.x}" y1="${inner.y}" x2="${outer.x}" y2="${outer.y}" />`;
  }).join("");
  return `<g class="natal-zodiac-layer">${ringMarkup}${ticks}${divisions}</g>`;
}

function renderHouseLayer(houses, center, radii) {
  if (!houses.length) {
    return "";
  }
  return `
    <g class="natal-house-layer">
      ${houses.map((house) => {
        const angle = longitudeToWheelAngle(house.longitude_deg);
        const outer = polarPoint(center, radii.houses, angle);
        const inner = polarPoint(center, radii.aspects - 18, angle);
        const label = polarPoint(center, radii.houses - 18, angle + 4);
        return `
          <line class="natal-house-cusp" x1="${inner.x}" y1="${inner.y}" x2="${outer.x}" y2="${outer.y}" />
          <text class="natal-house-number" x="${label.x}" y="${label.y}">${house.number}</text>
        `;
      }).join("")}
    </g>
  `;
}

function renderAspectLayer(aspects, planetsByBody, center, radii) {
  return `
    <g class="natal-aspect-layer">
      ${aspects.map((aspect) => {
        const line = aspectLineForPlanets(planetsByBody, aspect, center, radii.aspects);
        if (!line) {
          return "";
        }
        return `
          <line
            class="natal-aspect-line aspect-${aspect.aspect}"
            data-body-a="${aspect.body_a}"
            data-body-b="${aspect.body_b}"
            x1="${line.start.x}"
            y1="${line.start.y}"
            x2="${line.end.x}"
            y2="${line.end.y}"
          >
            <title>${aspect.body_a} ${aspect.aspect} ${aspect.body_b}, orb ${formatNumber(aspect.orb_deg)}°</title>
          </line>
        `;
      }).join("")}
    </g>
  `;
}

function renderAxisLayer(axes, center, radii) {
  if (!axes.length) {
    return "";
  }
  return `
    <g class="natal-axis-layer">
      ${axes.map((axis) => {
        const angle = longitudeToWheelAngle(axis.longitude_deg);
        const outer = polarPoint(center, radii.outer - 8, angle);
        const inner = polarPoint(center, radii.aspects - 42, angle);
        const label = polarPoint(center, radii.outer - 34, angle);
        return `
          <line class="natal-axis-line axis-${axis.name.toLowerCase()}" x1="${inner.x}" y1="${inner.y}" x2="${outer.x}" y2="${outer.y}" />
          <text class="natal-axis-label" x="${label.x}" y="${label.y}">${axis.name}</text>
        `;
      }).join("")}
    </g>
  `;
}

function renderPlanetLayer(planets, center, radii) {
  const placed = distributePlanetLabels(planets);
  return `
    <g class="natal-planet-layer">
      ${placed.map((planet) => {
        const angle = longitudeToWheelAngle(planet.longitude_deg);
        const point = polarPoint(center, planet.radius, angle);
        const labelPoint = polarPoint(center, planet.radius + 27, angle);
        return `
          <g class="natal-planet" data-body="${planet.body}" transform="translate(${point.x} ${point.y})">
            <circle class="natal-planet-dot" r="16" />
            <text class="natal-planet-glyph" y="6">${PLANET_GLYPHS[planet.body] || planet.body.slice(0, 1)}</text>
            <title>${planet.body}: ${formatDegree(planet.degree_in_sign)} ${planet.sign}${planet.house ? `, house ${planet.house}` : ""}${planet.retrograde ? " Rx" : ""}</title>
          </g>
          <text class="natal-planet-degree" x="${labelPoint.x}" y="${labelPoint.y}">${formatDegree(planet.degree_in_sign)}</text>
        `;
      }).join("")}
    </g>
  `;
}

function distributePlanetLabels(planets) {
  const sorted = [...planets].sort((left, right) => left.longitude_deg - right.longitude_deg);
  return sorted.map((planet, index) => {
    const previous = sorted[index - 1];
    const isClose = previous && Math.abs(planet.longitude_deg - previous.longitude_deg) < 7;
    return {
      ...planet,
      radius: 226 + (isClose ? 28 : index % 2 === 0 ? 0 : 12),
    };
  });
}

function formatDegree(value) {
  return `${Math.floor(value)}°${String(Math.round((value % 1) * 60)).padStart(2, "0")}`;
}

function formatNumber(value) {
  return Number(value || 0).toFixed(1);
}

export function attachNatalWheelInteractions(container) {
  if (!container) {
    return;
  }
  container.addEventListener("mouseover", (event) => {
    const planet = event.target.closest?.(".natal-planet");
    const aspect = event.target.closest?.(".natal-aspect-line");
    clearHighlights(container);
    if (planet) {
      const body = planet.dataset.body;
      planet.classList.add("is-highlighted");
      for (const line of container.querySelectorAll(".natal-aspect-line")) {
        if (line.dataset.bodyA === body || line.dataset.bodyB === body) {
          line.classList.add("is-highlighted");
        }
      }
    } else if (aspect) {
      aspect.classList.add("is-highlighted");
      highlightPlanet(container, aspect.dataset.bodyA);
      highlightPlanet(container, aspect.dataset.bodyB);
    }
  });
  container.addEventListener("mouseleave", () => clearHighlights(container));
}

function highlightPlanet(container, body) {
  const planet = container.querySelector(`.natal-planet[data-body="${body}"]`);
  planet?.classList.add("is-highlighted");
}

function clearHighlights(container) {
  for (const item of container.querySelectorAll(".is-highlighted")) {
    item.classList.remove("is-highlighted");
  }
}
