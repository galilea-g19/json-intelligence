/* ─────────────────────────────────────────────
   JSON Intelligence — demo UI (Issues #14 / #15)
   Plain JS, no build step. Served by FastAPI at /ui
   ───────────────────────────────────────────── */
(function () {
  "use strict";

  /* The UI is served by the API itself, so relative URLs are same-origin.
     Opening index.html straight from disk falls back to the dev server. */
  const API_BASE =
    location.protocol === "file:" ? "http://127.0.0.1:8000" : "";

  const ENDPOINTS = {
    analyze: "/api/v1/json/analyze",
    schema: "/api/v1/json/schema",
    explain: "/api/v1/json/explain",
  };

  /* Mirrors settings.max_body_bytes (Issue #13) so the UI fails fast. */
  const MAX_BODY_BYTES = 1024 * 1024;

  const SAMPLE = {
    user: {
      name: "Galilea",
      age: 30,
      active: true,
      address: { city: "Guadalajara", zip: 44100 },
    },
    skills: ["Python", "FastAPI", "PostgreSQL"],
    projects: [{ name: "json-intelligence", stars: 0, public: true }],
    last_login: null,
  };

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  const input = $("#json-input");
  const statusBadge = $("#status-badge");
  const inputMeta = $("#input-meta");
  const copyBtn = $("#btn-copy");
  const apiStatus = $("#api-status");
  const apiStatusText = $("#api-status-text");

  /* Raw text of the last successful result per tab, used by "Copy". */
  const lastResult = { analyze: "", schema: "", explain: "" };
  let activeTab = "analyze";

  /* ── helpers ───────────────────────────────── */

  const escapeHtml = (str) =>
    String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  const byteLength = (str) => new TextEncoder().encode(str).length;

  const panelOf = (tab) => document.querySelector(`[data-panel="${tab}"]`);

  /** Pretty-print JSON with lightweight syntax colouring (Issue #16). */
  function highlight(value) {
    const json = JSON.stringify(value, null, 2);
    return escapeHtml(json).replace(
      /("(?:\\.|[^"\\])*"\s*:)|("(?:\\.|[^"\\])*")|\b(true|false)\b|\b(null)\b|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g,
      (match, key, str, bool, nul, num) => {
        if (key) return `<span class="tok-key">${key}</span>`;
        if (str) return `<span class="tok-str">${str}</span>`;
        if (bool) return `<span class="tok-bool">${bool}</span>`;
        if (nul) return `<span class="tok-null">${nul}</span>`;
        return `<span class="tok-num">${num}</span>`;
      },
    );
  }

  const codeBlock = (value) => `<pre class="code">${highlight(value)}</pre>`;

  function setPanel(tab, html) {
    panelOf(tab).innerHTML = html;
  }

  function showLoading(tab, label) {
    setPanel(
      tab,
      `<div class="state"><div class="spinner"></div><p class="state-title">${label}</p></div>`,
    );
  }

  function showError(tab, title, detail, items) {
    const list = items && items.length
      ? `<ul class="error-list">${items.map((i) => `<li>${escapeHtml(i)}</li>`).join("")}</ul>`
      : "";
    setPanel(
      tab,
      `<div class="state state-error">
         <div class="error-box">
           <p class="error-title">${escapeHtml(title)}</p>
           <p class="error-detail">${escapeHtml(detail)}</p>
           ${list}
         </div>
       </div>`,
    );
    lastResult[tab] = "";
  }

  /* ── input handling ────────────────────────── */

  /** Parse the textarea and keep the badge/meta in sync. */
  function readInput() {
    const raw = input.value.trim();
    const bytes = byteLength(raw);

    inputMeta.textContent = `${bytes.toLocaleString()} bytes`;
    inputMeta.classList.toggle("is-warn", bytes > MAX_BODY_BYTES);

    if (!raw) {
      statusBadge.textContent = "Empty";
      statusBadge.className = "badge";
      return { ok: false, error: "Paste or type a JSON object first." };
    }

    let parsed;
    try {
      parsed = JSON.parse(raw);
    } catch (err) {
      statusBadge.textContent = "Invalid JSON";
      statusBadge.className = "badge is-err";
      statusBadge.title = err.message;
      return { ok: false, error: `Invalid JSON — ${err.message}` };
    }

    statusBadge.title = "";

    /* The API contract (JsonInput.data) expects a top-level object. */
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
      statusBadge.textContent = "Not an object";
      statusBadge.className = "badge is-err";
      return {
        ok: false,
        error: "The API expects a top-level JSON object, e.g. { \"key\": ... }",
      };
    }

    if (bytes > MAX_BODY_BYTES) {
      statusBadge.textContent = "Too large";
      statusBadge.className = "badge is-err";
      return {
        ok: false,
        error: `Body is ${bytes.toLocaleString()} bytes; the API rejects anything over ${MAX_BODY_BYTES.toLocaleString()} bytes (413).`,
      };
    }

    statusBadge.textContent = "Valid JSON";
    statusBadge.className = "badge is-ok";
    return { ok: true, data: parsed };
  }

  /* ── API calls (Issue #15) ─────────────────── */

  /** POST { data } and normalise the API error envelope into a throw. */
  async function callApi(tab, data) {
    let response;
    try {
      response = await fetch(API_BASE + ENDPOINTS[tab], {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data }),
      });
    } catch (err) {
      const error = new Error(
        "Could not reach the API. Is uvicorn running on this host?",
      );
      error.title = "Network error";
      throw error;
    }

    let payload = null;
    try {
      payload = await response.json();
    } catch {
      /* empty or non-JSON body */
    }

    if (!response.ok) {
      const error = new Error(
        (payload && (payload.error || payload.detail || payload.message)) ||
          response.statusText ||
          "Request failed",
      );
      error.title = `HTTP ${response.status}`;
      /* 422 from RequestValidationError carries a details array */
      if (payload && Array.isArray(payload.details)) {
        error.items = payload.details.map((d) => {
          const loc = Array.isArray(d.loc) ? d.loc.join(" → ") : "body";
          return `${loc}: ${d.msg}`;
        });
      }
      throw error;
    }

    return payload;
  }

  /* ── renderers ─────────────────────────────── */

  function renderAnalyze(res) {
    const types = res.types || {};
    const entries = Object.entries(types);
    const distinct = [...new Set(entries.map(([, t]) => t))];

    const rows = entries
      .map(
        ([key, type]) =>
          `<tr><td>${escapeHtml(key)}</td><td>${escapeHtml(type)}</td></tr>`,
      )
      .join("");

    setPanel(
      "analyze",
      `<div class="result-grid">
         <div class="result-item">
           <div class="result-label">Keys (recursive)</div>
           <div class="result-value">${res.key_count}</div>
         </div>
         <div class="result-item">
           <div class="result-label">Distinct types</div>
           <div class="result-value">${distinct.length}</div>
         </div>
         <div class="result-item">
           <div class="result-label">Top-level keys</div>
           <div class="result-value">${Object.keys(res.nested_structure || {}).length}</div>
         </div>
       </div>
       <div class="block">
         <p class="block-title">Detected types</p>
         <table class="types-table"><tbody>${rows}</tbody></table>
       </div>
       <div class="block">
         <p class="block-title">Nested structure</p>
         ${codeBlock(res.nested_structure)}
       </div>`,
    );
    lastResult.analyze = JSON.stringify(res, null, 2);
  }

  function renderSchema(res) {
    const schema = res.schema;
    setPanel("schema", codeBlock(schema));
    lastResult.schema = JSON.stringify(schema, null, 2);
  }

  function renderExplain(res) {
    const e = (res && res.explanation) || {};
    const pills = (values, neutral) =>
      (values || []).length
        ? `<div class="pill-row">${values
            .map(
              (v) =>
                `<span class="pill${neutral ? " is-neutral" : ""}">${escapeHtml(v)}</span>`,
            )
            .join("")}</div>`
        : `<p class="state-hint">—</p>`;

    setPanel(
      "explain",
      `<p class="summary-text">${escapeHtml(e.summary || "")}</p>
       <div class="result-grid block">
         <div class="result-item">
           <div class="result-label">Nesting levels</div>
           <div class="result-value">${e.nesting_levels ?? "—"}</div>
         </div>
       </div>
       <div class="block">
         <p class="block-title">Data types</p>
         ${pills(e.data_types, true)}
       </div>
       <div class="block">
         <p class="block-title">Important fields</p>
         ${pills(e.important_fields, false)}
       </div>`,
    );
    lastResult.explain = JSON.stringify(e, null, 2);
  }

  const RENDERERS = {
    analyze: renderAnalyze,
    schema: renderSchema,
    explain: renderExplain,
  };

  const LOADING_LABEL = {
    analyze: "Analyzing structure…",
    schema: "Generating schema…",
    explain: "Asking the AI…",
  };

  /* ── run ───────────────────────────────────── */

  async function run(tab) {
    switchTab(tab);

    const parsed = readInput();
    if (!parsed.ok) {
      showError(tab, "Invalid input", parsed.error);
      return;
    }

    const button = document.querySelector(`[data-run="${tab}"]`);
    button.classList.add("is-loading");
    $$("[data-run]").forEach((b) => (b.disabled = true));
    showLoading(tab, LOADING_LABEL[tab]);

    try {
      const payload = await callApi(tab, parsed.data);
      RENDERERS[tab](payload);
    } catch (err) {
      showError(tab, err.title || "Request failed", err.message, err.items);
    } finally {
      button.classList.remove("is-loading");
      $$("[data-run]").forEach((b) => (b.disabled = false));
    }
  }

  /* ── tabs ──────────────────────────────────── */

  function switchTab(tab) {
    activeTab = tab;
    $$(".tab").forEach((t) => {
      const on = t.dataset.tab === tab;
      t.classList.toggle("is-active", on);
      t.setAttribute("aria-selected", String(on));
    });
    $$(".tab-content").forEach((c) =>
      c.classList.toggle("is-hidden", c.dataset.panel !== tab),
    );
  }

  /* ── health check ──────────────────────────── */

  async function checkApi() {
    try {
      const res = await fetch(API_BASE + "/", { method: "GET" });
      if (!res.ok) throw new Error();
      apiStatus.dataset.state = "online";
      apiStatusText.textContent = "API online";
    } catch {
      apiStatus.dataset.state = "offline";
      apiStatusText.textContent = "API offline";
    }
  }

  /* ── wiring ────────────────────────────────── */

  $$(".tab").forEach((tab) =>
    tab.addEventListener("click", () => switchTab(tab.dataset.tab)),
  );
  $$("[data-run]").forEach((btn) =>
    btn.addEventListener("click", () => run(btn.dataset.run)),
  );

  input.addEventListener("input", readInput);

  $("#btn-sample").addEventListener("click", () => {
    input.value = JSON.stringify(SAMPLE, null, 2);
    readInput();
    input.focus();
  });

  $("#btn-format").addEventListener("click", () => {
    const parsed = readInput();
    if (!parsed.ok) return;
    input.value = JSON.stringify(parsed.data, null, 2);
    readInput();
  });

  $("#btn-clear").addEventListener("click", () => {
    input.value = "";
    readInput();
    input.focus();
  });

  copyBtn.addEventListener("click", async () => {
    const text = lastResult[activeTab];
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      copyBtn.textContent = "Copied";
      copyBtn.classList.add("is-done");
      setTimeout(() => {
        copyBtn.textContent = "Copy";
        copyBtn.classList.remove("is-done");
      }, 1200);
    } catch {
      copyBtn.textContent = "Failed";
      setTimeout(() => (copyBtn.textContent = "Copy"), 1200);
    }
  });

  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      run(activeTab);
    }
  });

  /* initial state */
  input.value = JSON.stringify(SAMPLE, null, 2);
  readInput();
  checkApi();
})();
