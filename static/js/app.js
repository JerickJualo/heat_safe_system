(function () {
    "use strict";

    const API_BASE = "/api";
    const COLORS = ["#f97316", "#38bdf8", "#ef4444", "#5eead4"];

    const $ = (selector, root = document) => root.querySelector(selector);
    const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

    function escapeHtml(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function formatHeat(value) {
        return value === null || value === undefined || value === "" || Number.isNaN(Number(value))
            ? "—"
            : `${Number(value).toFixed(1)}°C`;
    }

    function formatNumber(value, digits = 0) {
        return value === null || value === undefined || Number.isNaN(Number(value))
            ? "—"
            : Number(value).toLocaleString(undefined, { maximumFractionDigits: digits });
    }

    function formatDate(value) {
        if (!value) return "—";
        const date = new Date(`${value}T00:00:00`);
        return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
    }

    function riskClass(category) {
        const value = String(category || "").toLowerCase().replaceAll("_", "-").replaceAll(" ", "-");
        if (value.includes("extreme-danger")) return "risk-extreme-danger";
        if (value === "danger" || value.endsWith("-danger")) return "risk-danger";
        if (value.includes("extreme-caution")) return "risk-extreme-caution";
        if (value.includes("caution")) return "risk-caution";
        return "risk-neutral";
    }

    function riskBadge(category) {
        const label = category || "Unavailable";
        return `<span class="risk-badge ${riskClass(category)}">${escapeHtml(label)}</span>`;
    }

    async function fetchJson(path, options = {}) {
        const response = await fetch(`${API_BASE}${path}`, { headers: { Accept: "application/json" }, ...options });
        let payload;
        try { payload = await response.json(); } catch (error) { throw new Error(`The server returned an unreadable response (${response.status}).`); }
        if (!response.ok) throw new Error(payload.error || `Request failed (${response.status}).`);
        return payload;
    }

    function showError(element, message) {
        if (!element) return;
        element.textContent = message;
        element.hidden = false;
    }

    function hide(element) { if (element) element.hidden = true; }
    function setLoading(element, visible) { if (element) element.hidden = !visible; }

    function setOptions(select, locations, includeAll = true) {
        if (!select) return;
        const current = select.value;
        const prefix = includeAll ? '<option value="">All locations</option>' : '<option value="">Select a location</option>';
        select.innerHTML = prefix + locations.map(location => `<option value="${escapeHtml(location.slug)}">${escapeHtml(location.name)}</option>`).join("");
        if (locations.some(location => location.slug === current)) select.value = current;
    }

    function groupBy(records, key) {
        return records.reduce((groups, record) => {
            const value = record[key];
            (groups[value] ||= []).push(record);
            return groups;
        }, {});
    }

    function renderLineChart(container, series) {
        if (!container) return;
        const validSeries = series.map(item => ({ ...item, points: item.points.filter(point => point.value !== null && point.value !== undefined) })).filter(item => item.points.length);
        if (!validSeries.length) { container.innerHTML = '<div class="empty-state">No complete records match this selection.</div>'; return; }
        const width = 900, height = 300, left = 48, right = 18, top = 18, bottom = 34;
        const values = validSeries.flatMap(item => item.points.map(point => Number(point.value))).filter(Number.isFinite);
        const rawMin = Math.min(...values), rawMax = Math.max(...values);
        const spread = Math.max(rawMax - rawMin, 2);
        const min = Math.floor(rawMin - spread * .08), max = Math.ceil(rawMax + spread * .08);
        const plotWidth = width - left - right, plotHeight = height - top - bottom;
        const maxPoints = Math.max(...validSeries.map(item => item.points.length));
        const x = index => left + (maxPoints <= 1 ? plotWidth / 2 : (index / (maxPoints - 1)) * plotWidth);
        const y = value => top + ((max - value) / (max - min)) * plotHeight;
        const grid = [0, .25, .5, .75, 1].map(fraction => {
            const value = min + (max - min) * (1 - fraction);
            const yPosition = top + plotHeight * fraction;
            return `<line class="chart-grid-line" x1="${left}" x2="${width - right}" y1="${yPosition}" y2="${yPosition}"></line><text class="chart-axis-label" x="4" y="${yPosition + 4}">${value.toFixed(0)}°</text>`;
        }).join("");
        const paths = validSeries.map((item, index) => {
            const color = COLORS[index % COLORS.length];
            const points = item.points.map((point, pointIndex) => `${x(pointIndex).toFixed(1)},${y(Number(point.value)).toFixed(1)}`).join(" ");
            return `<polyline fill="none" stroke="${color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" points="${points}"></polyline>`;
        }).join("");
        const labels = validSeries.map((item, index) => `<span class="legend-item"><span class="legend-swatch" style="background:${COLORS[index % COLORS.length]}"></span>${escapeHtml(item.label)}</span>`).join("");
        container.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Heat index line chart">${grid}${paths}</svg><div class="chart-legend">${labels}</div>`;
    }

    function renderBarChart(container, items) {
        if (!container) return;
        const valid = items.filter(item => Number(item.value) > 0);
        if (!valid.length) { container.innerHTML = '<div class="empty-state">No risk classifications are available.</div>'; return; }
        const width = 600, height = 260, left = 150, right = 26, top = 20, barHeight = 28, gap = 16;
        const max = Math.max(...valid.map(item => Number(item.value)), 1);
        const available = width - left - right;
        const bars = valid.map((item, index) => {
            const y = top + index * (barHeight + gap);
            const barWidth = (Number(item.value) / max) * available;
            const color = COLORS[index % COLORS.length];
            return `<text class="chart-axis-label" x="0" y="${y + 19}">${escapeHtml(item.label)}</text><rect x="${left}" y="${y}" width="${Math.max(barWidth, 2)}" height="${barHeight}" rx="6" fill="${color}" opacity=".82"></rect><text class="chart-axis-label" x="${Math.min(left + barWidth + 8, width - 24)}" y="${y + 19}">${item.value}</text>`;
        }).join("");
        container.innerHTML = `<svg viewBox="0 0 ${width} ${Math.max(height, top + valid.length * (barHeight + gap))}" role="img" aria-label="Risk classification bar chart">${bars}</svg>`;
    }

    function renderScatterChart(container, points) {
        if (!container || !points.length) { if (container) container.innerHTML = '<div class="empty-state">No held-out prediction records are available.</div>'; return; }
        const width = 600, height = 300, left = 48, right = 18, top = 18, bottom = 34;
        const values = points.flatMap(point => [Number(point.actual), Number(point.predicted)]).filter(Number.isFinite);
        const rawMin = Math.min(...values), rawMax = Math.max(...values), spread = Math.max(rawMax - rawMin, 2);
        const min = Math.floor(rawMin - spread * .08), max = Math.ceil(rawMax + spread * .08);
        const plotWidth = width - left - right, plotHeight = height - top - bottom;
        const scaleX = value => left + ((value - min) / (max - min)) * plotWidth;
        const scaleY = value => top + ((max - value) / (max - min)) * plotHeight;
        const grid = [0, .25, .5, .75, 1].map(fraction => {
            const value = min + (max - min) * (1 - fraction), yPosition = top + plotHeight * fraction;
            const xPosition = left + plotWidth * fraction;
            return `<line class="chart-grid-line" x1="${left}" x2="${width - right}" y1="${yPosition}" y2="${yPosition}"></line><line class="chart-grid-line" x1="${xPosition}" x2="${xPosition}" y1="${top}" y2="${height - bottom}"></line><text class="chart-axis-label" x="4" y="${yPosition + 4}">${value.toFixed(0)}°</text>`;
        }).join("");
        const diagonal = `<line x1="${scaleX(min)}" y1="${scaleY(min)}" x2="${scaleX(max)}" y2="${scaleY(max)}" stroke="#8fa7b9" stroke-dasharray="5 5" opacity=".7"></line>`;
        const dots = points.map(point => `<circle cx="${scaleX(Number(point.actual)).toFixed(1)}" cy="${scaleY(Number(point.predicted)).toFixed(1)}" r="2.3" fill="#f97316" opacity=".42"></circle>`).join("");
        container.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Actual versus predicted scatter chart">${grid}${diagonal}${dots}<text class="chart-axis-label" x="${width / 2 - 28}" y="${height - 5}">Actual °C</text><text class="chart-axis-label" transform="translate(12 ${height / 2 + 28}) rotate(-90)">Predicted °C</text></svg>`;
    }

    function locationSeries(records, selectedSlug = "") {
        const groups = groupBy(selectedSlug ? records.filter(record => record.location === selectedSlug) : records, "location");
        return Object.entries(groups).sort((a, b) => a[0].localeCompare(b[0])).map(([slug, items], index) => ({
            label: items[0].location_name || slug,
            points: items.sort((a, b) => a.date.localeCompare(b.date)).map(item => ({ date: item.date, value: item.maximum_daytime_heat_index })),
            color: COLORS[index % COLORS.length],
        }));
    }

    async function initDashboard() {
        const loading = $("#dashboard-loading"), error = $("#dashboard-error"), filter = $("#dashboard-location-filter");
        setLoading(loading, true);
        try {
            const [dashboard, analytics] = await Promise.all([
                fetchJson("/dashboard/"),
                fetchJson("/analytics/?start_date=2017-01-01&end_date=2026-12-31&limit=10000"),
            ]);
            const locations = dashboard.locations || [];
            setOptions(filter, locations, true);
            const render = () => {
                const selected = filter.value;
                const visible = locations.filter(location => !selected || location.slug === selected);
                $("#dashboard-cards").innerHTML = visible.map(location => {
                    const summary = location.latest_summary;
                    const prediction = location.latest_prediction;
                    return `<article class="metric-card"><span class="metric-label">${escapeHtml(location.name)}</span><strong>${formatHeat(summary?.maximum_daytime_heat_index)}</strong><span class="metric-caption">${formatDate(summary?.date)} · ${riskBadge(summary?.daily_risk_category)}</span><span class="metric-caption">Next prediction: ${formatHeat(prediction?.predicted_heat_index_celsius)}</span></article>`;
                }).join("") || '<div class="empty-state">No active locations are available.</div>';
                const recent = visible.map(location => ({ location, summary: location.latest_summary })).filter(item => item.summary).sort((a, b) => (b.summary.date || "").localeCompare(a.summary.date || ""));
                $("#dashboard-latest-table").innerHTML = recent.map(item => `<tr><td>${escapeHtml(item.location.name)}</td><td>${formatDate(item.summary.date)}</td><td>${formatHeat(item.summary.maximum_daytime_heat_index)}</td><td>${riskBadge(item.summary.daily_risk_category)}</td></tr>`).join("") || '<tr><td colspan="4">No complete observations available.</td></tr>';
                renderLineChart($("#dashboard-trend-chart"), locationSeries(analytics.records || [], selected));
                $("#dashboard-updated").textContent = `${analytics.count || 0} complete daily records available`;
            };
            filter.addEventListener("change", render);
            render();
        } catch (requestError) { showError(error, requestError.message); }
        finally { setLoading(loading, false); }
    }

    async function initAnalytics() {
        const loading = $("#analytics-loading"), error = $("#analytics-error"), locationSelect = $("#analytics-location"), apply = $("#analytics-apply");
        setLoading(loading, true);
        try {
            const dashboard = await fetchJson("/dashboard/");
            setOptions(locationSelect, dashboard.locations || [], true);
            const load = async () => {
                setLoading(loading, true); hide(error);
                try {
                    const params = new URLSearchParams({ limit: "10000" });
                    if (locationSelect.value) params.set("location", locationSelect.value);
                    if ($("#analytics-start").value) params.set("start_date", $("#analytics-start").value);
                    if ($("#analytics-end").value) params.set("end_date", $("#analytics-end").value);
                    const payload = await fetchJson(`/analytics/?${params.toString()}`);
                    const records = payload.records || [];
                    const values = records.map(record => Number(record.maximum_daytime_heat_index)).filter(Number.isFinite);
                    const dangerCount = records.filter(record => ["danger", "extreme danger"].includes(String(record.daily_risk_category || "").toLowerCase())).length;
                    $("#analytics-record-count").textContent = formatNumber(records.length);
                    $("#analytics-mean-hi").textContent = values.length ? formatHeat(values.reduce((a, b) => a + b, 0) / values.length) : "—";
                    $("#analytics-peak-hi").textContent = values.length ? formatHeat(Math.max(...values)) : "—";
                    $("#analytics-high-risk-days").textContent = formatNumber(dangerCount);
                    $("#analytics-range-label").textContent = records.length ? `${formatDate(records[0].date)} – ${formatDate(records[records.length - 1].date)}` : "No matching records";
                    renderLineChart($("#analytics-chart"), locationSeries(records));
                    const riskCounts = records.reduce((counts, record) => { const risk = record.daily_risk_category || "Unavailable"; counts[risk] = (counts[risk] || 0) + 1; return counts; }, {});
                    renderBarChart($("#analytics-risk-chart"), Object.entries(riskCounts).map(([label, value]) => ({ label, value })));
                    $("#analytics-table").innerHTML = records.slice(0, 100).map(record => `<tr><td>${escapeHtml(record.location_name)}</td><td>${formatDate(record.date)}</td><td>${formatHeat(record.maximum_daytime_heat_index)}</td><td>${formatHeat(record.average_heat_index)}</td><td>${riskBadge(record.daily_risk_category)}</td><td>${escapeHtml(record.data_quality_flag || "—")}</td></tr>`).join("") || '<tr><td colspan="6">No complete records match these filters.</td></tr>';
                } catch (requestError) { showError(error, requestError.message); }
                finally { setLoading(loading, false); }
            };
            apply.addEventListener("click", load);
            locationSelect.addEventListener("change", load);
            await load();
        } catch (requestError) { showError(error, requestError.message); setLoading(loading, false); }
    }

    async function initPrediction() {
        const loading = $("#prediction-loading"), error = $("#prediction-error"), select = $("#prediction-location"), card = $("#prediction-card");
        setLoading(loading, true);
        try {
            const [dashboard, payload] = await Promise.all([fetchJson("/dashboard/"), fetchJson("/predictions/?limit=365")]);
            setOptions(select, dashboard.locations || [], false);
            const records = payload.records || [];
            const render = () => {
                const filtered = records.filter(record => !select.value || record.location === select.value);
                const latest = filtered[0];
                if (latest) {
                    card.hidden = false;
                    $("#prediction-location-name").textContent = latest.location_name;
                    $("#prediction-date").textContent = `Target date · ${formatDate(latest.target_date)} · feature date ${formatDate(latest.feature_date)}`;
                    $("#prediction-value").textContent = formatHeat(latest.predicted_heat_index_celsius);
                    $("#prediction-model").textContent = latest.model_name;
                } else { card.hidden = true; }
                $("#prediction-table").innerHTML = filtered.map(record => `<tr><td>${escapeHtml(record.location_name)}</td><td>${formatDate(record.feature_date)}</td><td>${formatDate(record.target_date)}</td><td>${formatHeat(record.predicted_heat_index_celsius)}</td><td>${escapeHtml(record.model_name)}</td></tr>`).join("") || '<tr><td colspan="5">No stored prediction records match this selection.</td></tr>';
            };
            select.addEventListener("change", render); render();
        } catch (requestError) { showError(error, requestError.message); }
        finally { setLoading(loading, false); }
    }

    async function initComparison() {
        const loading = $("#comparison-loading"), error = $("#comparison-error"), dateInput = $("#comparison-date"), apply = $("#comparison-apply");
        const render = payload => {
            const locations = payload.locations || [];
            dateInput.value = payload.date || "";
            $("#comparison-note").textContent = `${locations.length} locations with complete data on this date`;
            $("#comparison-date-label").textContent = formatDate(payload.date);
            $("#comparison-cards").innerHTML = locations.map(item => `<article class="metric-card"><span class="metric-label">${escapeHtml(item.location_name)}</span><strong>${formatHeat(item.maximum_daytime_heat_index)}</strong><span class="metric-caption">${riskBadge(item.daily_risk_category)}</span></article>`).join("") || '<div class="empty-state">No locations returned for this date.</div>';
            $("#comparison-table").innerHTML = [...locations].sort((a, b) => Number(b.maximum_daytime_heat_index || -Infinity) - Number(a.maximum_daytime_heat_index || -Infinity)).map(item => `<tr><td>${escapeHtml(item.location_name)}</td><td>${formatHeat(item.maximum_daytime_heat_index)}</td><td>${riskBadge(item.daily_risk_category)}</td></tr>`).join("") || '<tr><td colspan="3">No records returned.</td></tr>';
            renderBarChart($("#comparison-chart"), locations.map(item => ({ label: item.location_name, value: Number(item.maximum_daytime_heat_index) || 0 })));
        };
        const load = async (requestedDate = "") => {
            setLoading(loading, true); hide(error);
            try { render(await fetchJson(requestedDate ? `/locations/compare/?date=${encodeURIComponent(requestedDate)}` : "/locations/compare/")); }
            catch (requestError) { showError(error, requestError.message); }
            finally { setLoading(loading, false); }
        };
        apply.addEventListener("click", () => load(dateInput.value));
        await load();
    }

    async function initPerformance() {
        const loading = $("#performance-loading"), error = $("#performance-error");
        setLoading(loading, true);
        try {
            const payload = await fetchJson("/model-performance/");
            const metrics = payload.metrics || [];
            const selected = payload.selected_model || "—";
            const testMetric = metrics.find(metric => metric.model_name === selected && metric.split === "test_refit_train_validation");
            $("#performance-selected-model").textContent = selected.replaceAll("_", " ");
            $("#performance-test-mae").textContent = testMetric ? formatHeat(testMetric.mae) : "—";
            $("#performance-test-rmse").textContent = testMetric ? formatHeat(testMetric.rmse) : "—";
            $("#performance-test-r2").textContent = testMetric ? Number(testMetric.r2).toFixed(3) : "—";
            $("#performance-prediction-count").textContent = `${formatNumber(payload.test_prediction_count)} held-out rows`;
            $("#performance-metrics-table").innerHTML = metrics.map(metric => `<tr><td>${escapeHtml(metric.model_name.replaceAll("_", " "))}</td><td>${escapeHtml(metric.split)}</td><td>${formatNumber(metric.row_count)}</td><td>${formatHeat(metric.mae)}</td><td>${formatHeat(metric.rmse)}</td><td>${Number(metric.r2).toFixed(3)}</td></tr>`).join("") || '<tr><td colspan="6">No model evaluation records are available.</td></tr>';
            const points = (payload.predictions || []).filter(point => Number.isFinite(Number(point.actual)) && Number.isFinite(Number(point.predicted)));
            renderScatterChart($("#performance-scatter-chart"), points);
        } catch (requestError) { showError(error, requestError.message); }
        finally { setLoading(loading, false); }
    }

    function updateExportLink() {
        const params = new URLSearchParams();
        if ($("#report-location").value) params.set("location", $("#report-location").value);
        if ($("#report-start").value) params.set("start_date", $("#report-start").value);
        if ($("#report-end").value) params.set("end_date", $("#report-end").value);
        const query = params.toString();
        $("#report-csv-link").href = `/api/export/daily.csv${query ? `?${query}` : ""}`;
    }

    async function initReports() {
        const loading = $("#reports-loading"), error = $("#reports-error"), locationSelect = $("#report-location");
        setLoading(loading, true);
        try {
            const [report, dashboard] = await Promise.all([fetchJson("/report/"), fetchJson("/dashboard/")]);
            setOptions(locationSelect, dashboard.locations || [], true);
            const counts = report.counts || {};
            const countLabels = [["locations", "Active locations"], ["weather_records", "Hourly weather records"], ["heat_index_records", "Heat-index records"], ["daily_summaries", "Daily summaries"], ["predictions", "Stored predictions"]];
            $("#report-counts").innerHTML = countLabels.map(([key, label]) => `<article class="metric-card"><span class="metric-label">${label}</span><strong>${formatNumber(counts[key])}</strong><span class="metric-caption">PostgreSQL record count</span></article>`).join("");
            const source = report.data_source || {};
            $("#report-source-details").innerHTML = Object.entries(source).map(([key, value]) => `<dt>${escapeHtml(key.replaceAll("_", " "))}</dt><dd>${escapeHtml(value)}</dd>`).join("");
            const methodology = report.methodology || {};
            $("#report-methodology").innerHTML = Object.entries(methodology).map(([key, value]) => `<dt>${escapeHtml(key.replaceAll("_", " "))}</dt><dd>${escapeHtml(value)}</dd>`).join("");
            $("#report-limitations").innerHTML = (report.limitations || []).map(item => `<li>${escapeHtml(item)}</li>`).join("");
            [locationSelect, $("#report-start"), $("#report-end")].forEach(element => element.addEventListener("change", updateExportLink));
            updateExportLink();
        } catch (requestError) { showError(error, requestError.message); }
        finally { setLoading(loading, false); }
    }

    function initShell() {
        const currentDate = $("#current-date");
        if (currentDate) currentDate.textContent = new Intl.DateTimeFormat("en-PH", { dateStyle: "medium", timeZone: "Asia/Manila" }).format(new Date());
        const toggle = $("#menu-toggle"), sidebar = $("#app-sidebar");
        if (toggle && sidebar) toggle.addEventListener("click", () => { const open = sidebar.classList.toggle("is-open"); toggle.setAttribute("aria-expanded", String(open)); });
        $$(".nav-link").forEach(link => link.addEventListener("click", () => { sidebar?.classList.remove("is-open"); toggle?.setAttribute("aria-expanded", "false"); }));
    }

    document.addEventListener("DOMContentLoaded", () => {
        initShell();
        const page = document.body.dataset.page;
        if (page === "dashboard") initDashboard();
        if (page === "analytics") initAnalytics();
        if (page === "prediction") initPrediction();
        if (page === "comparison") initComparison();
        if (page === "performance") initPerformance();
        if (page === "reports") initReports();
    });
})();
