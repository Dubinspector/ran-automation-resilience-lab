DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>
    RAN Automation & Resilience Lab
</title>


<style>

* {
    box-sizing: border-box;
}

html {
    scroll-behavior: smooth;
}

body {
    margin: 0;

    font-family:
        Inter,
        Arial,
        sans-serif;

    background: #0f172a;
    color: #e2e8f0;
}

header {
    padding: 24px 32px;

    background:
        linear-gradient(
            135deg,
            #111827,
            #1e293b
        );

    border-bottom:
        1px solid #334155;
}

header h1 {
    margin: 0;
    font-size: 29px;
}

header p {
    margin: 8px 0 0;

    color: #94a3b8;

    line-height: 1.5;
}

.container {
    max-width: 1500px;
    margin: auto;
    padding: 26px;
}

.section {
    margin-top: 28px;
}

.section h2 {
    margin:
        0
        0
        8px;
}

.section-note {
    margin-bottom: 14px;

    color: #94a3b8;

    font-size: 13px;

    line-height: 1.5;
}


/* ===================================================== */
/* BANNER */
/* ===================================================== */

.banner {
    padding: 18px;

    border-radius: 10px;

    margin-bottom: 16px;

    font-size: 21px;

    font-weight: bold;

    border:
        1px solid #334155;
}

.banner-good {
    background: #052e16;
    color: #86efac;
}

.banner-warning {
    background: #431407;
    color: #fdba74;
}

.banner-bad {
    background: #450a0a;
    color: #fca5a5;
}


/* ===================================================== */
/* SUMMARY */
/* ===================================================== */

.summary-grid {
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(160px, 1fr)
        );

    gap: 12px;
}

.summary-card {
    padding: 16px;

    background: #1e293b;

    border:
        1px solid #334155;

    border-radius: 9px;
}

.summary-label {
    color: #94a3b8;

    font-size: 11px;

    text-transform: uppercase;
}

.summary-value {
    margin-top: 6px;

    font-size: 20px;

    font-weight: bold;
}


/* ===================================================== */
/* LIVE OPERATIONAL CONTEXT */
/* ===================================================== */

.context-grid {
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(360px, 1fr)
        );

    gap: 12px;
}

.context-panel {
    padding: 16px;

    background: #111827;

    border:
        1px solid #334155;

    border-radius: 9px;
}

.context-header {
    display: flex;

    align-items: center;

    justify-content: space-between;

    gap: 10px;

    margin-bottom: 12px;
}

.context-title {
    font-size: 16px;

    font-weight: bold;
}

.context-fields {
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(145px, 1fr)
        );

    gap: 9px;
}

.context-field {
    padding: 10px;

    background: #172033;

    border:
        1px solid #334155;

    border-radius: 6px;
}

.context-field-label {
    color: #94a3b8;

    font-size: 10px;

    text-transform: uppercase;
}

.context-field-value {
    margin-top: 5px;

    font-size: 15px;

    font-weight: bold;

    overflow-wrap: anywhere;
}

.context-wide {
    grid-column: 1 / -1;
}


/* ===================================================== */
/* INFO / ARCHITECTURE */
/* ===================================================== */

.info-panel {
    margin-top: 18px;

    padding: 17px;

    background: #111827;

    border:
        1px solid #334155;

    border-radius: 9px;

    color: #cbd5e1;

    line-height: 1.6;
}

.architecture {
    display: grid;

    grid-template-columns:
        repeat(
            6,
            1fr
        );

    gap: 7px;

    margin-top: 14px;
}

.arch-step {
    padding: 9px 6px;

    text-align: center;

    background: #172033;

    border:
        1px solid #334155;

    border-radius: 6px;

    font-size: 12px;

    font-weight: bold;
}


/* ===================================================== */
/* TOOLBAR */
/* ===================================================== */

.toolbar {
    margin-top: 18px;

    padding: 15px;

    display: flex;

    flex-wrap: wrap;

    gap: 12px;

    align-items: end;

    background: #1e293b;

    border:
        1px solid #334155;

    border-radius: 9px;
}

.toolbar-field {
    min-width: 210px;
}

.toolbar-field label {
    display: block;

    margin-bottom: 5px;

    color: #94a3b8;

    font-size: 12px;
}

.toolbar-field select {
    width: 100%;

    padding: 9px;

    border:
        1px solid #475569;

    border-radius: 6px;

    background: #0f172a;

    color: #e2e8f0;
}


/* ===================================================== */
/* DECISION */
/* ===================================================== */

.decision-panel {
    margin-top: 20px;

    padding: 19px;

    border-radius: 10px;

    border:
        1px solid #334155;

    background: #1e293b;
}

.decision-pass {
    background: #052e16;
    border-color: #166534;
}

.decision-warning {
    background: #431407;
    border-color: #9a3412;
}

.decision-fail {
    background: #450a0a;
    border-color: #7f1d1d;
}

.decision-headline {
    font-size: 24px;

    font-weight: bold;

    margin-bottom: 14px;
}

.decision-grid {
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(145px, 1fr)
        );

    gap: 10px;
}

.decision-item {
    min-width: 0;

    padding: 11px;

    overflow: hidden;

    background:
        rgba(
            15,
            23,
            42,
            0.65
        );

    border:
        1px solid #334155;

    border-radius: 6px;

    font-size: 13px;
}

.decision-item strong {
    display: block;

    min-width: 0;

    max-width: 100%;

    margin-top: 4px;

    font-size: 17px;

    line-height: 1.25;

    overflow-wrap: anywhere;

    word-break: normal;
}


/* ===================================================== */
/* TABLES */
/* ===================================================== */

.table-panel {
    overflow-x: auto;

    background: #1e293b;

    border:
        1px solid #334155;

    border-radius: 9px;
}

table {
    width: 100%;

    border-collapse: collapse;
}

th,
td {
    padding: 10px 9px;

    border-bottom:
        1px solid #334155;

    text-align: right;

    font-size: 13px;

    vertical-align: middle;
}

th {
    color: #94a3b8;

    background: #172033;

    font-size: 11px;

    text-transform: uppercase;
}

th:first-child,
td:first-child {
    text-align: left;
}

td.left,
th.left {
    text-align: left;
}

tr:last-child td {
    border-bottom: 0;
}

input,
select {
    padding: 7px 8px;

    border:
        1px solid #475569;

    border-radius: 5px;

    background: #0f172a;

    color: #e2e8f0;
}

input {
    width: 90px;
}

.cell-id {
    font-weight: bold;
}

.muted {
    color: #94a3b8;
}

.pass {
    color: #4ade80;

    font-weight: bold;
}

.fail {
    color: #f87171;

    font-weight: bold;
}

.warning {
    color: #fb923c;

    font-weight: bold;
}

.good-delta {
    color: #4ade80;

    font-weight: bold;
}

.bad-delta {
    color: #f87171;

    font-weight: bold;
}


/* ===================================================== */
/* BADGES */
/* ===================================================== */

.badge-pass,
.badge-fail,
.badge-warning,
.badge-info {
    display: inline-block;

    padding: 4px 7px;

    border-radius: 5px;

    font-size: 11px;

    font-weight: bold;
}

.badge-pass {
    background: #14532d;
    color: #86efac;
}

.badge-fail {
    background: #7f1d1d;
    color: #fca5a5;
}

.badge-warning {
    background: #7c2d12;
    color: #fdba74;
}

.badge-info {
    background: #1e3a8a;
    color: #bfdbfe;
}


/* ===================================================== */
/* BUTTONS */
/* ===================================================== */

.controls {
    margin-top: 16px;

    padding: 16px;

    background: #1e293b;

    border:
        1px solid #334155;

    border-radius: 9px;
}

button {
    margin:
        4px 5px
        4px 0;

    padding: 11px 16px;

    border: 0;

    border-radius: 6px;

    color: white;

    font-weight: bold;

    cursor: pointer;
}

button:hover {
    opacity: 0.85;
}

button:disabled {
    cursor: wait;
    opacity: 0.55;
}

.btn-evaluate {
    background: #2563eb;
}

.btn-apply {
    background: #15803d;
}

.btn-reset {
    background: #c2410c;
}

.btn-refresh {
    background: #475569;
}

.btn-fault {
    background: #b45309;
}

.btn-heal {
    background: #0f766e;
}

.self-heal-panel {
    margin-top: 16px;

    padding: 16px;

    background: #132238;

    border:
        1px solid #3b82f6;

    border-radius: 9px;
}

.self-heal-grid {
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(210px, 1fr)
        );

    gap: 12px;

    margin-top: 12px;
}

.self-heal-field {
    min-width: 0;

    padding: 11px;

    background: rgba(15, 23, 42, 0.7);

    border: 1px solid #334155;

    border-radius: 7px;
}

.self-heal-field label {
    display: block;

    margin-bottom: 6px;

    color: #94a3b8;

    font-size: 11px;

    text-transform: uppercase;
}

.self-heal-value {
    min-width: 0;

    overflow-wrap: anywhere;

    font-weight: bold;
}

.self-heal-actions {
    margin-top: 12px;
}


/* ===================================================== */
/* METRIC STRIP */
/* ===================================================== */

.metric-strip {
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(150px, 1fr)
        );

    gap: 10px;

    margin-bottom: 12px;
}

.metric-box {
    padding: 12px;

    background: #111827;

    border:
        1px solid #334155;

    border-radius: 7px;
}

.metric-name {
    color: #94a3b8;

    font-size: 11px;

    text-transform: uppercase;
}

.metric-number {
    margin-top: 5px;

    font-size: 18px;

    font-weight: bold;
}


/* ===================================================== */
/* WORKFLOW */
/* ===================================================== */

.workflow {
    margin-top: 13px;

    background: #111827;

    border:
        1px solid #334155;

    border-radius: 7px;
}

.workflow-row {
    display: grid;

    grid-template-columns:
        35px
        1fr
        100px;

    gap: 10px;

    padding: 9px 12px;

    border-bottom:
        1px solid #334155;

    align-items: center;

    font-size: 13px;
}

.workflow-row:last-child {
    border-bottom: 0;
}


/* ===================================================== */
/* EVENTS */
/* ===================================================== */

.timeline {
    background: #1e293b;

    border:
        1px solid #334155;

    border-radius: 9px;

    padding: 14px;
}

.event {
    display: grid;

    grid-template-columns:
        90px
        minmax(220px, 280px)
        105px
        minmax(0, 1fr);

    gap: 14px;

    padding: 8px 0;

    border-bottom:
        1px solid #334155;

    align-items: start;

    font-size: 13px;
}

.event > div {
    min-width: 0;
}

.event-type,
.event-message {
    overflow-wrap: anywhere;

    word-break: normal;
}

.event-status {
    min-width: 0;
}

