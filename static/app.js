/**
 * YTL Power (6742.KL) Satellite GEOINT — Ground-Truth Sheet
 * Client controller.
 *
 * The page is driven by one idea: a selected observation quarter sets both
 * registers of the sheet — what the satellite measured (the plate, the ledger)
 * and what the company filed (the filing column).
 */

"use strict";

/* =========================================================================
   0. State & helpers
   ========================================================================= */
const $ = (id) => document.getElementById(id);

const QUERY = new URLSearchParams(location.search);

const SITE = {
    bbox: { west: 103.505, south: 1.605, east: 103.545, north: 1.640 },
    centre: { lat: 1.6225, lon: 103.5250 },
    /* The crop is 445 x 387 Sentinel-2 pixels at 10 m, so the frame spans
       ~4.45 km east-west: the scale bar is derived from the rendered width. */
    cropPx: 445,
    pixelM: 10
};

const LAYER_LABELS = {
    split: "Before / after comparison",
    annotated: "AI overlay \u00b7 PV arrays and roof segmentation",
    solar_only: "Solar arrays only",
    roof_only: "Data-hall roofs only",
    yolo_annotated: "YOLOv8 instance segmentation",
    "2026": "Raw pass \u00b7 current",
    "2023": "Raw pass \u00b7 baseline",
    thermal: "Thermal infrared radiometry",
    substation: "TNB 275/500 kV intake substation",
    sar_composite: "Sentinel-1 radar composite",
    difference: "Expansion since the 2023 baseline"
};

const state = {
    layer: "split",
    split: 50,
    dragging: false,
    baseline: { solar: 9800, roof: 20600, stock: 0.77 },
    stock: null,
    epochLoaded: false,
    chart: null
};

const nf = new Intl.NumberFormat("en-US");
const int = (value) => nf.format(Math.round(Number(value) || 0));
const dec = (value, digits) => (Number(value) || 0).toFixed(digits == null ? 1 : digits);
const MINUS = "\u2212";

function setText(id, value) {
    const el = $(id);
    if (el) el.textContent = value;
}

function clamp01(value) {
    return Math.max(0, Math.min(1, value));
}

/* =========================================================================
   1. Appearance
   ========================================================================= */
function initTheme() {
    const buttons = Array.from(document.querySelectorAll(".theme__btn, .theme-btn"));
    const requested = QUERY.get("theme");
    let saved = null;
    try { saved = localStorage.getItem("ytl_theme"); } catch (err) { /* private mode */ }

    const system = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    applyTheme(requested || saved || system, Boolean(requested || saved));

    buttons.forEach((btn) => {
        btn.addEventListener("click", () => applyTheme(btn.dataset.themeVal, true));
    });

    if (window.matchMedia) {
        const query = window.matchMedia("(prefers-color-scheme: dark)");
        if (query.addEventListener) {
            query.addEventListener("change", (event) => {
                let stored = null;
                try { stored = localStorage.getItem("ytl_theme"); } catch (err) { /* ignore */ }
                if (!stored && !QUERY.get("theme")) applyTheme(event.matches ? "dark" : "light", false);
            });
        }
    }
}

function applyTheme(theme, persist) {
    document.documentElement.setAttribute("data-theme", theme);

    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", theme === "dark" ? "#0a0e17" : "#f4f6fa");

    if (persist) {
        try { localStorage.setItem("ytl_theme", theme); } catch (err) { /* ignore */ }
    }

    document.querySelectorAll(".theme__btn, .theme-btn").forEach((btn) => {
        btn.setAttribute("aria-pressed", String(btn.dataset.themeVal === theme));
    });

    if (state.stock && state.chart) renderChart(state.stock);
}

/* =========================================================================
   2. The plate: curtain, coordinate readout, scale bar
   ========================================================================= */
function plateFrame() {
    return $("satelliteViewport");
}

function setSplit(percent) {
    const frame = plateFrame();
    const divider = $("curtainDivider");
    const after = $("layerAfter");
    if (!frame || !divider || !after) return;

    const pct = Math.max(0, Math.min(100, percent));
    state.split = pct;

    divider.style.left = pct + "%";
    after.style.clipPath = "inset(0 0 0 " + pct + "%)";

    const rounded = String(Math.round(pct));
    setText("splitReadout", rounded + "%");
    divider.setAttribute("aria-valuenow", rounded);
    divider.setAttribute("aria-valuetext", rounded + " percent March 2023 baseline");
}

function splitFromPointer(event) {
    const frame = plateFrame();
    if (!frame) return;
    const rect = frame.getBoundingClientRect();
    if (!rect.width) return;
    setSplit(((event.clientX - rect.left) / rect.width) * 100);
}

function updateCoordinateReadout(event) {
    const frame = plateFrame();
    const readout = $("cursorReadout");
    if (!frame || !readout) return;

    const rect = frame.getBoundingClientRect();
    if (!rect.width || !rect.height) return;

    const fx = clamp01((event.clientX - rect.left) / rect.width);
    const fy = clamp01((event.clientY - rect.top) / rect.height);
    const lon = SITE.bbox.west + fx * (SITE.bbox.east - SITE.bbox.west);
    const lat = SITE.bbox.north - fy * (SITE.bbox.north - SITE.bbox.south);

    readout.textContent = lat.toFixed(4) + "\u00b0 N \u00b7 " + lon.toFixed(4) + "\u00b0 E";
}

function resetCoordinateReadout() {
    setText("cursorReadout",
        SITE.centre.lat.toFixed(4) + "\u00b0 N \u00b7 " + SITE.centre.lon.toFixed(4) + "\u00b0 E");
}

