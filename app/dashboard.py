DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>RAN Automation Resilience Lab</title>


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
    padding: 26px 35px;

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
    font-size: 30px;
}

header p {
    margin: 8px 0 0 0;
    color: #94a3b8;
}

.container {
    max-width: 1500px;
    margin: auto;
    padding: 28px;
}

.section {
    margin-top: 30px;
}

.section h2 {
    margin-bottom: 15px;
}

.banner {
    padding: 22px;
    border-radius: 10px;
    margin-bottom: 20px;

    font-size: 25px;
    font-weight: bold;

    border:
        1px solid #334155;
}

.banner-stable {
    background: #052e16;
    color: #86efac;
}

.banner-fail {
    background: #450a0a;
    color: #fca5a5;
}

.banner-warning {
    background: #451a03;
    color: #fdba74;
}

.banner-blocked {
    background: #422006;
    color: #fde68a;
}

.grid {
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(200px, 1fr)
        );

    gap: 15px;
}

.summary-card {
    background: #1e293b;

    border:
        1px solid #334155;

    border-radius: 10px;
    padding: 18px;
}

.summary-card .title {
    color: #94a3b8;
    font-size: 12px;
    text-transform: uppercase;
}

.summary-card .value {
    margin-top: 8px;
    font-size: 23px;
    font-weight: bold;
}


/* ================================================= */
/* CURRENT DEMO OUTCOME */
/* ================================================= */

.rollout-main {
    margin-top: 20px;
    padding: 22px;

    border:
        1px solid #334155;

    border-radius: 10px;
    background: #1e293b;
}

.rollout-main-success {
    border-color: #166534;
    background: #052e16;
}

.rollout-main-fail {
    border-color: #7f1d1d;
    background: #2b1111;
}

.rollout-main-warning {
    border-color: #9a3412;
    background: #431407;
}

.rollout-main-neutral {
    border-color: #334155;
    background: #1e293b;
}

.rollout-main h2 {
    margin-top: 0;
}

.rollout-headline {
    font-size: 27px;
    font-weight: bold;
    margin-bottom: 20px;
}

.rollout-summary-grid {
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(200px, 1fr)
        );

    gap: 12px;
}

.rollout-summary-item {
    background:
        rgba(
            15,
            23,
            42,
            0.55
        );

    padding: 15px;

    border-radius: 8px;

    border:
        1px solid #334155;
}

.rollout-summary-label {
    color: #94a3b8;
    font-size: 12px;
    text-transform: uppercase;
}

.rollout-summary-value {
    margin-top: 6px;
    font-size: 20px;
    font-weight: bold;
}


/* ================================================= */
/* WORKFLOW */
/* ================================================= */

.workflow {
    background: #1e293b;

    border:
        1px solid #334155;

    border-radius: 10px;
    overflow: hidden;
}

.step {
    display: grid;

    grid-template-columns:
        45px
        minmax(180px, 1fr)
        110px
        120px;

    gap: 10px;

    align-items: center;

    padding: 12px 18px;

    border-bottom:
        1px solid #334155;
}

.step:last-child {
    border-bottom: 0;
}

.step-number {
    color: #64748b;
    font-weight: bold;
}

.pass-badge,
.fail-badge,
.warning-badge {
    display: inline-block;

    border-radius: 5px;

    padding: 4px 9px;

    font-size: 12px;
    font-weight: bold;
}

.pass-badge {
    color: #86efac;
    background: #14532d;
}

.fail-badge {
    color: #fca5a5;
    background: #7f1d1d;
}

.warning-badge {
    color: #fdba74;
    background: #7c2d12;
}


/* ================================================= */
/* INCIDENT / RECOVERY */
/* ================================================= */

.incident-panel {
    margin-top: 16px;
    padding: 20px;

    background: #2b1111;

    border:
        1px solid #7f1d1d;

    border-radius: 10px;
}

.incident-panel h2,
.incident-panel h3 {
    color: #fca5a5;
}

.recovery-strip {
    margin-top: 16px;
    padding: 18px;

    background: #052e16;

    border:
        1px solid #166534;

    border-radius: 10px;
}

.recovery-strip h3 {
    margin-top: 0;
    color: #86efac;
}


/* ================================================= */
/* CONTROLS */
/* ================================================= */