.event:last-child {
    border-bottom: 0;
}

.event-time {
    color: #94a3b8;

    font-family: monospace;
}


/* ===================================================== */
/* DETAILS / ADVANCED */
/* ===================================================== */

details {
    margin-top: 14px;

    background: #111827;

    border:
        1px solid #334155;

    border-radius: 7px;
}

summary {
    padding: 12px 14px;

    cursor: pointer;

    font-weight: bold;
}

.details-body {
    padding:
        0
        14px
        14px;
}

.raw {
    max-height: 420px;

    overflow: auto;

    padding: 14px;

    background: #020617;

    border:
        1px solid #334155;

    border-radius: 6px;

    color: #cbd5e1;

    font-size: 12px;
}

.hidden {
    display: none;
}


/* ===================================================== */
/* RESPONSIVE */
/* ===================================================== */

@media (
    max-width: 850px
) {

    .container {
        padding: 14px;
    }

    .architecture {
        grid-template-columns:
            repeat(
                2,
                1fr
            );
    }

    .event {
        grid-template-columns:
            80px
            1fr;
    }

    .event-status,
    .event-message {
        display: none;
    }
}

</style>

</head>


<body>


<header>

<h1>
    RAN Automation & Resilience Lab
</h1>

<p>
    Operator overview:
    observe the active RAN and environmental context,
    configure a synthetic candidate,
    evaluate RF and traffic impact,
    then promote, roll back, block, or run an explicitly authorized recovery workflow.
</p>

</header>


<div class="container">


<div
    id="system-banner"
    class="banner banner-good"
>
    Loading...
</div>


<div class="summary-grid">

    <div class="summary-card">

        <div class="summary-label">
            Application
        </div>

        <div
            id="application-release"
            class="summary-value"
        >
            -
        </div>

    </div>


    <div class="summary-card">

        <div class="summary-label">
            Active Config
        </div>

        <div
            id="ran-version"
            class="summary-value"
        >
            -
        </div>

    </div>


    <div class="summary-card">

        <div class="summary-label">
            Automation State
        </div>

        <div
            id="rollout-state"
            class="summary-value"
        >
            -
        </div>

    </div>


    <div class="summary-card">

        <div class="summary-label">
            Active RAN Health
        </div>

        <div
            id="ran-validation"
            class="summary-value"
        >
            -
        </div>

    </div>


    <div class="summary-card">

        <div class="summary-label">
            Served UE
        </div>

        <div
            id="served-ratio"
            class="summary-value"
        >
            -
        </div>

    </div>


    <div class="summary-card">

        <div class="summary-label">
            Configured / Serving
        </div>

        <div
            id="cell-counts"
            class="summary-value"
        >
            -
        </div>

    </div>

</div>


<div class="section">

<h2>
    Live Operational Context
</h2>

<div class="section-note">
    Weather is read from the backend-authoritative snapshot used
    to re-observe the active RAN. The browser does not fetch
    Open-Meteo directly. The backend weather cache TTL is 10 minutes.
</div>

<div class="context-grid">

    <div
        id="weather-context-panel"
        class="context-panel"
    >

        <div class="context-header">

            <div class="context-title">
                Environmental Snapshot
            </div>

            <div id="weather-source-status">
                -
            </div>

        </div>

        <div class="context-fields">

            <div class="context-field">
                <div class="context-field-label">
                    Temperature
                </div>
                <div
                    id="weather-temperature"
                    class="context-field-value"
                >
                    -
                </div>
            </div>

            <div class="context-field">
                <div class="context-field-label">
                    Rain Rate
                </div>
                <div
                    id="weather-rain"
                    class="context-field-value"
                >
                    -
                </div>
            </div>

            <div class="context-field">
                <div class="context-field-label">
                    Humidity
                </div>
                <div
                    id="weather-humidity"
                    class="context-field-value"
                >
                    -
                </div>
            </div>

            <div class="context-field">
                <div class="context-field-label">
                    Surface Pressure
                </div>
                <div
                    id="weather-pressure"
                    class="context-field-value"
                >
                    -
                </div>
            </div>

            <div class="context-field">
                <div class="context-field-label">
                    Wind
                </div>
                <div
                    id="weather-wind"
                    class="context-field-value"
                >
                    -
                </div>
            </div>

            <div class="context-field">
                <div class="context-field-label">
                    Cache Age
                </div>
                <div
                    id="weather-cache-age"
                    class="context-field-value"
                >
                    -
                </div>
            </div>

            <div class="context-field context-wide">
                <div class="context-field-label">
                    Weather Valid At / Location
                </div>
                <div
                    id="weather-valid-at"
                    class="context-field-value"
                >
                    -
                </div>
            </div>

            <div
                id="weather-error-field"
                class="context-field context-wide hidden"
            >
                <div class="context-field-label">
                    Weather Feed Note
                </div>
                <div
                    id="weather-error"
                    class="context-field-value warning"
                >
                    -
                </div>
            </div>

        </div>

    </div>


    <div
        id="baseline-context-panel"
        class="context-panel"
    >

        <div class="context-header">

            <div class="context-title">
                Active RAN Baseline
            </div>

            <div id="baseline-health-badge">
                -
            </div>

        </div>

        <div class="context-fields">

            <div class="context-field">
                <div class="context-field-label">
                    Active Config
                </div>
                <div
                    id="baseline-active-config"
                    class="context-field-value"
                >
                    -
                </div>
            </div>

            <div class="context-field">
                <div class="context-field-label">
                    Requested Active UE
                </div>
                <div
                    id="baseline-requested-ues"
                    class="context-field-value"
                >
                    -
                </div>
            </div>

            <div class="context-field">
                <div class="context-field-label">
                    Served Active UE
                </div>
                <div
                    id="baseline-served-ues"
                    class="context-field-value"
                >
                    -
                </div>
            </div>

            <div class="context-field">
                <div class="context-field-label">
                    Served Ratio
                </div>
                <div
                    id="baseline-served-ratio"
                    class="context-field-value"
                >
                    -
                </div>
            </div>

            <div class="context-field">
                <div class="context-field-label">
                    Failed Safety Checks
                </div>
                <div
                    id="baseline-failed-count"
                    class="context-field-value"
                >
                    -
                </div>
            </div>

            <div class="context-field context-wide">
                <div class="context-field-label">
                    Active Safety Finding
                </div>
                <div
                    id="baseline-failure"
                    class="context-field-value"
                >
                    -
                </div>
            </div>

        </div>

    </div>

</div>

</div>


<div class="info-panel">

<b>
    Automation decision path
</b>

<div class="architecture">

    <div class="arch-step">
        CHANGE
    </div>

    <div class="arch-step">
        RF
    </div>

    <div class="arch-step">
        UE ASSOCIATION
    </div>

    <div class="arch-step">
        TRAFFIC / PRB
    </div>

    <div class="arch-step">
        GUARDRAILS
    </div>

    <div class="arch-step">
        PROMOTE / ROLLBACK / BLOCK / SELF-HEAL
    </div>

</div>

<div
    class="muted"
    style="margin-top:12px"
>

The sites and operational thresholds are synthetic
learning-lab data.

The RF layer is geography-aware and physics-inspired.

</div>

</div>


<div class="toolbar">

    <div class="toolbar-field">

        <label>
            Working site
        </label>

        <select
            id="site-filter"
            onchange="renderWorkingView(); updateSelfHealingScope()"
        >
        </select>

    </div>


    <div class="toolbar-field">

        <label>
            Carrier band
        </label>

        <select
            id="band-filter"
            onchange="renderWorkingView()"
        >

            <option value="ALL">
                All bands
            </option>

            <option value="n78">
                n78
            </option>

            <option value="n28">
                n28
            </option>

            <option value="B3">
                B3
            </option>

        </select>

    </div>

</div>


<div
    id="decision-panel"
    class="decision-panel"
>

<div
    id="decision-headline"
    class="decision-headline"
>
    READY FOR CHANGE
</div>

<div
    id="decision-summary"
    class="decision-grid"
>

    <div class="decision-item">

        Select a parameter change,
        then choose
        <strong>
            Evaluate Candidate
        </strong>

    </div>

</div>

<div
    id="workflow"
    class="workflow hidden"
>
</div>

</div>


<div class="section">

<h2>
    1. Candidate Configuration
</h2>

<div
    id="working-site-note"
    class="section-note"
>
</div>


<h3>
    Cell / Carrier Parameters
</h3>

<div
    id="cell-editor"
    class="table-panel"
>
</div>


<h3 style="margin-top:16px">
    Antenna Parameters
</h3>

<div
    id="antenna-editor"
    class="table-panel"
>
</div>


<div class="controls">

<button
    class="btn-evaluate"
    onclick="withOperationLock(evaluateCandidate)"
>
    Evaluate Candidate
</button>

<button
    class="btn-apply"
    onclick="withOperationLock(guardedApply)"
>
    Guarded Apply
</button>

<button
    class="btn-reset"
    onclick="withOperationLock(restoreBaseline)"
>
    Restore Factory Baseline
</button>

<button
    class="btn-refresh"
    onclick="withOperationLock(loadEverything)"
>
    Refresh
</button>

<div
    class="muted"
    style="margin-top:9px; font-size:12px"
>

Evaluate is preview-only.

Guarded Apply promotes only when the resulting
network state passes the guardrails.

</div>

</div>


<div class="self-heal-panel">

<h3>
    Self-Healing / Recovery Demo
</h3>

<div class="section-note">
    Normal Guarded Apply stays fail-closed when the active RAN is already
    outside the safe envelope. The default v2.2 operating point is calibrated
    to be healthy. Separate learning-lab fault buttons can inject either an RF
    TX-power degradation or a traffic/local capacity hotspot without changing the
    accepted CONFIG revision. Self-healing restores RF configuration or keeps
    the hotspot demand fixed while enabling capacity-recovery split steering, then verifies
    the resulting safe envelope.
</div>

<div class="self-heal-grid">

    <div class="self-heal-field">
        <label>Fault Scope</label>
        <div
            id="self-heal-scope"
            class="self-heal-value"
        >
            Loading...
        </div>
    </div>

    <div class="self-heal-field">
        <label>Injected TX Power</label>
        <div class="self-heal-value">
            <input
                id="fault-tx-power"
                type="number"
                min="30"
                max="49"
                step="1"
                value="30"
            >
            dBm
        </div>
    </div>

    <div class="self-heal-field">
        <label>Capacity Spike Factor</label>
        <div class="self-heal-value">
            <input
                id="capacity-spike-factor"
                type="number"
                min="1.1"
                max="8.0"
                step="0.1"
                value="8.0"
            >
            x normal traffic
        </div>
    </div>

    <div class="self-heal-field">
        <label>Recovery State</label>
        <div
            id="self-heal-state"
            class="self-heal-value"
        >
            Loading...
        </div>
    </div>

