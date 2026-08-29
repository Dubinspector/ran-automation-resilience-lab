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

Current application release:

```text
APP-v2.2
```

Current immutable Kubernetes image used by the final validated lab:

```text
ran-automation-resilience-lab:v2.2.2
```

The final v2.2.2 regression and Kubernetes validation demonstrated:

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

The final full regression suite passed after v2.2.2.

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
- verify recovery rather than assuming success

---

## Interview-Safe Description

A concise description of the project is:

> I built my own Kubernetes learning lab around a simulated RAN automation delivery and resilience workflow. I containerized the application, deployed it on Kubernetes, introduced controlled infrastructure, integration, RF and capacity failures, performed root-cause analysis, and practiced rollout, rollback and self-healing procedures. The RAN environment is synthetic and uses a physics-inspired RF model. This is hands-on learning-lab experience, not production Kubernetes or production RAN experience.

---

## Status

Final v2.2.2 lab state:

```text
Application runtime: validated
Kubernetes deployment: validated
RF self-healing: PASS
Capacity self-healing: PASS
Full local regression suite: PASS
```
