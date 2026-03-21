const state = {
  sessionId: null,
  session: null,
  pollTimer: null,
};

const SITE_PRESETS = [
  { label: "Amazon", url: "https://www.amazon.com/", category: "general", group: "popular" },
  { label: "Best Buy", url: "https://www.bestbuy.com/", category: "electronics", group: "popular" },
  { label: "Target", url: "https://www.target.com/", category: "general", group: "popular" },
  { label: "Walmart", url: "https://www.walmart.com/", category: "general", group: "popular" },
  { label: "B&H Photo", url: "https://www.bhphotovideo.com/", category: "electronics", group: "popular" },
  { label: "Newegg", url: "https://www.newegg.com/", category: "electronics", group: "popular" },
  { label: "Apple", url: "https://www.apple.com/", category: "electronics", group: "electronics" },
  { label: "Samsung", url: "https://www.samsung.com/us/", category: "electronics", group: "electronics" },
  { label: "Dell", url: "https://www.dell.com/", category: "electronics", group: "electronics" },
  { label: "HP", url: "https://www.hp.com/us-en/home.html", category: "electronics", group: "electronics" },
  { label: "Lenovo", url: "https://www.lenovo.com/us/en/", category: "electronics", group: "electronics" },
  { label: "Micro Center", url: "https://www.microcenter.com/", category: "electronics", group: "electronics" },
  { label: "Adorama", url: "https://www.adorama.com/", category: "electronics", group: "electronics" },
  { label: "eBay", url: "https://www.ebay.com/", category: "general", group: "general" },
  { label: "Costco", url: "https://www.costco.com/", category: "general", group: "general" },
  { label: "Staples", url: "https://www.staples.com/", category: "office", group: "general" },
  { label: "Office Depot", url: "https://www.officedepot.com/", category: "office", group: "general" },
  { label: "Home Depot", url: "https://www.homedepot.com/", category: "home", group: "general" },
  { label: "Lowe's", url: "https://www.lowes.com/", category: "home", group: "general" },
  { label: "Macy's", url: "https://www.macys.com/", category: "fashion", group: "general" },
  { label: "Nordstrom", url: "https://www.nordstrom.com/", category: "fashion", group: "general" },
  { label: "REI", url: "https://www.rei.com/", category: "outdoor", group: "general" },
  { label: "Sephora", url: "https://www.sephora.com/", category: "beauty", group: "general" },
  { label: "Ulta", url: "https://www.ulta.com/", category: "beauty", group: "general" },
  { label: "CVS", url: "https://www.cvs.com/", category: "health", group: "general" },
  { label: "Walgreens", url: "https://www.walgreens.com/", category: "health", group: "general" },
];

const form = document.getElementById("run-form");
const fillDemoButton = document.getElementById("fill-demo");
const exportButton = document.getElementById("export-button");
const formMessage = document.getElementById("form-message");
const emptyState = document.getElementById("empty-state");
const resultsGrid = document.getElementById("results-grid");
const summaryStrip = document.getElementById("summary-strip");
const submitButton = document.getElementById("submit-button");
const cardTemplate = document.getElementById("result-card-template");
const leadCard = document.getElementById("lead-card");
const leadTitle = document.getElementById("lead-title");
const leadCopy = document.getElementById("lead-copy");
const leadPrice = document.getElementById("lead-price");
const sitePresets = document.getElementById("site-presets");
const presetCount = document.getElementById("preset-count");
const selectPopularButton = document.getElementById("select-popular");
const selectElectronicsButton = document.getElementById("select-electronics");
const clearSitesButton = document.getElementById("clear-sites");

renderSitePresets();
updatePresetCount();

fillDemoButton.addEventListener("click", () => {
  document.getElementById("product-query").value = "Sony WH-1000XM5";
  setSelectedSites([
    "https://www.bestbuy.com/",
    "https://www.target.com/",
    "https://www.bhphotovideo.com/",
  ]);
  document.getElementById("vendor-urls").value = "";
  document.getElementById("notes").value = "Prefer in-stock listings and mention shipping timing if visible.";
  document.getElementById("browser-profile").value = "lite";
  document.getElementById("country-code").value = "";
});

selectPopularButton.addEventListener("click", () => {
  setSelectedSites(SITE_PRESETS.filter((site) => site.group === "popular").map((site) => site.url));
});

selectElectronicsButton.addEventListener("click", () => {
  setSelectedSites(SITE_PRESETS.filter((site) => site.category === "electronics").map((site) => site.url));
});