</div>

<div class="self-heal-actions">

    <button
        class="btn-fault"
        onclick="withOperationLock(injectRfFault)"
    >
        Inject RF Fault
    </button>

    <button
        class="btn-fault"
        onclick="withOperationLock(injectCapacitySpike)"
    >
        Inject Capacity Spike
    </button>

    <button
        class="btn-heal"
        onclick="withOperationLock(runSelfHealing)"
    >
        Run Self-Healing
    </button>

    <span class="muted" style="font-size:12px">
        RF demo scope: enabled n78 cells on the selected site. Capacity demo auto-selects a recoverable local traffic hotspot.
    </span>

</div>

</div>

</div>


<div
    id="changes-section"
    class="section hidden"
>

<h2>
    2. Requested Change
</h2>

<div
    id="change-table"
    class="table-panel"
>
</div>

</div>


<div
    id="impact-section"
    class="section hidden"
>

<h2>
    3. Network Impact
</h2>

<div class="section-note">

Only cells with a meaningful KPI or UE change are shown.
The complete serving-cell view remains available under Advanced.

</div>

<div
    id="impact-table"
    class="table-panel"
>
</div>

</div>


<div
    id="guardrails-section"
    class="section hidden"
>

<h2 id="guardrails-title">
    4. Guardrail Decision
</h2>

<div
    id="guardrail-metrics"
    class="metric-strip"
>
</div>

<div
    id="failed-guardrails"
    class="table-panel"
>
</div>

<details>

<summary>
    Show all guardrail checks
</summary>

<div class="details-body">

<div
    id="all-guardrails"
    class="table-panel"
>
</div>

</div>

</details>

</div>


<div
    id="reassociation-section"
    class="section hidden"
>

<h2>
    UE Reassociation
</h2>

<div class="section-note">

A serving-cell change is not automatically a failure.
The resulting service quality and load decide whether
the candidate is accepted.

</div>

<div
    id="reassociation-table"
    class="table-panel"
>
</div>

</div>


<div class="section">

<h2>
    Current Serving View
</h2>

<div
    id="serving-summary"
    class="section-note"
>
</div>

<div
    id="serving-table"
    class="table-panel"
>
</div>

</div>


<div class="section">

<h2>
    Recent Automation Events
</h2>

<div
    id="timeline"
    class="timeline"
>
    No events.
</div>

</div>


<div class="section">

<h2>
    Advanced
</h2>


<details>

<summary>
    Show all active serving cells
</summary>

<div class="details-body">

<div
    id="all-serving-table"
    class="table-panel"
>
</div>

</div>

</details>


<details>

<summary>
    Show last raw API response
</summary>

<div class="details-body">

<pre
    id="raw-output"
    class="raw"
>No operation yet.</pre>

</div>

</details>

</div>


<div
    class="section muted"
    style="font-size:12px"
>

TX power, electrical tilt, bandwidth,
RSRP, SINR, PRB utilization and active UE count
are real categories of RAN configuration and KPIs.

Numerical configuration values, traffic assumptions and
acceptance thresholds in this application remain
learning-lab values.

</div>


</div>


<script>


let ranConfigData = null;

let activeConfigSnapshot = null;

let activeServingCells = [];

let lastRawResponse = null;

let lastStatusSnapshot = null;

let contextRefreshInFlight = false;

let operationInFlight = false;

const LIVE_CONTEXT_REFRESH_MS =
    60 * 1000;


/* ===================================================== */
/* API */
/* ===================================================== */

async function api(
    url,
    options = {}
) {

    const response =
        await fetch(
            url,
            options
        );


    if (!response.ok) {

        const text =
            await response.text();


        throw new Error(
            `HTTP ${response.status}: ${text}`
        );
    }


    return response.json();
}


/* ===================================================== */
/* GENERAL HELPERS */
/* ===================================================== */

function setOperationBusy(
    busy
) {

    document
        .querySelectorAll(
            "button"
        )
        .forEach(
            button => {
                button.disabled = busy;
            }
        );
}


async function withOperationLock(
    action
) {

    if (
        operationInFlight
    ) {
        return;
    }

    operationInFlight = true;
    setOperationBusy(true);

    try {
        await action();
    }

    finally {
        operationInFlight = false;
        setOperationBusy(false);
    }
}


function badge(
    status
) {

    if (
        status === "PASS"
        ||
        status === "APPLIED"
        ||
        status === "ACTIVE"
        ||
        status === "STABLE"
        ||
        status === "LIVE"
        ||
        status === "RECOVERED"
        ||
        status === "SELF_HEALED"
    ) {

        return `
            <span class="badge-pass">
                ${status}
            </span>
        `;
    }


    if (
        status === "ROLLED_BACK"
        ||
        status === "DEGRADED"
        ||
        status === "WARNING"
        ||
        status === "STALE_LAST_KNOWN"
        ||
        status === "FALLBACK"
        ||
        status === "FAULT_INJECTED"
        ||
        status === "BLOCKED"
    ) {

        return `
            <span class="badge-warning">
                ${status}
            </span>
        `;
    }


    if (
        status === "INFO"
        ||
        status === "CACHE"
        ||
        status === "FIXED"
        ||
        status === "EVALUATED"
        ||
        status === "NO_ACTION"
    ) {

        return `
            <span class="badge-info">
                ${status}
            </span>
        `;
    }


    return `
        <span class="badge-fail">
            ${status}
        </span>
    `;
}


function displayValue(
    value
) {

    if (
        value === null
        ||
        value === undefined
    ) {

        return "-";
    }


    if (
        typeof value === "object"
    ) {

        if (
            value.cell_id
            &&
            value.prb_utilization_pct
                !== undefined
        ) {

            return (
                `${value.cell_id}`
                + ` / `
                + `${value.prb_utilization_pct}%`
            );
        }


        return JSON.stringify(
            value
        );
    }


    return value;
}


function signed(
    value,
    unit = ""
) {

    if (
        value === null
        ||
        value === undefined
    ) {

        return "-";
    }


    const numeric =
        Number(
            value
        );


    if (
        Number.isNaN(
            numeric
        )
    ) {

        return value;
    }


    if (
        numeric > 0
    ) {

        return `+${numeric}${unit}`;
    }


    return `${numeric}${unit}`;
}


function deltaClass(
    value,
    lowerIsBetter = false
) {

    if (
        value === null
        ||
        value === undefined
        ||
        value === 0
    ) {

        return "";
    }


    if (
        lowerIsBetter
    ) {

        return (
            value < 0
            ? "good-delta"
            : "bad-delta"
        );
    }


    return (
        value > 0
        ? "good-delta"
        : "bad-delta"
    );
}


function selectedSite() {

    return (
        document
            .getElementById(
                "site-filter"
            )
            .value
    );
}


function selectedBand() {

    return (
        document
            .getElementById(
                "band-filter"
            )
            .value
    );
}


function showRaw(
    data
) {

    lastRawResponse =
        data;


    document.getElementById(
        "raw-output"
    ).textContent =

        JSON.stringify(
            data,
            null,
            2
        );
}


function activeGuardrailName(
    name
) {

    if (
        name === "MAX_CANDIDATE_PRB"
    ) {

        return "MAX_ACTIVE_PRB";
    }


    return name;
}


function operationalFailureText(
    baselineHealth
) {

    const failed =
        baselineHealth.failed_checks
        || [];


    if (
        failed.length === 0
    ) {

        return "No active-state safety finding.";
    }


    const check =
        failed[0];


    const observed =
        check.candidate
        !== null
        &&
        check.candidate
        !== undefined

        ? check.candidate

        : check.baseline;


    return (
        `${activeGuardrailName(check.name)}: `
        + `${displayValue(observed)}`
        + ` / limit ${displayValue(check.limit)}`
    );
}


function renderOperationalContext(
    status
) {

    const weather =
        status.weather
        || {};


    const baselineHealth =
        status.baseline_health
        || {};


    const service =
        status.service
        || {};


    lastStatusSnapshot =
        status;


    document.getElementById(
        "weather-source-status"
    ).innerHTML =
        badge(
            weather.source_status
            || "UNKNOWN"
        );


    document.getElementById(
        "weather-temperature"
    ).textContent =
        weather.temperature_c
        !== undefined
        &&
        weather.temperature_c
        !== null

        ? `${weather.temperature_c} °C`

        : "-";


    document.getElementById(
        "weather-rain"
    ).textContent =
        weather.rain_rate_mm_per_h
        !== undefined
        &&
        weather.rain_rate_mm_per_h
        !== null

        ? `${weather.rain_rate_mm_per_h} mm/h`

        : "-";


    document.getElementById(
        "weather-humidity"
    ).textContent =
        weather.relative_humidity_pct
        !== undefined
        &&
        weather.relative_humidity_pct
        !== null

        ? `${weather.relative_humidity_pct}%`

        : "-";


    document.getElementById(
        "weather-pressure"
    ).textContent =
        weather.pressure_hpa
        !== undefined
        &&
        weather.pressure_hpa
        !== null

        ? `${weather.pressure_hpa} hPa`

        : "-";


    const windSpeed =
        weather.wind_speed_m_per_s;


    const windDirection =
        weather.wind_direction_deg;


    document.getElementById(
        "weather-wind"
    ).textContent =
        windSpeed
        !== undefined
        &&
        windSpeed
        !== null

        ? (
            `${windSpeed} m/s`
            + (
                windDirection
                !== undefined
                &&
                windDirection
                !== null

                ? ` / ${windDirection}°`

                : ""
            )
        )

        : "-";


    document.getElementById(
        "weather-cache-age"
    ).textContent =
        weather.cache_age_seconds
        !== undefined
        &&
        weather.cache_age_seconds
        !== null

        ? `${Math.round(weather.cache_age_seconds)} s`

        : "-";


    const locationName =
        weather.location
        &&
        weather.location.name

        ? weather.location.name

        : "Jesenice u Prahy";


    document.getElementById(
        "weather-valid-at"
    ).textContent =
        (
            `${weather.timestamp || "-"}`
            + ` / ${locationName}`
        );


    const weatherErrorField =
        document.getElementById(
            "weather-error-field"
        );


    if (
        weather.error
    ) {

        weatherErrorField.classList.remove(
            "hidden"
        );


        document.getElementById(
            "weather-error"
        ).textContent =
            weather.error;
    }

    else {

        weatherErrorField.classList.add(
            "hidden"
        );
    }


    document.getElementById(
        "baseline-health-badge"
    ).innerHTML =
        badge(
            baselineHealth.status
            || "UNKNOWN"
        );


    document.getElementById(
        "baseline-active-config"
    ).textContent =
        status.ran_config_version
        || "-";


    document.getElementById(
        "baseline-requested-ues"
    ).textContent =
        displayValue(
            service.requested_active_ues
        );


    document.getElementById(
        "baseline-served-ues"
    ).textContent =
        displayValue(
            service.served_active_ues
        );


    document.getElementById(
        "baseline-served-ratio"
    ).textContent =
        service.served_ratio_pct
        !== undefined
        &&
        service.served_ratio_pct
        !== null

        ? `${service.served_ratio_pct}%`

        : "-";


    document.getElementById(
        "baseline-failed-count"
    ).textContent =
        displayValue(
            baselineHealth.failed_check_count
        );


    const baselineFailure =
        document.getElementById(
            "baseline-failure"
        );


    baselineFailure.textContent =
        operationalFailureText(
            baselineHealth
        );


    baselineFailure.className =
        (
            baselineHealth.status
            === "FAIL"

            ? "context-field-value fail"

            : "context-field-value pass"
        );
}