.control-panel {
    background: #1e293b;
    padding: 20px;

    border:
        1px solid #334155;

    border-radius: 10px;
}

button {
    border: 0;
    border-radius: 7px;

    padding: 12px 17px;

    margin:
        5px 6px
        5px 0;

    font-size: 14px;
    font-weight: bold;

    cursor: pointer;

    color: white;
    background: #334155;
}

button:hover {
    opacity: 0.85;
}

.btn-good {
    background: #15803d;
}

.btn-danger {
    background: #b91c1c;
}

.btn-rollout {
    background: #2563eb;
}

.btn-warning {
    background: #c2410c;
}

.description {
    margin-top: 12px;

    color: #94a3b8;

    line-height: 1.6;
    font-size: 14px;
}


/* ================================================= */
/* KPI CARDS */
/* ================================================= */

.cells-grid {
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(380px, 1fr)
        );

    gap: 18px;
}

.cell-card {
    background: #1e293b;

    border:
        1px solid #334155;

    border-radius: 10px;

    overflow: hidden;
}

.cell-header {
    padding: 17px;

    display: flex;

    justify-content:
        space-between;

    align-items: center;

    background: #172033;
}

.cell-header h3 {
    margin: 0;
}

.kpi-table {
    width: 100%;
    border-collapse: collapse;
}

.kpi-table th,
.kpi-table td {
    padding: 12px 10px;

    text-align: right;

    border-bottom:
        1px solid #334155;
}

.kpi-table th:first-child,
.kpi-table td:first-child {
    text-align: left;
}

.kpi-table th {
    color: #94a3b8;
    font-size: 12px;
}

.kpi-pass {
    color: #4ade80;
    font-weight: bold;
}

.kpi-fail {
    color: #f87171;
    font-weight: bold;
}

.delta-good {
    color: #cbd5e1;
}

.delta-bad {
    color: #f87171;
    font-weight: bold;
}


/* ================================================= */
/* THRESHOLDS */
/* ================================================= */

.threshold-box {
    background: #111827;

    border:
        1px solid #334155;

    border-radius: 8px;

    padding: 18px;

    color: #cbd5e1;

    line-height: 1.8;
}


/* ================================================= */
/* TIMELINE */
/* ================================================= */

.timeline {
    background: #1e293b;

    border:
        1px solid #334155;

    border-radius: 10px;

    padding: 20px;
}

.timeline-event {
    display: grid;

    grid-template-columns:
        110px
        110px
        90px
        1fr;

    gap: 10px;

    padding: 10px 0;

    border-bottom:
        1px solid #334155;
}

.timeline-event:last-child {
    border-bottom: 0;
}

.timeline-time {
    color: #94a3b8;
    font-family: monospace;
}

.timeline-type {
    font-weight: bold;
}


/* ================================================= */
/* RAW */
/* ================================================= */

.raw-output {
    background: #020617;

    border:
        1px solid #334155;

    padding: 18px;

    border-radius: 8px;

    max-height: 450px;

    overflow-x: auto;

    font-family: monospace;

    color: #cbd5e1;
}

.small {
    color: #94a3b8;
    font-size: 13px;
}

.hidden {
    display: none;
}


@media (
    max-width: 750px
) {

    .container {
        padding: 15px;
    }

    .cells-grid {
        grid-template-columns: 1fr;
    }

    .step {
        grid-template-columns:
            35px
            1fr
            80px;
    }

    .step-detail {
        display: none;
    }

    .timeline-event {
        grid-template-columns:
            90px
            80px
            1fr;
    }

    .timeline-status {
        display: none;
    }
}

</style>

</head>


<body>


<header>

<h1>
    RAN Automation Delivery & Resilience Lab
</h1>

<p>
    Synthetic RAN validation,
    guarded rollout,
    failure detection
    and automatic application-level rollback
</p>

</header>


<div class="container">


<!-- ================================================= -->
<!-- SYSTEM STATUS -->
<!-- ================================================= -->

<div
    id="system-banner"
    class="banner banner-stable"
>
    Loading system state...
</div>