clearSitesButton.addEventListener("click", () => {
  setSelectedSites([]);
  document.getElementById("vendor-urls").value = "";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage("Starting TinyFish runs...", "info");
  submitButton.disabled = true;
  exportButton.disabled = true;
  clearPoller();

  try {
    const mergedVendorUrls = buildVendorUrlPayload();
    if (!mergedVendorUrls) {
      throw new Error("Pick at least one site preset or add a custom vendor URL.");
    }

    const payload = {
      product_query: document.getElementById("product-query").value,
      vendor_urls: mergedVendorUrls,
      browser_profile: document.getElementById("browser-profile").value,
      country_code: document.getElementById("country-code").value,
      notes: document.getElementById("notes").value,
    };

    const response = await fetch("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Could not start run.");
    }

    state.sessionId = data.session_id;
    state.session = data.session;
    renderSession();
    startPoller();
    setMessage("Runs started. Polling for live results...", "success");
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    submitButton.disabled = false;
  }
});

exportButton.addEventListener("click", () => {
  if (!state.session) {
    return;
  }

  const rows = [
    [
      "vendor",
      "site_url",
      "status",
      "matched_product_name",
      "matched_url",
      "price",
      "currency",
      "availability",
      "shipping_notes",
      "return_policy_notes",
      "confidence",
      "notes",
    ],
  ];

  state.session.runs.forEach((run) => {
    const result = run.result || {};
    rows.push([
      run.vendor_name || "",
      run.site_url || "",
      run.status || "",
      result.matched_product_name || "",
      result.matched_url || "",
      result.price || "",
      result.currency || "",
      result.availability || "",
      result.shipping_notes || "",
      result.return_policy_notes || "",
      result.confidence || "",
      result.notes || "",
    ]);
  });

  const csv = rows
    .map((row) =>
      row
        .map((value) => `"${String(value).replaceAll('"', '""')}"`)
        .join(",")
    )
    .join("\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `vendorscout-${Date.now()}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
});

async function pollSession() {
  if (!state.sessionId) {
    return;
  }

  try {
    const response = await fetch(`/api/runs/${state.sessionId}`);
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Could not refresh session.");
    }

    state.session = data.session;
    renderSession();

    if (state.session.all_finished) {
      clearPoller();
      exportButton.disabled = false;
      setMessage("All runs finished. Review the comparison and export the results.", "success");
    }
  } catch (error) {
    clearPoller();
    setMessage(error.message, "error");
  }
}

function startPoller() {
  clearPoller();
  state.pollTimer = setInterval(pollSession, 4000);
  void pollSession();
}

function clearPoller() {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
}

function renderSession() {
  if (!state.session) {
    emptyState.classList.remove("hidden");
    summaryStrip.classList.add("hidden");
    leadCard.classList.add("hidden");
    resultsGrid.innerHTML = "";
    exportButton.disabled = true;
    return;
  }

  emptyState.classList.add("hidden");
  resultsGrid.innerHTML = "";

  const summary = state.session.summary || {};
  summaryStrip.classList.remove("hidden");
  summaryStrip.innerHTML = `
    <div class="summary-card">
      <span class="summary-label">Product</span>
      <strong>${escapeHtml(state.session.product_query)}</strong>
    </div>
    <div class="summary-card">
      <span class="summary-label">Completed</span>
      <strong>${summary.completed_runs || 0} / ${summary.total_runs || 0}</strong>
    </div>
    <div class="summary-card">
      <span class="summary-label">Best live price</span>
      <strong>${summary.lowest_price_value ? formatPrice(summary.lowest_price_value) : "Pending"}</strong>
    </div>
    <div class="summary-card">
      <span class="summary-label">Cheapest vendor</span>
      <strong>${summary.cheapest_vendor || "Pending"}</strong>
    </div>
  `;

  renderLeadCard();

  state.session.runs.forEach((run) => {
    const card = cardTemplate.content.firstElementChild.cloneNode(true);
    const result = run.result || {};

    card.querySelector(".vendor-name").textContent = run.vendor_name;

    const siteLink = card.querySelector(".site-link");
    siteLink.href = run.site_url;
    siteLink.textContent = run.site_url;

    const statusBadge = card.querySelector(".status-badge");
    statusBadge.textContent = run.status;
    statusBadge.classList.add(`status-${(run.status || "pending").toLowerCase()}`);

    card.querySelector(".price-value").textContent = result.price || "Pending";
    card.querySelector(".availability").textContent = result.availability || run.error?.message || "";
    card.querySelector(".match-name").textContent = result.matched_product_name || "Waiting for a structured match...";
    card.querySelector(".notes").textContent = result.notes || "The agent is still collecting a reliable buying signal.";
    card.querySelector(".confidence").textContent = result.confidence || "n/a";
    card.querySelector(".shipping").textContent = result.shipping_notes || "n/a";
    card.querySelector(".currency").textContent = result.currency || "n/a";
    card.querySelector(".returns").textContent = result.return_policy_notes || "n/a";

    const matchedLink = card.querySelector(".matched-link");
    if (result.matched_url) {
      matchedLink.href = result.matched_url;
      matchedLink.classList.remove("hidden");
    }

    resultsGrid.appendChild(card);
  });
}