/* ===================================================== */
/* STATUS */
/* ===================================================== */

async function loadStatus() {

    const status =
        await api(
            "/status"
        );


    document.getElementById(
        "application-release"
    ).textContent =
        status.application_release;


    document.getElementById(
        "ran-version"
    ).textContent =
        status.ran_config_version;


    document.getElementById(
        "rollout-state"
    ).textContent =
        status.rollout_state;


    document.getElementById(
        "ran-validation"
    ).textContent =
        status.ran_validation;


    document.getElementById(
        "served-ratio"
    ).textContent =
        `${status.served_ratio_pct}%`;


    renderOperationalContext(
        status
    );


    const banner =
        document.getElementById(
            "system-banner"
        );


    if (
        status.self_healing
        &&
        status.self_healing.fault_active
    ) {

        banner.className =
            "banner banner-warning";


        banner.textContent =
            "LEARNING-LAB RF FAULT ACTIVE - SELF-HEAL AVAILABLE";
    }

    else if (
        status.baseline_health
        &&
        status.baseline_health.status
        === "FAIL"
    ) {

        banner.className =
            "banner banner-bad";


        banner.textContent =
            "APPLICATION HEALTHY - ACTIVE RAN OUTSIDE SAFE ENVELOPE";
    }

    else if (
        status.rollout_state
        === "ROLLED_BACK"
    ) {

        banner.className =
            "banner banner-warning";


        banner.textContent =
            "CANDIDATE REJECTED - KNOWN-GOOD CONFIG RESTORED";
    }

    else {

        banner.className =
            "banner banner-good";


        banner.textContent =
            "APPLICATION HEALTHY - ACTIVE RAN INSIDE SAFE ENVELOPE";
    }


    return status;
}


/* ===================================================== */
/* CONFIG LOAD */
/* ===================================================== */

async function loadRanConfig() {

    const previousSite =
        document.getElementById(
            "site-filter"
        ).value;


    ranConfigData =
        await api(
            "/ran-config"
        );


    activeConfigSnapshot =
        JSON.parse(
            JSON.stringify(
                ranConfigData.active
            )
        );


    populateSiteFilter(
        previousSite
    );


    updateCellCountSummary();


    renderWorkingView();

    updateSelfHealingScope();
}


/* ===================================================== */
/* SITE FILTER */
/* ===================================================== */

function populateSiteFilter(
    previousSite
) {

    const select =
        document.getElementById(
            "site-filter"
        );


    const sites =
        ranConfigData
            .topology
            .sites;


    select.innerHTML =
        "";


    for (
        const siteId
        of sites
    ) {

        const option =
            document.createElement(
                "option"
            );


        option.value =
            siteId;


        option.textContent =
            siteId;


        select.appendChild(
            option
        );
    }


    if (
        previousSite
        &&
        sites.includes(
            previousSite
        )
    ) {

        select.value =
            previousSite;

        return;
    }


    const preferredSite =
        "SITE-JESENICE-01";


    if (
        sites.includes(
            preferredSite
        )
    ) {

        select.value =
            preferredSite;
    }

    else if (
        sites.length > 0
    ) {

        select.value =
            sites[0];
    }
}


/* ===================================================== */
/* WORKING VIEW */
/* ===================================================== */

function renderWorkingView() {

    if (
        !ranConfigData
    ) {

        return;
    }


    renderCellEditor();

    renderAntennaEditor();

    renderServingView();
}


/* ===================================================== */
/* CELL EDITOR */
/* ===================================================== */

function renderCellEditor() {

    const siteId =
        selectedSite();


    const band =
        selectedBand();


    const cells =
        Object.entries(
            ranConfigData
                .active
                .cells
        )
        .filter(
            (
                [
                    cellId,
                    config
                ]
            ) => {

                if (
                    config.site_id
                    !== siteId
                ) {

                    return false;
                }


                if (
                    band !== "ALL"
                    &&
                    config.band !== band
                ) {

                    return false;
                }


                return true;
            }
        );


    document.getElementById(
        "working-site-note"
    ).textContent =
        (
            `Working site: ${siteId}. `
            + `${cells.length} configured cells are shown. `
            + `Changing the site or band filter discards unsaved form edits.`
        );


    const container =
        document.getElementById(
            "cell-editor"
        );


    if (
        cells.length === 0
    ) {

        container.innerHTML =
            `
            <div style="padding:14px">
                No cells match the current filter.
            </div>
            `;

        return;
    }


    container.innerHTML = `

        <table>

        <thead>

            <tr>

                <th>Cell</th>
                <th>Tech</th>
                <th>Band</th>
                <th>Frequency</th>
                <th>TX Power</th>
                <th>Bandwidth</th>

            </tr>

        </thead>


        <tbody>

        ${
            cells.map(
                (
                    [
                        cellId,
                        config
                    ]
                ) => {

                    const allowedBandwidth =
                        ranConfigData
                            .allowed_ranges
                            .bandwidth_mhz_by_band[
                                config.band
                            ];


                    const options =
                        allowedBandwidth
                            .map(
                                value => `

                                <option
                                    value="${value}"
                                    ${
                                        value
                                        === config.bandwidth_mhz
                                        ? "selected"
                                        : ""
                                    }
                                >
                                    ${value}
                                </option>
                                `
                            )
                            .join("");


                    return `

                        <tr>

                            <td>

                                <span class="cell-id">
                                    ${cellId}
                                </span>

                                <br>

                                <span class="muted">
                                    ${config.sector_id}
                                </span>

                            </td>

                            <td>
                                ${config.technology}
                            </td>

                            <td>
                                ${config.band}
                            </td>

                            <td>
                                ${config.carrier_frequency_mhz}
                                MHz
                            </td>

                            <td>

                                <input
                                    id="cell-${cellId}-tx"
                                    type="number"
                                    min="${ranConfigData.allowed_ranges.tx_power_dbm.min}"
                                    max="${ranConfigData.allowed_ranges.tx_power_dbm.max}"
                                    step="0.5"
                                    value="${config.tx_power_dbm}"
                                >

                                dBm

                            </td>

                            <td>

                                <select
                                    id="cell-${cellId}-bandwidth"
                                >
                                    ${options}
                                </select>

                                MHz

                            </td>

                        </tr>
                    `;
                }
            )
            .join("")
        }

        </tbody>

        </table>
    `;
}


/* ===================================================== */
/* ANTENNA EDITOR */
/* ===================================================== */

function renderAntennaEditor() {

    const siteId =
        selectedSite();


    const band =
        selectedBand();


    const topology =
        ranConfigData
            .topology
            .antennas;


    const antennas =
        Object.entries(
            ranConfigData
                .active
                .antennas
        )
        .filter(
            (
                [
                    antennaId,
                    config
                ]
            ) => {

                if (
                    config.site_id
                    !== siteId
                ) {

                    return false;
                }


                if (
                    band === "ALL"
                ) {

                    return true;
                }


                const attachedCells =
                    topology[
                        antennaId
                    ]
                    .cells;


                return attachedCells.some(
                    cellId =>
                        ranConfigData
                            .active
                            .cells[
                                cellId
                            ]
                            .band
                        === band
                );
            }
        );


    const container =
        document.getElementById(
            "antenna-editor"
        );


    if (
        antennas.length === 0
    ) {

        container.innerHTML =
            `
            <div style="padding:14px">
                No antennas match the current filter.
            </div>
            `;

        return;
    }


    container.innerHTML = `

        <table>

        <thead>

            <tr>

                <th>Antenna</th>
                <th>Sector</th>
                <th>Azimuth</th>
                <th>Electrical Tilt</th>
                <th class="left">Affected Cells</th>

            </tr>

        </thead>


        <tbody>

        ${
            antennas.map(
                (
                    [
                        antennaId,
                        config
                    ]
                ) => {

                    const topo =
                        topology[
                            antennaId
                        ];


                    return `

                        <tr>

                            <td>
                                <span class="cell-id">
                                    ${antennaId}
                                </span>
                            </td>

                            <td>
                                ${config.sector_id}
                            </td>

                            <td>
                                ${config.azimuth_deg}
                                deg
                            </td>

                            <td>

                                <input
                                    id="antenna-${antennaId}-tilt"
                                    type="number"
                                    min="${ranConfigData.allowed_ranges.electrical_tilt_deg.min}"
                                    max="${ranConfigData.allowed_ranges.electrical_tilt_deg.max}"
                                    step="0.5"
                                    value="${config.electrical_tilt_deg}"
                                >

                                deg

                            </td>

                            <td class="left">
                                ${topo.cells.join(", ")}
                            </td>

                        </tr>
                    `;
                }
            )
            .join("")
        }

        </tbody>

        </table>
    `;
}


/* ===================================================== */
/* BUILD CANDIDATE REQUEST */
/* ===================================================== */

function buildCandidateRequest() {

    const cells = {};

    const antennas = {};


    for (
        const [
            cellId,
            activeConfig
        ]
        of Object.entries(
            ranConfigData
                .active
                .cells
        )
    ) {

        const txInput =
            document.getElementById(
                `cell-${cellId}-tx`
            );


        const bandwidthInput =
            document.getElementById(
                `cell-${cellId}-bandwidth`
            );


        if (
            !txInput
            ||
            !bandwidthInput
        ) {

            continue;
        }


        const tx =
            Number(
                txInput.value
            );


        const bandwidth =
            Number(
                bandwidthInput.value
            );


        const update = {};


        if (
            tx
            !== activeConfig.tx_power_dbm
        ) {

            update.tx_power_dbm =
                tx;
        }


        if (
            bandwidth
            !== activeConfig.bandwidth_mhz
        ) {

            update.bandwidth_mhz =
                bandwidth;
        }


        if (
            Object.keys(
                update
            ).length
            > 0
        ) {

            cells[
                cellId
            ] =
                update;
        }
    }


    for (
        const [
            antennaId,
            activeConfig
        ]
        of Object.entries(
            ranConfigData
                .active
                .antennas
        )
    ) {

        const input =
            document.getElementById(
                `antenna-${antennaId}-tilt`
            );


        if (
            !input
        ) {

            continue;
        }


        const tilt =
            Number(
                input.value
            );


        if (
            tilt
            !== activeConfig.electrical_tilt_deg
        ) {

            antennas[
                antennaId
            ] = {

                electrical_tilt_deg:
                    tilt
            };
        }
    }


    return {
        cells,
        antennas
    };
}


