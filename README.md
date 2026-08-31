# RAN Automation Delivery & Resilience Lab

Personal learning lab focused on Kubernetes deployment, system integration, troubleshooting, rollout/rollback, RAN-aware operational validation and self-healing automation.

> **Learning Lab Disclaimer**
>
> This repository is a personal Kubernetes and RAN automation learning project created to practice deployment, system integration, troubleshooting, rollout/rollback, operational validation and resilience concepts.
>
> It uses synthetic RAN topology, traffic and configuration data and a physics-inspired RF model. It does not represent production Kubernetes or production RAN experience.

---

## Project Goal

The main engineering idea of this project is:

**Kubernetes deployment success does not automatically mean service or RAN success.**

A workload can be healthy from the Kubernetes perspective while a release still causes unacceptable service-level or RAN KPI degradation.

The lab demonstrates how platform health, RAN-domain validation and automated recovery can be combined in one delivery and resilience workflow.

---

## Current Lab Version

Current application release candidate:

```text
APP-v2.6.0
```

Current immutable Kubernetes image candidate for the v2.6 AI-gated control update:

```text
ran-automation-resilience-lab:v2.6.0-r1
```

Version v2.6.0 keeps the v2.4 deterministic network-wide optimizer authoritative, evolves the v2.5 AI advisor into a bounded APPROVE / HOLD / ABSTAIN decision gate, and adds a single-process safety supervisor. The supervisor can submit only the exact deterministic TX-power or electrical-tilt candidate through the existing guarded-apply path. Every applied change remains pending until the next observation cycle verifies a healthy RAN. An unhealthy post-change state forces rollback to the previous verified-healthy checkpoint. Five consecutive bad AI-approved actuation outcomes open a circuit breaker and disable further AI-gated actuation until a healthy manual reset. Direct model-to-RAN actuation remains impossible.

The previously validated v2.2.2/v2.3.1 baseline demonstrated:

- healthy default RAN state across all traffic profiles
- guarded configuration promotion
- automatic rejection and rollback of harmful RAN changes
- injected RF degradation followed by RF self-healing
- injected local capacity congestion followed by capacity recovery
- Kubernetes liveness/readiness separation
- application remaining alive during long controller operations
- no configuration revision increment for fault injection or recovery actions
- full regression suite passing

---

## System Architecture

The lab is intentionally split into layers with clear responsibilities.

```text
Operator / Dashboard / REST client
               |
               v
        FastAPI API layer
               |
               v
   RanAutomationController
               |
               v
       RAN Evaluation Engine
          /             \
         v               v
     RF Model       Traffic Model
         \               /
          \             /
           v           v
          RAN KPI State
               |
               v
      Guardrails / Validation
               |
        +------+------+
        |      |      |
        v      v      v
     PROMOTE ROLLBACK RECOVER
```

### API layer

The FastAPI layer exposes the system to operators and external clients.

Its responsibility is transport and request/response handling.

It does **not** own RF calculations or rollout policy.

### RAN automation controller

The controller orchestrates the control loop.

It:

- freezes the evaluation context when required
- builds candidate configurations
- invokes RAN evaluation
- runs pre-checks
- evaluates guardrail results
- promotes safe configurations
- rejects and rolls back unsafe configurations
- manages fault state
- selects recovery workflows

### RAN evaluation engine

The RAN engine combines configuration, RF evaluation, traffic demand and KPI generation into a normalized RAN state.

It provides the domain state used by guardrails and controller decisions.

### RF model

The RF model is geography-aware and physics-inspired.

It evaluates effects such as:

- UE-to-site geometry
- carrier frequency
- antenna azimuth
- electrical tilt
- antenna pattern
- transmit power
- path loss
- propagation condition
- co-channel interference
- thermal noise
- weather attenuation

The purpose is to derive plausible RF outcomes rather than directly injecting arbitrary KPI penalties.

Representative RF outputs include:

- RSRP
- SINR
- received power
- interference
- propagation condition
- serving-cell candidates

### Traffic model

The traffic model converts RF serviceability and demand into service and capacity behavior.

It models:

- time-of-day traffic profiles
- active UE demand
- serving-cell association
- load-aware steering
- capacity-recovery steering
- estimated cell capacity
- PRB utilization
- served and unserved active UEs