<div class="grid">

    <div class="summary-card">

        <div class="title">
            Environment
        </div>

        <div
            id="environment"
            class="value"
        >
            -
        </div>

    </div>


    <div class="summary-card">

        <div class="title">
            Application Health
        </div>

        <div
            id="application-health"
            class="value"
        >
            -
        </div>

    </div>


    <div class="summary-card">

        <div class="title">
            Active Release
        </div>

        <div
            id="active-release"
            class="value"
        >
            -
        </div>

    </div>


    <div class="summary-card">

        <div class="title">
            Rollout State
        </div>

        <div
            id="rollout-state"
            class="value"
        >
            -
        </div>

    </div>


    <div class="summary-card">

        <div class="title">
            RAN Validation
        </div>

        <div
            id="ran-validation"
            class="value"
        >
            -
        </div>

    </div>


    <div class="summary-card">

        <div class="title">
            Safety Score
        </div>

        <div
            id="safety-score"
            class="value"
        >
            -
        </div>

    </div>

</div>


<!-- ================================================= -->
<!-- CURRENT DEMO OUTCOME -->
<!-- ================================================= -->

<div
    id="rollout-result-section"
    class="rollout-main rollout-main-neutral"
>

<h2>
    Current Demo Outcome
</h2>


<div
    id="rollout-headline"
    class="rollout-headline"
>
    READY — HEALTHY BASELINE
</div>


<div
    id="rollout-summary"
    class="rollout-summary-grid"
>

    <div class="rollout-summary-item">

        <div class="rollout-summary-label">
            Attempted Release
        </div>

        <div class="rollout-summary-value">
            -
        </div>

    </div>


    <div class="rollout-summary-item">

        <div class="rollout-summary-label">
            Active Release
        </div>

        <div class="rollout-summary-value">
            v1.0.0
        </div>

    </div>


    <div class="rollout-summary-item">

        <div class="rollout-summary-label">
            RAN Validation
        </div>

        <div class="rollout-summary-value">
            PASS
        </div>

    </div>


    <div class="rollout-summary-item">

        <div class="rollout-summary-label">
            Failed Cells
        </div>

        <div class="rollout-summary-value">
            None
        </div>

    </div>

</div>

</div>


<!-- ================================================= -->
<!-- GUARDED ROLLOUT WORKFLOW -->
<!-- ================================================= -->

<div class="section">

<h2>
    Guarded Rollout Workflow
</h2>


<div
    id="rollout-steps"
    class="workflow"
>

    <div class="step">

        <div class="step-number">
            -
        </div>

        <div>
            Waiting for guarded rollout
        </div>

        <div>
            -
        </div>

        <div class="small step-detail">
            Ready for test
        </div>

    </div>

</div>


<div
    id="incident-panel"
    class="incident-panel hidden"
>

<h2>
    RAN REGRESSION DETECTED
</h2>

<div
    id="incident-content"
>
</div>

</div>


<div
    id="recovery-panel"
    class="recovery-strip hidden"
>

<h3>
    AUTOMATIC ROLLBACK COMPLETED
</h3>

<div
    id="recovery-content"
>
</div>

</div>

</div>


<!-- ================================================= -->
<!-- CONTROLS -->
<!-- ================================================= -->

<div class="section">

<h2>
    RAN Failure & Recovery Controls
</h2>


<div class="control-panel">

<button
    class="btn-danger"
    onclick="injectRegression()"
>
    Inject Major RAN Regression
</button>


<button
    class="btn-good"
    onclick="restoreHealthy()"
>
    Restore Healthy Baseline
</button>


<button
    class="btn-rollout"
    onclick="runGuardedRollout()"
>
    Run Guarded Rollout
</button>


<button
    class="btn-warning"
    onclick="manualRollback()"
>
    Manual Application Rollback
</button>


<button
    onclick="refreshDashboard()"
>
    Refresh
</button>


<div class="description">

<b>Inject Major RAN Regression</b>
leaves the synthetic environment
in a degraded state so the failure
can be inspected directly.

<br><br>

<b>Restore Healthy Baseline</b>
returns the live RAN state to the
known-good baseline and clears the
current demo result.

<br><br>

<b>Run Guarded Rollout</b>
attempts release v1.1.0,
collects post-change KPIs,
detects unacceptable degradation
and automatically restores v1.0.0.

</div>

</div>

</div>