/* ===================================================== */
/* CONFIG CHANGE TABLE */
/* ===================================================== */

function renderConfigChanges(
    candidate
) {

    const rows = [];


    for (
        const [
            cellId,
            candidateConfig
        ]
        of Object.entries(
            candidate.cells
        )
    ) {

        const baseline =
            activeConfigSnapshot
                .cells[
                    cellId
                ];


        if (
            candidateConfig.tx_power_dbm
            !== baseline.tx_power_dbm
        ) {

            rows.push({

                object:
                    cellId,

                parameter:
                    "TX Power",

                baseline:
                    `${baseline.tx_power_dbm} dBm`,

                candidate:
                    `${candidateConfig.tx_power_dbm} dBm`
            });
        }


        if (
            candidateConfig.bandwidth_mhz
            !== baseline.bandwidth_mhz
        ) {

            rows.push({

                object:
                    cellId,

                parameter:
                    "Bandwidth",

                baseline:
                    `${baseline.bandwidth_mhz} MHz`,

                candidate:
                    `${candidateConfig.bandwidth_mhz} MHz`
            });
        }
    }


    for (
        const [
            antennaId,
            candidateConfig
        ]
        of Object.entries(
            candidate.antennas
        )
    ) {

        const baseline =
            activeConfigSnapshot
                .antennas[
                    antennaId
                ];


        if (
            candidateConfig.electrical_tilt_deg
            !== baseline.electrical_tilt_deg
        ) {

            rows.push({

                object:
                    antennaId,

                parameter:
                    "Electrical Tilt",

                baseline:
                    `${baseline.electrical_tilt_deg} deg`,

                candidate:
                    `${candidateConfig.electrical_tilt_deg} deg`
            });
        }
    }


    const section =
        document.getElementById(
            "changes-section"
        );


    const container =
        document.getElementById(
            "change-table"
        );


    section.classList.remove(
        "hidden"
    );


    if (
        rows.length === 0
    ) {

        container.innerHTML =
            `
            <div style="padding:14px">
                No configuration difference.
            </div>
            `;

        return;
    }


    container.innerHTML = `

        <table>

        <thead>

            <tr>

                <th>Object</th>
                <th>Parameter</th>
                <th>Active</th>
                <th>Candidate</th>

            </tr>

        </thead>


        <tbody>

        ${
            rows.map(
                row => `

                    <tr>

                        <td>
                            ${row.object}
                        </td>

                        <td>
                            ${row.parameter}
                        </td>

                        <td>
                            ${row.baseline}
                        </td>

                        <td>
                            <b>
                                ${row.candidate}
                            </b>
                        </td>

                    </tr>
                `
            )
            .join("")
        }

        </tbody>

        </table>
    `;
}


/* ===================================================== */
/* NETWORK IMPACT */
/* ===================================================== */

function impactScore(
    cell
) {

    return (
        Math.abs(
            Number(
                cell.delta.sinr
                || 0
            )
        )
        * 4

        +

        Math.abs(
            Number(
                cell.delta.rsrp
                || 0
            )
        )
        * 3

        +

        Math.abs(
            Number(
                cell.delta.prb
                || 0
            )
        )
        * 2

        +

        Math.abs(
            Number(
                cell.delta.users
                || 0
            )
        )
    );
}


function meaningfulImpact(
    cell
) {

    return (

        Math.abs(
            Number(
                cell.delta.sinr
                || 0
            )
        )
        >= 0.1

        ||

        Math.abs(
            Number(
                cell.delta.rsrp
                || 0
            )
        )
        >= 0.1

        ||

        Math.abs(
            Number(
                cell.delta.prb
                || 0
            )
        )
        >= 0.1

        ||

        Math.abs(
            Number(
                cell.delta.users
                || 0
            )
        )
        >= 1
    );
}


function renderImpact(
    validation
) {

    const section =
        document.getElementById(
            "impact-section"
        );


    const container =
        document.getElementById(
            "impact-table"
        );


    if (
        !validation
        ||
        !Array.isArray(
            validation.cells
        )
    ) {

        section.classList.add(
            "hidden"
        );

        return;
    }


    const interesting =
        validation
            .cells
            .filter(
                meaningfulImpact
            )
            .sort(
                (
                    left,
                    right
                ) =>
                    impactScore(
                        right
                    )
                    -
                    impactScore(
                        left
                    )
            )
            .slice(
                0,
                12
            );


    section.classList.remove(
        "hidden"
    );


    if (
        interesting.length === 0
    ) {

        container.innerHTML =
            `
            <div style="padding:14px">
                No meaningful serving-cell KPI change detected.
            </div>
            `;

        return;
    }


    container.innerHTML = `

        <table>

        <thead>

            <tr>

                <th>Cell</th>
                <th>RSRP Delta</th>
                <th>SINR Delta</th>
                <th>PRB Delta</th>
                <th>UE Delta</th>
                <th>Status</th>

            </tr>

        </thead>


        <tbody>

        ${
            interesting.map(
                cell => `

                    <tr>

                        <td>
                            ${cell.cell_id}
                        </td>

                        <td
                            class="${
                                deltaClass(
                                    cell.delta.rsrp
                                )
                            }"
                        >
                            ${signed(
                                cell.delta.rsrp,
                                " dB"
                            )}
                        </td>

                        <td
                            class="${
                                deltaClass(
                                    cell.delta.sinr
                                )
                            }"
                        >
                            ${signed(
                                cell.delta.sinr,
                                " dB"
                            )}
                        </td>

                        <td
                            class="${
                                deltaClass(
                                    cell.delta.prb,
                                    true
                                )
                            }"
                        >
                            ${signed(
                                cell.delta.prb,
                                " pp"
                            )}
                        </td>

                        <td>
                            ${signed(
                                cell.delta.users
                            )}
                        </td>

                        <td>
                            ${
                                (
                                    cell.checks.prb === "FAIL"
                                    ||
                                    cell.checks.sinr === "FAIL"
                                    ||
                                    cell.checks.rsrp === "FAIL"
                                )
                                ? badge("FAIL")
                                : badge("PASS")
                            }
                        </td>

                    </tr>
                `
            )
            .join("")
        }

        </tbody>

        </table>
    `;
}


/* ===================================================== */
/* GUARDRAILS */
/* ===================================================== */

function renderGuardrails(
    guardrails,
    context = "CANDIDATE"
) {

    const section =
        document.getElementById(
            "guardrails-section"
        );


    if (
        !guardrails
    ) {

        section.classList.add(
            "hidden"
        );

        return;
    }


    section.classList.remove(
        "hidden"
    );


    const baselineContext =
        context === "BASELINE";


    document.getElementById(
        "guardrails-title"
    ).textContent =
        (
            baselineContext

            ? "4. Active Baseline Guardrails"

            : "4. Candidate Guardrail Decision"
        );


    const summary =
        guardrails.summary
        || {};


    const reassociation =
        guardrails.reassociation
        || {
            reassociated_active_ues: 0
        };


    document.getElementById(
        "guardrail-metrics"
    ).innerHTML = `

        <div class="metric-box">

            <div class="metric-name">
                Verdict
            </div>

            <div class="metric-number">
                ${badge(guardrails.verdict)}
            </div>

        </div>


        <div class="metric-box">

            <div class="metric-name">
                Served Ratio
            </div>

            <div class="metric-number">
                ${displayValue(
                    summary.candidate_served_ratio_pct
                )}%
            </div>

        </div>


        <div class="metric-box">

            <div class="metric-name">
                Degraded UE
            </div>

            <div class="metric-number">
                ${displayValue(
                    summary.baseline_degraded_ues
                )}
                →
                ${displayValue(
                    summary.candidate_degraded_ues
                )}
            </div>

        </div>


        <div class="metric-box">

            <div class="metric-name">
                Weighted SINR
            </div>

            <div class="metric-number">
                ${displayValue(
                    summary.candidate_weighted_sinr_db
                )}
                dB
            </div>

        </div>


        <div class="metric-box">

            <div class="metric-name">
                Max PRB
            </div>

            <div class="metric-number">
                ${
                    summary.max_candidate_prb
                    ? `${summary.max_candidate_prb.prb_utilization_pct}%`
                    : "-"
                }
            </div>

        </div>


        <div class="metric-box">

            <div class="metric-name">
                Reassociated UE
            </div>

            <div class="metric-number">
                ${reassociation.reassociated_active_ues}
            </div>

        </div>
    `;


    const failed =
        guardrails.failed_checks
        || [];


    const failedContainer =
        document.getElementById(
            "failed-guardrails"
        );


    if (
        failed.length === 0
    ) {

        failedContainer.innerHTML =
            `
            <div
                class="pass"
                style="padding:14px"
            >
                All guardrails passed.
            </div>
            `;
    }

    else {

        failedContainer.innerHTML =
            buildGuardrailTable(
                failed,
                baselineContext
            );
    }


    document.getElementById(
        "all-guardrails"
    ).innerHTML =
        buildGuardrailTable(
            guardrails.checks
            || [],
            baselineContext
        );
}


function buildGuardrailTable(
    checks,
    baselineContext = false
) {

    return `

        <table>

        <thead>

            <tr>

                <th>Guardrail</th>
                <th>Status</th>
                <th>Baseline</th>
                <th>
                    ${
                        baselineContext
                        ? "Observed Active"
                        : "Candidate"
                    }
                </th>
                <th>Delta</th>
                <th>Limit</th>

            </tr>

        </thead>


        <tbody>

        ${
            checks.map(
                check => `

                    <tr>

                        <td>
                            ${
                                baselineContext
                                ? activeGuardrailName(
                                    check.name
                                )
                                : check.name
                            }
                        </td>

                        <td>
                            ${badge(check.status)}
                        </td>

                        <td>
                            ${displayValue(
                                check.baseline
                            )}
                        </td>

                        <td>
                            ${displayValue(
                                check.candidate
                            )}
                        </td>

                        <td
                            class="${
                                check.status
                                === "FAIL"
                                ? "fail"
                                : ""
                            }"
                        >
                            ${displayValue(
                                check.delta
                            )}
                        </td>

                        <td>
                            ${displayValue(
                                check.limit
                            )}
                        </td>

                    </tr>
                `
            )
            .join("")
        }

        </tbody>

        </table>
    `;
}