A strong RF signal does not automatically mean the best traffic-placement decision. Coverage and capacity are evaluated together.

### Guardrails

Guardrails evaluate the **resulting network behavior**, not only the requested configuration values.

The controller therefore follows this pattern:

```text
candidate configuration
        |
        v
RF + traffic evaluation
        |
        v
resulting KPI state
        |
        v
guardrail validation
        |
        +---- PASS ---> PROMOTE
        |
        +---- FAIL ---> ROLLBACK / BLOCK
```

---

## Kubernetes Runtime Architecture

```text
Deployment
    |
    v
ReplicaSet
    |
    v
Pod
    |
    v
Application container

Service
    |
    v
EndpointSlice
    |
    v
Pod IP
```

The Kubernetes deployment uses:

- `Deployment`
- `ReplicaSet`
- `Pod`
- `ClusterIP Service`
- `EndpointSlice`
- `ConfigMap`
- resource requests and limits
- readiness probe
- liveness probe

The final probe design intentionally separates process liveness from controller readiness:

```text
Liveness:
TCP socket on port 8000

Readiness:
HTTP GET /cells
```

This distinction matters because a long-running controller operation can temporarily block domain-state access without meaning that the application process is dead.

---

## Control Loops

### 1. Guarded configuration apply

A normal configuration change follows:

```text
OBSERVE
   |
   v
PRE-CHECK
   |
   v
BUILD CANDIDATE
   |
   v
EVALUATE RF + TRAFFIC
   |
   v
VALIDATE GUARDRAILS
   |
   +---- PASS ---> PROMOTE
   |
   +---- FAIL ---> ROLLBACK
```

A safe candidate becomes the new known-good configuration.

A failed candidate does not become active and does not increment the accepted configuration revision.

Rollback returns to the last intentionally accepted known-good state, not necessarily the original factory baseline.

---

### 2. RF self-healing

RF self-healing is a separate workflow from normal configuration acceptance.

Example lab scenario:

```text
healthy RAN
   |
   v
inject RF degradation
   |
   v
TX power reduced on selected cells
   |
   v
RSRP / SINR / service degradation
   |
   v
self-healing trigger
   |
   v
restore known-good RF parameters
   |
   v
verify safe envelope
   |
   v
RECOVERED
```

This demonstrates that rollback and self-healing are different concepts:

- rollback answers: **Was my requested change safe?**
- self-healing answers: **The network is already degraded; what remediation should I perform?**

---

### 3. Capacity self-healing

Capacity congestion uses a different actuator from RF degradation.

Final validated flow:

```text
healthy baseline
max PRB 75.0 %
        |
        v
local capacity hotspot
        |
        v
max PRB 100.0 %
        |
        v
capacity fault detected
        |
        v
LOAD_AWARE -> CAPACITY_RECOVERY
        |
        v
split traffic steering
        |
        v
max PRB 84.4 %
        |
        v
RECOVERED
```

The 85% PRB guardrail was kept unchanged.

Instead of weakening the guardrail, the synthetic normal-load calibration was adjusted to provide realistic operational headroom.

Recovery does not create a new RAN configuration revision because the accepted RF configuration itself is not being replaced.

---

### 4. Network-wide read-only optimization evaluator (v2.4)

The v2.4 update separates **safety** from **optimality**. A configuration can PASS guardrails and still be suboptimal. Every 60 seconds the evaluator therefore performs:

```text
CAPTURE one frozen context
weather + traffic clock + traffic multiplier + UE demand context
        |
        v
RE-EVALUATE complete active RAN
        |
        v
SCREEN ALL CONFIGURED CELLS
        |
        v
SHORTLIST highest-priority opportunities
        |
        v
BOUNDED SINGLE-ACTUATOR SEARCH
TX power / electrical tilt / traffic steering
        |
        v
RF + UE association + interference + traffic + PRB
        |
        v
EXISTING GUARDRAILS
        |
        +---- FAIL ---> reject candidate
        |
        v
NETWORK-WIDE OBJECTIVE
        |
        +---- no meaningful gain ---> NO_ACTION
        |
        +---- best safe gain -------> OPPORTUNITY_FOUND

Automatic actuation: DISABLED
```

Factory and known-good values are only **candidate seeds**. The optimizer does not recommend a previous value because it is previous. Every candidate is re-simulated against the same context and must both PASS guardrails and improve the transparent network-wide objective.