<!-- ================================================= -->
<!-- LIVE RAN KPI -->
<!-- ================================================= -->

<div class="section">

<h2>
    Live RAN KPI State
</h2>


<div
    id="cells-grid"
    class="cells-grid"
>
</div>

</div>


<!-- ================================================= -->
<!-- THRESHOLDS -->
<!-- ================================================= -->

<div class="section">

<h2>
    Validation Thresholds
</h2>


<div
    id="threshold-box"
    class="threshold-box"
>
    Loading thresholds...
</div>

</div>


<!-- ================================================= -->
<!-- EVENTS -->
<!-- ================================================= -->

<div class="section">

<h2>
    Operational Event Timeline
</h2>


<div
    id="timeline"
    class="timeline"
>
    No events.
</div>

</div>


<!-- ================================================= -->
<!-- RAW -->
<!-- ================================================= -->

<div class="section">

<h2>
    Last API Operation
</h2>


<pre
    id="raw-output"
    class="raw-output"
>No operation executed yet.</pre>

</div>


<div class="section small">

The event timeline is intentionally
preserved when the baseline is restored.

It represents operational history.

The automatic rollback shown here
restores simulated application and
RAN release state.

It is not an automatic Kubernetes
Deployment rollback.

</div>


</div>


<script>


// =====================================================
// API
// =====================================================

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

        throw new Error(
            `HTTP ${response.status} ` +
            `${response.statusText}`
        );
    }


    return response.json();
}


// =====================================================
// HELPERS
// =====================================================

function signed(
    value,
    unit = ""
) {

    if (value > 0) {
        return `+${value}${unit}`;
    }

    return `${value}${unit}`;
}


function statusBadge(
    status
) {

    if (
        status === "PASS"
    ) {

        return `
            <span class="pass-badge">
                PASS
            </span>
        `;
    }


    if (
        status === "ROLLED_BACK"
    ) {

        return `
            <span class="warning-badge">
                ROLLED BACK
            </span>
        `;
    }


    return `
        <span class="fail-badge">
            ${status}
        </span>
    `;
}


function formatTimestamp(
    timestamp
) {

    try {

        return new Date(
            timestamp
        ).toLocaleTimeString(
            [],
            {
                hour12: false
            }
        );

    }

    catch {

        return timestamp;
    }
}


// =====================================================
// RESET CURRENT DEMO VIEW
// =====================================================

function resetDemoView(
    headlineText =
        "READY — HEALTHY BASELINE"
) {

    const section =
        document.getElementById(
            "rollout-result-section"
        );


    section.className =
        "rollout-main rollout-main-success";


    document.getElementById(
        "rollout-headline"
    ).textContent =
        headlineText;


    document.getElementById(
        "rollout-summary"
    ).innerHTML = `

        <div class="rollout-summary-item">

            <div class="rollout-summary-label">
                Attempted Release
            </div>

            <div class="rollout-summary-value">
                -
            </div>

        </div>


        <div class="rollout-summary-item">

            <div class="rollout-summary-label">
                Active Release
            </div>

            <div class="rollout-summary-value">
                v1.0.0
            </div>

        </div>


        <div class="rollout-summary-item">

            <div class="rollout-summary-label">
                RAN Validation
            </div>

            <div class="rollout-summary-value">
                PASS
            </div>

        </div>


        <div class="rollout-summary-item">

            <div class="rollout-summary-label">
                Failed Cells
            </div>

            <div class="rollout-summary-value">
                None
            </div>

        </div>
    `;


    document.getElementById(
        "rollout-steps"
    ).innerHTML = `

        <div class="step">

            <div class="step-number">
                -
            </div>

            <div>
                Waiting for guarded rollout
            </div>

            <div>
                -
            </div>

            <div class="small step-detail">
                Ready for next test
            </div>

        </div>
    `;


    document.getElementById(
        "incident-panel"
    ).classList.add(
        "hidden"
    );


    document.getElementById(
        "recovery-panel"
    ).classList.add(
        "hidden"
    );
}


// =====================================================
// MANUAL INCIDENT OUTCOME
// =====================================================