/* ===================================================== */
/* REASSOCIATION */
/* ===================================================== */

function renderReassociation(
    reassociation
) {

    const section =
        document.getElementById(
            "reassociation-section"
        );


    const container =
        document.getElementById(
            "reassociation-table"
        );


    if (
        !reassociation
        ||
        reassociation.changed_sample_count
        === 0
    ) {

        section.classList.add(
            "hidden"
        );

        return;
    }


    section.classList.remove(
        "hidden"
    );


    container.innerHTML = `

        <table>

        <thead>

            <tr>

                <th>UE Sample</th>
                <th>Active UE</th>
                <th>From</th>
                <th>To</th>
                <th>Band</th>
                <th>Service</th>

            </tr>

        </thead>


        <tbody>

        ${
            reassociation
                .changes
                .map(
                    change => `

                        <tr>

                            <td>
                                ${change.sample_id}
                            </td>

                            <td>
                                ${change.active_ues}
                            </td>

                            <td>
                                ${change.baseline_cell_id}
                            </td>

                            <td>
                                ${change.candidate_cell_id}
                            </td>

                            <td>
                                ${change.baseline_band}
                                →
                                ${change.candidate_band}
                            </td>

                            <td>

                                ${change.baseline_serviceability}
                                →

                                <span
                                    class="${
                                        change.candidate_serviceability
                                        === "DEGRADED"
                                        ? "warning"
                                        : "pass"
                                    }"
                                >
                                    ${change.candidate_serviceability}
                                </span>

                            </td>

                        </tr>
                    `
                )
                .join("")
        }

        </tbody>

        </table>
    `;
}


/* ===================================================== */
/* ACTIVE SERVING CELLS */
/* ===================================================== */

async function loadLiveCells() {

    activeServingCells =
        await api(
            "/cells"
        );


    updateCellCountSummary();


    renderServingView();

    renderAllServingCells();
}


function updateCellCountSummary() {

    if (
        !ranConfigData
    ) {

        return;
    }


    const configured =
        Object.keys(
            ranConfigData
                .active
                .cells
        ).length;


    const serving =
        activeServingCells.length;


    document.getElementById(
        "cell-counts"
    ).textContent =
        `${configured} / ${serving}`;
}


function renderServingView() {

    if (
        !ranConfigData
    ) {

        return;
    }


    const siteId =
        selectedSite();


    const band =
        selectedBand();


    const configured =
        Object.values(
            ranConfigData
                .active
                .cells
        )
        .filter(
            config => {

                if (
                    config.site_id
                    !== siteId
                ) {

                    return false;
                }


                if (
                    band !== "ALL"
                    &&
                    config.band !== band
                ) {

                    return false;
                }


                return true;
            }
        );


    const serving =
        activeServingCells
            .filter(
                cell => {

                    if (
                        cell.site_id
                        !== siteId
                    ) {

                        return false;
                    }


                    if (
                        band !== "ALL"
                        &&
                        cell.band !== band
                    ) {

                        return false;
                    }


                    return true;
                }
            );


    document.getElementById(
        "serving-summary"
    ).textContent =
        (
            `${configured.length} cells are configured in this view; `
            + `${serving.length} are currently serving active UE.`
        );


    document.getElementById(
        "serving-table"
    ).innerHTML =
        buildServingTable(
            serving
        );
}


function renderAllServingCells() {

    document.getElementById(
        "all-serving-table"
    ).innerHTML =
        buildServingTable(
            activeServingCells
        );
}


function buildServingTable(
    cells
) {

    if (
        cells.length === 0
    ) {

        return `
            <div style="padding:14px">
                No active serving cells in this view.
            </div>
        `;
    }


    return `

        <table>

        <thead>

            <tr>

                <th>Cell</th>
                <th>Band</th>
                <th>RSRP</th>
                <th>SINR</th>
                <th>PRB</th>
                <th>Active UE</th>
                <th>Traffic</th>
                <th>Status</th>

            </tr>

        </thead>


        <tbody>

        ${
            cells.map(
                cell => `

                    <tr>

                        <td>
                            ${cell.cell_id}

                            <br>

                            <span class="muted">
                                ${cell.site_id}
                            </span>
                        </td>

                        <td>
                            ${cell.band}
                        </td>

                        <td>
                            ${cell.rsrp_dbm}
                            dBm
                        </td>

                        <td>
                            ${cell.sinr_db}
                            dB
                        </td>

                        <td>
                            ${cell.prb_utilization}
                            %
                        </td>

                        <td>
                            ${cell.active_users}
                        </td>

                        <td>
                            ${cell.traffic_mbps}
                            Mbps
                        </td>

                        <td>
                            ${badge(cell.status)}
                        </td>

                    </tr>
                `
            )
            .join("")
        }

        </tbody>

        </table>
    `;
}


/* ===================================================== */
/* EVALUATE */
/* ===================================================== */

async function evaluateCandidate() {

    try {

        const payload =
            buildCandidateRequest();


        const result =
            await api(

                "/ran-config/evaluate",

                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            payload
                        )
                }
            );


        showRaw(
            result
        );


        renderConfigChanges(
            result.candidate_config
        );


        renderImpact(
            result.validation
        );


        renderGuardrails(
            result.guardrails,
            "CANDIDATE"
        );


        renderReassociation(
            result.reassociation
        );


        renderEvaluationDecision(
            result
        );


        await loadEvents();


        document
            .getElementById(
                "decision-panel"
            )
            .scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

    }

    catch (
        error
    ) {

        showError(
            error
        );
    }
}


/* ===================================================== */
/* EVALUATE DECISION */
/* ===================================================== */

function renderEvaluationDecision(
    result
) {

    const panel =
        document.getElementById(
            "decision-panel"
        );


    const headline =
        document.getElementById(
            "decision-headline"
        );


    const summary =
        document.getElementById(
            "decision-summary"
        );


    document.getElementById(
        "workflow"
    ).classList.add(
        "hidden"
    );


    if (
        result.decision
        === "BLOCKED_BASELINE_HEALTH"
    ) {

        panel.className =
            "decision-panel decision-warning";


        headline.textContent =
            "DIAGNOSTIC PREVIEW - PROMOTION BLOCKED BY BASELINE HEALTH";
    }

    else if (
        result.would_be_accepted
    ) {

        panel.className =
            "decision-panel decision-pass";


        headline.textContent =
            "CANDIDATE PASSES - ELIGIBLE FOR PROMOTION";
    }

    else {

        panel.className =
            "decision-panel decision-fail";


        headline.textContent =
            "CANDIDATE WOULD BE REJECTED";
    }


    const guardrailSummary =
        result.guardrails.summary
        || {};


    const weather =
        result.weather
        || {};


    const baselineHealth =
        result.baseline_health
        || {};


    const reassociation =
        result.reassociation
        || {
            reassociated_active_ues: 0
        };


    summary.innerHTML = `

        <div class="decision-item">

            Decision

            <strong>
                ${result.decision || "-"}
            </strong>

        </div>


        <div class="decision-item">

            Baseline Health

            <strong>
                ${badge(baselineHealth.status || "UNKNOWN")}
            </strong>

        </div>


        <div class="decision-item">

            Candidate Guardrails

            <strong>
                ${badge(result.guardrails.verdict)}
            </strong>

        </div>


        <div class="decision-item">

            Candidate Failed Checks

            <strong>
                ${result.guardrails.failed_check_count}
            </strong>

        </div>


        <div class="decision-item">

            Candidate

            <strong>
                ${result.candidate_version}
            </strong>

        </div>


        <div class="decision-item">

            Active

            <strong>
                ${result.active_version}
            </strong>

        </div>


        <div class="decision-item">

            Served UE

            <strong>
                ${displayValue(
                    guardrailSummary.candidate_served_ratio_pct
                )}%
            </strong>

        </div>


        <div class="decision-item">

            Reassociated UE

            <strong>
                ${reassociation.reassociated_active_ues}
            </strong>

        </div>


        <div class="decision-item">

            Weather Snapshot

            <strong>
                ${weather.timestamp || "-"}
            </strong>

        </div>


        <div class="decision-item">

            Active changed?

            <strong>
                NO - PREVIEW ONLY
            </strong>

        </div>
    `;
}


/* ===================================================== */
/* GUARDED APPLY */
/* ===================================================== */

async function guardedApply() {

    try {

        const payload =
            buildCandidateRequest();


        const result =
            await api(

                "/ran-config/guarded-apply",

                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            payload
                        )
                }
            );


        showRaw(
            result
        );


        if (
            result.status
            === "BLOCKED"
        ) {

            document.getElementById(
                "changes-section"
            ).classList.add(
                "hidden"
            );


            document.getElementById(
                "impact-section"
            ).classList.add(
                "hidden"
            );


            document.getElementById(
                "reassociation-section"
            ).classList.add(
                "hidden"
            );


            if (
                result.baseline_health
                &&
                result.baseline_health.guardrails
            ) {

                renderGuardrails(
                    result.baseline_health.guardrails,
                    "BASELINE"
                );
            }

            else {

                document.getElementById(
                    "guardrails-section"
                ).classList.add(
                    "hidden"
                );
            }
        }

        else {

            if (
                result.candidate_config
            ) {

                renderConfigChanges(
                    result.candidate_config
                );
            }


            if (
                result.status
                === "APPLIED"
            ) {

                renderImpact(
                    result.validation
                );
            }

            else if (
                result.status
                === "ROLLED_BACK"
            ) {

                renderImpact(
                    result.failed_validation
                );
            }


            renderGuardrails(
                result.guardrails,
                "CANDIDATE"
            );


            renderReassociation(
                result.reassociation
            );
        }


        renderApplyDecision(
            result
        );


        if (
            result.status
            === "BLOCKED"
        ) {

            await refreshOperationalContext(
                true
            );
        }

        else {

            await refreshAfterOperation();
        }


        document
            .getElementById(
                "decision-panel"
            )
            .scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

    }

    catch (
        error
    ) {

        showError(
            error
        );
    }
}


/* ===================================================== */
/* APPLY DECISION */
/* ===================================================== */