The objective uses service continuity as a hard priority through the existing guardrails, then ranks safe candidates using network-wide changes such as weighted SINR, weighted RSRP, max/p95 PRB, degraded users and served ratio. A small change-magnitude penalty avoids recommending unnecessary parameter movement. The weights are learning-lab policy, not operator policy.

The complete cell inventory is scanned, but the optimizer intentionally avoids brute-forcing all multi-cell combinations. It shortlists a few cells and evaluates a bounded number of single-actuator candidates. This preserves explainability and avoids combinatorial explosion and excessive CPU load.

Bandwidth expansion is intentionally not searched because high PRB alone does not prove that additional licensed spectrum, carrier capability or hardware support is available.

The dashboard exposes both:

```text
RAN guardrail state: HEALTHY / OUTSIDE_SAFE_ENVELOPE
Optimization state:  NO_MEANINGFUL_GAIN / OPPORTUNITY_FOUND
```

This makes a safe-but-suboptimal case explicit. For example, a manually accepted TX-power increase can remain `PASS` while the optimizer later recommends a lower TX value if the full-network simulation predicts better neighbor SINR / PRB behavior without service loss.

The evaluator is read-only. Any recommended RF change still requires the existing guarded-apply path; autonomous actuation would additionally require authorization, persistence, auditability, idempotency, distributed coordination / leader election and explicit rollout policies.

---

## Important Engineering Principle: Match the Actuator to the Failure

Different failure classes require different remediation.

Examples:

```text
RF degradation
    -> restore RF configuration such as TX power / tilt

Capacity congestion
    -> traffic steering / load redistribution

Application process failure
    -> Kubernetes restart / rollout action

Bad application release
    -> Kubernetes Deployment rollback

Bad RAN configuration candidate
    -> RAN configuration rollback
```

A Kubernetes rollback and a RAN configuration rollback are therefore different operations at different layers.

---

## Synthetic RAN Scenario

The lab uses synthetic sites and cells around the Jesenice area.

The scenario contains multiple sites, sectors and radio layers including:

- 5G n78
- 5G n28
- LTE Band 3

The topology is learning-lab data and must not be interpreted as an exact real operator deployment.

The RF model uses geography and physics-inspired calculations to make configuration changes produce internally consistent effects.

---

## Key KPIs

### RSRP

Reference Signal Received Power represents received reference-signal strength.

It is influenced by factors including:

- transmit power
- distance
- frequency
- path loss
- antenna direction
- antenna gain
- electrical tilt

### SINR

Signal-to-Interference-plus-Noise Ratio represents signal quality relative to interference and noise.

Increasing transmit power is therefore not automatically beneficial because it can improve one link while increasing interference for others.

### PRB utilization

Physical Resource Block utilization is used as a capacity/load indicator.

In this lab it arises from traffic demand relative to estimated radio capacity rather than from an arbitrary injected KPI value.

---

## Traffic Profiles

The traffic model supports time-of-day profiles such as:

- `NIGHT`
- `EARLY_MORNING`
- `MORNING_COMMUTE`
- `DAYTIME`
- `EVENING_BUSY_HOUR`
- `EVENING`
- `LATE_EVENING`

The final synthetic normal-traffic multiplier is:

```text
0.25
```

This leaves enough operational headroom for the healthy busy-hour baseline while still allowing a local hotspot to produce a real guardrail failure.

---

## API Overview

Representative endpoints include:

```text
GET  /
GET  /status
GET  /weather
GET  /baseline-health
GET  /cells
GET  /cells/{id}/kpis
GET  /alarms
GET  /events
GET  /precheck
GET  /safety-score
GET  /validation
GET  /ran-config

POST /ran-config/evaluate
POST /ran-config/guarded-apply
POST /ran-config/restore-baseline

GET  /self-healing/status
POST /self-healing/inject-rf-fault
POST /self-healing/inject-capacity-spike
POST /self-healing/run

GET  /optimization/status
POST /optimization/evaluate-now
```

Legacy configuration endpoints intentionally return HTTP 410 where applicable.

---

## Troubleshooting Scenarios Practiced

### ImagePullBackOff

A nonexistent image tag was deployed.

Evidence:

- Pod rollout failure
- image pull events
- old Pod remaining available during RollingUpdate

Resolution:

- inspect `kubectl describe`
- identify bad image reference
- perform Kubernetes rollout recovery

---

### Service selector mismatch

Pods were Running but the Service had no usable endpoints.

Evidence:

```text
Pods: Running
EndpointSlice: empty
```

Resolution:

- compare Service selector with Pod labels
- repair selector
- verify EndpointSlice population

This demonstrates that Pod health and service routing are separate concerns.

---

### Scheduling failure

A worker node was cordoned and a replacement Pod remained Pending.

Evidence came from scheduler Events rather than application logs.

Resolution:

- inspect scheduling Events
- identify node availability constraint
- uncordon the worker
- verify reconciliation

---

### Bad ConfigMap integration value

The Pod itself was healthy but the external integration pre-check failed.

The important lesson was that environment variables sourced from a ConfigMap are consumed by the process at Pod startup.

Changing the ConfigMap alone does not rewrite the environment of an already running process.

---

### Kubernetes healthy, RAN unhealthy

A Kubernetes deployment can be technically successful while the resulting RAN state fails service-level validation.

This is one of the central lessons of the lab.

---

### Liveness probe incident

A long capacity-hotspot search held the controller lock.

The readiness endpoint `/cells` depended on that lock.

When liveness also used `/cells`, the kubelet interpreted controller unavailability as process failure and restarted the container.

Evidence included:

- liveness probe timeouts
- kubelet `Killing` events
- exit code 137
- no Python traceback
- normal application shutdown logs

The fix was not to hide the controller delay.

Instead, process liveness and controller readiness were separated:

```text
Liveness -> TCP port 8000
Readiness -> HTTP /cells
```

This is an example of evidence-driven troubleshooting across application and Kubernetes boundaries.

---

## Troubleshooting Method

The lab uses the following operational sequence:

```text
Symptom
   |
   v
Evidence
   |
   v
Hypothesis
   |
   v
Investigation
   |
   v
Root Cause
   |
   v
Smallest Correct Fix
   |
   v
Verification
   |
   v
Prevention
```

Useful Kubernetes evidence sources include:

```text
kubectl get pods
kubectl get deployments
kubectl get events
kubectl describe pod
kubectl logs
kubectl logs --previous
kubectl describe service
kubectl get endpointslice
kubectl rollout status
```


---

## AI Engineering Decision Gate + Safety Supervisor (v2.6)

v2.6 deliberately does **not** turn the LLM into an unconstrained RAN controller.
The deterministic network model still owns physics, full-cell screening, candidate generation, hard guardrails and network-wide objective ranking.
The AI gets one bounded candidate and may return only `APPROVE`, `HOLD` or `ABSTAIN` plus the engineering assessment.

```text
synthetic RAN / weather / UE / traffic
                |
                v
physics-inspired RAN engine
                |
                v
network-wide deterministic optimizer
(all configured cells screened; bounded candidate search)
                |
                v
hard guardrails + transparent objective
                |
                v
BEST SAFE CANDIDATE
                |
                v
AI bounded decision gate
APPROVE / HOLD / ABSTAIN
                |
        APPROVE only
                v
deterministic safety supervisor
                |
                v
guarded_apply(EXACT optimizer value)
        |                   |
        | PASS              | FAIL
        v                   v
pending verification     rollback/reject
        |
        v
next observation cycle
        |                   |
        | HEALTHY           | UNHEALTHY
        v                   v
promote safety          FORCE RESTORE
checkpoint              previous verified-healthy checkpoint
                            |
                            v
                   bad-AI outcome strike
                            |
                     5 consecutive strikes
                            v
                   CIRCUIT BREAKER OPEN
                   AI-gated actuation disabled
```

### What AI receives

The provider input remains bounded and inspectable:

```text
current_state
candidate_result
network_effect
top_affected_cells
guardrails
alarms
weather
traffic
```

`candidate_result` is produced by deterministic code. The model cannot return a replacement target cell, parameter or target value because these fields are not part of its output schema. The supervisor copies the exact optimizer result into the guarded apply request.

### What AI returns

```text
control_decision: APPROVE | HOLD | ABSTAIN
engineering_interpretation
likely_cause
decision_reason
risk_level
confidence
rationale
recommended_verification
alternative_hypothesis
evidence_limitations
```

### Deterministic policy gate after AI