function showManualRegressionOutcome() {

    const section =
        document.getElementById(
            "rollout-result-section"
        );


    section.className =
        "rollout-main rollout-main-fail";


    document.getElementById(
        "rollout-headline"
    ).textContent =
        "MANUAL RAN REGRESSION ACTIVE";


    document.getElementById(
        "rollout-summary"
    ).innerHTML = `

        <div class="rollout-summary-item">

            <div class="rollout-summary-label">
                Release
            </div>

            <div class="rollout-summary-value">
                v1.0.0
            </div>

        </div>


        <div class="rollout-summary-item">

            <div class="rollout-summary-label">
                Application Health
            </div>

            <div class="rollout-summary-value">
                HEALTHY
            </div>

        </div>


        <div class="rollout-summary-item">

            <div class="rollout-summary-label">
                RAN Validation
            </div>

            <div class="rollout-summary-value">
                FAIL
            </div>

        </div>


        <div class="rollout-summary-item">

            <div class="rollout-summary-label">
                Failed Cells
            </div>

            <div class="rollout-summary-value">
                CELL-001, CELL-002
            </div>

        </div>
    `;


    document.getElementById(
        "rollout-steps"
    ).innerHTML = `

        <div class="step">

            <div class="step-number">
                1
            </div>

            <div>
                Manual KPI regression injected
            </div>

            <div>
                ${statusBadge("FAIL")}
            </div>

            <div class="small step-detail">
                Inspect live KPIs
            </div>

        </div>
    `;


    document.getElementById(
        "incident-panel"
    ).classList.add(
        "hidden"
    );


    document.getElementById(
        "recovery-panel"
    ).classList.add(
        "hidden"
    );
}


// =====================================================
// SYSTEM STATUS
// =====================================================

async function loadStatus() {

    const status =
        await api(
            "/status"
        );


    document.getElementById(
        "environment"
    ).textContent =
        status.environment;


    document.getElementById(
        "application-health"
    ).textContent =
        status.application_health;


    document.getElementById(
        "active-release"
    ).textContent =
        status.active_release;


    document.getElementById(
        "rollout-state"
    ).textContent =
        status.rollout_state;


    document.getElementById(
        "ran-validation"
    ).textContent =
        status.ran_validation;


    const banner =
        document.getElementById(
            "system-banner"
        );


    banner.className =
        "banner";


    if (
        status.ran_validation
        === "FAIL"
    ) {

        banner.classList.add(
            "banner-fail"
        );

        banner.textContent =
            "RAN KPI REGRESSION DETECTED";

    }

    else if (
        status.rollout_state
        === "ROLLED_BACK"
    ) {

        banner.classList.add(
            "banner-warning"
        );

        banner.textContent =
            "ROLLBACK COMPLETED — SERVICE RECOVERED";

    }

    else if (
        status.rollout_state
        === "BLOCKED"
    ) {

        banner.classList.add(
            "banner-blocked"
        );

        banner.textContent =
            "ROLLOUT BLOCKED";

    }

    else {

        banner.classList.add(
            "banner-stable"
        );

        banner.textContent =
            "SYSTEM STABLE — RAN VALIDATION PASS";
    }
}


// =====================================================
// SAFETY
// =====================================================

async function loadSafety() {

    const safety =
        await api(
            "/safety-score"
        );


    document.getElementById(
        "safety-score"
    ).textContent =
        `${safety.total}/100`;
}


// =====================================================
// VALIDATION
// =====================================================

async function loadValidation() {

    const validation =
        await api(
            "/validation"
        );


    renderCells(
        validation.cells
    );


    if (
        validation.cells.length
        > 0
    ) {

        const thresholds =
            validation
                .cells[0]
                .thresholds;


        document.getElementById(
            "threshold-box"
        ).innerHTML = `

            <b>
                Failure thresholds
            </b>

            <br>

            PRB absolute change:
            &gt;
            ${thresholds.prb_change}
            percentage points

            <br>

            SINR degradation:
            &gt;
            ${thresholds.sinr_drop}
            dB

            <br>

            RSRP degradation:
            &gt;
            ${thresholds.rsrp_drop}
            dB

            <br>

            Active user change:
            &gt;
            ${thresholds.user_change}

            <br><br>

            <span class="small">

            SINR and RSRP negative
            deltas indicate degradation.

            Large positive or negative
            user changes are treated as
            abnormal traffic behaviour.

            </span>
        `;
    }
}