function renderApplyDecision(
    result
) {

    const panel =
        document.getElementById(
            "decision-panel"
        );


    const headline =
        document.getElementById(
            "decision-headline"
        );


    const summary =
        document.getElementById(
            "decision-summary"
        );


    const workflow =
        document.getElementById(
            "workflow"
        );


    workflow.classList.remove(
        "hidden"
    );


    if (
        result.status
        === "APPLIED"
    ) {

        panel.className =
            "decision-panel decision-pass";


        headline.textContent =
            "CANDIDATE PROMOTED";


        summary.innerHTML = `

            <div class="decision-item">

                Result

                <strong>
                    ${badge("APPLIED")}
                </strong>

            </div>


            <div class="decision-item">

                Previous

                <strong>
                    ${result.previous_version}
                </strong>

            </div>


            <div class="decision-item">

                Active

                <strong>
                    ${result.active_version}
                </strong>

            </div>


            <div class="decision-item">

                Baseline Health

                <strong>
                    ${
                        badge(
                            result.baseline_health
                            ? result.baseline_health.status
                            : "UNKNOWN"
                        )
                    }
                </strong>

            </div>


            <div class="decision-item">

                Candidate Guardrails

                <strong>
                    ${badge(result.guardrails.verdict)}
                </strong>

            </div>


            <div class="decision-item">

                Decision

                <strong>
                    PROMOTE
                </strong>

            </div>
        `;
    }

    else if (
        result.status
        === "ROLLED_BACK"
    ) {

        panel.className =
            "decision-panel decision-warning";


        headline.textContent =
            "CANDIDATE REJECTED - ROLLBACK COMPLETED";


        summary.innerHTML = `

            <div class="decision-item">

                Candidate

                <strong>
                    ${result.candidate_version}
                </strong>

            </div>


            <div class="decision-item">

                Active Known-Good

                <strong>
                    ${result.active_version}
                </strong>

            </div>


            <div class="decision-item">

                Failed Checks

                <strong>
                    ${result.guardrails.failed_check_count}
                </strong>

            </div>


            <div class="decision-item">

                Reassociated UE

                <strong>
                    ${result.reassociation.reassociated_active_ues}
                </strong>

            </div>


            <div class="decision-item">

                Rollback Verify

                <strong>
                    ${
                        badge(
                            result
                                .rollback_verification
                                .verdict
                        )
                    }
                </strong>

            </div>


            <div class="decision-item">

                Decision

                <strong>
                    REJECT + RESTORE
                </strong>

            </div>
        `;
    }

    else if (
        result.status
        === "BLOCKED"
    ) {

        panel.className =
            "decision-panel decision-warning";


        const reason =
            result.reason
            || "PRECHECK_FAILED";


        if (
            reason
            === "ACTIVE_RAN_OUTSIDE_SAFE_ENVELOPE"
        ) {

            headline.textContent =
                "CHANGE BLOCKED - ACTIVE RAN OUTSIDE SAFE ENVELOPE";
        }

        else if (
            reason
            === "EXTERNAL_PRECHECK_FAILED"
        ) {

            headline.textContent =
                "CHANGE BLOCKED - EXTERNAL PRECHECK FAILED";
        }

        else {

            headline.textContent =
                "CHANGE BLOCKED";
        }


        summary.innerHTML = `

            <div class="decision-item">

                Result

                <strong>
                    ${badge("BLOCKED")}
                </strong>

            </div>


            <div class="decision-item">

                Reason

                <strong>
                    ${reason}
                </strong>

            </div>


            <div class="decision-item">

                Active Config

                <strong>
                    ${result.active_version || "-"}
                </strong>

            </div>


            <div class="decision-item">

                Baseline Health

                <strong>
                    ${
                        result.baseline_health
                        ? badge(
                            result.baseline_health.status
                        )
                        : "-"
                    }
                </strong>

            </div>


            <div class="decision-item">

                Candidate Evaluated?

                <strong>
                    ${
                        result.candidate_evaluated
                        ? "YES"
                        : "NO"
                    }
                </strong>

            </div>


            <div class="decision-item">

                Configuration Changed?

                <strong>
                    ${
                        result.configuration_changed
                        ? "YES"
                        : "NO"
                    }
                </strong>

            </div>
        `;
    }

    else {

        panel.className =
            "decision-panel decision-fail";


        headline.textContent =
            `RAN CHANGE ${result.status}`;


        summary.innerHTML =
            `
            <div class="decision-item">
                Active configuration remains
                <strong>
                    ${result.active_version || "-"}
                </strong>
            </div>
            `;
    }


    workflow.innerHTML =
        "";


    if (
        Array.isArray(
            result.steps
        )
    ) {

        result.steps.forEach(
            (
                step,
                index
            ) => {

                workflow.innerHTML += `

                    <div class="workflow-row">

                        <div>
                            ${index + 1}
                        </div>

                        <div>
                            ${step.step}
                        </div>

                        <div>
                            ${badge(step.status)}
                        </div>

                    </div>
                `;
            }
        );
    }
}


/* ===================================================== */
/* RESTORE BASELINE */
/* ===================================================== */

async function restoreBaseline() {

    try {

        const result =
            await api(

                "/ran-config/restore-baseline",

                {
                    method: "POST"
                }
            );


        showRaw(
            result
        );


        const panel =
            document.getElementById(
                "decision-panel"
            );


        const baselineHealth =
            result.baseline_health
            || {};


        if (
            baselineHealth.status
            === "FAIL"
        ) {

            panel.className =
                "decision-panel decision-warning";


            document.getElementById(
                "decision-headline"
            ).textContent =
                "FACTORY CONFIG RESTORED - ACTIVE RAN STILL OUTSIDE SAFE ENVELOPE";
        }

        else {

            panel.className =
                "decision-panel decision-pass";


            document.getElementById(
                "decision-headline"
            ).textContent =
                "FACTORY CONFIG RESTORED - ACTIVE RAN HEALTHY";
        }


        document.getElementById(
            "decision-summary"
        ).innerHTML = `

            <div class="decision-item">

                Previous

                <strong>
                    ${result.previous_version || "-"}
                </strong>

            </div>


            <div class="decision-item">

                Active

                <strong>
                    ${result.active_version || "-"}
                </strong>

            </div>


            <div class="decision-item">

                Baseline Health

                <strong>
                    ${
                        badge(
                            baselineHealth.status
                            || "UNKNOWN"
                        )
                    }
                </strong>

            </div>


            <div class="decision-item">

                Served UE

                <strong>
                    ${
                        result.service
                        ? `${result.service.served_ratio_pct}%`
                        : "-"
                    }
                </strong>

            </div>


            <div class="decision-item">

                Interpretation

                <strong>
                    ${
                        baselineHealth.status
                        === "FAIL"

                        ? "KNOWN-GOOD CONFIG != CURRENTLY HEALTHY RAN"

                        : "RESTORED STATE INSIDE SAFE ENVELOPE"
                    }
                </strong>

            </div>
        `;


        document.getElementById(
            "workflow"
        ).classList.add(
            "hidden"
        );


        hideCandidateSections();


        await refreshAfterOperation();


        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });

    }

    catch (
        error
    ) {

        showError(
            error
        );
    }
}


/* ===================================================== */
/* SELF-HEALING / RECOVERY DEMO */
/* ===================================================== */

function updateSelfHealingScope() {

    const target =
        document.getElementById(
            "self-heal-scope"
        );


    if (
        !target
        ||
        !ranConfigData
    ) {
        return;
    }


    const siteId =
        selectedSite();


    const cells =
        Object.entries(
            ranConfigData.active.cells
        )
        .filter(
            ([cellId, config]) => (
                config.site_id === siteId
                &&
                config.band === "n78"
                &&
                config.enabled !== false
            )
        );


    target.textContent =
        `${siteId} / n78 / ${cells.length} cell(s)`;
}


async function loadSelfHealingState() {

    const state =
        await api(
            "/self-healing/status"
        );


    const target =
        document.getElementById(
            "self-heal-state"
        );


    if (!target) {
        return state;
    }


    if (
        state.fault_active
    ) {

        const fault =
            state.fault
            || {};


        if (fault.type === "CAPACITY_SPIKE") {
            target.innerHTML =
                `${badge("FAULT_INJECTED")} `
                + `CAPACITY_SPIKE / `
                + `${displayValue(fault.hotspot_area_id)} / `
                + `${displayValue(fault.spike_factor)}x local / `
                + `${displayValue(state.traffic_multiplier)} global / `
                + `${displayValue(state.steering_mode)}`;
        }
        else {
            target.innerHTML =
                `${badge("FAULT_INJECTED")} `
                + `${displayValue(fault.type)} / `
                + `${(fault.cell_ids || []).length} cell(s) / `
                + `recover ${state.recovery_target_version}`;
        }
    }

    else {

        target.innerHTML =
            `${badge("STABLE")} no injected fault / `
            + `${displayValue(state.traffic_multiplier)} traffic / `
            + `${displayValue(state.steering_mode)}`;
    }


    return state;
}


function renderWorkflowSteps(
    steps
) {

    const workflow =
        document.getElementById(
            "workflow"
        );


    if (
        !Array.isArray(steps)
        ||
        steps.length === 0
    ) {

        workflow.classList.add(
            "hidden"
        );

        workflow.innerHTML = "";

        return;
    }


    workflow.classList.remove(
        "hidden"
    );

    workflow.innerHTML = "";


    steps.forEach(
        (step, index) => {

            workflow.innerHTML += `
                <div class="workflow-row">
                    <div>${index + 1}</div>
                    <div>${step.step}</div>
                    <div>${badge(step.status)}</div>
                </div>
            `;
        }
    );
}


function metricTransition(
    before,
    after,
    unit = ""
) {

    return (
        `${displayValue(before)}${before === null || before === undefined ? "" : unit}`
        + " → "
        + `${displayValue(after)}${after === null || after === undefined ? "" : unit}`
    );
}


async function injectRfFault() {

    try {

        const siteId =
            selectedSite();


        const txPower =
            Number(
                document.getElementById(
                    "fault-tx-power"
                ).value
            );


        const result =
            await api(
                "/self-healing/inject-rf-fault",
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify({
                        site_id: siteId,
                        band: "n78",
                        tx_power_dbm: txPower
                    })
                }
            );


        showRaw(result);


        const panel =
            document.getElementById(
                "decision-panel"
            );


        if (
            result.status === "BLOCKED"
        ) {
            panel.className =
                "decision-panel decision-warning";

            document.getElementById(
                "decision-headline"
            ).textContent =
                "RF FAULT INJECTION BLOCKED";
        }
        else {
            panel.className =
                "decision-panel decision-warning";

            document.getElementById(
                "decision-headline"
            ).textContent =
                "RF FAULT INJECTED - SELF-HEAL AVAILABLE";
        }


        const before =
            result.before_scope
            || {};

        const after =
            result.after_scope
            || {};


        document.getElementById(
            "decision-summary"
        ).innerHTML = `
            <div class="decision-item">
                Status
                <strong>${badge(result.status)}</strong>
            </div>

            <div class="decision-item">
                Scope
                <strong>${result.site_id || siteId} / ${result.band || "n78"}</strong>
            </div>

            <div class="decision-item">
                Target Cells
                <strong>${(result.cell_ids || []).length}</strong>
            </div>

            <div class="decision-item">
                Forced TX
                <strong>${txPower} dBm</strong>
            </div>

            <div class="decision-item">
                Serving Cells
                <strong>${metricTransition(before.serving_cells, after.serving_cells)}</strong>
            </div>

            <div class="decision-item">
                Mean RSRP
                <strong>${metricTransition(before.mean_rsrp_dbm, after.mean_rsrp_dbm, " dBm")}</strong>
            </div>

            <div class="decision-item">
                Mean SINR
                <strong>${metricTransition(before.mean_sinr_db, after.mean_sinr_db, " dB")}</strong>
            </div>

            <div class="decision-item">
                Active UE on Scope
                <strong>${metricTransition(before.active_users, after.active_users)}</strong>
            </div>

            <div class="decision-item">
                Accepted Config Revision
                <strong>${result.active_version || "-"} / UNCHANGED</strong>
            </div>
        `;


        renderWorkflowSteps(
            result.steps
        );

        hideCandidateSections();

        await refreshAfterOperation();

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });
    }

    catch (error) {
        showError(error);
    }
}