Even `APPROVE` is not sufficient on its own. The supervisor independently requires:

- current optimizer `ran_state == HEALTHY`,
- `optimization_state == OPPORTUNITY_FOUND`,
- deterministic candidate guardrail verdict `PASS`,
- positive objective gain,
- complete target/value data,
- auto-actuator allowlist match,
- no `HIGH` AI risk,
- no `LOW` AI confidence,
- no active `CRITICAL` alarm.

For v2.6, automatic actuation is intentionally restricted to bounded RF configuration changes:

```text
tx_power_dbm
electrical_tilt_deg
```

`TRAFFIC_STEERING` remains outside the automatic AI path because it belongs to the separate capacity-recovery/policy actuator path already present in the lab. This preserves the rule that different failure classes use different actuators.

### Post-change verification and rollback

Before an AI-approved change, the supervisor stores the currently verified-healthy controller configuration as a safety checkpoint. `guarded_apply()` still performs its normal precheck and candidate guardrails. If the change applies, an immediate health check must pass and the change enters `PENDING_VERIFICATION`.

At the next control cycle, a fresh health observation is the acceptance window:

- `PASS` -> the applied configuration becomes the new verified-healthy safety checkpoint and the bad-outcome counter resets to zero.
- `FAIL` -> the supervisor calls the separately authorized safety-checkpoint restore path and verifies the rollback result.
- rollback does not restore health -> circuit opens immediately because the issue may no longer be attributable to the AI configuration change.

### Five-strike circuit breaker

A strike means an **AI-approved state-changing attempt produced a bad actuation outcome**. It is not simply an AI API error.

Counts as a strike:

- exact AI-approved candidate is rejected/rolled back by guarded apply,
- immediate post-apply health check fails,
- next-cycle post-change verification becomes unhealthy or errors.

Does **not** count as a strike because no actuation occurs:

- provider timeout/unavailability,
- malformed AI output,
- `HOLD`,
- `ABSTAIN`,
- deterministic pre-gate blocks the candidate,
- baseline becomes unsafe before apply.

After 5 consecutive bad AI-approved outcomes, the circuit state becomes `OPEN`. Optimizer evaluation remains available read-only, but AI-gated actuation stops. Reset is explicit and accepted only while the current RAN baseline is healthy.

### 60-second cadence

Default:

```text
AI_CONTROL_INTERVAL_SECONDS=60
AI_CONTROL_BAD_DECISION_THRESHOLD=5
```

The supervisor is single-threaded and does not overlap control cycles. It uses a fixed start-to-start cadence when the complete optimizer + AI + verification cycle finishes inside the configured period. `duration_seconds` and `interval_overrun` are exposed in status. If a cycle takes longer than 60 seconds, increase the interval rather than running concurrent decisions.

The deterministic optimizer still screens the complete configured-cell inventory; the AI does not need raw per-UE or raw all-cell telemetry to redo RF mathematics. It receives the optimizer's bounded engineering evidence, network effect and top affected cells. This keeps the LLM out of the physics authority boundary.

### Failure behavior

The AI provider is optional for observation but **fail-closed for actuation**:

- missing `OPENAI_API_KEY` -> no AI-gated change,
- provider timeout/HTTP error -> no AI-gated change,
- malformed structured output -> no AI-gated change,
- deterministic optimizer remains available,
- Kubernetes liveness/readiness never depend on the AI provider.

Direct AI actuation is always disabled. The model only returns a decision token. State-changing calls are made by deterministic application code and still pass through the existing guarded controller.

New v2.6 endpoints:

```text
GET  /ai-control/status
POST /ai-control/run-once
POST /ai-control/reset-circuit-breaker
```

Existing AI inspection endpoints remain:

```text
GET  /ai-advisor/status
GET  /ai-advisor/input-preview
POST /ai-advisor/analyze-latest
```

`/ai-advisor/analyze-latest` returns a decision and assessment but does not actuate anything by itself.

---

## Testing Strategy

The lab contains deterministic regression tests for:

- RF model behavior
- traffic modeling
- Dolní Jirčany radio layers
- site geometry
- RAN engine integration
- UE reassociation
- guardrails
- guardrail failures
- controller state machine
- RF self-healing
- healthy baseline across traffic profiles
- capacity self-healing
- network-wide configured-cell screening
- bounded physics/UE/weather candidate search
- safe-but-suboptimal optimization detection
- transparent network-wide objective ranking
- read-only evaluator / dashboard widget injection