function renderLeadCard() {
  const completedRuns = state.session.runs.filter((run) => run.status === "COMPLETED" && run.result);

  if (!completedRuns.length) {
    leadCard.classList.remove("hidden");
    leadTitle.textContent = "Waiting for the first completed result";
    leadCopy.textContent = "As runs complete, the strongest result will show up here first.";
    leadPrice.textContent = "Pending";
    return;
  }

  const scoredRuns = completedRuns
    .map((run) => ({
      run,
      priceValue: parsePrice(run.result?.price),
    }))
    .sort((a, b) => {
      if (a.priceValue == null && b.priceValue == null) {
        return 0;
      }
      if (a.priceValue == null) {
        return 1;
      }
      if (b.priceValue == null) {
        return -1;
      }
      return a.priceValue - b.priceValue;
    });

  const best = scoredRuns[0].run;
  leadCard.classList.remove("hidden");
  leadTitle.textContent = `${best.vendor_name} is leading right now`;
  leadCopy.textContent = best.result?.matched_product_name || best.result?.notes || "A live result has been found.";
  leadPrice.textContent = best.result?.price || "Pending";
}

function setMessage(message, tone) {
  formMessage.textContent = message;
  formMessage.dataset.tone = tone;
}

function renderSitePresets() {
  sitePresets.innerHTML = "";

  SITE_PRESETS.forEach((site, index) => {
    const id = `site-${index}`;
    const item = document.createElement("label");
    item.className = "site-preset";
    item.innerHTML = `
      <input type="checkbox" class="site-checkbox" value="${escapeAttribute(site.url)}" data-category="${escapeAttribute(site.category)}">
      <span class="site-chip">
        <span class="site-chip-name">${escapeHtml(site.label)}</span>
        <span class="site-chip-domain">${escapeHtml(site.url.replace(/^https?:\/\//, "").replace(/\/$/, ""))}</span>
      </span>
    `;
    const checkbox = item.querySelector("input");
    checkbox.id = id;
    checkbox.addEventListener("change", updatePresetCount);
    sitePresets.appendChild(item);
  });
}

function getSelectedPresetUrls() {
  return Array.from(document.querySelectorAll(".site-checkbox:checked")).map((input) => input.value);
}

function setSelectedSites(urls) {
  const wanted = new Set(urls);
  document.querySelectorAll(".site-checkbox").forEach((checkbox) => {
    checkbox.checked = wanted.has(checkbox.value);
  });
  updatePresetCount();
}

function updatePresetCount() {
  const count = getSelectedPresetUrls().length;
  presetCount.textContent = `${count} site${count === 1 ? "" : "s"} selected`;
}

function buildVendorUrlPayload() {
  const selected = getSelectedPresetUrls();
  const custom = document.getElementById("vendor-urls").value
    .split(/\r?\n/)
    .map((value) => value.trim())
    .filter(Boolean);

  const merged = [];
  const seen = new Set();

  [...selected, ...custom].forEach((url) => {
    let normalized = url;
    if (!/^https?:\/\//i.test(normalized)) {
      normalized = `https://${normalized}`;
    }
    if (seen.has(normalized)) {
      return;
    }
    seen.add(normalized);
    merged.push(normalized);
  });

  return merged.join("\n");
}

function parsePrice(value) {
  if (typeof value !== "string") {
    return null;
  }

  const cleaned = value.replace(/[^0-9.,]/g, "").replace(/,/g, "");
  if (!cleaned) {
    return null;
  }

  const parsed = Number.parseFloat(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatPrice(value) {
  if (typeof value !== "number") {
    return String(value);
  }

  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value;
  return div.innerHTML;
}

function escapeAttribute(value) {
  return String(value).replaceAll("&", "&amp;").replaceAll('"', "&quot;");
}