// =====================================================
// CELL CARDS
// =====================================================

function renderCells(
    cells
) {

    const grid =
        document.getElementById(
            "cells-grid"
        );


    grid.innerHTML = "";


    for (
        const cell
        of cells
    ) {

        const card =
            document.createElement(
                "div"
            );


        const cellFailed =
            Object.values(
                cell.checks
            ).includes(
                "FAIL"
            );


        card.className =
            "cell-card";


        card.innerHTML = `

        <div class="cell-header">

            <h3>
                ${cell.cell_id}
            </h3>

            ${
                statusBadge(
                    cellFailed
                    ? "FAIL"
                    : "PASS"
                )
            }

        </div>


        <table class="kpi-table">

        <thead>

        <tr>

            <th>KPI</th>
            <th>Baseline</th>
            <th>Current</th>
            <th>Delta</th>
            <th>Check</th>

        </tr>

        </thead>


        <tbody>


        ${kpiRow(
            "PRB",
            `${cell.baseline.prb_utilization}%`,
            `${cell.current.prb_utilization}%`,
            signed(
                cell.delta.prb,
                " pp"
            ),
            cell.checks.prb
        )}


        ${kpiRow(
            "SINR",
            `${cell.baseline.sinr_db} dB`,
            `${cell.current.sinr_db} dB`,
            signed(
                cell.delta.sinr,
                " dB"
            ),
            cell.checks.sinr
        )}


        ${kpiRow(
            "RSRP",
            `${cell.baseline.rsrp_dbm} dBm`,
            `${cell.current.rsrp_dbm} dBm`,
            signed(
                cell.delta.rsrp,
                " dB"
            ),
            cell.checks.rsrp
        )}


        ${kpiRow(
            "Users",
            cell.baseline.active_users,
            cell.current.active_users,
            signed(
                cell.delta.users
            ),
            cell.checks.users
        )}


        </tbody>

        </table>
        `;


        grid.appendChild(
            card
        );
    }
}


function kpiRow(
    name,
    baseline,
    current,
    delta,
    check
) {

    const fail =
        check === "FAIL";


    return `

    <tr>

        <td>
            ${name}
        </td>

        <td>
            ${baseline}
        </td>

        <td
            class="${
                fail
                    ? "kpi-fail"
                    : ""
            }"
        >
            ${current}
        </td>

        <td
            class="${
                fail
                    ? "delta-bad"
                    : "delta-good"
            }"
        >
            ${delta}
        </td>

        <td
            class="${
                fail
                    ? "kpi-fail"
                    : "kpi-pass"
            }"
        >
            ${check}
        </td>

    </tr>
    `;
}


// =====================================================
// INJECT REGRESSION
// =====================================================