function updateScaleBar() {
    const frame = plateFrame();
    const bar = $("scaleBarBar");
    const label = $("scaleBarLabel");
    if (!frame || !bar || !label) return;

    const width = frame.clientWidth;
    if (!width) return;

    const metresPerPixel = (SITE.cropPx * SITE.pixelM) / width;
    const candidates = [100, 200, 250, 500, 1000, 2000];
    const target = width * 0.22 * metresPerPixel;

    let chosen = candidates[candidates.length - 1];
    for (let i = 0; i < candidates.length; i += 1) {
        if (candidates[i] >= target) { chosen = candidates[i]; break; }
    }

    bar.style.width = Math.max(36, chosen / metresPerPixel).toFixed(0) + "px";
    label.textContent = chosen >= 1000 ? (chosen / 1000) + " km" : chosen + " m";
}

function initPlate() {
    const frame = plateFrame();
    const divider = $("curtainDivider");
    if (!frame || !divider) return;

    frame.addEventListener("pointerdown", (event) => {
        if (event.button !== 0 || state.layer !== "split") return;
        state.dragging = true;
        if (frame.setPointerCapture) {
            try { frame.setPointerCapture(event.pointerId); } catch (err) { /* ignore */ }
        }
        splitFromPointer(event);
    });

    frame.addEventListener("pointermove", (event) => {
        if (state.layer !== "split") return;
        if (state.dragging) splitFromPointer(event);
        else updateCoordinateReadout(event);
    });

    const endDrag = () => { state.dragging = false; };
    frame.addEventListener("pointerup", endDrag);
    frame.addEventListener("pointercancel", endDrag);
    window.addEventListener("pointerup", endDrag);

    frame.addEventListener("pointerleave", () => {
        if (!state.dragging) resetCoordinateReadout();
    });

    divider.addEventListener("keydown", (event) => {
        const step = event.shiftKey ? 10 : 2;
        if (event.key === "ArrowLeft") { setSplit(state.split - step); event.preventDefault(); }
        else if (event.key === "ArrowRight") { setSplit(state.split + step); event.preventDefault(); }
        else if (event.key === "Home") { setSplit(0); event.preventDefault(); }
        else if (event.key === "End") { setSplit(100); event.preventDefault(); }
    });

    resetCoordinateReadout();
    updateScaleBar();

    if (window.ResizeObserver) {
        new ResizeObserver(updateScaleBar).observe(frame);
    } else {
        window.addEventListener("resize", updateScaleBar);
    }

    setSplit(50);
    introSweep();
}

/* One orchestrated moment: the curtain opens on first visit, revealing the
   change the whole page is about. Skipped for reduced motion or on reuse. */
function introSweep() {
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let seen = false;
    try { seen = sessionStorage.getItem("ytl_split_intro") === "1"; } catch (err) { /* ignore */ }

    if (reduceMotion || seen || state.layer !== "split") {
        setSplit(50);
        return;
    }

    try { sessionStorage.setItem("ytl_split_intro", "1"); } catch (err) { /* ignore */ }

    const started = performance.now();
    const from = 8;
    const to = 50;
    const duration = 900;

    function step(now) {
        const t = Math.min(1, (now - started) / duration);
        const eased = 1 - Math.pow(1 - t, 3);
        setSplit(from + (to - from) * eased);
        if (t < 1 && !state.dragging && state.layer === "split") requestAnimationFrame(step);
    }

    requestAnimationFrame(step);
}

/* =========================================================================
   3. Layer selection
   ========================================================================= */
function initLayers() {
    document.querySelectorAll("[data-layer]").forEach((tab) => {
        tab.addEventListener("click", () => selectLayer(tab.dataset.layer));
    });

    /* ?layer=thermal shares a specific plate view */
    const requested = QUERY.get("layer");
    selectLayer(requested && LAYER_LABELS[requested] ? requested : "split");
}

function selectLayer(layer) {
    const tabs = document.querySelectorAll("[data-layer]");
    if (!tabs.length) return;

    state.layer = layer;

    tabs.forEach((tab) => {
        const on = tab.dataset.layer === layer;
        tab.classList.toggle("is-active", on);
        tab.setAttribute("aria-pressed", String(on));
    });

    const isSplit = layer === "split";
    const splitWrap = $("splitContainer");
    const single = $("singleLayerImage");
    const divider = $("curtainDivider");

    if (splitWrap) splitWrap.hidden = !isSplit;
    if (single) single.hidden = isSplit;
    if (divider) divider.hidden = !isSplit;

    document.querySelectorAll(".plate__tag").forEach((tag) => {
        tag.hidden = !isSplit;
    });

    if (isSplit) {
        setSplit(state.split);
    } else if (single) {
        single.alt = LAYER_LABELS[layer] || layer;
        loadImage(single, layerUrl(layer));
    }

    setText("plateLayerName", LAYER_LABELS[layer] || layer);
}

/* =========================================================================
   4. Timeline: one quarter drives the plate, the filing and the ledger
   ========================================================================= */
const timeline = { order: [], active: "", mode: "all" };

/* Bumped after a CV re-analysis so cached layer images are refetched. */
let imageVersion = 0;

function layerUrl(layer) {
    return "/api/layers/" + layer + (imageVersion ? "?v=" + imageVersion : "");
}

/* Historical passes are deterministic composites; the latest pass is the
   segmented layer, which is re-rendered whenever CV parameters change. */
function quarterUrl(id) {
    return id === "2026_08"
        ? layerUrl("annotated")
        : "/api/layers/epoch/" + id + "?annotated=false";
}

/* Swaps an image and shows the plate's rendering state until it lands. */
function loadImage(img, url) {
    if (!img) return;
    const frame = plateFrame();
    const settle = () => {
        if (frame) frame.classList.remove("is-loading");
    };

    if (frame) frame.classList.add("is-loading");
    img.onload = settle;
    img.onerror = settle;
    img.src = url;
}

function setActiveTick(id) {
    const container = $("epochPillsContainer");
    if (container) {
        container.querySelectorAll(".epoch-pill").forEach((pill) => {
            const on = pill.dataset.epoch === id;
            pill.classList.toggle("is-active", on);
            pill.setAttribute("aria-pressed", String(on));
        });
    }
    updateStepper();
}

