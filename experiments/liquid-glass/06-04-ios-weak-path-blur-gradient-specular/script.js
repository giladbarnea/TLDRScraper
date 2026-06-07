/* Populates the feed with varied article rows so the glass dock has real,
   structured content to blur and dampen as the page scrolls beneath it. */
(() => {
  "use strict";

  const ARTICLES = [
    { tag: "Research", title: "Trendshift Daily Express", body: "A new architecture for long-context retrieval claims a 40% latency cut on commodity GPUs." },
    { tag: "Newsletter", title: "Simon Willison's Weblog", body: "Notes on running local models, embeddings, and the tooling that finally made it practical." },
    { tag: "Podcast", title: "Latent Space", body: "The hosts walk through the week in open models and what shipped under the radar." },
    { tag: "Release", title: "Vercel Changelog", body: "Edge config gets regional pinning; build cache hit rates improve across the board." },
    { tag: null, title: "Anthropic News", body: "Constitutional classifiers, interpretability progress, and an updated safety framework.", accent: true },
    { tag: "Deep Dive", title: "The Pragmatic Engineer", body: "How a mid-size team rebuilt their incident process after a painful multi-region outage." },
    { tag: "Newsletter", title: "TLDR Web Dev", body: "CSS color-mix() ships everywhere, view transitions stabilize, and a WebGPU primer." },
    { tag: "Research", title: "Import AI", body: "Survey of synthetic data pipelines and the quiet shift toward verifier-driven training." },
    { tag: null, title: "Hacker News Digest", body: "Top threads on local-first software, SQLite at scale, and the return of the personal site." },
    { tag: "Release", title: "React Labs Update", body: "Compiler reaches release candidate; the team details memoization edge cases to watch." },
  ];

  // ---- Live debug knobs -> CSS variables on the surface -----------------
  const surface = document.getElementById("dock");
  const scrim = document.getElementById("scrim");
  const bind = (id, cssVar, fmt, target = surface) => {
    const input = document.getElementById(id);
    const out = document.getElementById(id + "_v");
    const apply = () => {
      const { css, label } = fmt(input.value);
      target.style.setProperty(cssVar, css);
      out.textContent = label;
    };
    input.addEventListener("input", apply);
    apply();
  };
  bind("white", "--lg-white", (v) => ({ css: v + "%", label: v }));
  bind("blur", "--lg-blur", (v) => ({ css: v + "px", label: v }));
  bind("sat", "--lg-saturate", (v) => ({ css: v + "%", label: v }));
  bind("bright", "--lg-brightness", (v) => ({ css: (v / 100).toFixed(2), label: (v / 100).toFixed(2) }));
  bind("dim", "--lg-dim", (v) => ({ css: (v / 100).toFixed(2), label: v }), scrim);
  bind("lit", "--lg-lit", (v) => ({ css: (v / 100).toFixed(2), label: v }));

  // Press feedback driven by pointer events, not CSS :active — iOS withholds
  // :active to disambiguate tap/scroll, which lands the light-up too late (in
  // the context-menu-open window). pointerdown fires on finger contact, so the
  // surface lights up immediately and holds until finger up, like a real menu.
  const dockButtons = Array.from(surface.querySelectorAll(".dock-btn"));
  const previewPress = document.getElementById("preview_press");

  const releasePress = () => {
    if (previewPress.checked) return; // leave the static preview engaged
    surface.classList.remove("is-lit");
    for (const button of dockButtons) button.classList.remove("is-pressed");
  };
  for (const button of dockButtons) {
    button.addEventListener("pointerdown", () => {
      surface.classList.add("is-lit");
      button.classList.add("is-pressed");
    });
  }
  window.addEventListener("pointerup", releasePress);
  window.addEventListener("pointercancel", releasePress);

  // Static preview: light the whole surface (.is-lit) AND give the "Read" button
  // (2nd) its item-highlight pill (.is-pressed), inspectable without a finger.
  const readButton = dockButtons[1];
  previewPress.addEventListener("change", () => {
    surface.classList.toggle("is-lit", previewPress.checked);
    readButton.classList.toggle("is-pressed", previewPress.checked);
  });

  const panel = document.getElementById("panel");
  const toggle = document.getElementById("panel_toggle");
  toggle.addEventListener("click", () => {
    panel.classList.toggle("is-collapsed");
    toggle.textContent = panel.classList.contains("is-collapsed") ? "tune" : "hide";
  });

  const rows = document.getElementById("rows");
  // Repeat the set so there's enough scroll travel under the fixed dock.
  for (let pass = 0; pass < 3; pass++) {
    for (const a of ARTICLES) {
      const card = document.createElement("article");
      card.className = "card" + (a.accent ? " card--accent" : "");
      card.innerHTML =
        (a.tag ? `<span class="card__tag">${a.tag}</span>` : "") +
        `<h2>${a.title}</h2><p>${a.body}</p>`;
      rows.appendChild(card);
    }
  }
})();