async function injectRegression() {

    try {

        const result =
            await api(

                "/configuration?mode=degraded",

                {
                    method: "POST"
                }
            );


        showRaw(
            result
        );


        await refreshDashboard();


        showManualRegressionOutcome();


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


// =====================================================
// RESTORE HEALTHY
// =====================================================

async function restoreHealthy() {

    try {

        const result =
            await api(

                "/configuration?mode=healthy",

                {
                    method: "POST"
                }
            );


        showRaw(
            result
        );


        await refreshDashboard();


        resetDemoView(
            "HEALTHY BASELINE RESTORED — READY FOR NEXT TEST"
        );


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


// =====================================================
// MANUAL ROLLBACK
// =====================================================

async function manualRollback() {

    try {

        const result =
            await api(

                "/rollback",

                {
                    method: "POST"
                }
            );


        showRaw(
            result
        );


        await refreshDashboard();


        resetDemoView(
            "MANUAL ROLLBACK COMPLETED — BASELINE RESTORED"
        );


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


// =====================================================
// GUARDED ROLLOUT
// =====================================================

async function runGuardedRollout() {

    try {

        const result =
            await api(

                "/rollout",

                {
                    method: "POST"
                }
            );


        showRaw(
            result
        );


        renderRollout(
            result
        );


        await refreshDashboard();


        document
            .getElementById(
                "rollout-result-section"
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


// =====================================================
// GUARDED ROLLOUT RESULT
// =====================================================

function renderRollout(
    result
) {

    const section =
        document.getElementById(
            "rollout-result-section"
        );


    const headline =
        document.getElementById(
            "rollout-headline"
        );


    section.className =
        "rollout-main";


    if (
        result.status
        === "ROLLED_BACK"
    ) {

        section.classList.add(
            "rollout-main-warning"
        );

        headline.textContent =
            "ROLLBACK COMPLETED — FAILED RELEASE REJECTED";

    }

    else if (
        result.status
        === "DEPLOYED"
    ) {

        section.classList.add(
            "rollout-main-success"
        );

        headline.textContent =
            "ROLLOUT COMPLETED SUCCESSFULLY";

    }

    else {

        section.classList.add(
            "rollout-main-fail"
        );

        headline.textContent =
            `ROLLOUT ${result.status}`;
    }


    const failedCells =
        result.failed_validation
        ? result
            .failed_validation
            .failed_cells
        : [];


    let validationText = "-";


    if (
        result.failed_validation
        &&
        result.post_rollback_validation
    ) {

        validationText =
            `${result.failed_validation.status}` +
            " → " +
            `${result.post_rollback_validation.status}`;
    }

    else if (
        result.validation
    ) {

        validationText =
            result.validation.status;
    }


    document.getElementById(
        "rollout-summary"
    ).innerHTML = `

        <div class="rollout-summary-item">

            <div class="rollout-summary-label">
                Attempted Release
            </div>

            <div class="rollout-summary-value">
                ${
                    result.attempted_release
                    || "-"
                }
            </div>

        </div>


        <div class="rollout-summary-item">

            <div class="rollout-summary-label">
                Active Release
            </div>

            <div class="rollout-summary-value">
                ${
                    result.active_release
                    || "-"
                }
            </div>

        </div>


        <div class="rollout-summary-item">

            <div class="rollout-summary-label">
                RAN Validation
            </div>

            <div class="rollout-summary-value">
                ${validationText}
            </div>

        </div>


        <div class="rollout-summary-item">

            <div class="rollout-summary-label">
                Failed Cells
            </div>

            <div class="rollout-summary-value">
                ${
                    failedCells.length
                    > 0
                    ? failedCells.join(", ")
                    : "None"
                }
            </div>

        </div>
    `;


    renderWorkflow(
        result
    );


    renderIncidentSnapshot(
        result
    );


    renderRecovery(
        result
    );
}


// =====================================================
// WORKFLOW
// =====================================================

function renderWorkflow(
    result
) {

    const stepsElement =
        document.getElementById(
            "rollout-steps"
        );


    stepsElement.innerHTML =
        "";


    if (
        !result.steps
        ||
        result.steps.length === 0
    ) {

        return;
    }


    result.steps.forEach(
        (
            step,
            index
        ) => {

            const row =
                document.createElement(
                    "div"
                );


            row.className =
                "step";


            row.innerHTML = `

                <div class="step-number">
                    ${index + 1}
                </div>

                <div>
                    ${step.step}
                </div>

                <div>
                    ${
                        statusBadge(
                            step.status
                        )
                    }
                </div>

                <div
                    class="small step-detail"
                >
                    ${
                        step.detail
                        || ""
                    }
                </div>
            `;


            stepsElement
                .appendChild(
                    row
                );
        }
    );
}


// =====================================================
// FAILED SNAPSHOT
// =====================================================

function renderIncidentSnapshot(
    result
) {

    const panel =
        document.getElementById(
            "incident-panel"
        );


    const content =
        document.getElementById(
            "incident-content"
        );


    if (
        !result.failed_validation
    ) {

        panel.classList.add(
            "hidden"
        );

        return;
    }


    panel.classList.remove(
        "hidden"
    );


    let html = `

        <p>

            Release

            <b>
                ${result.attempted_release}
            </b>

            was technically activated,
            but post-change RAN validation
            detected unacceptable KPI
            degradation.

        </p>
    `;


    for (
        const cell
        of result
            .failed_validation
            .cells
    ) {

        if (
            !result
                .failed_validation
                .failed_cells
                .includes(
                    cell.cell_id
                )
        ) {

            continue;
        }


        html += `

        <div
            class="cell-card"
            style="margin-top:15px"
        >

        <div class="cell-header">

            <h3>
                ${cell.cell_id}
            </h3>

            <span class="fail-badge">
                FAILED
            </span>

        </div>


        <table class="kpi-table">

        <thead>

        <tr>

            <th>KPI</th>
            <th>Baseline</th>
            <th>Failed State</th>
            <th>Delta</th>
            <th>Check</th>

        </tr>

        </thead>


        <tbody>


        ${kpiRow(
            "PRB",
            `${cell.baseline.prb_utilization}%`,
            `${cell.current.prb_utilization}%`,
            signed(
                cell.delta.prb,
                " pp"
            ),
            cell.checks.prb
        )}


        ${kpiRow(
            "SINR",
            `${cell.baseline.sinr_db} dB`,
            `${cell.current.sinr_db} dB`,
            signed(
                cell.delta.sinr,
                " dB"
            ),
            cell.checks.sinr
        )}


        ${kpiRow(
            "RSRP",
            `${cell.baseline.rsrp_dbm} dBm`,
            `${cell.current.rsrp_dbm} dBm`,
            signed(
                cell.delta.rsrp,
                " dB"
            ),
            cell.checks.rsrp
        )}


        ${kpiRow(
            "Users",
            cell.baseline.active_users,
            cell.current.active_users,
            signed(
                cell.delta.users
            ),
            cell.checks.users
        )}


        </tbody>

        </table>

        </div>
        `;
    }


    content.innerHTML =
        html;
}


// =====================================================
// AUTOMATIC RECOVERY
// =====================================================

function renderRecovery(
    result
) {

    const panel =
        document.getElementById(
            "recovery-panel"
        );


    const content =
        document.getElementById(
            "recovery-content"
        );


    if (
        result.status
        !== "ROLLED_BACK"
    ) {

        panel.classList.add(
            "hidden"
        );

        return;
    }


    panel.classList.remove(
        "hidden"
    );


    content.innerHTML = `

        Attempted release:

        <b>
            ${result.attempted_release}
        </b>

        &nbsp;&nbsp; | &nbsp;&nbsp;

        Active release:

        <b>
            ${result.active_release}
        </b>

        &nbsp;&nbsp; | &nbsp;&nbsp;

        Post-rollback validation:

        ${
            statusBadge(
                result
                    .post_rollback_validation
                    .status
            )
        }

        <br><br>

        Failed RAN state was rejected
        and the known-good synthetic
        baseline was restored.
    `;
}


// =====================================================
// EVENTS
// =====================================================

async function loadEvents() {

    const events =
        await api(
            "/events"
        );


    const timeline =
        document.getElementById(
            "timeline"
        );


    if (
        events.length === 0
    ) {

        timeline.innerHTML =
            `
            <div class="small">
                No events recorded yet.
            </div>
            `;

        return;
    }


    timeline.innerHTML =
        "";


    const newestFirst =
        [...events].reverse();


    for (
        const event
        of newestFirst
    ) {

        const row =
            document.createElement(
                "div"
            );


        row.className =
            "timeline-event";


        row.innerHTML = `

            <div class="timeline-time">

                ${
                    formatTimestamp(
                        event.timestamp
                    )
                }

            </div>


            <div class="timeline-type">

                ${event.type}

            </div>


            <div class="timeline-status">

                ${
                    statusBadge(
                        event.status
                    )
                }

            </div>


            <div>

                ${event.message}

            </div>
        `;


        timeline.appendChild(
            row
        );
    }
}


// =====================================================
// RAW OUTPUT
// =====================================================

function showRaw(
    result
) {

    document.getElementById(
        "raw-output"
    ).textContent =

        JSON.stringify(
            result,
            null,
            2
        );
}


function showError(
    error
) {

    document.getElementById(
        "raw-output"
    ).textContent =
        error.toString();
}


// =====================================================
// REFRESH
// =====================================================

async function refreshDashboard() {

    try {

        await Promise.all([

            loadStatus(),

            loadSafety(),

            loadValidation(),

            loadEvents()

        ]);

    }

    catch (
        error
    ) {

        showError(
            error
        );


        const banner =
            document.getElementById(
                "system-banner"
            );


        banner.className =
            "banner banner-fail";


        banner.textContent =
            "APPLICATION API UNAVAILABLE";
    }
}


refreshDashboard();


</script>

</body>

</html>
"""