function updateStepper() {
    const index = timeline.order.indexOf(timeline.active);
    const prev = $("btnPrevQuarter");
    const next = $("btnNextQuarter");
    if (prev) prev.disabled = index <= 0;
    if (next) next.disabled = index < 0 || index >= timeline.order.length - 1;
}

let epochAbortCtrl = null;
let valAbortCtrl = null;

async function loadEpoch(id, quiet) {
    if (epochAbortCtrl) {
        try { epochAbortCtrl.abort(); } catch (e) { /* ignore */ }
    }
    epochAbortCtrl = new AbortController();
    const signal = epochAbortCtrl.signal;

    try {
        const res = await fetch("/api/timeline/epoch/" + id, { signal });
        if (!res.ok) throw new Error("epoch " + id);
        const epoch = await res.json();

        timeline.active = id;
        applyEpoch(epoch, signal);
        setActiveTick(id);

        if (!quiet) showToast(epoch.quarter + " \u00b7 " + epoch.date, "info");
    } catch (err) {
        if (err.name === "AbortError") return; // Expected abort during fast scrubbing
        console.error("Epoch transition failed:", err);
    }
}

function stepQuarter(delta) {
    const index = timeline.order.indexOf(timeline.active);
    if (index < 0) return;
    const target = timeline.order[index + delta];
    if (target) loadEpoch(target, false);
}

/* Warm the neighbouring passes so stepping through time is instant. */
function prefetchNeighbours() {
    const index = timeline.order.indexOf(timeline.active);
    [index - 1, index + 1].forEach((position) => {
        const id = timeline.order[position];
        if (!id || id === "2026_08") return;
        const probe = new Image();
        probe.src = quarterUrl(id);
    });
}

function initTimeline() {
    const container = $("epochPillsContainer");
    if (!container) return;

    /* ?quarter=2024_09 shares a specific observation quarter */
    timeline.active = QUERY.get("quarter") || "2026_08";

    async function renderTicks(nextMode) {
        timeline.mode = nextMode;
        const btnAll = $("btnScrubber14Q");
        const btnMilestones = $("btnScrubber5M");
        if (btnAll) btnAll.classList.toggle("is-active", timeline.mode === "all");
        if (btnMilestones) btnMilestones.classList.toggle("is-active", timeline.mode === "milestones");

        try {
            const res = await fetch("/api/timeline/epochs?mode=" + timeline.mode);
            if (!res.ok) throw new Error("epochs");
            const data = await res.json();
            const epochs = data.epochs || [];
            if (!epochs.length) return;

            timeline.order = epochs.map((epoch) => epoch.id);

            const first = epochs[0];
            if (first && first.solar_area_m2 != null && first.roof_area_m2 != null) {
                state.baseline = {
                    solar: first.solar_area_m2,
                    roof: first.roof_area_m2,
                    stock: first.stock_price_myr
                };
            }

            container.textContent = "";
            epochs.forEach((epoch) => {
                const parts = String(epoch.quarter || "").split(" ");
                const pill = document.createElement("button");
                pill.type = "button";
                pill.className = "epoch-pill";
                if (epoch.is_milestone) pill.classList.add("is-milestone");
                if (epoch.id === timeline.active) pill.classList.add("is-active");
                pill.dataset.epoch = epoch.id;
                pill.title = epoch.quarter + " \u2014 " + epoch.title + " (" + epoch.date + ")";
                pill.setAttribute("aria-pressed", String(epoch.id === timeline.active));

                const q = document.createElement("span");
                q.textContent = parts[0] || epoch.quarter;
                pill.appendChild(q);

                if (parts[1]) {
                    const fy = document.createElement("span");
                    fy.className = "epoch-pill__fy";
                    fy.textContent = parts[1];
                    pill.appendChild(fy);
                }

                pill.addEventListener("click", () => loadEpoch(epoch.id, false));
                container.appendChild(pill);
            });

            updateStepper();

            const present = epochs.some((epoch) => epoch.id === timeline.active);
            if (!present) await loadEpoch(epochs[epochs.length - 1].id, true);
            else if (!state.epochLoaded) await loadEpoch(timeline.active, true);
        } catch (err) {
            console.error("Failed to render timeline:", err);
        }
    }

    const btnAll = $("btnScrubber14Q");
    const btnMilestones = $("btnScrubber5M");
    const btnPrev = $("btnPrevQuarter");
    const btnNext = $("btnNextQuarter");

    if (btnAll) btnAll.addEventListener("click", () => renderTicks("all"));
    if (btnMilestones) btnMilestones.addEventListener("click", () => renderTicks("milestones"));
    if (btnPrev) btnPrev.addEventListener("click", () => stepQuarter(-1));
    if (btnNext) btnNext.addEventListener("click", () => stepQuarter(1));

    renderTicks("all");
}

