(() => {
    "use strict";

    const $ = (selector, root = document) => root.querySelector(selector);
    const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const state = {
        config: null,
        profiles: [],
        aoi: null,
        sceneData: null,
        selectedScenes: { before: null, after: null },
        result: null,
        historyId: null,
        historyLoaded: false,
        map: null,
        drawn: null,
        searchTimer: null,
        searchSequence: 0,
        toastTimer: null,
        running: false,
        timelineDates: null,
    };

    const els = {
        serviceStatus: $("#service-status"),
        tabs: $$(".tab"),
        views: {
            live: $("#view-live"),
            upload: $("#view-upload"),
            history: $("#view-history"),
        },
        placeSearch: $("#place-search"),
        searchResults: $("#search-results"),
        searchSpinner: $("#search-spinner"),
        zoomLevel: $("#zoom-level"),
        mapFallback: $("#map-fallback"),
        aoiStatus: $("#aoi-status"),
        aoiInfo: $("#aoi-info"),
        aoiManual: $("#aoi-manual"),
        liveForm: $("#live-form"),
        dateBefore: $("#date-before"),
        dateAfter: $("#date-after"),
        windowDays: $("#window-days"),
        seasonNote: $("#season-note"),
        profileSelect: $("#profile-select"),
        profileInfo: $("#profile-info"),
        mmuHa: $("#mmu-ha"),
        compositeScenes: $("#composite-scenes"),
        normalise: $("#normalise"),
        cleanup: $("#cleanup"),
        includeRoadContext: $("#include-road-context"),
        liveError: $("#live-error"),
        findScenesBtn: $("#find-scenes-btn"),
        sceneSection: $("#scene-section"),
        seasonWarning: $("#season-warning"),
        sceneGrid: $("#scene-grid"),
        sceneError: $("#scene-error"),
        runAnalysisBtn: $("#run-analysis-btn"),
        resultsSection: $("#results-section"),
        resultMode: $("#result-mode"),
        resultSummary: $("#result-summary"),
        validationBanner: $("#validation-banner"),
        warnings: $("#warnings"),
        resultStats: $("#result-stats"),
        compare: $("#compare"),
        compareBefore: $("#compare-before"),
        compareAfter: $("#compare-after"),
        compareAfterWrap: $("#compare-after-wrap"),
        compareRange: $("#compare-range"),
        comparePosition: $("#compare-position"),
        evidenceImage: $("#evidence-image"),
        heatmapCanvas: $("#heatmap-canvas"),
        heatmapLegend: $("#heatmap-legend"),
        evidenceCaption: $("#evidence-caption"),
        regionsList: $("#regions-list"),
        regionCount: $("#region-count"),
        roadContext: $("#road-context"),
        profileNotes: $("#profile-notes"),
        classTableBlock: $("#class-table-block"),
        classTableBody: $("#class-table-body"),
        classTableNote: $("#class-table-note"),
        timelineCard: $("#timeline-card"),
        timelineDates: $("#timeline-dates"),
        timelineBtn: $("#timeline-btn"),
        timelineStatus: $("#timeline-status"),
        timelineChart: $("#timeline-chart"),
        provenance: $("#provenance"),
        provenanceDetails: $("#provenance-details"),
        downloadPdf: $("#download-pdf"),
        exportGeojson: $("#export-geojson"),
        exportCsv: $("#export-csv"),
        downloadImages: $("#download-images"),
        uploadForm: $("#upload-form"),
        imageA: $("#image-a"),
        imageB: $("#image-b"),
        previewA: $("#preview-a"),
        previewB: $("#preview-b"),
        boxA: $("#box-a"),
        boxB: $("#box-b"),
        uploadError: $("#upload-error"),
        uploadSubmit: $("#upload-submit"),
        modelNote: $("#model-note"),
        historyStatus: $("#history-status"),
        historyList: $("#history-list"),
        historyDashboard: $("#history-dashboard"),
        historyDashboardCount: $("#history-dashboard-count"),
        historyStats: $("#history-stats"),
        historyRecentChart: $("#history-recent-chart"),
        historyRangeChart: $("#history-range-chart"),
        footerVersion: $("#footer-version"),
        busy: $("#busy"),
        busyText: $("#busy-text"),
        toast: $("#toast"),
        themeToggle: $("#theme-toggle"),
        wizardFill: $("#wizard-fill"),
        wizardItems: $$(".wizard-progress li"),
        stepPanels: $$("[data-step-panel]"),
        toDatesBtn: $("#to-dates-btn"),
        toDatesHelp: $("#to-dates-help"),
        backToAreaBtn: $("#back-to-area-btn"),
        loadExampleBtn: $("#load-example-btn"),
        goalInputs: $$('input[name="goal"]'),
        goalNote: $("#goal-note"),
        qualityBadge: $("#quality-badge"),
        qualityText: $("#quality-text"),
        qualityReasons: $("#quality-reasons"),
        summaryCards: $("#summary-cards"),
        learnMoreBtn: $("#learn-more-btn"),
        learnMore: $("#learn-more"),
        hintTour: $("#hint-tour"),
        hintStepCount: $("#hint-step-count"),
        hintText: $("#hint-text"),
        hintNext: $("#hint-next"),
        hintSkip: $("#hint-skip"),
    };

    /* ── Small utilities ─────────────────────────────────────────────────── */

    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined && text !== null) node.textContent = String(text);
        return node;
    }

    function svgEl(tag, attrs = {}) {
        const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
        Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, String(value)));
        return node;
    }

    function clear(node) {
        while (node.firstChild) node.removeChild(node.firstChild);
    }

    function showError(node, message) {
        if (!message) {
            node.hidden = true;
            node.textContent = "";
            return;
        }
        node.hidden = false;
        node.textContent = message;
    }

    function setBusy(on, message = "Working…") {
        state.busy = Boolean(on);
        els.busyText.textContent = message;
        els.busy.hidden = !on;
        document.body.style.overflow = on ? "hidden" : "";
    }

    function toast(message, kind = "info") {
        clearTimeout(state.toastTimer);
        els.toast.className = "toast" + (kind === "error" ? " is-error" : kind === "success" ? " is-success" : "");
        els.toast.textContent = message;
        els.toast.hidden = false;
        state.toastTimer = setTimeout(() => {
            els.toast.hidden = true;
        }, kind === "error" ? 7000 : 4500);
    }

    function scrollTo(node) {
        if (!node) return;
        node.scrollIntoView({ behavior: prefersReducedMotion ? "auto" : "smooth", block: "start" });
    }

    function fmt(value, digits = 2) {
        const number = Number(value);
        return Number.isFinite(number) ? number.toFixed(digits) : "—";
    }

    function fmtNumber(value, digits = 1) {
        const number = Number(value);
        return Number.isFinite(number) ? number.toLocaleString(undefined, { maximumFractionDigits: digits }) : "—";
    }

    function pct(value, digits = 2) {
        const number = Number(value);
        return Number.isFinite(number) ? `${number.toFixed(digits)}%` : "—";
    }

    function numOr(...values) {
        for (const value of values) {
            const number = Number(value);
            if (Number.isFinite(number)) return number;
        }
        return NaN;
    }

    function localISO(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const day = String(date.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    function parseISO(value) {
        const [year, month, day] = String(value).slice(0, 10).split("-").map(Number);
        return new Date(Date.UTC(year, month - 1, day));
    }

    function isoUTC(date) {
        return date.toISOString().slice(0, 10);
    }

    function addDays(date, days) {
        const copy = new Date(date.getTime());
        copy.setDate(copy.getDate() + days);
        return copy;
    }

    function dataUrl(base64) {
        return base64 ? `data:image/png;base64,${base64}` : "";
    }

    async function request(url, options = {}) {
        let response;
        try {
            response = await fetch(url, options);
        } catch (_) {
            throw new Error(
                "The app could not reach the analysis service. Check your internet connection, wait a moment, and try again."
            );
        }
        const type = response.headers.get("content-type") || "";
        let payload = null;
        if (type.includes("application/json")) {
            payload = await response.json().catch(() => null);
        } else {
            const text = await response.text().catch(() => "");
            payload = text ? { error: text } : null;
        }
        if (!response.ok) {
            const error = new Error(
                (payload && (payload.error || payload.detail)) || `Request failed (HTTP ${response.status}).`
            );
            error.status = response.status;
            error.payload = payload;
            throw error;
        }
        return payload;
    }

    function jsonRequest(url, body) {
        return request(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
    }

    async function requestBlob(url, options = {}) {
        let response;
        try {
            response = await fetch(url, options);
        } catch (_) {
            throw new Error(
                "The app could not reach the analysis service. Check your internet connection, wait a moment, and try again."
            );
        }
        if (!response.ok) {
            let payload = null;
            try {
                payload = await response.json();
            } catch (_) {
                payload = null;
            }
            const error = new Error(
                (payload && (payload.error || payload.detail)) || `Request failed (HTTP ${response.status}).`
            );
            error.status = response.status;
            throw error;
        }
        return { blob: await response.blob(), response };
    }

    function filenameFrom(response, fallback) {
        const header = response.headers.get("content-disposition") || "";
        const match = /filename\*?=(?:UTF-8''|")?([^";]+)/i.exec(header);
        if (!match) return fallback;
        try {
            return decodeURIComponent(match[1].replace(/"/g, ""));
        } catch (_) {
            return match[1].replace(/"/g, "");
        }
    }

    function triggerDownload(href, filename) {
        const link = document.createElement("a");
        link.href = href;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
    }

    function liveErrorMessage(error) {
        const lines = [error.message || "The request failed."];
        const payload = error.payload || {};
        if (payload.hint) lines.push(payload.hint);
        if (payload.details && payload.details.suggestion) lines.push(payload.details.suggestion);
        if (payload.details && Array.isArray(payload.details.candidates) && payload.details.candidates.length) {
            const candidates = payload.details.candidates
                .slice(0, 5)
                .map((row) => `${row.id} (${row.date || row.datetime || "unknown date"})`)
                .join("; ");
            lines.push(`Candidate scenes: ${candidates}`);
        }
        return lines.join("\n");
    }

    /* ── Tabs ────────────────────────────────────────────────────────────── */

    function activateTab(name, focusTab = false) {
        document.body.dataset.view = name;
        Object.entries(els.views).forEach(([key, view]) => {
            view.hidden = key !== name;
        });
        els.tabs.forEach((tab) => {
            const active = tab.dataset.tab === name;
            tab.setAttribute("aria-selected", active ? "true" : "false");
            tab.tabIndex = active ? 0 : -1;
            if (active && focusTab) tab.focus();
        });
        if (name === "live" && state.map) {
            setTimeout(() => state.map.invalidateSize(), 80);
        }
        if (name === "history") loadHistory();
    }

    function wireTabs() {
        els.tabs.forEach((tab, index) => {
            tab.addEventListener("click", () => activateTab(tab.dataset.tab));
            tab.addEventListener("keydown", (event) => {
                let target = null;
                if (event.key === "ArrowRight" || event.key === "ArrowDown") {
                    target = els.tabs[(index + 1) % els.tabs.length];
                } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
                    target = els.tabs[(index - 1 + els.tabs.length) % els.tabs.length];
                } else if (event.key === "Home") {
                    target = els.tabs[0];
                } else if (event.key === "End") {
                    target = els.tabs[els.tabs.length - 1];
                }
                if (target) {
                    event.preventDefault();
                    activateTab(target.dataset.tab, true);
                }
            });
        });
    }

    /* ── Config, profiles and status ─────────────────────────────────────── */

    function fallbackProfiles() {
        return [
            {
                key: "general",
                label: "General change (default)",
                description: "NDVI decrease or NDBI increase.",
                validation_status: "unvalidated, qualitative only",
                validation_short: "unvalidated",
                validation_evidence: "",
                display_metrics: false,
                indices: ["ndvi", "ndbi"],
                default_mmu_ha: 0,
                supports_timeline: false,
            },
        ];
    }

    function renderProfiles() {
        clear(els.profileSelect);
        state.profiles.forEach((profile) => {
            const option = el("option", null, profile.label);
            option.value = profile.key;
            els.profileSelect.appendChild(option);
        });
        if (!state.profiles.length) {
            const option = el("option", null, "General change (default)");
            option.value = "general";
            els.profileSelect.appendChild(option);
        }
        els.profileSelect.value = "general";
        if (!els.profileSelect.value) els.profileSelect.selectedIndex = 0;
        renderProfileInfo();
    }

    function currentProfile() {
        return state.profiles.find((profile) => profile.key === els.profileSelect.value) || null;
    }

    function renderProfileInfo() {
        const profile = currentProfile();
        clear(els.profileInfo);
        if (!profile) {
            els.profileInfo.textContent = "Profile details are unavailable.";
            return;
        }
        els.profileInfo.appendChild(el("p", null, profile.description || ""));
        const validation = el("p");
        validation.appendChild(document.createTextNode("Validation: "));
        validation.appendChild(el("strong", null, profile.validation_status || profile.validation_short || "unvalidated"));
        els.profileInfo.appendChild(validation);

        const details = [];
        if (Array.isArray(profile.indices) && profile.indices.length) {
            details.push(`Indices: ${profile.indices.map((item) => item.toUpperCase()).join(", ")}`);
        }
        if (profile.default_mmu_ha !== undefined) {
            details.push(`Default MMU: ${profile.default_mmu_ha} ha`);
        }
        if (profile.supports_timeline) details.push("NDVI timeline available");
        if (details.length) els.profileInfo.appendChild(el("p", "help", details.join(" · ")));

        if (profile.validation_evidence) {
            els.profileInfo.appendChild(el("p", "help", profile.validation_evidence));
        }
        els.mmuHa.placeholder = `${profile.default_mmu_ha ?? 0} (profile default)`;
    }

    async function loadConfig() {
        try {
            const config = await request("/config");
            state.config = config;
            state.profiles = Array.isArray(config.profiles) && config.profiles.length ? config.profiles : fallbackProfiles();
            renderProfiles();
            $$("[data-max-aoi]").forEach((node) => {
                node.textContent = String(config.max_aoi_km ?? 10);
            });
            if (config.max_aoi_km) {
                els.aoiManual.setAttribute(
                    "placeholder",
                    "west, south, east, north (max " + config.max_aoi_km + " km per side)"
                );
            }
            const commit = config.commit && config.commit !== "unknown" ? ` · ${String(config.commit).slice(0, 10)}` : "";
            els.footerVersion.textContent = `Version ${config.version || "3.0.0"}${commit}`;
            if (!config.model_present) {
                els.modelNote.textContent =
                    "The optional ONNX model is absent on this server, so pair uploads will return a model-unavailable error. " +
                    "The live Sentinel-2 spectral path works without it. The CNN was trained on 0.5 m LEVIR-CD pairs and " +
                    "does not transfer well to 10 m Sentinel-2; no accuracy number is shown in this interface.";
            }
        } catch (error) {
            state.profiles = fallbackProfiles();
            renderProfiles();
            els.footerVersion.textContent = "Version unavailable";
            toast("Configuration could not be loaded; defaults are being used.", "error");
        }
    }

    async function checkHealth() {
        try {
            const health = await request("/health");
            els.serviceStatus.textContent = health.model_present
                ? "Service online · CNN weights present"
                : "Service online · spectral path";
            els.serviceStatus.classList.add("is-online");
        } catch (_) {
            els.serviceStatus.textContent = "Service unreachable";
            els.serviceStatus.classList.add("is-offline");
        }
    }

    /* ── Dates, seasons and AOI ──────────────────────────────────────────── */

    function seasonOf(iso) {
        const month = Number(String(iso).slice(5, 7));
        if ([12, 1, 2].includes(month)) return "DJF";
        if ([3, 4, 5].includes(month)) return "MAM";
        if ([6, 7, 8].includes(month)) return "JJA";
        return "SON";
    }

    const SEASON_NAMES = { DJF: "Dec–Feb", MAM: "Mar–May", JJA: "Jun–Aug", SON: "Sep–Nov" };

    function dateValues() {
        return { before: els.dateBefore.value, after: els.dateAfter.value };
    }

    function validateDates() {
        const { before, after } = dateValues();
        if (!before || !after) return { ok: false, message: "Choose both a before and an after date." };
        if (before >= after) return { ok: false, message: "The before date must be earlier than the after date." };
        if (after > localISO(new Date())) return { ok: false, message: "The after date cannot be in the future." };
        const days = Math.round((parseISO(after) - parseISO(before)) / 86400000);
        if (days < 1) return { ok: false, message: "The dates must be at least one day apart." };
        return { ok: true, before, after };
    }

    function updateSeasonNote() {
        const { before, after } = dateValues();
        if (!before || !after || before >= after) {
            els.seasonNote.hidden = true;
            return;
        }
        const first = seasonOf(before);
        const second = seasonOf(after);
        if (first === second) {
            els.seasonNote.hidden = true;
            return;
        }
        els.seasonNote.textContent =
            `Season check: before is in ${SEASON_NAMES[first]} while after is in ${SEASON_NAMES[second]}. ` +
            "Vegetation, crops and surface moisture change with season; a cross-season pair can confuse phenology with damage.";
        els.seasonNote.hidden = false;
    }

    function initDates() {
        const today = new Date();
        today.setHours(12, 0, 0, 0);
        const after = addDays(today, -30);
        const before = addDays(after, -180);
        els.dateBefore.value = localISO(before);
        els.dateAfter.value = localISO(after);
        els.dateBefore.max = localISO(today);
        els.dateAfter.max = localISO(today);
        updateSeasonNote();
    }

    function computeAoi(bbox) {
        const maxKm = Number(state.config && state.config.max_aoi_km) || 10;
        const values = Array.from(bbox || [], Number);
        if (values.length !== 4 || values.some((value) => !Number.isFinite(value))) {
            return { valid: false, bbox: values, message: "The bounding box needs four finite numbers." };
        }
        const [west, south, east, north] = values;
        if (!(-180 <= west && west < east && east <= 180 && -90 <= south && south < north && north <= 90)) {
            return {
                valid: false,
                bbox: values,
                message: "Coordinates are out of range, or the west/south corner is not smaller than the east/north corner.",
            };
        }
        const midLat = ((south + north) / 2) * (Math.PI / 180);
        const widthKm = (east - west) * 111.32 * Math.cos(midLat);
        const heightKm = (north - south) * 111.32;
        const areaKm2 = widthKm * heightKm;
        const problems = [];
        if (widthKm > maxKm || heightKm > maxKm) {
            problems.push(
                `The area is ${widthKm.toFixed(2)} km × ${heightKm.toFixed(2)} km; the limit is ${maxKm} km per side. Draw a smaller box.`
            );
        }
        if (areaKm2 > maxKm * maxKm + 1e-9) {
            problems.push(`The area is ${areaKm2.toFixed(2)} km², above the ${(maxKm * maxKm).toFixed(0)} km² limit.`);
        }
        return {
            valid: problems.length === 0,
            bbox: [west, south, east, north],
            widthKm,
            heightKm,
            areaKm2,
            small: areaKm2 * 100 < 0.5,
            message: problems.join(" "),
            maxKm,
        };
    }

    function formatAreaKm2(areaKm2) {
        const ha = areaKm2 * 100;
        if (areaKm2 >= 1) return `${fmt(areaKm2, 2)} km² (${fmtNumber(ha, 0)} ha)`;
        if (ha >= 0.01) return `${fmt(ha, 2)} ha (${fmt(ha * 2.47105, 1)} acres)`;
        return `${fmtNumber(areaKm2 * 1e6, 0)} m² (${fmt(ha, 3)} ha)`;
    }

    function formatLengthKm(km) {
        return km >= 0.1 ? `${fmt(km, 2)} km` : `${fmtNumber(km * 1000, 0)} m`;
    }

    function estimateRaster(aoi) {
        const maxPx = Number(state.config && state.config.max_analysis_px) || 1024;
        const nativeWidth = Math.max(1, Math.round((aoi.widthKm * 1000) / 10));
        const nativeHeight = Math.max(1, Math.round((aoi.heightKm * 1000) / 10));
        const scale = Math.max(nativeWidth, nativeHeight) > maxPx ? maxPx / Math.max(nativeWidth, nativeHeight) : 1;
        return {
            width: Math.max(64, Math.min(maxPx, Math.round(nativeWidth * scale))),
            height: Math.max(64, Math.min(maxPx, Math.round(nativeHeight * scale))),
            capped: scale < 1,
            nativeWidth,
            nativeHeight,
        };
    }

    function renderAoi() {
        if (!state.aoi) {
            els.aoiInfo.hidden = true;
            els.aoiStatus.className = "aoi-status";
            els.aoiStatus.textContent = "No area selected yet.";
            els.aoiManual.value = "";
            els.toDatesBtn.disabled = true;
            els.toDatesHelp.textContent = "Choose or draw an area first.";
            return;
        }
        const aoi = state.aoi;
        clear(els.aoiInfo);
        els.aoiInfo.hidden = false;
        els.aoiInfo.classList.toggle("is-invalid", !aoi.valid);
        els.aoiStatus.className = "aoi-status " + (aoi.valid ? "is-valid" : "is-invalid");

        if (aoi.valid) {
            els.aoiStatus.textContent = `Area selected: ${formatLengthKm(aoi.widthKm)} × ${formatLengthKm(aoi.heightKm)} (${formatAreaKm2(aoi.areaKm2)}).`;
        } else {
            els.aoiStatus.textContent = aoi.message || "This area is not valid for analysis.";
        }
        els.toDatesBtn.disabled = !aoi.valid;
        els.toDatesHelp.textContent = aoi.valid
            ? "Area ready. Continue to pick the two dates."
            : "Choose or draw an area first.";
        if (!aoi.widthKm) {
            els.aoiManual.value = (aoi.bbox || []).join(", ");
            return;
        }
        const raster = estimateRaster(aoi);
        const list = el("dl");
        const addRow = (label, value) => {
            list.appendChild(el("dt", null, label));
            list.appendChild(el("dd", null, value));
        };
        addRow("Width", formatLengthKm(aoi.widthKm));
        addRow("Height", formatLengthKm(aoi.heightKm));
        addRow("Area", formatAreaKm2(aoi.areaKm2));
        addRow(
            "Detail level",
            `${raster.width} × ${raster.height} px at about 10 m${raster.capped ? " (capped)" : ""}`
        );
        addRow("Per-side limit", `${aoi.maxKm} km`);
        if (aoi.small) {
            const pixels = Math.max(1, Math.round((aoi.areaKm2 * 1e6) / 100));
            els.aoiInfo.appendChild(
                el(
                    "p",
                    "help",
                    `Very small area: under 0.5 ha, so about ${pixels} pixels at 10 m. Results on such a small box will be noisy; consider a slightly larger area.`
                )
            );
        }
        if (!aoi.valid) {
            const problem = el("p", "help", aoi.message);
            els.aoiInfo.appendChild(problem);
        }
        els.aoiInfo.prepend(list);
        els.aoiManual.value = aoi.bbox.map((value) => Number(value).toFixed(6)).join(", ");
    }

    function drawAoiOnMap(aoi, fit = false) {
        if (!state.map || !state.drawn) return;
        state.drawn.clearLayers();
        if (!aoi || !Array.isArray(aoi.bbox) || aoi.bbox.length !== 4) return;
        const [west, south, east, north] = aoi.bbox;
        if (![west, south, east, north].every(Number.isFinite)) return;
        if (!(west < east && south < north)) return;
        const rectangle = L.rectangle(
            [
                [south, west],
                [north, east],
            ],
            { color: "#67e8f9", weight: 2, fillColor: "#3b82f6", fillOpacity: 0.08 }
        );
        state.drawn.addLayer(rectangle);
        if (fit) {
            state.map.fitBounds(rectangle.getBounds(), { padding: [24, 24], maxZoom: 15 });
        }
    }

    function applyAoi(bbox, options = {}) {
        const aoi = computeAoi(bbox);
        state.aoi = aoi;
        renderAoi();
        if (!options.fromMap) drawAoiOnMap(aoi, Boolean(options.fit));
        updateFindButton();
        invalidateScenes();
        if (!aoi.valid) toast(aoi.message, "error");
    }

    function clearAoi() {
        state.aoi = null;
        if (state.drawn) state.drawn.clearLayers();
        renderAoi();
        updateFindButton();
        invalidateScenes();
    }

    function updateFindButton() {
        const dates = validateDates();
        els.findScenesBtn.disabled = !(state.aoi && state.aoi.valid && dates.ok);
    }

    function invalidateScenes() {
        if (!state.sceneData) return;
        state.sceneData = null;
        state.selectedScenes = { before: null, after: null };
        els.sceneSection.hidden = true;
        showError(els.sceneError, "");
    }

    function parseBboxText(text) {
        const parts = String(text).split(",").map((part) => part.trim());
        if (parts.length !== 4 || parts.some((part) => part === "")) {
            throw new Error("Enter exactly four comma-separated numbers: west, south, east, north.");
        }
        const values = parts.map(Number);
        if (values.some((value) => !Number.isFinite(value))) {
            throw new Error("Every bounding-box value must be a number.");
        }
        return values;
    }

    /* ── Map ─────────────────────────────────────────────────────────────── */

    function updateZoomLabel() {
        if (!state.map) return;
        els.zoomLevel.textContent = `Zoom ${state.map.getZoom()}`;
    }

    function initMap() {
        if (!window.L || typeof window.L.map !== "function") {
            els.mapFallback.hidden = false;
            els.zoomLevel.textContent = "Map unavailable";
            const mapNode = $("#map");
            if (mapNode) mapNode.hidden = true;
            return;
        }
        try {
            const map = L.map("map", {
                minZoom: 2,
                maxZoom: 19,
                zoomControl: true,
                worldCopyJump: true,
            }).setView([20.5937, 78.9629], 4);
            L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
                maxZoom: 19,
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            }).addTo(map);
            state.map = map;
            state.drawn = new L.FeatureGroup();
            map.addLayer(state.drawn);

            if (L.Control && L.Control.Draw) {
                map.addControl(
                    new L.Control.Draw({
                        position: "topleft",
                        edit: { featureGroup: state.drawn, edit: false, remove: true },
                        draw: {
                            polygon: false,
                            polyline: false,
                            circle: false,
                            circlemarker: false,
                            marker: false,
                            rectangle: {
                                shapeOptions: { color: "#67e8f9", weight: 2, fillOpacity: 0.08 },
                            },
                        },
                    })
                );
                map.on(L.Draw.Event.CREATED, (event) => {
                    state.drawn.clearLayers();
                    state.drawn.addLayer(event.layer);
                    const bounds = event.layer.getBounds();
                    if (map.getZoom() < 12) {
                        map.fitBounds(bounds, { padding: [24, 24], maxZoom: 14 });
                    }
                    applyAoi(
                        [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()],
                        { fromMap: true }
                    );
                });
                map.on(L.Draw.Event.DELETED, () => {
                    if (!state.drawn.getLayers().length && state.aoi) {
                        state.aoi = null;
                        renderAoi();
                        updateFindButton();
                        invalidateScenes();
                    }
                });
            } else {
                toast("The drawing control did not load. Enter coordinates manually.", "error");
            }
            map.on("zoomend", updateZoomLabel);
            updateZoomLabel();
            setTimeout(() => map.invalidateSize(), 120);
        } catch (error) {
            els.mapFallback.hidden = false;
            els.zoomLevel.textContent = "Map unavailable";
            const mapNode = $("#map");
            if (mapNode) mapNode.hidden = true;
        }
    }

    function wireMapActions() {
        $("#use-view-btn").addEventListener("click", () => {
            if (!state.map) {
                toast("The interactive map is unavailable; enter a bounding box manually.", "error");
                return;
            }
            if (state.map.getZoom() < 12) {
                toast("Zoom in to at least level 12 before using the current view as an AOI.", "error");
                return;
            }
            const bounds = state.map.getBounds();
            applyAoi(
                [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()],
                { fit: false }
            );
        });
        $("#clear-aoi-btn").addEventListener("click", clearAoi);
        $("#apply-bbox-btn").addEventListener("click", () => {
            try {
                const bbox = parseBboxText(els.aoiManual.value);
                showError(els.liveError, "");
                applyAoi(bbox, { fit: true });
            } catch (error) {
                showError(els.liveError, error.message);
                els.aoiStatus.className = "aoi-status is-invalid";
                els.aoiStatus.textContent = error.message;
            }
        });
        els.aoiManual.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                $("#apply-bbox-btn").click();
            }
        });
    }

    /* ── Wizard steps ────────────────────────────────────────────────────── */

    function updateWizard(step) {
        const current = Math.max(1, Math.min(3, Number(step) || 1));
        els.wizardItems.forEach((item) => {
            const itemStep = Number(item.dataset.step);
            if (itemStep === current) {
                item.setAttribute("aria-current", "step");
                item.classList.remove("is-done");
            } else {
                item.removeAttribute("aria-current");
                item.classList.toggle("is-done", itemStep < current);
            }
            const bubble = $(".step-bubble", item);
            if (bubble) bubble.textContent = itemStep < current ? "✓" : String(itemStep);
        });
        els.wizardFill.style.width = current === 1 ? "8%" : current === 2 ? "50%" : "100%";
        els.stepPanels.forEach((panel) => {
            panel.hidden = Number(panel.dataset.stepPanel) !== current;
        });
        if (current !== 2) els.sceneSection.hidden = true;
        if (current === 2) $("#next-2").textContent =
            "What happens next: we list the clearest images around each date, and you pick one per date.";
    }

    function wireWizard() {
        els.toDatesBtn.addEventListener("click", () => {
            updateWizard(2);
            scrollTo($("#settings-heading"));
            els.dateBefore.focus();
        });
        els.backToAreaBtn.addEventListener("click", () => {
            updateWizard(1);
            scrollTo($("#map-heading"));
        });
    }

    /* ── Area presets and example ────────────────────────────────────────── */

    function applyPreset(hectares) {
        if (!state.map) {
            toast("The interactive map is unavailable; enter a bounding box manually.", "error");
            return;
        }
        const center = state.map.getCenter();
        const metersPerDegLat = 111320;
        const metersPerDegLon = 111320 * Math.max(0.05, Math.cos((center.lat * Math.PI) / 180));
        const sideM = Math.sqrt(hectares * 10000);
        const dLat = sideM / 2 / metersPerDegLat;
        const dLon = sideM / 2 / metersPerDegLon;
        applyAoi([center.lng - dLon, center.lat - dLat, center.lng + dLon, center.lat + dLat], { fit: false });
    }

    const EXAMPLE_AREA = {
        name: "Palm Jumeirah, Dubai",
        bbox: [55.1302, 25.1005, 55.1524, 25.1174],
        before: "2023-01-15",
        after: "2023-07-15",
    };

    function loadExample() {
        if (state.map) {
            const [west, south, east, north] = EXAMPLE_AREA.bbox;
            state.map.fitBounds(L.latLngBounds([[south, west], [north, east]]), { padding: [24, 24], maxZoom: 14 });
        }
        els.placeSearch.value = EXAMPLE_AREA.name;
        applyAoi(EXAMPLE_AREA.bbox, { fit: false });
        els.dateBefore.value = EXAMPLE_AREA.before;
        els.dateAfter.value = EXAMPLE_AREA.after;
        updateSeasonNote();
        updateWizard(2);
        scrollTo($("#settings-heading"));
        toast("Example loaded: Palm Jumeirah, Dubai. Adjust the dates if you like.");
    }

    function wirePresetsAndExample() {
        $$(".preset-btn").forEach((button) => {
            button.addEventListener("click", () => applyPreset(Number(button.dataset.presetHa)));
        });
        els.loadExampleBtn.addEventListener("click", loadExample);
    }

    /* ── Goal picker ─────────────────────────────────────────────────────── */

    const GOAL_PROFILES = {
        any: "general",
        farmland: "agriculture",
        buildings: "builtup",
        forest: "deforestation",
        water: "water",
    };
    const PROFILE_GOALS = {
        general: "any",
        agriculture: "farmland",
        builtup: "buildings",
        deforestation: "forest",
        water: "water",
    };
    const GOAL_NOTES = {
        any: "Looks at every kind of change and labels each patch as best the rules can. The clearest signals are usually vegetation loss or new bare ground; fine detail is missed at 10 m.",
        farmland: "Compares how green and how wet the fields were: spots patches that lost greenness, patches that became greener, and stressed crops. Comparing different seasons can confuse crop cycles with damage.",
        buildings: "Looks for more built-up surface between the two dates. Tested on one urban dataset with moderate scores; individual buildings (under about 10 m) are usually missed.",
        forest: "Looks for trees turning to bare ground or water. Seasonal leaf change can be mistaken for loss, so compare similar seasons where you can.",
        water: "Looks for open water appearing or disappearing using two moisture rules. This has not been tested against labelled data, and wet soil or shadows can be mistaken for water.",
    };

    function selectedGoal() {
        const checked = els.goalInputs.find((input) => input.checked);
        return checked ? checked.value : null;
    }

    function updateGoalNote() {
        const goal = selectedGoal();
        els.goalNote.textContent = goal && GOAL_NOTES[goal]
            ? GOAL_NOTES[goal]
            : "Custom profile chosen in advanced settings — the goal cards are only quick presets.";
    }

    function syncGoalFromProfile() {
        const goal = PROFILE_GOALS[els.profileSelect.value];
        if (goal) {
            els.goalInputs.forEach((input) => {
                input.checked = input.value === goal;
            });
        } else {
            els.goalInputs.forEach((input) => {
                input.checked = false;
            });
        }
        updateGoalNote();
    }

    function wireGoalPicker() {
        els.goalInputs.forEach((input) => {
            input.addEventListener("change", () => {
                if (!input.checked) return;
                const profile = GOAL_PROFILES[input.value];
                if (profile && profile !== els.profileSelect.value) {
                    els.profileSelect.value = profile;
                    renderProfileInfo();
                }
                updateGoalNote();
            });
        });
        updateGoalNote();
    }

    /* ── Place search ────────────────────────────────────────────────────── */

    function closeSearch() {
        els.searchResults.hidden = true;
        els.placeSearch.setAttribute("aria-expanded", "false");
    }

    function renderSearchResults(items) {
        clear(els.searchResults);
        if (!items.length) {
            els.searchResults.appendChild(el("p", "search-empty", "No matching places found."));
        } else {
            items.forEach((item, index) => {
                const button = el("button", "search-option", item.display_name || "Unnamed place");
                button.type = "button";
                button.setAttribute("role", "option");
                button.id = `place-option-${index}`;
                button.addEventListener("click", () => choosePlace(item));
                els.searchResults.appendChild(button);
            });
        }
        els.searchResults.hidden = false;
        els.placeSearch.setAttribute("aria-expanded", "true");
    }

    function choosePlace(item) {
        closeSearch();
        els.placeSearch.value = item.display_name || "";
        const info = computeAoi(item.boundingbox);
        if (!state.map) {
            applyAoi(item.boundingbox, { fit: false });
            return;
        }
        const [west, south, east, north] = item.boundingbox;
        const bounds = L.latLngBounds([[south, west], [north, east]]);
        state.map.fitBounds(bounds, { maxZoom: 14, padding: [24, 24] });
        if (!info.valid && (info.widthKm > info.maxKm || info.heightKm > info.maxKm)) {
            clearAoi();
            els.aoiStatus.className = "aoi-status is-invalid";
            els.aoiStatus.textContent =
                `"${item.display_name}" is about ${info.widthKm.toFixed(1)} × ${info.heightKm.toFixed(1)} km, ` +
                `above the ${info.maxKm} km per-side limit. Draw a smaller box inside it.`;
            toast("This place is too large. Draw a smaller analysis box.", "error");
            return;
        }
        applyAoi(item.boundingbox, { fit: false });
    }

    function wireSearch() {
        els.placeSearch.addEventListener("input", () => {
            const query = els.placeSearch.value.trim();
            clearTimeout(state.searchTimer);
            state.searchSequence += 1;
            const sequence = state.searchSequence;
            if (query.length < 2) {
                closeSearch();
                els.searchSpinner.hidden = true;
                return;
            }
            els.searchSpinner.hidden = false;
            state.searchTimer = setTimeout(async () => {
                try {
                    const data = await request(`/geocode-suggest?q=${encodeURIComponent(query)}`);
                    if (sequence !== state.searchSequence) return;
                    renderSearchResults(Array.isArray(data) ? data : []);
                } catch (error) {
                    if (sequence !== state.searchSequence) return;
                    clear(els.searchResults);
                    els.searchResults.appendChild(el("p", "search-empty", "Place search failed. Enter coordinates instead."));
                    els.searchResults.hidden = false;
                    els.placeSearch.setAttribute("aria-expanded", "true");
                } finally {
                    if (sequence === state.searchSequence) els.searchSpinner.hidden = true;
                }
            }, 380);
        });

        els.placeSearch.addEventListener("keydown", (event) => {
            if (event.key === "Escape") closeSearch();
        });

        document.addEventListener("click", (event) => {
            if (!els.searchResults.contains(event.target) && event.target !== els.placeSearch) closeSearch();
        });
    }

    /* ── Live form and scene search ──────────────────────────────────────── */

    function wireLiveForm() {
        [els.dateBefore, els.dateAfter].forEach((input) => {
            input.addEventListener("change", () => {
                updateSeasonNote();
                updateFindButton();
                invalidateScenes();
                showError(els.liveError, "");
            });
        });
        els.windowDays.addEventListener("input", () => {
            updateFindButton();
            invalidateScenes();
        });
        els.profileSelect.addEventListener("change", () => {
            renderProfileInfo();
            syncGoalFromProfile();
        });
        els.sceneGrid.addEventListener("change", (event) => {
            const input = event.target;
            if (!(input instanceof HTMLInputElement) || input.type !== "radio") return;
            const windowKey = input.dataset.window;
            if (windowKey !== "before" && windowKey !== "after") return;
            state.selectedScenes[windowKey] = input.value;
            $$(".scene-card", els.sceneGrid).forEach((card) => {
                const radio = card.querySelector('input[type="radio"]');
                card.classList.toggle("is-selected", Boolean(radio && radio.checked));
            });
            updateRunButton();
        });
        els.liveForm.addEventListener("submit", (event) => {
            event.preventDefault();
            findScenes();
        });
        $("#change-scenes-btn").addEventListener("click", () => {
            els.dateBefore.focus();
            scrollTo($("#settings-heading"));
        });
        els.runAnalysisBtn.addEventListener("click", runAnalysis);
    }

    async function findScenes() {
        showError(els.liveError, "");
        const dates = validateDates();
        if (!state.aoi || !state.aoi.valid) {
            showError(els.liveError, "Select a valid analysis area first.");
            return;
        }
        if (!dates.ok) {
            showError(els.liveError, dates.message);
            return;
        }
        const windowDays = Number(els.windowDays.value);
        if (!Number.isFinite(windowDays) || windowDays < 1 || windowDays > 120) {
            showError(els.liveError, "The scene window must be between 1 and 120 days.");
            return;
        }
        setBusy(true, "Looking for the clearest images…");
        try {
            const data = await jsonRequest("/scenes", {
                bbox: state.aoi.bbox,
                date_before: dates.before,
                date_after: dates.after,
                window_days: windowDays,
            });
            state.sceneData = data;
            state.selectedScenes = { before: null, after: null };
            renderScenes(data);
            els.sceneSection.hidden = false;
            updateWizard(2);
            scrollTo(els.sceneSection);
        } catch (error) {
            showError(els.liveError, liveErrorMessage(error));
            els.sceneSection.hidden = true;
            scrollTo(els.liveError);
        } finally {
            setBusy(false);
        }
    }

    function sceneWindowLabel(key) {
        return key === "before" ? "Before" : "After";
    }

    function buildSceneColumn(key, windowData) {
        const column = el("div", "scene-column");
        const heading = el("h3", null, sceneWindowLabel(key));
        column.appendChild(heading);
        const requested = windowData.requested_date || "";
        const range = windowData.start && windowData.end ? ` · search window ${windowData.start.slice(0, 10)} to ${windowData.end.slice(0, 10)}` : "";
        column.appendChild(el("p", null, `Target ${requested}${range}`));

        const scenes = Array.isArray(windowData.scenes) ? windowData.scenes : [];
        if (!scenes.length) {
            column.appendChild(el("p", "region-empty", "No images were found for this window. Try widening the search window."));
            return column;
        }

        const warnCloud = Number(state.config && state.config.cloud_warn_percent) || 30;
        scenes.forEach((scene, index) => {
            const card = el("label", "scene-card");
            const input = document.createElement("input");
            input.type = "radio";
            input.name = `scene-${key}`;
            input.value = scene.id;
            input.dataset.window = key;
            input.id = `scene-${key}-${index}`;
            input.checked = scene.id === windowData.recommended_id || (!windowData.recommended_id && index === 0);
            input.setAttribute(
                "aria-label",
                `${sceneWindowLabel(key)} image ${scene.date || scene.id}, cloud cover ${fmt(scene.cloud_cover_percent, 1)} percent`
            );
            if (input.checked) {
                state.selectedScenes[key] = scene.id;
                card.classList.add("is-selected");
            }
            card.appendChild(input);

            const top = el("div", "scene-card-top");
            top.appendChild(el("span", "scene-date", scene.date || String(scene.datetime || "").slice(0, 10)));
            top.appendChild(el("span", "scene-score", `score ${fmt(scene.score, 3)}`));
            card.appendChild(top);

            const meta = el("div", "scene-meta");
            meta.appendChild(el("span", null, `Catalog cloud ${fmt(scene.cloud_cover_percent, 1)}%`));
            meta.appendChild(el("span", null, `AOI cover ${fmt(scene.coverage_percent, 1)}%`));
            meta.appendChild(el("span", null, `±${fmtNumber(scene.days_from_target, 0)} d`));
            card.appendChild(meta);

            const badges = el("div", "scene-badges");
            badges.appendChild(el("span", "badge", `Rank ${scene.rank || index + 1}`));
            if (scene.recommended) badges.appendChild(el("span", "badge is-recommended", "Recommended"));
            if (Number(scene.cloud_cover_percent) >= warnCloud) {
                badges.appendChild(el("span", "badge is-cloudy", "Cloudy catalog"));
            }
            card.appendChild(badges);
            column.appendChild(card);
        });
        return column;
    }

    function renderScenes(data) {
        clear(els.sceneGrid);
        clear(els.seasonWarning);
        const warningParts = [];
        if (data.season_warning) warningParts.push(data.season_warning);
        (data.warnings || []).forEach((warning) => {
            if (warning && warning.code !== "season" && warning.message) {
                warningParts.push(warning.message);
            }
        });
        if (warningParts.length) {
            warningParts.forEach((text) => els.seasonWarning.appendChild(el("p", null, text)));
            els.seasonWarning.hidden = false;
        } else {
            els.seasonWarning.hidden = true;
        }

        ["before", "after"].forEach((key) => {
            const windowData = data[key];
            if (windowData) els.sceneGrid.appendChild(buildSceneColumn(key, windowData));
        });
        showError(els.sceneError, "");
        updateRunButton();
    }

    function updateRunButton() {
        els.runAnalysisBtn.disabled = !(state.selectedScenes.before && state.selectedScenes.after) || state.running;
    }

    function gatherOptions() {
        const mmuRaw = els.mmuHa.value.trim();
        const mmu = mmuRaw === "" ? null : Number(mmuRaw);
        if (mmu !== null && (!Number.isFinite(mmu) || mmu < 0 || mmu > 100)) {
            throw new Error("The minimum mapping unit must be between 0 and 100 hectares, or blank.");
        }
        const composite = Number(els.compositeScenes.value);
        if (![1, 2, 3].includes(composite)) {
            throw new Error("Scenes per date must be 1, 2, or 3.");
        }
        return {
            profile: els.profileSelect.value || "general",
            mmu_ha: mmu,
            composite_scenes: composite,
            normalise: els.normalise.checked,
            cleanup: els.cleanup.checked,
            include_road_context: els.includeRoadContext.checked,
        };
    }

    async function runAnalysis() {
        if (state.running) return;
        showError(els.sceneError, "");
        if (!state.sceneData || !state.aoi || !state.aoi.valid) {
            showError(els.sceneError, "Search for images again before running the analysis.");
            return;
        }
        const dates = validateDates();
        if (!dates.ok) {
            showError(els.sceneError, dates.message);
            return;
        }
        if (!state.selectedScenes.before || !state.selectedScenes.after) {
            showError(els.sceneError, "Select one image for each date.");
            return;
        }
        let options;
        try {
            options = gatherOptions();
        } catch (error) {
            showError(els.sceneError, error.message);
            return;
        }
        const windowDays = Number(els.windowDays.value);
        state.running = true;
        updateRunButton();
        setBusy(true, "Downloading the images and measuring changes…");
        try {
            const result = await jsonRequest("/fetch-and-predict", {
                bbox: state.aoi.bbox,
                date_before: dates.before,
                date_after: dates.after,
                window_days: windowDays,
                scene_before_id: state.selectedScenes.before,
                scene_after_id: state.selectedScenes.after,
                profile: options.profile,
                mmu_ha: options.mmu_ha,
                composite_scenes: options.composite_scenes,
                normalise: options.normalise,
                cleanup: options.cleanup,
                include_road_context: options.include_road_context,
            });
            state.historyLoaded = false;
            renderResult(result);
            updateWizard(3);
            scrollTo(els.resultsSection);
        } catch (error) {
            showError(els.sceneError, liveErrorMessage(error));
            scrollTo(els.sceneError);
        } finally {
            state.running = false;
            updateRunButton();
            setBusy(false);
        }
    }

    /* ── Results ─────────────────────────────────────────────────────────── */

    function setActionAvailability(enabled) {
        [els.downloadPdf, els.exportGeojson, els.exportCsv, els.downloadImages].forEach((button) => {
            button.disabled = !enabled;
        });
    }

    function renderResult(result) {
        state.result = result;
        state.historyId = result.history_id ?? state.historyId ?? null;
        const isCnn = result.pipeline === "cnn";
        const profileLabel = result.profile_label || result.profile || "general";
        els.resultMode.textContent = isCnn
            ? "Uploaded pair · CNN (experimental)"
            : `Live Sentinel-2 · ${profileLabel}${
                  result.scenes && result.scenes.before && result.scenes.after
                      ? ` · ${result.scenes.before.date} → ${result.scenes.after.date}`
                      : ""
              }`;

        const percent = Number(result.percent_changed);
        els.resultSummary.textContent =
            result.summary_sentence ||
            (isCnn
                ? `The CNN flagged ${fmt(percent, 2)}% of pixels as changed. Pair mode has no cloud masking or scene provenance; review the overlay before interpreting it.`
                : `The selected rules flagged ${fmt(percent, 2)}% of raster pixels. Decision support, not ground truth.`);

        renderValidationBanner(result, isCnn);
        renderQualityBadge(result, isCnn);
        renderSummaryCards(result, isCnn);
        renderWarnings(result);
        renderStats(result, isCnn);
        renderClassTable(result);
        renderCompare(result);
        renderEvidence(result);
        renderRegions(result);
        renderProfileNotes(result, isCnn);
        renderTimelineCard(result, isCnn);
        renderProvenance(result, isCnn);
        setActionAvailability(true);

        els.resultsSection.hidden = false;
    }

    /* ── Data-quality badge ───────────────────────────────────────────────── */

    function renderQualityBadge(result, isCnn) {
        if (isCnn) {
            els.qualityBadge.hidden = true;
            return;
        }
        const reasons = [];
        let worst = 0; // 0 good, 1 okay, 2 poor

        const cloudBefore = numOr(result.aoi_cloud_fraction_before, result.cloud_coverage_before);
        const cloudAfter = numOr(result.aoi_cloud_fraction_after, result.cloud_coverage_after);
        const worstCloud = Math.max(cloudBefore, cloudAfter);
        if (Number.isFinite(worstCloud)) {
            const cloudPct = worstCloud * 100;
            if (cloudPct > 30) {
                worst = Math.max(worst, 2);
                reasons.push(`over ${fmt(cloudPct, 0)}% of your area was cloud or shadow in at least one image`);
            } else if (cloudPct > 10) {
                worst = Math.max(worst, 1);
                reasons.push(`${fmt(cloudPct, 0)}% of your area was cloud or shadow in at least one image`);
            }
        }

        if (result.season_warning) {
            worst = Math.max(worst, 1);
            reasons.push("the two dates fall in different seasons");
        }

        const scenes = result.scenes || {};
        let maxGap = null;
        ["before", "after"].forEach((key) => {
            const window = scenes[key];
            if (!window || !window.date || !window.requested_date) return;
            const gap = Math.abs(new Date(window.date) - new Date(window.requested_date)) / 86400000;
            if (!Number.isFinite(gap)) return;
            maxGap = maxGap === null ? gap : Math.max(maxGap, gap);
        });
        if (maxGap !== null && maxGap > 15) {
            worst = Math.max(worst, maxGap > 60 ? 2 : 1);
            reasons.push(`the clearest images landed ${fmt(maxGap, 0)} days from the dates you chose`);
        }

        const levels = [
            ["is-good", "Data quality: good", "Both images are mostly clear over your area and close to your dates."],
            ["is-okay", "Data quality: okay", "Use the results with extra care."],
            ["is-poor", "Data quality: poor", "Treat this result as a rough pointer only."],
        ];
        const [cssClass, title, base] = levels[worst];
        els.qualityBadge.className = `quality-badge ${cssClass}`;
        els.qualityText.textContent = title;
        els.qualityReasons.textContent = reasons.length ? `${base} Because: ${reasons.join("; ")}.` : base;
        els.qualityBadge.hidden = false;
    }

    /* ── Summary cards ────────────────────────────────────────────────────── */

    function renderSummaryCards(result, isCnn) {
        clear(els.summaryCards);
        const percent = Number(result.percent_changed);
        const regions = Array.isArray(result.change_regions) ? result.change_regions : [];
        const aoiKm2 = result.aoi && Number(result.aoi.area_km2);

        const card = (label, value, sub) => {
            const node = el("div", "summary-card");
            node.appendChild(el("span", "summary-card-label", label));
            node.appendChild(el("span", "summary-card-value", value));
            if (sub) node.appendChild(el("span", "summary-card-sub", sub));
            els.summaryCards.appendChild(node);
        };

        if (Number.isFinite(percent)) {
            if (Number.isFinite(aoiKm2)) {
                const changedKm2 = (percent / 100) * aoiKm2;
                card("Area changed", formatAreaKm2(changedKm2), `out of a ${formatAreaKm2(aoiKm2)} area`);
            } else {
                card("Area changed", "—", "area unknown for pair uploads");
            }
            card("Share of the area", pct(percent), isCnn ? "flagged pixels, no cloud mask" : "after cloud and shadow masking");
        } else {
            card("Area changed", "—", "no change percentage returned");
            card("Share of the area", "—", "");
        }

        const main = regions
            .slice()
            .sort((a, b) => Number(b.pixel_area || 0) - Number(a.pixel_area || 0))[0];
        card(
            "Main change type",
            main ? main.change_type || "Change (type unclear)" : "No change detected",
            main ? "largest patch, by area" : "no patches passed the rules"
        );
    }

    function renderValidationBanner(result, isCnn) {
        clear(els.validationBanner);
        els.validationBanner.className = "validation-banner";
        if (isCnn) {
            els.validationBanner.appendChild(el("strong", null, "Experimental transfer — no accuracy is claimed in this interface"));
            els.validationBanner.appendChild(
                el(
                    "p",
                    null,
                    "These weights were trained on 0.5 m LEVIR-CD aerial pairs. Transfer to 10 m Sentinel-2 imagery is poor and documented in the repository benchmarks. Pair mode has no cloud masking, scene ranking or AOI provenance."
                )
            );
            return;
        }
        const benchmarked = Boolean(result.display_metrics);
        els.validationBanner.classList.toggle("is-benchmarked", benchmarked);
        els.validationBanner.appendChild(
            el(
                "strong",
                null,
                benchmarked ? "Benchmarked profile — narrow scope only" : "Unvalidated profile — no accuracy number is shown"
            )
        );
        if (result.validation_status) {
            els.validationBanner.appendChild(el("p", null, result.validation_status));
        }
        if (result.validation_evidence) {
            els.validationBanner.appendChild(el("p", null, result.validation_evidence));
        }
        if (!benchmarked) {
            els.validationBanner.appendChild(
                el("p", null, "Treat these regions as candidates to verify against imagery and local knowledge, not as measured change.")
            );
        }
    }

    function renderWarnings(result) {
        clear(els.warnings);
        const warnings = Array.isArray(result.warnings) ? result.warnings : [];
        if (!warnings.length) {
            els.warnings.hidden = true;
            return;
        }
        warnings.forEach((warning) => {
            if (!warning || !warning.message) return;
            const item = el("li", warning.severity === "high" ? "is-high" : null);
            item.appendChild(document.createTextNode(warning.message));
            if (Array.isArray(warning.suggested_scenes) && warning.suggested_scenes.length) {
                const names = warning.suggested_scenes
                    .slice(0, 3)
                    .map((scene) => `${scene.id} (${scene.date || "date unknown"}, ${fmt(scene.cloud_cover_percent, 1)}% catalog cloud)`)
                    .join("; ");
                item.appendChild(document.createTextNode(` Alternatives: ${names}.`));
            }
            els.warnings.appendChild(item);
        });
        els.warnings.hidden = !els.warnings.childElementCount;
    }

    function addStat(label, value) {
        const wrap = el("div", "stat");
        wrap.appendChild(el("dt", null, label));
        wrap.appendChild(el("dd", null, value));
        els.resultStats.appendChild(wrap);
    }

    function renderStats(result, isCnn) {
        clear(els.resultStats);
        addStat("Change, all pixels", pct(result.percent_changed));
        if (result.percent_changed_valid !== undefined && result.percent_changed_valid !== null) {
            addStat("Change, valid pixels", pct(result.percent_changed_valid));
        }
        if (result.percent_cloud_masked !== undefined && result.percent_cloud_masked !== null) {
            addStat("Cloud/shadow masked", pct(result.percent_cloud_masked));
        }
        const regions = Array.isArray(result.change_regions) ? result.change_regions : [];
        addStat("Patches", String(regions.length));
        if (result.aoi && result.aoi.area_km2 !== undefined) {
            addStat("AOI", formatAreaKm2(Number(result.aoi.area_km2)));
        }
        if (result.aoi && result.aoi.expected_pixels) {
            const px = result.aoi.expected_pixels;
            const x = Number(px.pixel_size_x_m);
            const y = Number(px.pixel_size_y_m);
            if (Number.isFinite(x) && Number.isFinite(y)) {
                addStat("Pixel size", Math.abs(x - y) < 0.05 ? `${fmt(x, 1)} m` : `${fmt(x, 1)} × ${fmt(y, 1)} m`);
            }
        }
        if (Array.isArray(result.image_shape) && result.image_shape.length >= 2) {
            addStat("Raster", `${fmtNumber(result.image_shape[1], 0)} × ${fmtNumber(result.image_shape[0], 0)} px`);
        }
        if (isCnn) addStat("Mode", "pair upload");
    }

    function renderClassTable(result) {
        const table = result.class_table;
        clear(els.classTableBody);
        if (!table || !Array.isArray(table.rows) || !table.rows.length) {
            els.classTableBlock.hidden = true;
            return;
        }
        els.classTableBlock.hidden = false;
        table.rows.forEach((row) => {
            const tr = el("tr");
            tr.appendChild(el("th", "class-name", row.change_type || "Unlabelled change"));
            tr.appendChild(el("td", null, formatAreaKm2(Number(row.area_ha || 0) / 100)));
            tr.appendChild(el("td", null, pct(row.percent_of_aoi)));
            tr.appendChild(el("td", null, String(row.region_count ?? 0)));
            els.classTableBody.appendChild(tr);
        });
        const total = table.total;
        if (total) {
            const tr = el("tr", "is-total");
            tr.appendChild(el("th", "class-name", total.change_type || "Total"));
            tr.appendChild(el("td", null, formatAreaKm2(Number(total.area_ha || 0) / 100)));
            tr.appendChild(el("td", null, pct(total.percent_of_aoi)));
            tr.appendChild(el("td", null, String(total.region_count ?? 0)));
            els.classTableBody.appendChild(tr);
        }
        els.classTableNote.textContent = table.note || "";
    }

    function setComparePosition(value) {
        const position = Math.max(0, Math.min(100, Number(value) || 0));
        els.compareAfterWrap.style.clipPath = `inset(0 0 0 ${position}%)`;
        const handle = $(".compare-handle", els.compare);
        if (handle) handle.style.left = `${position}%`;
        els.compareRange.value = String(Math.round(position));
        els.comparePosition.textContent = `${Math.round(position)}%`;
    }

    function wireCompare() {
        let dragging = false;
        const move = (event) => {
            if (!dragging) return;
            const point = event.touches ? event.touches[0] : event;
            const rect = els.compare.getBoundingClientRect();
            if (!rect.width) return;
            setComparePosition(((point.clientX - rect.left) / rect.width) * 100);
        };
        els.compare.addEventListener("pointerdown", (event) => {
            dragging = true;
            els.compare.setPointerCapture && els.compare.setPointerCapture(event.pointerId);
            move(event);
        });
        els.compare.addEventListener("pointermove", move);
        window.addEventListener("pointerup", () => {
            dragging = false;
        });
        els.compare.addEventListener("touchstart", (event) => {
            dragging = true;
            move(event);
        }, { passive: true });
        window.addEventListener("touchmove", move, { passive: true });
        window.addEventListener("touchend", () => {
            dragging = false;
        });
        els.compareRange.addEventListener("input", () => setComparePosition(els.compareRange.value));
        setComparePosition(50);
    }

    function renderCompare(result) {
        const before = dataUrl(result.image_a_base64);
        const after = dataUrl(result.image_b_base64);
        const block = els.compare.closest(".result-block");
        if (!before || !after) {
            if (block) block.hidden = true;
            return;
        }
        if (block) block.hidden = false;
        els.compareBefore.src = before;
        els.compareAfter.src = after;
        els.compareBefore.alt = "Before image for the analysed area";
        els.compareAfter.alt = "After image for the analysed area";
        setComparePosition(50);
    }

    const EVIDENCE_SOURCES = {
        overlay: {
            caption: "Red marks pixels selected by the profile's rules on the after image. Only the after image is shown beneath the overlay.",
            alt: "Change overlay on the after image",
        },
        mask: {
            caption: "White is flagged change after cloud/shadow masking, MMU filtering and optional cleanup. Black is unchanged or excluded; excluded area is not inferred.",
            alt: "Binary change mask",
        },
        heatmap: {
            caption: "Continuous spectral-rule magnitude, rescaled to the 99th percentile of this raster. This is not a probability or a confidence score.",
            alt: "Heatmap of spectral rule evidence",
        },
    };
    let activeEvidence = "overlay";

    function drawHeatmap() {
        if (!state.result || !state.result.confidence_base64) return;
        const canvas = els.heatmapCanvas;
        const ctx = canvas.getContext("2d");
        const image = new Image();
        image.onload = () => {
            canvas.width = image.naturalWidth;
            canvas.height = image.naturalHeight;
            ctx.drawImage(image, 0, 0);
            let pixels;
            try {
                pixels = ctx.getImageData(0, 0, canvas.width, canvas.height);
            } catch (_) {
                return;
            }
            const data = pixels.data;
            for (let index = 0; index < data.length; index += 4) {
                const value = data[index] / 255;
                const [red, green, blue] = evidenceColor(value);
                data[index] = red;
                data[index + 1] = green;
                data[index + 2] = blue;
                data[index + 3] = 255;
            }
            ctx.putImageData(pixels, 0, 0);
        };
        image.src = dataUrl(state.result.confidence_base64);
    }

    function evidenceColor(value) {
        // Viridis: monotonic luminance keeps the scale readable for common colour-vision deficiencies.
        const stops = [
            [0.0, [68, 1, 84]],
            [0.25, [59, 82, 139]],
            [0.5, [33, 145, 140]],
            [0.75, [94, 201, 98]],
            [1.0, [253, 231, 37]],
        ];
        const clamped = Math.max(0, Math.min(1, value));
        for (let index = 1; index < stops.length; index += 1) {
            if (clamped <= stops[index][0]) {
                const [leftAt, leftColor] = stops[index - 1];
                const [rightAt, rightColor] = stops[index];
                const span = rightAt - leftAt || 1;
                const t = (clamped - leftAt) / span;
                return leftColor.map((channel, channelIndex) =>
                    Math.round(channel + (rightColor[channelIndex] - channel) * t)
                );
            }
        }
        return stops[stops.length - 1][1];
    }

    function setEvidence(layer) {
        activeEvidence = layer;
        $$("[data-evidence]").forEach((button) => {
            const selected = button.dataset.evidence === layer;
            button.setAttribute("aria-selected", selected ? "true" : "false");
            button.tabIndex = selected ? 0 : -1;
        });
        if (!state.result) return;
        const sources = {
            overlay: dataUrl(state.result.overlay_base64),
            mask: dataUrl(state.result.mask_base64),
            heatmap: dataUrl(state.result.confidence_base64),
        };
        const source = sources[layer];
        if (!source) return;
        const config = EVIDENCE_SOURCES[layer];
        els.evidenceCaption.textContent = config.caption;
        if (layer === "heatmap") {
            els.evidenceImage.hidden = true;
            els.heatmapCanvas.hidden = false;
            els.heatmapLegend.hidden = false;
            if (!state.heatmapDrawnFor || state.heatmapDrawnFor !== state.result) {
                drawHeatmap();
                state.heatmapDrawnFor = state.result;
            }
        } else {
            els.evidenceImage.hidden = false;
            els.heatmapCanvas.hidden = true;
            els.heatmapLegend.hidden = true;
            els.evidenceImage.src = source;
            els.evidenceImage.alt = config.alt;
        }
    }

    function renderEvidence(result) {
        const available = {
            overlay: Boolean(result.overlay_base64),
            mask: Boolean(result.mask_base64),
            heatmap: Boolean(result.confidence_base64),
        };
        const block = els.evidenceImage.closest(".result-block");
        if (block) block.hidden = !Object.values(available).some(Boolean);
        $$("[data-evidence]").forEach((button) => {
            button.disabled = !available[button.dataset.evidence];
        });
        if (available.overlay) setEvidence("overlay");
        else if (available.mask) setEvidence("mask");
        else if (available.heatmap) setEvidence("heatmap");
    }

    function wireEvidence() {
        $$("[data-evidence]").forEach((button, index, buttons) => {
            button.addEventListener("click", () => setEvidence(button.dataset.evidence));
            button.addEventListener("keydown", (event) => {
                let target = null;
                if (event.key === "ArrowRight" || event.key === "ArrowDown") {
                    target = buttons[(index + 1) % buttons.length];
                } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
                    target = buttons[(index - 1 + buttons.length) % buttons.length];
                }
                if (target && !target.disabled) {
                    event.preventDefault();
                    target.focus();
                    setEvidence(target.dataset.evidence);
                }
            });
        });
    }

    function metaSpan(label, value) {
        const span = el("span");
        span.appendChild(document.createTextNode(`${label} `));
        span.appendChild(el("b", null, value));
        return span;
    }

    function renderRegions(result) {
        clear(els.regionsList);
        const regions = Array.isArray(result.change_regions) ? result.change_regions : [];
        els.regionCount.textContent = `${regions.length} patch${regions.length === 1 ? "" : "es"}`;
        if (!regions.length) {
            els.regionsList.appendChild(
                el(
                    "p",
                    "region-empty",
                    "No connected patches passed the profile's rules and minimum mapping unit. This does not prove that no change occurred; inspect the change map."
                )
            );
        }
        regions.forEach((region, index) => {
            const card = el("article", "region-card");
            const confidence = String(region.confidence_label || "low").toLowerCase();
            const colors = {
                high: "var(--green)",
                medium: "var(--amber)",
                low: "var(--line-strong)",
            };
            card.style.borderLeftColor = colors[confidence] || colors.low;

            const head = el("div", "region-head");
            head.appendChild(el("span", "region-title", `${index + 1}. ${region.change_type || "Unclassified change"}`));
            const badge = el("span", `region-badge is-${["high", "medium", "low"].includes(confidence) ? confidence : "low"}`, region.confidence_label || "Low");
            head.appendChild(badge);
            card.appendChild(head);

            const meta = el("div", "region-meta");
            const pixelArea = Number(region.pixel_area);
            let areaText = Number.isFinite(pixelArea) ? `${pixelArea.toLocaleString()} px` : "—";
            if (region.area_ha !== undefined && region.area_ha !== null) {
                areaText = `${fmt(region.area_ha, 3)} ha (${areaText})`;
            }
            meta.appendChild(metaSpan("Area:", areaText));
            if (Array.isArray(region.bounding_box) && region.bounding_box.length === 4) {
                const [x, y, width, height] = region.bounding_box;
                meta.appendChild(metaSpan("Box:", `${Math.round(x)}, ${Math.round(y)}, ${Math.round(width)} × ${Math.round(height)}`));
            }
            if (region.stats) {
                if (region.stats.color_shift_mag !== undefined) {
                    meta.appendChild(metaSpan("Colour shift:", fmt(region.stats.color_shift_mag, 1)));
                }
                if (region.stats.veg_ratio_before !== undefined && region.stats.veg_ratio_after !== undefined) {
                    meta.appendChild(
                        metaSpan(
                            "Green ratio:",
                            `${fmt(region.stats.veg_ratio_before, 2)} → ${fmt(region.stats.veg_ratio_after, 2)}`
                        )
                    );
                }
                if (region.stats.brightness_before !== undefined && region.stats.brightness_after !== undefined) {
                    meta.appendChild(
                        metaSpan(
                            "Brightness:",
                            `${fmt(region.stats.brightness_before, 0)} → ${fmt(region.stats.brightness_after, 0)}`
                        )
                    );
                }
            }
            card.appendChild(meta);
            if (region.explanation) {
                const why = el("details", "region-why");
                const summary = el("summary", null, "Why we think this changed");
                why.appendChild(summary);
                why.appendChild(el("p", null, region.explanation));
                card.appendChild(why);
            }
            els.regionsList.appendChild(card);
        });
        renderRoadContext(result);
    }

    function renderRoadContext(result) {
        const context = result.road_context;
        clear(els.roadContext);
        if (!context) {
            els.roadContext.hidden = true;
            return;
        }
        els.roadContext.hidden = false;
        els.roadContext.appendChild(el("strong", null, "Mapped-road context (OpenStreetMap)"));
        els.roadContext.appendChild(
            el(
                "p",
                null,
                `${fmt(context.percent_changed_within_distance, 2)}% of changed pixels are within ${fmt(context.distance_m, 0)} m of a mapped road ` +
                    `(${fmtNumber(context.changed_pixels_near_roads, 0)} of ${fmtNumber(context.total_changed_pixels, 0)} px; ` +
                    `${fmtNumber(context.road_count, 0)} mapped ways, ${fmt(context.mapped_road_km, 1)} km).`
            )
        );
        if (context.note) els.roadContext.appendChild(el("p", "help", context.note));
        if (context.licence) els.roadContext.appendChild(el("p", "help", context.licence));
    }

    function renderProfileNotes(result, isCnn) {
        clear(els.profileNotes);
        const block = els.profileNotes.closest(".result-block");
        let notes = Array.isArray(result.profile_notes) ? result.profile_notes.slice() : [];
        if (isCnn) {
            notes = [
                "Weights were trained on 0.5 m LEVIR-CD aerial pairs; transfer to 10 m Sentinel-2 is not validated here.",
                "Pair mode has no cloud/shadow mask, scene metadata, AOI check or minimum mapping unit.",
                "Decision support, not ground truth. Verify regions against imagery and local knowledge.",
            ];
        }
        if (!notes.length) {
            if (block) block.hidden = true;
            return;
        }
        if (block) block.hidden = false;
        notes.forEach((note) => els.profileNotes.appendChild(el("li", null, note)));
    }

    function buildTimelineDates() {
        if (!state.result || !state.result.date_before || !state.result.date_after) return null;
        const start = parseISO(state.result.date_before);
        const end = parseISO(state.result.date_after);
        const span = Math.round((end - start) / 86400000);
        if (span < 2) return null;
        const count = span >= 4 ? 4 : 3;
        const dates = [];
        for (let index = 0; index < count; index += 1) {
            const offset = Math.round((span * index) / (count - 1));
            const date = addDays(start, offset);
            const value = isoUTC(date);
            if (!dates.includes(value)) dates.push(value);
        }
        return dates.length >= 3 ? dates : null;
    }

    function renderTimelineCard(result, isCnn) {
        clear(els.timelineChart);
        clear(els.timelineStatus);
        els.timelineStatus.hidden = true;
        els.timelineBtn.disabled = false;
        const show = result.profile === "agriculture" && !isCnn;
        els.timelineCard.hidden = !show;
        if (!show) return;
        const dates = buildTimelineDates();
        state.timelineDates = dates;
        if (!dates) {
            els.timelineDates.textContent = "";
            showError(els.timelineStatus, "The selected dates span less than two days; a 3-date timeline needs a wider interval.");
            els.timelineBtn.disabled = true;
            return;
        }
        els.timelineDates.textContent = `Proposed dates: ${dates.join(", ")}.`;
        els.timelineChart.setAttribute("aria-label", "NDVI timeline will appear here after you build it.");
    }

    async function loadTimeline() {
        if (!state.timelineDates || !state.result) return;
        const bbox = (state.result.aoi && state.result.aoi.bbox) || (state.aoi && state.aoi.bbox);
        if (!bbox) {
            showError(els.timelineStatus, "The AOI is unavailable for this result.");
            return;
        }
        const original = els.timelineBtn.textContent;
        els.timelineBtn.disabled = true;
        els.timelineBtn.textContent = "Building timeline…";
        showError(els.timelineStatus, "");
        try {
            const data = await jsonRequest("/timeline", {
                bbox,
                dates: state.timelineDates,
                window_days: 10,
            });
            renderTimeline(data);
        } catch (error) {
            showError(els.timelineStatus, liveErrorMessage(error));
        } finally {
            els.timelineBtn.disabled = false;
            els.timelineBtn.textContent = original;
        }
    }

    function renderTimeline(data) {
        clear(els.timelineChart);
        const points = (data.points || []).filter((point) => Number.isFinite(Number(point.ndvi_mean)));
        if (!points.length) {
            showError(els.timelineStatus, "No valid NDVI values were available; every date was fully masked or missing.");
            return;
        }
        showError(els.timelineStatus, "");
        const width = 720;
        const height = 280;
        const padding = { left: 48, right: 18, top: 18, bottom: 42 };
        const plotWidth = width - padding.left - padding.right;
        const plotHeight = height - padding.top - padding.bottom;
        const values = points.map((point) => Number(point.ndvi_mean));
        let minValue = Math.min(...values);
        let maxValue = Math.max(...values);
        const pad = Math.max(0.05, (maxValue - minValue) * 0.15);
        minValue = Math.max(-1, minValue - pad);
        maxValue = Math.min(1, maxValue + pad);
        if (!(maxValue > minValue)) {
            minValue -= 0.1;
            maxValue += 0.1;
        }
        const x = (index) =>
            padding.left + (points.length === 1 ? plotWidth / 2 : (plotWidth * index) / (points.length - 1));
        const y = (value) =>
            padding.top + plotHeight - ((value - minValue) / (maxValue - minValue)) * plotHeight;

        const svg = svgEl("svg", {
            viewBox: `0 0 ${width} ${height}`,
            role: "img",
            "aria-label": "Mean NDVI by date",
            preserveAspectRatio: "xMidYMid meet",
        });
        for (let tick = 0; tick <= 4; tick += 1) {
            const value = minValue + ((maxValue - minValue) * tick) / 4;
            const yy = y(value);
            svg.appendChild(svgEl("line", { x1: padding.left, y1: yy, x2: width - padding.right, y2: yy, class: "gridline" }));
            const label = svgEl("text", { x: padding.left - 8, y: yy + 4, "text-anchor": "end" });
            label.textContent = value.toFixed(2);
            svg.appendChild(label);
        }
        svg.appendChild(svgEl("line", { x1: padding.left, y1: height - padding.bottom, x2: width - padding.right, y2: height - padding.bottom, class: "axis" }));
        svg.appendChild(svgEl("line", { x1: padding.left, y1: padding.top, x2: padding.left, y2: height - padding.bottom, class: "axis" }));

        const linePoints = points.map((point, index) => `${x(index)},${y(Number(point.ndvi_mean))}`).join(" ");
        svg.appendChild(svgEl("polyline", { points: linePoints, class: "line" }));

        points.forEach((point, index) => {
            const cx = x(index);
            const cy = y(Number(point.ndvi_mean));
            const circle = svgEl("circle", { cx, cy, r: 5, class: "dot" });
            const title = svgEl("title");
            title.textContent =
                `${point.requested_date || point.scene_date}: mean NDVI ${fmt(point.ndvi_mean, 3)}, ` +
                `${fmt(point.valid_percent, 1)}% valid pixels, scene ${point.scene_id || "unknown"}`;
            circle.appendChild(title);
            svg.appendChild(circle);

            const label = svgEl("text", { x: cx, y: height - padding.bottom + 20, "text-anchor": "middle" });
            label.textContent = String(point.requested_date || point.scene_date || "").slice(5);
            const dateTitle = svgEl("title");
            dateTitle.textContent = point.requested_date || point.scene_date || "";
            label.appendChild(dateTitle);
            svg.appendChild(label);
        });

        const axisLabel = svgEl("text", { x: 12, y: 16 });
        axisLabel.textContent = "NDVI";
        svg.appendChild(axisLabel);
        els.timelineChart.appendChild(svg);

        const detail = el("p", "help");
        detail.textContent = points
            .map(
                (point) =>
                    `${point.scene_date || point.requested_date}: NDVI ${fmt(point.ndvi_mean, 3)} (${fmt(point.valid_percent, 1)}% valid)`
            )
            .join(" · ");
        els.timelineChart.appendChild(detail);
        if (data.note) {
            const note = el("p", "help", data.note);
            els.timelineChart.appendChild(note);
        }
        els.timelineChart.setAttribute(
            "aria-label",
            "Mean NDVI timeline: " +
                points
                    .map((point) => `${point.requested_date || point.scene_date} ${fmt(point.ndvi_mean, 2)}`)
                    .join(", ")
        );
    }

    function provenanceRows(result) {
        const provenance = result.provenance;
        if (!provenance) return [];
        const rows = [];
        rows.push(["Commit", provenance.commit || "unknown", true]);
        rows.push(["App version", provenance.app_version || "—", false]);
        rows.push(["Pipeline", provenance.pipeline || result.pipeline || "—", false]);
        rows.push(["Profile", provenance.profile || result.profile || "—", false]);
        if (Array.isArray(provenance.scene_ids) && provenance.scene_ids.length) {
            rows.push(["Scene IDs", provenance.scene_ids.join(", "), true]);
        }
        if (provenance.dates && (provenance.dates.before || provenance.dates.after)) {
            rows.push(["Dates", `${provenance.dates.before || "?"} → ${provenance.dates.after || "?"}`, false]);
        }
        if (provenance.aoi && Array.isArray(provenance.aoi.bbox)) {
            rows.push(["AOI bbox", provenance.aoi.bbox.join(", "), true]);
        }
        if (Array.isArray(provenance.pixel_size_m)) {
            rows.push(["Pixel size", `${provenance.pixel_size_m.join(" × ")} m`, false]);
        }
        if (provenance.options) {
            rows.push(["Options", JSON.stringify(provenance.options), false]);
        }
        if (provenance.thresholds) {
            rows.push(["Thresholds", JSON.stringify(provenance.thresholds), false]);
        }
        if (provenance.percent_masked !== undefined && provenance.percent_masked !== null) {
            rows.push(["Masked", pct(provenance.percent_masked), false]);
        }
        if (provenance.timestamp_utc) rows.push(["Timestamp (UTC)", provenance.timestamp_utc, false]);
        return rows;
    }

    function renderProvenance(result, isCnn) {
        clear(els.provenance);
        els.provenanceDetails.textContent = "";
        const block = els.provenance.closest(".result-block");
        if (!result.provenance) {
            if (block) block.hidden = true;
            return;
        }
        if (block) block.hidden = false;
        const rows = provenanceRows(result);
        rows.forEach(([label, value, mono]) => {
            els.provenance.appendChild(el("dt", null, label));
            els.provenance.appendChild(el("dd", mono ? "mono" : null, value));
        });
        if (isCnn && !rows.some((row) => row[0] === "Scene IDs")) {
            els.provenance.appendChild(el("dt", null, "Note"));
            els.provenance.appendChild(el("dd", null, "Pair uploads have no scene IDs, AOI geometry, or cloud mask."));
        }
        try {
            els.provenanceDetails.textContent = JSON.stringify(result.provenance, null, 2);
        } catch (_) {
            els.provenanceDetails.textContent = "Provenance could not be serialised.";
        }
    }

    function wireResults() {
        $("#new-analysis-btn").addEventListener("click", () => {
            state.result = null;
            state.historyId = null;
            setActionAvailability(false);
            updateWizard(state.sceneData ? 2 : 1);
            els.sceneSection.hidden = !state.sceneData;
            scrollTo(state.sceneData ? els.sceneSection : $("#map-heading"));
        });
        els.downloadPdf.addEventListener("click", downloadPdf);
        els.exportGeojson.addEventListener("click", () => exportResult("geojson"));
        els.exportCsv.addEventListener("click", () => exportResult("csv"));
        els.downloadImages.addEventListener("click", downloadImages);
        els.timelineBtn.addEventListener("click", loadTimeline);
        wireCompare();
        wireEvidence();
    }

    async function downloadPdf() {
        if (!state.result) return;
        setBusy(true, "Building the PDF report…");
        try {
            const { blob, response } = await requestBlob("/report", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ result: state.result }),
            });
            const filename = filenameFrom(response, "change-report.pdf");
            const url = URL.createObjectURL(blob);
            triggerDownload(url, filename);
            setTimeout(() => URL.revokeObjectURL(url), 2000);
        } catch (error) {
            toast(`PDF failed: ${error.message}`, "error");
        } finally {
            setBusy(false);
        }
    }

    async function exportResult(format) {
        if (!state.result) return;
        try {
            const { blob, response } = await requestBlob(`/export/${format}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ result: state.result }),
            });
            const fallback = format === "geojson" ? "change-regions.geojson" : "change-regions.csv";
            const url = URL.createObjectURL(blob);
            triggerDownload(url, filenameFrom(response, fallback));
            setTimeout(() => URL.revokeObjectURL(url), 2000);
            toast(`${format.toUpperCase()} export downloaded.`, "success");
        } catch (error) {
            toast(`${format.toUpperCase()} export failed: ${error.message}`, "error");
        }
    }

    function downloadImages() {
        if (!state.result) return;
        const result = state.result;
        const stem = result.date_after ? `change-${result.date_after}` : "change-pair";
        const images = [
            ["before", result.image_a_base64],
            ["after", result.image_b_base64],
            ["mask", result.mask_base64],
            ["overlay", result.overlay_base64],
            ["rule-evidence", result.confidence_base64],
        ].filter(([, base64]) => base64);
        if (!images.length) {
            toast("No images are available for this result.", "error");
            return;
        }
        images.forEach(([name, base64], index) => {
            setTimeout(() => triggerDownload(dataUrl(base64), `${stem}-${name}.png`), index * 250);
        });
        toast(`Downloading ${images.length} image${images.length === 1 ? "" : "s"}.`, "success");
    }

    /* ── Upload mode ─────────────────────────────────────────────────────── */

    function setPreview(input, preview, box) {
        const file = input.files && input.files[0];
        if (!file) {
            preview.hidden = true;
            preview.removeAttribute("src");
            box.classList.remove("has-file");
            return;
        }
        if (!file.type.startsWith("image/")) {
            showError(els.uploadError, "Choose an image file (PNG or JPEG).");
            input.value = "";
            return;
        }
        const reader = new FileReader();
        reader.onload = () => {
            preview.src = String(reader.result);
            preview.hidden = false;
            box.classList.add("has-file");
        };
        reader.readAsDataURL(file);
    }

    function updateUploadButton() {
        const a = els.imageA.files && els.imageA.files.length;
        const b = els.imageB.files && els.imageB.files.length;
        els.uploadSubmit.disabled = !(a && b);
    }

    function wireUpload() {
        els.imageA.addEventListener("change", () => {
            showError(els.uploadError, "");
            setPreview(els.imageA, els.previewA, els.boxA);
            updateUploadButton();
        });
        els.imageB.addEventListener("change", () => {
            showError(els.uploadError, "");
            setPreview(els.imageB, els.previewB, els.boxB);
            updateUploadButton();
        });
        updateUploadButton();
        els.uploadForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            showError(els.uploadError, "");
            if (!els.imageA.files.length || !els.imageB.files.length) {
                showError(els.uploadError, "Choose both a before and an after image.");
                return;
            }
            const formData = new FormData();
            formData.append("image_a", els.imageA.files[0]);
            formData.append("image_b", els.imageB.files[0]);
            setBusy(true, "Comparing your two images…");
            try {
                const result = await request("/predict", { method: "POST", body: formData });
                state.historyLoaded = false;
                state.historyId = result.history_id ?? null;
                activateTab("live");
                renderResult(result);
                scrollTo(els.resultsSection);
            } catch (error) {
                showError(els.uploadError, liveErrorMessage(error));
                scrollTo(els.uploadError);
            } finally {
                setBusy(false);
            }
        });
    }

    /* ── History ─────────────────────────────────────────────────────────── */

    async function loadHistory(force = false) {
        if (state.historyLoaded && !force) return;
        showError(els.historyStatus, "");
        if (!els.historyList.childElementCount) {
            els.historyList.appendChild(el("p", "history-empty", "Loading history…"));
        }
        try {
            const rows = await request("/history");
            state.historyLoaded = true;
            renderHistory(Array.isArray(rows) ? rows : []);
        } catch (error) {
            showError(els.historyStatus, error.message || "History could not be loaded.");
            clear(els.historyList);
        }
    }

    function formatTimestamp(value) {
        if (!value) return "unknown time";
        const date = new Date(value);
        return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
    }

    function renderChartRows(container, items, ceiling) {
        clear(container);
        const max = Math.max(Number(ceiling) || 0, 1);
        items.forEach((item) => {
            const row = el("div", "chart-row");
            row.setAttribute("role", "listitem");
            const label = el("span", "chart-label", item.label);
            if (item.title) label.title = item.title;
            row.appendChild(label);
            row.appendChild(el("span", "chart-value", item.valueText));
            const track = el("span", "chart-track");
            track.setAttribute("aria-hidden", "true");
            const bar = el("span", "chart-bar");
            const width = item.value > 0 ? Math.max(2, (item.value / max) * 100) : 0;
            bar.style.width = `${Math.min(100, width)}%`;
            track.appendChild(bar);
            row.appendChild(track);
            container.appendChild(row);
        });
    }

    function renderHistoryDashboard(rows) {
        if (!els.historyDashboard) return;
        if (!rows.length) {
            els.historyDashboard.hidden = true;
            return;
        }
        els.historyDashboard.hidden = false;

        const values = rows.map((row) => {
            const value = Number(row.percent_changed);
            return Number.isFinite(value) ? Math.max(0, value) : 0;
        });
        const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
        const largest = Math.max(...values);
        const uploads = rows.filter((row) => row.pipeline === "cnn").length;
        const live = rows.length - uploads;

        els.historyDashboardCount.textContent =
            `${rows.length} saved ${rows.length === 1 ? "analysis" : "analyses"} · most recent first`;

        clear(els.historyStats);
        [
            { label: "Saved analyses", value: String(rows.length), note: "in the local database" },
            { label: "Live / image pair", value: `${live} / ${uploads}`, note: "from the saved pipeline" },
            { label: "Average flagged", value: pct(mean), note: "simple mean, not area-weighted" },
            { label: "Largest flagged", value: pct(largest), note: "single saved analysis" },
        ].forEach((stat) => {
            const wrapper = el("div", "dashboard-stat");
            wrapper.appendChild(el("dt", null, stat.label));
            const value = el("dd", null, stat.value);
            value.appendChild(el("span", "stat-note", stat.note));
            wrapper.appendChild(value);
            els.historyStats.appendChild(wrapper);
        });

        const recent = rows.slice(0, 10);
        renderChartRows(
            els.historyRecentChart,
            recent.map((row, index) => ({
                label: `#${row.id} · ${row.location || (row.pipeline === "cnn" ? "Image pair" : "Live analysis")}`,
                value: values[index],
                valueText: pct(values[index]),
                title: formatTimestamp(row.created_at),
            })),
            Math.max(...values.slice(0, 10), 0)
        );

        const ranges = [
            { label: "Under 1%", count: values.filter((value) => value < 1).length },
            { label: "1% to under 5%", count: values.filter((value) => value >= 1 && value < 5).length },
            { label: "5% to under 10%", count: values.filter((value) => value >= 5 && value < 10).length },
            { label: "10% or more", count: values.filter((value) => value >= 10).length },
        ];
        renderChartRows(
            els.historyRangeChart,
            ranges.map((range) => ({
                label: range.label,
                value: range.count,
                valueText: `${range.count} ${range.count === 1 ? "analysis" : "analyses"}`,
            })),
            Math.max(...ranges.map((range) => range.count), 0)
        );
    }

    function renderHistory(rows) {
        renderHistoryDashboard(rows);
        clear(els.historyList);
        if (!rows.length) {
            els.historyList.appendChild(el("p", "history-empty", "No analyses yet. Run one from the live Sentinel-2 tab."));
            return;
        }
        rows.forEach((row) => {
            const item = el("div", "history-item");
            const main = el("div", "history-item-main");
            main.appendChild(
                el("div", "history-item-title", row.location || (row.pipeline === "cnn" ? "Uploaded image pair" : "Live analysis"))
            );
            main.appendChild(
                el(
                    "div",
                    "history-item-meta",
                    `#${row.id} · ${formatTimestamp(row.created_at)} · ${row.pipeline || "unknown"} · ${fmt(row.percent_changed, 2)}% flagged`
                )
            );
            item.appendChild(main);

            const open = el("button", "button button-quiet", "Open");
            open.type = "button";
            open.addEventListener("click", () => openHistory(row.id));
            item.appendChild(open);

            ["geojson", "csv"].forEach((format) => {
                const button = el("button", "button button-quiet", format.toUpperCase());
                button.type = "button";
                button.addEventListener("click", () => exportHistory(row.id, format));
                item.appendChild(button);
            });
            els.historyList.appendChild(item);
        });
    }

    async function openHistory(id) {
        setBusy(true, `Loading analysis #${id}…`);
        try {
            const item = await request(`/history/${id}`);
            state.historyId = id;
            activateTab("live");
            renderResult(item.result);
            updateWizard(3);
            scrollTo(els.resultsSection);
        } catch (error) {
            showError(els.historyStatus, error.message || "The analysis could not be opened.");
        } finally {
            setBusy(false);
        }
    }

    async function exportHistory(id, format) {
        try {
            const { blob, response } = await requestBlob(`/history/${id}/export/${format}`);
            const fallback = format === "geojson" ? `analysis-${id}.geojson` : `analysis-${id}.csv`;
            const url = URL.createObjectURL(blob);
            triggerDownload(url, filenameFrom(response, fallback));
            setTimeout(() => URL.revokeObjectURL(url), 2000);
        } catch (error) {
            toast(`Export failed: ${error.message}`, "error");
        }
    }

    function wireHistory() {
        $("#refresh-history-btn").addEventListener("click", () => loadHistory(true));
    }

    /* ── Theme, honesty note and hint tour ────────────────────────────────── */

    function applyTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        els.themeToggle.setAttribute(
            "aria-label",
            theme === "dark" ? "Switch to light theme" : "Switch to dark theme"
        );
        try {
            localStorage.setItem("scd-theme", theme);
        } catch (_) {
            /* storage unavailable; theme simply won't persist */
        }
    }

    function wireThemeToggle() {
        els.themeToggle.addEventListener("click", () => {
            applyTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark");
        });
        let saved = null;
        try {
            saved = localStorage.getItem("scd-theme");
        } catch (_) {
            /* storage unavailable */
        }
        const preferred =
            saved ||
            (window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
        applyTheme(preferred);
    }

    function wireHonestyNote() {
        els.learnMoreBtn.addEventListener("click", () => {
            const open = els.learnMore.hidden;
            els.learnMore.hidden = !open;
            els.learnMoreBtn.setAttribute("aria-expanded", String(open));
            els.learnMoreBtn.textContent = open ? "Hide" : "Learn more";
        });
    }

    const HINT_TOUR = [
        "Start by drawing a small box on the map around the place you care about — or search for it by name.",
        "Then pick the two dates you want to compare, and tell us what kind of change you are looking for.",
        "We list the clearest satellite images near each date, then show what changed — with an honest data-quality check.",
    ];

    function wireHintTour() {
        let shown = false;
        try {
            shown = localStorage.getItem("scd-hint-tour-done") === "1";
        } catch (_) {
            /* storage unavailable */
        }
        const smallScreen = window.innerWidth < 640;
        if (shown || smallScreen) return;

        let step = 0;
        const render = () => {
            els.hintStepCount.textContent = `Tip ${step + 1} of ${HINT_TOUR.length}`;
            els.hintText.textContent = HINT_TOUR[step];
            els.hintNext.textContent = step === HINT_TOUR.length - 1 ? "Finish" : "Next";
        };
        const close = () => {
            els.hintTour.hidden = true;
            try {
                localStorage.setItem("scd-hint-tour-done", "1");
            } catch (_) {
                /* storage unavailable */
            }
        };
        els.hintNext.addEventListener("click", () => {
            if (step >= HINT_TOUR.length - 1) {
                close();
            } else {
                step += 1;
                render();
            }
        });
        els.hintSkip.addEventListener("click", close);
        render();
        els.hintTour.hidden = false;
    }

    /* ── Init ────────────────────────────────────────────────────────────── */

    function init() {
        document.body.dataset.view = "live";
        wireThemeToggle();
        wireHonestyNote();
        wireTabs();
        initDates();
        initMap();
        wireMapActions();
        wireWizard();
        wirePresetsAndExample();
        wireGoalPicker();
        wireSearch();
        wireLiveForm();
        wireResults();
        wireUpload();
        wireHistory();
        setActionAvailability(false);
        updateFindButton();
        updateWizard(1);
        loadConfig();
        checkHealth();
        wireHintTour();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
