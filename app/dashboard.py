DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RAN Automation Resilience Lab</title>

    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 40px;
            background: #f4f6f8;
            color: #222;
        }

        h1 {
            margin-bottom: 5px;
        }

        .subtitle {
            color: #666;
            margin-bottom: 30px;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }

        .card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        }

        .status {
            font-size: 24px;
            font-weight: bold;
        }

        .pass {
            color: green;
        }

        .fail {
            color: red;
        }

        button {
            padding: 10px 16px;
            margin: 5px;
            cursor: pointer;
            border: none;
            border-radius: 5px;
            background: #333;
            color: white;
        }

        button:hover {
            opacity: 0.8;
        }

        .danger {
            background: #b00020;
        }

        .success {
            background: #087f23;
        }

        .warning {
            background: #d97706;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
        }

        th, td {
            padding: 10px;
            border-bottom: 1px solid #ddd;
            text-align: left;
        }

        pre {
            background: #111;
            color: #eee;
            padding: 15px;
            overflow-x: auto;
            border-radius: 5px;
        }
    </style>
</head>

<body>

<h1>RAN Automation Resilience Lab</h1>

<div class="subtitle">
    Synthetic RAN delivery, validation and rollback learning environment
</div>

<div class="grid">

    <div class="card">
        <h3>Application API</h3>
        <div id="api-status" class="status">Checking...</div>
    </div>

    <div class="card">
        <h3>RAN Precheck</h3>
        <div id="precheck-status" class="status">Checking...</div>
    </div>

    <div class="card">
        <h3>RAN Validation</h3>
        <div id="validation-status" class="status">Checking...</div>
    </div>

    <div class="card">
        <h3>Safety Score</h3>
        <div id="safety-score" class="status">Checking...</div>
    </div>

</div>


<h2>RAN Simulation Controls</h2>

<div class="card">

    <button
        class="success"
        onclick="applyConfiguration('healthy')">
        Healthy Configuration
    </button>

    <button
        class="warning"
        onclick="applyConfiguration('degraded')">
        Simulate KPI Regression
    </button>

    <button
        onclick="runRollout()">
        Run Rollout
    </button>

    <button
        class="danger"
        onclick="rollback()">
        Rollback
    </button>

    <button onclick="refreshDashboard()">
        Refresh
    </button>

</div>


<h2>Cells</h2>

<table>
    <thead>
        <tr>
            <th>Cell</th>
            <th>Technology</th>
            <th>PRB Utilization</th>
            <th>SINR</th>
            <th>Active Users</th>
            <th>Status</th>
        </tr>
    </thead>

    <tbody id="cells-table">
    </tbody>
</table>


<h2>Last Operation</h2>

<pre id="operation-output">
No operation executed yet.
</pre>


<script>

async function getJson(url, options = {}) {
    const response = await fetch(url, options);

    if (!response.ok) {
        throw new Error(
            `HTTP ${response.status}: ${response.statusText}`
        );
    }

    return response.json();
}


function setStatus(elementId, status) {

    const element = document.getElementById(elementId);

    element.textContent = status;

    element.classList.remove("pass", "fail");

    if (
        status === "PASS" ||
        status === "ONLINE"
    ) {
        element.classList.add("pass");
    }

    if (
        status === "FAIL" ||
        status === "OFFLINE"
    ) {
        element.classList.add("fail");
    }
}


async function refreshDashboard() {

    try {

        const cells = await getJson("/cells");

        setStatus("api-status", "ONLINE");

        const table = document.getElementById("cells-table");

        table.innerHTML = "";

        for (const cell of cells) {

            const row = document.createElement("tr");

            row.innerHTML = `
                <td>${cell.cell_id}</td>
                <td>${cell.technology}</td>
                <td>${cell.prb_utilization}%</td>
                <td>${cell.sinr_db} dB</td>
                <td>${cell.active_users}</td>
                <td>${cell.status}</td>
            `;

            table.appendChild(row);
        }


        const precheck = await getJson("/precheck");

        setStatus(
            "precheck-status",
            precheck.status
        );


        const validation = await getJson("/validation");

        setStatus(
            "validation-status",
            validation.status
        );


        const safety = await getJson("/safety-score");

        const safetyElement =
            document.getElementById("safety-score");

        safetyElement.textContent =
            `${safety.total}/100`;

        safetyElement.classList.remove(
            "pass",
            "fail"
        );

        safetyElement.classList.add(
            safety.rollout_allowed
                ? "pass"
                : "fail"
        );

    }

    catch (error) {

        setStatus(
            "api-status",
            "OFFLINE"
        );

        document.getElementById(
            "operation-output"
        ).textContent = error;
    }
}


async function applyConfiguration(mode) {

    try {

        const result = await getJson(
            `/configuration?mode=${mode}`,
            {
                method: "POST"
            }
        );

        showResult(result);

        await refreshDashboard();

    }

    catch (error) {
        showResult({
            error: error.toString()
        });
    }
}


async function runRollout() {

    try {

        const result = await getJson(
            "/rollout",
            {
                method: "POST"
            }
        );

        showResult(result);

        await refreshDashboard();

    }

    catch (error) {
        showResult({
            error: error.toString()
        });
    }
}


async function rollback() {

    try {

        const result = await getJson(
            "/rollback",
            {
                method: "POST"
            }
        );

        showResult(result);

        await refreshDashboard();

    }

    catch (error) {
        showResult({
            error: error.toString()
        });
    }
}


function showResult(result) {

    document.getElementById(
        "operation-output"
    ).textContent =
        JSON.stringify(
            result,
            null,
            2
        );
}


refreshDashboard();

</script>

</body>
</html>
"""