/* One quarter fills both registers of the sheet. */
function applyEpoch(epoch, signal) {
    /* Picking a quarter always shows imagery: if an instrument layer was open,
       the plate returns to the comparison view first. */
    if (state.layer !== "split") selectLayer("split");

    /* Plate */
    setText("plateQuarter", epoch.quarter);
    setText("plateDateB", epoch.date);
    setText("plateTagB", epoch.quarter);
    setText("stripSensor", epoch.sensor || "Sentinel-2 L2A");
    setText("stripCloud", dec(epoch.cloud_pct) + "%");
    setText("ledgerAsOf", "As of " + epoch.date);

    loadImage($("afterImage"), quarterUrl(epoch.id));
    updateStepper();
    prefetchNeighbours();

    /* Filing register */
    const days = Number(epoch.consensus_variance_days) || 0;
    const pacing = String(epoch.pacing_status || "on track").replace(/_/g, " ").toLowerCase();

    setText("filingQuarter", epoch.quarter);
    setText("epochMilestoneText", epoch.quarter + " (" + epoch.date + ") \u00b7 " + epoch.milestone);
    setText("bursaDateVal", epoch.qr_announcement_date || epoch.date);
    setText("bursaPeriodVal", epoch.period_ended || epoch.date);
    setText("bursaRevVal", "RM " + int(epoch.revenue_myr_m) + " M");
    setText("bursaPatamiVal", "RM " + int(epoch.patami_myr_m) + " M");
    setText("bursaPsVal", "RM " + int(epoch.powerseraya_profit_m) + " M");
    setText("bursaKulaiVal", "RM " + dec(epoch.kulai_revenue_m) + " M");

    const pacingEl = $("bursaPacingVal");
    if (pacingEl) {
        pacingEl.textContent = (days >= 0 ? "+" : MINUS) + Math.abs(days) + " d \u00b7 " + pacing;
        pacingEl.classList.toggle("up", days > 0);
        pacingEl.classList.toggle("down", days < 0);
    }

    setText("filingRead", days > 0
        ? "Physical delivery leads sell-side commercial-operation guidance by " + days + " days."
        : days < 0
            ? "Physical delivery trails sell-side commercial-operation guidance by " + Math.abs(days) + " days."
            : "Physical delivery is in line with sell-side commercial-operation guidance.");

    /* Delivery ledger */
    const solar = Number(epoch.solar_area_m2) || 0;
    const roof = Number(epoch.roof_area_m2) || 0;
    const capacity = Number(epoch.solar_capacity_mw) || 0;

    setText("kpiSolarVal", int(solar));
    setDelta("kpiSolarDelta", solar - state.baseline.solar, "m\u00b2");
    setText("kpiCapacityVal", "~" + dec(capacity));
    setText("kpiCapacityPct", dec((capacity / 500) * 100) + "% of the 500 MW campus target");
    setText("kpiRoofVal", int(roof));
    setDelta("kpiRoofDelta", roof - state.baseline.roof, "m\u00b2");
    setText("kpiStockVal", dec(epoch.stock_price_myr, 2));

    const gain = $("kpiStockGain");
    if (gain) {
        /* Derived from the two prices on screen, so the quote line and the
           ledger can never disagree. */
        const price = Number(epoch.stock_price_myr) || 0;
        const base = Number(state.baseline.stock) || price;
        const pct = base > 0 ? ((price / base) - 1) * 100 : 0;

        if (Math.abs(pct) < 0.05) {
            gain.textContent = "baseline pass";
            gain.classList.remove("up", "down");
        } else {
            gain.textContent = (pct >= 0 ? "+" : MINUS) + dec(Math.abs(pct)) + "% since March 2023";
            gain.classList.toggle("up", pct > 0);
            gain.classList.toggle("down", pct < 0);
        }
    }

    scaleValuationToEpoch(epoch, signal);
    state.epochLoaded = true;
}

function setDelta(id, delta, unit) {
    const el = $(id);
    if (!el) return;

    if (Math.abs(delta) < 1) {
        el.textContent = "baseline pass";
        el.classList.remove("up", "down");
        return;
    }

    el.textContent = (delta > 0 ? "+" : MINUS) + int(Math.abs(delta)) + " " + unit + " vs baseline";
    el.classList.toggle("up", delta > 0);
    el.classList.toggle("down", delta < 0);
}

/* Revenue, EBITDA and rack count all move with delivered critical IT load. */
async function scaleValuationToEpoch(epoch, signal) {
    if (valAbortCtrl) {
        try { valAbortCtrl.abort(); } catch (e) { /* ignore */ }
    }
    valAbortCtrl = new AbortController();
    const activeSignal = signal || valAbortCtrl.signal;

    try {
        const res = await fetch("/api/financial/simulate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            signal: activeSignal,
            body: JSON.stringify({
                lease_usd_per_kw: Number(($("simLeaseRate") || {}).value) || 135,
                usd_to_myr: Number(($("simUsdMyr") || {}).value) || 4.45,
                pue: Number(($("simPue") || {}).value) || 1.22
            })
        });
        if (!res.ok) return;
        applyValuation(await res.json(), epoch);
    } catch (err) {
        if (err.name === "AbortError") return;
        console.error("Epoch valuation failed:", err);
    }
}

/* =========================================================================
   5. Financial model
   ========================================================================= */
function applyValuation(data, epoch) {
    if (!data) return;

    const runway = data.financial_runway || {};
    const it = data.critical_it_load || {};
    const solar = data.solar_economics || {};
    const consensus = data.consensus_variance || {};
    const tb = data.tenant_breakdown || {};

    const modelItMw = Number(it.critical_it_mw) || 0;
    const itMw = epoch ? Number(epoch.critical_it_mw) || modelItMw : modelItMw;
    const ratio = modelItMw ? itMw / modelItMw : 1;

    if (runway.annual_revenue_myr != null) {
        setText("finAnnualRev", "RM " + int(runway.annual_revenue_myr * ratio));
    }
    if (runway.annual_revenue_usd != null) {
        const usd = dec((runway.annual_revenue_usd * ratio) / 1e6);
        const ebitda = runway.annual_ebitda_myr != null
            ? " \u00b7 EBITDA RM " + int((runway.annual_ebitda_myr * ratio) / 1e6) + " M"
            : "";
        setText("finAnnualRevUsd", "\u2248 $" + usd + " M USD run-rate" + ebitda);
    }

    setText("finCriticalIt", "~" + dec(itMw) + " MW");
    setText("finRackCapacity", int(itMw * 40) + " racks (GB200)");

    /* Tenant Heterogeneity Breakdown */
    const sea = tb.sea_ltd || {};
    const nv = tb.nvidia_dgx || {};

    if (sea.critical_it_mw != null) {
        setText("tenantSeaMw", "~" + dec(sea.critical_it_mw * ratio) + " MW");
        setText("tenantSeaRev", "RM " + int((sea.annual_revenue_myr || 0) * ratio / 1e6) + " M ARR");
    }
    if (nv.critical_it_mw != null) {
        setText("tenantNvidiaMw", "~" + dec(nv.critical_it_mw * ratio) + " MW");
        setText("tenantNvidiaRev", "RM " + int((nv.annual_revenue_myr || 0) * ratio / 1e6) + " M ARR");
    }
    if (tb.blended_monthly_lease_usd_per_kw != null) {
        setText("tenantBlendedRate", "$" + dec(tb.blended_monthly_lease_usd_per_kw, 1) + "/kW/mo blended");
    }

    if (solar.annual_energy_savings_myr != null) {
        setText("finEnergySavings", "RM " + int(solar.annual_energy_savings_myr) + " / yr");
    }
    if (solar.annual_generation_mwh != null) {
        setText("finCarbonOffset",
            dec(solar.annual_generation_mwh / 1000) + "k MWh \u00b7 "
            + dec((solar.carbon_offset_tonnes || 0) / 1000) + "k tCO\u2082");
    }

    if (consensus.variance_days != null) {
        setText("consensusVarianceBadge", "+" + consensus.variance_days + " d ahead of guidance");
        setText("finConsensusStatus", "Ahead +" + consensus.variance_days + " days");
    }
}