The v2.2.2 regression suite and v2.3.1 periodic evaluator were validated before this extension. The v2.4 package adds an acceptance scenario that intentionally promotes `CELL-JES-B-N28` from 40 to 45 dBm and verifies that any lower-TX recommendation is selected by re-simulated network outcome, not by rollback history. Run it together with the existing RF and capacity regression tests before committing the update.

Important final validated results include:

```text
RF self-healing:
OVERALL SELF-HEALING TEST: PASS

Capacity recovery:
baseline PRB: 75.0 %
fault PRB:    100.0 %
recovery PRB: 84.4 %
safe envelope restored: True

OVERALL V2.2 HEALTHY/CAPACITY TEST: PASS
```

---

## Repository Structure

```text
ran-automation-resilience-lab/
|
├── app/
|   ├── main.py
|   ├── dashboard.py
|   ├── ran_controller.py
|   ├── optimization_evaluator.py
|   ├── ai_advisor.py
|   ├── ran_engine.py
|   ├── rf_model.py
|   ├── traffic_model.py
|   └── ...
|
├── k8s/
|   └── deployment.yaml
|
├── incidents/
|
├── runbook/
|
├── tests / regression scripts
|
├── Dockerfile
├── README.md
└── .gitignore
```

---

## What This Lab Demonstrates

The project is designed to practice the kind of thinking required when operating an integrated automation platform:

- understand component boundaries
- distinguish platform health from domain health
- work with Kubernetes reconciliation and rollout behavior
- validate system integrations
- reason from logs and Events
- use domain KPIs as operational evidence
- define guardrails and acceptance criteria
- maintain known-good state
- select remediation based on failure class
- continuously evaluate RAN state without automatically actuating changes
- distinguish a safe configuration from an optimal configuration
- scan the full configured-cell inventory and bound the candidate search
- rank safe candidates by transparent network-wide RF / service / capacity evidence
- produce concrete cell-level recommendations with predicted network impact
- keep AI advisory separate from deterministic RF physics and guardrails
- degrade gracefully when the external AI provider is unavailable
- verify recovery rather than assuming success

---

## Interview-Safe Description

A concise description of the project is:

> I built my own Kubernetes learning lab around a simulated RAN automation delivery and resilience workflow. I containerized the application, deployed it on Kubernetes, introduced controlled infrastructure, integration, RF and capacity failures, performed root-cause analysis, and practiced rollout, rollback and self-healing procedures. I added a network-wide deterministic optimizer that screens all configured cells, evaluates bounded candidates under one frozen context and rejects unsafe candidates with hard guardrails. In v2.6 I added a bounded AI decision gate: the model can only approve, hold or abstain on the exact deterministic candidate. A separate safety supervisor owns guarded apply, next-window health verification, forced rollback to the previous verified-healthy checkpoint and a five-strike circuit breaker. Direct AI-to-RAN actuation is not allowed. The RAN environment is synthetic and uses a physics-inspired RF model. This is hands-on learning-lab experience, not production Kubernetes or production RAN experience.

---

## Status

Validated baseline before the v2.4 network-wide optimizer extension:

```text
v2.2.2 application runtime: validated
v2.2.2 Kubernetes deployment: validated
RF self-healing: PASS
Capacity self-healing: PASS
v2.2.2 full local regression suite: PASS
```

For v2.4.0, run `test_optimization_evaluator.py` plus the existing self-healing and capacity regression tests. Then run a container startup/API smoke test, deploy the immutable `v2.4.0` image, verify `/optimization/status`, and confirm the safe-but-suboptimal 45 dBm scenario before committing the update.


The v2.5 lineage used `test_ai_advisor.py` for a read-only, on-demand advisor. In v2.6 the same test validates the bounded structured decision schema while `test_ai_control_loop.py` validates the new state-changing supervisor path with a mocked provider. The AI provider is never part of Kubernetes liveness/readiness.

For v2.6.0, run both tests plus the unchanged v2.4 optimizer and existing self-healing/capacity regressions. Validate the 60-second supervisor status, exact candidate mapping, pending verification, forced checkpoint rollback, five-strike circuit breaker, healthy-only reset and provider fail-closed actuation behavior before rollout.