async function injectCapacitySpike() {

    try {

        const spikeFactor =
            Number(
                document.getElementById(
                    "capacity-spike-factor"
                ).value
            );

        const result =
            await api(
                "/self-healing/inject-capacity-spike",
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify({
                        spike_factor: spikeFactor
                    })
                }
            );

        showRaw(result);

        const panel =
            document.getElementById(
                "decision-panel"
            );

        panel.className =
            "decision-panel decision-warning";

        document.getElementById(
            "decision-headline"
        ).textContent =
            result.status === "BLOCKED"
            ? "CAPACITY SPIKE INJECTION BLOCKED"
            : "CAPACITY SPIKE INJECTED - SELF-HEAL AVAILABLE";

        const beforeMax =
            result.max_prb_before
            || {};

        const afterMax =
            result.max_prb_after
            || {};

        document.getElementById(
            "decision-summary"
        ).innerHTML = `
            <div class="decision-item">
                Status
                <strong>${badge(result.status)}</strong>
            </div>

            <div class="decision-item">
                Spike Factor
                <strong>${displayValue(result.fault?.spike_factor || spikeFactor)}x</strong>
            </div>

            <div class="decision-item">
                Hotspot Area
                <strong>${displayValue(result.hotspot_area_id)}</strong>
            </div>

            <div class="decision-item">
                Global Traffic Scale
                <strong>${displayValue(result.traffic_multiplier_after)}x</strong>
            </div>

            <div class="decision-item">
                Steering
                <strong>${displayValue(result.steering_mode_before)} → ${displayValue(result.steering_mode_after)}</strong>
            </div>

            <div class="decision-item">
                Max PRB
                <strong>${displayValue(beforeMax.prb_utilization_pct)}% → ${displayValue(afterMax.prb_utilization_pct)}%</strong>
            </div>

            <div class="decision-item">
                Worst Cell
                <strong>${displayValue(afterMax.cell_id)}</strong>
            </div>

            <div class="decision-item">
                Accepted Config Revision
                <strong>${result.active_version || "-"} / UNCHANGED</strong>
            </div>
        `;

        renderWorkflowSteps(
            result.steps
        );

        hideCandidateSections();
        await refreshAfterOperation();

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });
    }

    catch (error) {
        showError(error);
    }
}


async function runSelfHealing() {

    try {

        const result =
            await api(
                "/self-healing/run",
                {
                    method: "POST"
                }
            );


        showRaw(result);


        const panel =
            document.getElementById(
                "decision-panel"
            );


        if (
            result.status === "RECOVERED"
        ) {

            panel.className =
                result.full_safe_envelope_restored
                ? "decision-panel decision-pass"
                : "decision-panel decision-warning";


            const faultType =
                (result.fault || {}).type;

            document.getElementById(
                "decision-headline"
            ).textContent =
                result.full_safe_envelope_restored
                ? (
                    faultType === "CAPACITY_SPIKE"
                    ? "SELF-HEAL COMPLETED - CAPACITY RECOVERED"
                    : "SELF-HEAL COMPLETED - ACTIVE RAN RECOVERED"
                )
                : (
                    faultType === "CAPACITY_SPIKE"
                    ? "CAPACITY REMEDIATION INCOMPLETE"
                    : "RF FAULT RECOVERED - SAFETY FINDING REMAINS"
                );
        }

        else {

            panel.className =
                "decision-panel decision-warning";


            document.getElementById(
                "decision-headline"
            ).textContent =
                result.status === "NO_ACTION"
                ? "SELF-HEAL: NO ACTIVE INJECTED FAULT"
                : "SELF-HEAL BLOCKED";
        }


        const before =
            result.before_scope
            || {};

        const after =
            result.after_scope
            || {};


        document.getElementById(
            "decision-summary"
        ).innerHTML = `
            <div class="decision-item">
                Status
                <strong>${badge(result.status)}</strong>
            </div>

            <div class="decision-item">
                Reason
                <strong>${result.reason || "-"}</strong>
            </div>

            <div class="decision-item">
                Active Config
                <strong>${result.active_version || "-"}</strong>
            </div>

            <div class="decision-item">
                Config Restored
                <strong>${result.configuration_restored === true ? "YES" : result.configuration_restored === false ? "NO" : "-"}</strong>
            </div>

            <div class="decision-item">
                Traffic Multiplier
                <strong>${displayValue(result.traffic_multiplier)}</strong>
            </div>

            <div class="decision-item">
                Steering
                <strong>${displayValue(result.steering_mode_before)} → ${displayValue(result.steering_mode_after)}</strong>
            </div>

            <div class="decision-item">
                Max PRB
                <strong>${displayValue((result.max_prb_before || {}).prb_utilization_pct)}% → ${displayValue((result.max_prb_after || {}).prb_utilization_pct)}%</strong>
            </div>

            <div class="decision-item">
                Mean RSRP
                <strong>${metricTransition(before.mean_rsrp_dbm, after.mean_rsrp_dbm, " dBm")}</strong>
            </div>

            <div class="decision-item">
                Mean SINR
                <strong>${metricTransition(before.mean_sinr_db, after.mean_sinr_db, " dB")}</strong>
            </div>

            <div class="decision-item">
                Active UE on Scope
                <strong>${metricTransition(before.active_users, after.active_users)}</strong>
            </div>

            <div class="decision-item">
                Target Recovery Improved
                <strong>${result.scope_recovery_improved === true ? "YES" : result.scope_recovery_improved === false ? "NO / CONFIG VERIFIED" : "-"}</strong>
            </div>

            <div class="decision-item">
                Full Safe Envelope
                <strong>${result.full_safe_envelope_restored === true ? badge("PASS") : result.full_safe_envelope_restored === false ? badge("FAIL") : "-"}</strong>
            </div>

            <div class="decision-item">
                Remaining Findings
                <strong>${(result.remaining_failed_checks || []).join(", ") || "NONE"}</strong>
            </div>
        `;


        renderWorkflowSteps(
            result.steps
        );

        hideCandidateSections();

        await refreshAfterOperation();

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });
    }

    catch (error) {
        showError(error);
    }
}


/* ===================================================== */
/* EVENTS */
/* ===================================================== */

async function loadEvents() {

    const events =
        await api(
            "/events"
        );


    const container =
        document.getElementById(
            "timeline"
        );


    if (
        events.length === 0
    ) {

        container.innerHTML =
            `
            <div class="muted">
                No events recorded.
            </div>
            `;

        return;
    }


    const newest =
        [...events]
            .reverse()
            .slice(
                0,
                8
            );


    container.innerHTML =
        "";


    for (
        const event
        of newest
    ) {

        const row =
            document.createElement(
                "div"
            );


        row.className =
            "event";


        const time =
            new Date(
                event.timestamp
            )
            .toLocaleTimeString(
                [],
                {
                    hour12: false
                }
            );


        row.innerHTML = `

            <div class="event-time">
                ${time}
            </div>

            <div class="event-type">
                <b>
                    ${event.type}
                </b>
            </div>

            <div class="event-status">
                ${badge(event.status)}
            </div>

            <div class="event-message">
                ${event.message}
            </div>
        `;


        container.appendChild(
            row
        );
    }
}


/* ===================================================== */
/* UI STATE */
/* ===================================================== */

function hideCandidateSections() {

    document.getElementById(
        "changes-section"
    ).classList.add(
        "hidden"
    );


    document.getElementById(
        "impact-section"
    ).classList.add(
        "hidden"
    );


    document.getElementById(
        "guardrails-section"
    ).classList.add(
        "hidden"
    );


    document.getElementById(
        "reassociation-section"
    ).classList.add(
        "hidden"
    );
}


/* ===================================================== */
/* ERROR */
/* ===================================================== */

function showError(
    error
) {

    const panel =
        document.getElementById(
            "decision-panel"
        );


    panel.className =
        "decision-panel decision-fail";


    document.getElementById(
        "decision-headline"
    ).textContent =
        "REQUEST FAILED";


    document.getElementById(
        "decision-summary"
    ).innerHTML =
        `
        <div class="decision-item">

            Error

            <strong>
                ${error.toString()}
            </strong>

        </div>
        `;


    document.getElementById(
        "raw-output"
    ).textContent =
        error.toString();
}


/* ===================================================== */
/* REFRESH */
/* ===================================================== */

async function refreshOperationalContext(
    includeEvents = false
) {

    if (
        contextRefreshInFlight
    ) {

        return;
    }


    contextRefreshInFlight =
        true;


    try {

        // /status re-observes the active RAN under one
        // authoritative backend weather snapshot.
        await loadStatus();


        // Fetch cells only after /status has refreshed the
        // active snapshot. This keeps the serving view aligned
        // with the weather / baseline context just displayed.
        await loadLiveCells();


        if (
            includeEvents
        ) {

            await loadEvents();
        }
    }

    finally {

        contextRefreshInFlight =
            false;
    }
}


async function refreshAfterOperation() {

    // Refresh status first so all following active views use the
    // same newly observed controller state.
    await loadStatus();


    await Promise.all([

        loadRanConfig(),

        loadLiveCells(),

        loadEvents(),

        loadSelfHealingState()
    ]);
}


async function loadEverything() {

    try {

        // Status is intentionally first, not parallel. It is the
        // authoritative active-RAN + weather observation.
        await loadStatus();


        await Promise.all([

            loadRanConfig(),

            loadLiveCells(),

            loadEvents(),

            loadSelfHealingState()
        ]);

    }

    catch (
        error
    ) {

        showError(
            error
        );
    }
}


loadEverything();


setInterval(
    () => {

        refreshOperationalContext(
            false
        ).catch(
            showError
        );
    },

    LIVE_CONTEXT_REFRESH_MS
);


</script>


</body>

</html>
"""