async function loadValuation() {
    try {
        const res = await fetch("/api/financial/valuation");
        if (!res.ok) throw new Error("valuation");
        applyValuation(await res.json(), null);
    } catch (err) {
        console.error("Valuation load failed:", err);
    }
}

/* =========================================================================
   5b. Sum-of-the-Parts (SOTP) Valuation Model
   ========================================================================= */
async function loadSotp() {
    try {
        const res = await fetch("/api/financial/sotp");
        if (!res.ok) throw new Error("sotp");
        applySotp(await res.json());
    } catch (err) {
        console.error("SOTP load failed:", err);
    }
}

function applySotp(data) {
    if (!data) return;
    setText("sotpTargetPrice", "RM " + dec(data.target_price_myr, 2));
    setText("sotpCurrentPrice", "RM " + dec(data.current_market_price_myr, 2));
    const upside = Number(data.implied_upside_pct) || 0;
    const upEl = $("sotpUpside");
    if (upEl) {
        upEl.textContent = (upside >= 0 ? "+" : MINUS) + dec(Math.abs(upside)) + "% Implied Upside";
        upEl.classList.toggle("badge--success", upside > 0);
        upEl.classList.toggle("badge--danger", upside < 0);
    }
    setText("sotpGroupEv", "RM " + int(data.group_enterprise_value_myr) + " M");
    setText("sotpNetDebt", "-RM " + int(data.group_net_debt_myr) + " M");
    setText("sotpEquityVal", "RM " + int(data.group_equity_value_myr) + " M");

    const tbody = document.querySelector("#sotpSegmentsTable tbody");
    if (tbody && data.segments) {
        tbody.textContent = "";
        data.segments.forEach((seg) => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>
                    <div class="font-semibold text-primary-val">${seg.segment_name}</div>
                    <div class="text-xs text-muted">${seg.peer_benchmark || ""}</div>
                </td>
                <td class="mono font-semibold">RM ${int(seg.financial_metric_myr_m)} M <span class="text-xs text-muted">(${seg.financial_metric_label})</span></td>
                <td class="mono font-semibold">${dec(seg.multiple, 1)}x <span class="text-xs text-muted">${seg.multiple_type}</span></td>
                <td class="mono font-semibold text-primary-val">RM ${int(seg.implied_ev_myr_m)} M</td>
                <td class="mono text-muted">${dec(seg.pct_of_total_ev)}%</td>
                <td class="mono font-semibold text-success">+RM ${dec(seg.target_price_contribution_myr, 2)}</td>
            `;
            tbody.appendChild(tr);
        });
    }
}

function initSotpControls() {
    const btn = $("btnSimulateSotp");
    if (btn) {
        btn.addEventListener("click", async () => {
            const label = btn.textContent;
            btn.disabled = true;
            btn.textContent = "Calculating";

            try {
                const res = await fetch("/api/financial/sotp-simulate", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        dc_multiple: parseFloat(($("simDcMultiple") || {}).value) || 18.0,
                        powerseraya_multiple: parseFloat(($("simPsMultiple") || {}).value) || 7.0,
                        wessex_multiple: parseFloat(($("simWessexMultiple") || {}).value) || 1.05
                    })
                });
                if (!res.ok) throw new Error("sotp simulate");
                applySotp(await res.json());
                showToast("SOTP target re-calculated", "success");
            } catch (err) {
                console.error("SOTP simulation failed:", err);
                showToast("SOTP calculation failed", "error");
            } finally {
                btn.disabled = false;
                btn.textContent = label;
            }
        });
    }
}

/* =========================================================================
   6. Correlation chart (all colours come from the CSS tokens)
   ========================================================================= */
function tokens() {
    const css = getComputedStyle(document.documentElement);
    const get = (name) => css.getPropertyValue(name).trim();
    return {
        price: get("--chart-price") || "#191b18",
        capacity: get("--chart-capacity") || "#b4721a",
        rule: get("--rule") || "#d5d6ce",
        ink: get("--ink") || "#191b18",
        ink2: get("--ink-2") || "#4e544c",
        muted: get("--muted") || "#63695f",
        surface: get("--surface") || "#fbfbf8",
        mono: get("--mono") || "monospace",
        sans: get("--sans") || "sans-serif"
    };
}

function solarStep(date) {
    if (date < "2023-12-01") return 1.0;
    if (date < "2024-05-01") return 15.0;
    if (date < "2024-08-01") return 45.0;
    if (date < "2025-01-01") return 72.0;
    return 103.6;
}

async function loadStock() {
    try {
        const res = await fetch("/api/stock");
        if (!res.ok) throw new Error("stock");
        state.stock = await res.json();
        renderChart(state.stock);
    } catch (err) {
        console.error("Stock chart failed:", err);
    }
}

function renderChart(data) {
    const canvas = $("correlationChart");
    if (!canvas || !window.Chart) return;

    const series = data.series || [];
    if (!series.length) return;

    const labels = series.map((point) => point.date);
    const prices = series.map((point) => point.close);
    const capacities = labels.map(solarStep);
    const c = tokens();
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (state.chart) state.chart.destroy();

    state.chart = new Chart(canvas, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Share price",
                    data: prices,
                    borderColor: c.price,
                    borderWidth: 1.6,
                    pointRadius: 0,
                    pointHoverRadius: 3,
                    pointHoverBackgroundColor: c.price,
                    pointHoverBorderWidth: 0,
                    fill: false,
                    tension: 0.12,
                    yAxisID: "y"
                },
                {
                    label: "Installed solar",
                    data: capacities,
                    borderColor: c.capacity,
                    borderWidth: 1.3,
                    borderDash: [4, 4],
                    stepped: "before",
                    pointRadius: 0,
                    pointHoverRadius: 3,
                    pointHoverBackgroundColor: c.capacity,
                    pointHoverBorderWidth: 0,
                    fill: false,
                    yAxisID: "y1"
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: reduceMotion ? false : { duration: 420, easing: "easeOutQuart" },
            interaction: { mode: "index", intersect: false },
            layout: { padding: { top: 6, right: 4 } },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: c.surface,
                    titleColor: c.ink,
                    bodyColor: c.ink2,
                    borderColor: c.rule,
                    borderWidth: 1,
                    cornerRadius: 0,
                    padding: 10,
                    displayColors: false,
                    titleFont: { family: c.mono, size: 10 },
                    bodyFont: { family: c.mono, size: 11 },
                    callbacks: {
                        label: (ctx) => ctx.datasetIndex === 0
                            ? "RM " + Number(ctx.parsed.y).toFixed(2)
                            : Number(ctx.parsed.y).toFixed(1) + " MW"
                    }
                }
            },
            scales: {
                x: {
                    border: { color: c.rule },
                    grid: { display: false },
                    ticks: {
                        color: c.muted,
                        maxTicksLimit: 8,
                        maxRotation: 0,
                        autoSkip: true,
                        font: { family: c.mono, size: 9.5 },
                        padding: 6
                    }
                },
                y: {
                    position: "left",
                    border: { display: false },
                    grid: { color: c.rule, drawTicks: false, lineWidth: 1 },
                    ticks: {
                        color: c.muted,
                        font: { family: c.mono, size: 9.5 },
                        padding: 8,
                        maxTicksLimit: 6,
                        callback: (value) => "RM " + Number(value).toFixed(2)
                    }
                },
                y1: {
                    position: "right",
                    border: { display: false },
                    grid: { display: false },
                    ticks: {
                        color: c.capacity,
                        font: { family: c.mono, size: 9.5 },
                        padding: 8,
                        maxTicksLimit: 6,
                        callback: (value) => value + " MW"
                    }
                }
            }
        }
    });
}

/* =========================================================================
   7. Telemetry, catalogue, thermal & grid
   ========================================================================= */
async function loadKpi() {
    try {
        const res = await fetch("/api/kpi");
        if (!res.ok) throw new Error("kpi");
        const data = await res.json();

        setText("hudPrice", "RM " + dec(data.stock.current_price, 2));
        const gain = $("hudGain");
        if (gain) {
            const pct = Number(data.stock.gain_pct) || 0;
            gain.textContent = (pct >= 0 ? "+" : MINUS) + dec(Math.abs(pct)) + "%";
            gain.classList.toggle("up", pct > 0);
            gain.classList.toggle("down", pct < 0);
        }

        renderTelemetryPreview(data);
    } catch (err) {
        console.error("KPI load failed:", err);
    }
}

function renderTelemetryPreview(data) {
    const box = $("bigqueryJsonPreview");
    if (!box || !data || !data.solar) return;

    box.textContent = JSON.stringify({
        observation_time: (data.satellite || {}).latest_date,
        ticker: data.ticker,
        asset: data.asset,
        solar_area_m2: data.solar.current_area_m2,
        est_solar_capacity_mw: data.solar.est_capacity_mw,
        solar_pct_of_target: data.solar.pct_target_achieved,
        data_hall_roof_m2: data.data_halls.current_roof_m2,
        stock_price_myr: data.stock.current_price,
        stock_gain_pct: data.stock.gain_pct
    }, null, 2);
}

async function loadSceneCatalogue() {
    const body = document.querySelector("#sceneCatalogue tbody");
    if (!body) return;

    try {
        const res = await fetch("/api/scenes");
        if (!res.ok) throw new Error("scenes");
        const scenes = await res.json();

        body.textContent = "";
        scenes.forEach((scene) => {
            const row = document.createElement("tr");
            if (scene.id === "S2C_48NUG_20260822_0_L2A") row.className = "is-current";

            const cells = [
                [scene.date, "mono"],
                [String(scene.platform || "").toUpperCase(), ""],
                [dec(scene.cloud_pct) + "%", "mono"],
                [scene.milestone, ""]
            ];

            cells.forEach(([value, cls]) => {
                const cell = document.createElement("td");
                if (cls) cell.className = cls;
                cell.textContent = value;
                row.appendChild(cell);
            });

            body.appendChild(row);
        });
    } catch (err) {
        console.error("Scene catalogue failed:", err);
        body.innerHTML = "";
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.className = "mono";
        cell.colSpan = 4;
        cell.textContent = "Catalogue unavailable";
        row.appendChild(cell);
        body.appendChild(row);
    }
}

async function loadEnvironmentalTelemetry() {
    try {
        const [thermalRes, substationRes] = await Promise.all([
            fetch("/api/thermal/telemetry"),
            fetch("/api/substation/telemetry")
        ]);

        if (thermalRes.ok) {
            const thermal = await thermalRes.json();
            setText("finThermalLoad",
                dec(thermal.operational_thermal_load_mw) + " MW ("
                + dec(thermal.operational_load_factor_pct) + "%)");
            setText("finThermalPlume",
                String(thermal.sensor).split("/")[0].trim()
                + " detects cooling-tower plumes +" + dec(thermal.max_delta_t_kelvin, 1)
                + " K over ambient at PUE " + dec(thermal.cooling_infrastructure_pue, 2)
                + ", confirming the halls are drawing grid power.");
        }

        if (substationRes.ok) {
            const substation = await substationRes.json();
            setText("finSubstationCap",
                int(substation.installed_capacity_mva) + " MVA ("
                + substation.transformer_bays_energized + " of "
                + substation.transformer_bays_total + " bays)");
            setText("finSubstationStatus",
                substation.voltage_rating_kv + " \u00b7 "
                + String(substation.grid_interconnection_status).replace(/_/g, " ").toLowerCase()
                + " \u00b7 " + int(substation.headroom_capacity_mva) + " MVA headroom.");
        }
    } catch (err) {
        console.error("Thermal/substation telemetry failed:", err);
    }
}

async function loadProvenance() {
    try {
        const res = await fetch("/api/quant/provenance");
        if (!res.ok) throw new Error("provenance");
        const data = await res.json();
        if (data.cryptographic_provenance) {
            setText("mosaicHashText", data.cryptographic_provenance.sha256_hash);
        }
    } catch (err) {
        console.error("Provenance load failed:", err);
    }
}

/* =========================================================================
   8. Computer-vision parameters & instruments
   ========================================================================= */
function initParameters() {
    [
        ["sliderSolarV", "valSolarV"],
        ["sliderSolarS", "valSolarS"],
        ["sliderRoofV", "valRoofV"],
        ["sliderMwPerHa", "valMwPerHa"],
        ["sliderMinSolar", "valMinSolar"]
    ].forEach(([sliderId, badgeId]) => {
        const slider = $(sliderId);
        const badge = $(badgeId);
        if (!slider || !badge) return;
        slider.addEventListener("input", () => { badge.textContent = slider.value; });
    });

    const runBtn = $("btnRunAnalysis");
    if (runBtn) runBtn.addEventListener("click", runAnalysis);

    const resetBtn = $("btnResetDefaults");
    if (resetBtn) resetBtn.addEventListener("click", resetParameters);
}

function analysisPayload() {
    const read = (id, fallback) => {
        const el = $(id);
        return el ? el.value : fallback;
    };
    return {
        solar_v_max: parseInt(read("sliderSolarV", 75), 10),
        solar_s_max: parseInt(read("sliderSolarS", 120), 10),
        roof_v_min: parseInt(read("sliderRoofV", 175), 10),
        mw_per_hectare: parseFloat(read("sliderMwPerHa", 1.0)),
        min_solar_contour: parseInt(read("sliderMinSolar", 200), 10),
        min_roof_contour: 100
    };
}

async function runAnalysis() {
    const runBtn = $("btnRunAnalysis");
    const label = runBtn ? runBtn.textContent : "";

    if (runBtn) {
        runBtn.disabled = true;
        runBtn.textContent = "Running";
    }

    try {
        const res = await fetch("/api/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(analysisPayload())
        });
        if (!res.ok) throw new Error("analyze");

        /* New segmentation invalidates every cached layer image. */
        imageVersion += 1;
        loadImage($("afterImage"), quarterUrl(timeline.active));
        if (state.layer !== "split") loadImage($("singleLayerImage"), layerUrl(state.layer));

        loadKpi();
        loadValuation();
        showToast("Re-segmentation complete", "success");
    } catch (err) {
        console.error("Analysis failed:", err);
        showToast("Re-segmentation failed", "error");
    } finally {
        if (runBtn) {
            runBtn.disabled = false;
            runBtn.textContent = label;
        }
    }
}

function resetParameters() {
    [
        ["sliderSolarV", "valSolarV", "75"],
        ["sliderSolarS", "valSolarS", "120"],
        ["sliderRoofV", "valRoofV", "175"],
        ["sliderMwPerHa", "valMwPerHa", "1.0"],
        ["sliderMinSolar", "valMinSolar", "200"]
    ].forEach(([sliderId, badgeId, value]) => {
        const slider = $(sliderId);
        const badge = $(badgeId);
        if (slider) slider.value = value;
        if (badge) badge.textContent = value;
    });

    runAnalysis();
}

/* =========================================================================
   9. Actions: model, exports, alerts, telemetry commit
   ========================================================================= */
function initActions() {
    const simBtn = $("btnSimulateFin");
    if (simBtn) {
        simBtn.addEventListener("click", async () => {
            const label = simBtn.textContent;
            simBtn.disabled = true;
            simBtn.textContent = "Computing";

            try {
                const res = await fetch("/api/financial/simulate", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        lease_usd_per_kw: parseFloat((($("simLeaseRate") || {}).value) || 135),
                        usd_to_myr: parseFloat((($("simUsdMyr") || {}).value) || 4.45),
                        pue: parseFloat((($("simPue") || {}).value) || 1.22)
                    })
                });
                if (!res.ok) throw new Error("simulate");
                applyValuation(await res.json(), null);
                showToast("Valuation re-run", "success");
            } catch (err) {
                console.error("Valuation re-run failed:", err);
                showToast("Valuation model failed", "error");
            } finally {
                simBtn.disabled = false;
                simBtn.textContent = label;
            }
        });
    }

    const reportBtn = $("btnExportReport");
    if (reportBtn) reportBtn.addEventListener("click", exportAuditBrief);

    const alertBtn = $("btnDispatchAlert");
    if (alertBtn) {
        alertBtn.addEventListener("click", async () => {
            const label = alertBtn.textContent;
            alertBtn.disabled = true;
            alertBtn.textContent = "Dispatching";

            try {
                await adminFetch("/api/alerts/dispatch");
                showToast("Alpha alert dispatched", "success");
            } catch (err) {
                console.error("Alert dispatch failed:", err);
                notifyAdminOnly(err, "Alert dispatch failed");
            } finally {
                alertBtn.disabled = false;
                alertBtn.textContent = label;
            }
        });
    }

    const syncBtn = $("btnSyncBigQuery");
    if (syncBtn) {
        syncBtn.addEventListener("click", async () => {
            const label = syncBtn.textContent;
            syncBtn.disabled = true;
            syncBtn.textContent = "Committing";

            try {
                const res = await adminFetch("/api/bigquery/sync");
                const result = await res.json();
                showToast("Telemetry " + (result.status || "committed"), "success");
            } catch (err) {
                console.error("Telemetry commit failed:", err);
                notifyAdminOnly(err, "Telemetry commit failed");
            } finally {
                syncBtn.disabled = false;
                syncBtn.textContent = label;
            }
        });
    }
}

async function exportAuditBrief() {
    try {
        const res = await fetch("/api/report/summary");
        if (!res.ok) throw new Error("report");
        const report = await res.json();

        const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "ytl_geoint_audit_brief_" + new Date().toISOString().slice(0, 10) + ".json";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        showToast("Audit brief downloaded", "success");
    } catch (err) {
        console.error("Audit brief failed:", err);
        showToast("Audit brief failed", "error");
    }
}

/* Admin-only actions (pipeline run, BigQuery commit, alerts, engine switch).
   The server requires an X-Admin-Token header for these. On your own deployment, run
   localStorage.setItem("geointAdminToken", "<your token>") in the browser console once. */
function adminHeaders(extra) {
    const headers = Object.assign({}, extra || {});
    try {
        const token = localStorage.getItem("geointAdminToken");
        if (token) headers["X-Admin-Token"] = token;
    } catch (e) { /* storage unavailable: send no token */ }
    return headers;
}

async function adminFetch(url, options) {
    const opts = Object.assign({ method: "POST" }, options || {});
    opts.headers = adminHeaders(opts.headers);
    const res = await fetch(url, opts);
    if (res.status === 401 || res.status === 403) {
        const err = new Error("admin only");
        err.adminOnly = true;
        throw err;
    }
    if (!res.ok) throw new Error("request failed: " + res.status);
    return res;
}

function notifyAdminOnly(err, failMessage) {
    if (err && err.adminOnly) {
        showToast("Admin only: this action is disabled on the public demo", "info");
    } else {
        showToast(failMessage, "error");
    }
}

/* =========================================================================
   10. Pipeline, engine and cloud status
   ========================================================================= */
function initPipelineControls() {
    fetch("/api/gcp/status")
        .then((res) => res.json())
        .then((data) => {
            const platform = String(data.platform || "local")
                .replace(/\s*ready$/i, "")
                .toLowerCase();
            setText("hudGcpStatus", platform + " \u00b7 " + (data.region || "local"));
        })
        .catch((err) => console.error("Cloud status failed:", err));

    const triggerBtn = $("btnTriggerPipeline");
    if (triggerBtn) {
        triggerBtn.addEventListener("click", async () => {
            const label = triggerBtn.textContent;
            triggerBtn.disabled = true;
            triggerBtn.textContent = "Ingesting";
            setText("pipelineTriggerStatus", "querying STAC and BigQuery");

            try {
                const res = await adminFetch("/api/pipeline/update?force=true");
                const data = await res.json();
                showToast("Pipeline finished in " + data.duration_seconds + " s", "success");
                setText("pipelineTriggerStatus",
                    "committed " + String(data.cycle_timestamp).slice(11, 19) + " UTC ("
                    + data.duration_seconds + " s)");
                loadKpi();
                loadStock();
                loadValuation();
            } catch (err) {
                console.error("Pipeline trigger failed:", err);
                notifyAdminOnly(err, "Pipeline trigger failed");
                setText("pipelineTriggerStatus", err && err.adminOnly ? "admin only" : "failed");
            } finally {
                triggerBtn.disabled = false;
                triggerBtn.textContent = label;
            }
        });
    }

    const toggleBtn = $("btnToggleEngine");
    let currentEngine = "spectral";

    if (toggleBtn) {
        toggleBtn.addEventListener("click", async () => {
            const target = currentEngine === "spectral" ? "yolo" : "spectral";

            try {
                const res = await adminFetch("/api/engine/select", {
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ engine: target })
                });
                const data = await res.json();
                currentEngine = data.active_engine;

                if (currentEngine === "yolo") {
                    setText("activeEngineText", "YOLOv8 instance segmentation");
                    toggleBtn.textContent = "Switch to spectral engine";
                    const yoloTab = document.querySelector("[data-layer='yolo_annotated']");
                    if (yoloTab) yoloTab.click();
                    showToast("YOLO engine active", "success");
                } else {
                    setText("activeEngineText", "Spectral morphological CV");
                    toggleBtn.textContent = "Switch to YOLO engine";
                    const cvTab = document.querySelector("[data-layer='annotated']");
                    if (cvTab) cvTab.click();
                    showToast("Spectral engine active", "info");
                }
            } catch (err) {
                console.error("Engine switch failed:", err);
                notifyAdminOnly(err, "Engine switch failed");
            }
        });
    }
}

/* =========================================================================
   11. Toasts
   ========================================================================= */
function showToast(message, type) {
    const container = $("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = "toast" + (type ? " toast--" + type : "");
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 260);
    }, 3400);
}

/* =========================================================================
   12. Boot
   ========================================================================= */
document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initPlate();
    initLayers();
    initTimeline();
    initParameters();
    initActions();
    initSotpControls();
    initPipelineControls();

    loadKpi();
    loadStock();
    loadValuation();
    loadSotp();
    loadSceneCatalogue();
    loadEnvironmentalTelemetry();
    loadProvenance();
});
