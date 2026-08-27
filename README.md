\# RAN Automation Delivery \& Resilience Lab



Personal learning lab focused on Kubernetes deployment, system integration, troubleshooting, rollout/rollback and RAN-aware operational validation.



\## Project Goal



The main engineering idea of this project is:



\*\*Kubernetes deployment success does not automatically mean service or RAN success.\*\*



A workload can be healthy from the Kubernetes perspective while a release still causes unacceptable service-level or RAN KPI degradation.



The lab demonstrates how platform health and service-level validation can be combined in a deployment workflow.



\## Architecture



```text

Synthetic RAN Environment

&#x20;       ↓

RAN Adapter API

&#x20;       ↓

Automation / Validation Logic

&#x20;       ↓

Pre-check

Safety checks

KPI validation

Rollback decision

&#x20;       ↓

Kubernetes

Deployment

Service

ConfigMap

Readiness / Liveness

Resources

Synthetic RAN Environment

The application exposes synthetic RAN data for three cells.

Example KPIs:

PRB utilization
SINR
active users
technology
cell status
alarms

This is simulated data and does not represent a real RAN implementation.

API

Implemented endpoints include:

GET /cells
GET /cells/{cell_id}/kpis
GET /alarms
GET /precheck
GET /safety-score
GET /validation
POST /configuration
POST /rollback
POST /rollout
Kubernetes

The application is containerized with a custom Docker image and deployed to a local Kubernetes cluster.

Implemented Kubernetes resources and concepts:

Deployment
ReplicaSet
Pods
ClusterIP Service
EndpointSlices
ConfigMap
environment variables
readinessProbe
livenessProbe
CPU and memory requests
CPU and memory limits
rolling updates
rollout history
rollout rollback
node cordon / uncordon
RAN-Aware Validation

The application stores a KPI baseline and compares post-change values against configurable thresholds.

Example:

CELL-001 baseline

PRB  = 54
SINR = 18 dB

After simulated release

PRB  = 91
SINR = 11 dB

Configured thresholds:

PRB increase > 20 → regression
SINR drop > 5 dB → regression

The release therefore fails service-level validation even though the Kubernetes Pod remains healthy.

Incident Scenarios

Five controlled incidents were created and investigated.

01 - ImagePullBackOff

Invalid image tag caused a new Pod to fail during image pull.

Practiced:

Pod Events
kubectl describe
ReplicaSet behavior
rolling update behavior
kubectl rollout undo
02 - Service Selector Mismatch

Pod remained healthy but the Service selector did not match its labels.

Practiced:

Service selectors
Pod labels
EndpointSlices
Service-to-Pod troubleshooting
03 - Node Cordoned

The worker node was cordoned during a rollout.

The new Pod remained Pending while the previous healthy Pod stayed available.

Practiced:

scheduling
Pending Pods
taints
cordon / uncordon
scheduler Events
04 - Bad ConfigMap / Integration Failure

The Pod remained 1/1 Running, but an incorrect RAN adapter URL caused the integration pre-check to fail.

Practiced:

ConfigMaps
environment variables
dependency validation
difference between platform health and integration health
05 - RAN KPI Regression

Kubernetes remained healthy while synthetic RAN KPI values degraded after a simulated release.

The application detected the regression and restored the previous simulated RAN state.

Practiced:

baseline comparison
post-change validation
service-level health
automatic application-level rollback
Troubleshooting Method

Incidents are investigated using:

Symptom
↓
Evidence
↓
Hypothesis
↓
Investigation
↓
Root Cause
↓
Fix
↓
Verification
↓
Prevention

The troubleshooting layer is identified before applying a fix.

Typical path:

Client
↓
Network
↓
Service
↓
EndpointSlice
↓
Pod
↓
Container
↓
Application
↓
Dependency / RAN Adapter
Repository Structure
ran-automation-resilience-lab/
│
├── app/
│   └── main.py
│
├── k8s/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── configmap.yaml
│
├── incidents/
│   ├── 01-imagepullbackoff.md
│   ├── 02-service-selector.md
│   ├── 03-node-cordoned.md
│   ├── 04-bad-configmap.md
│   └── 05-ran-kpi-regression.md
│
├── runbook/
│   └── operations.md
│
├── Dockerfile
├── requirements.txt
├── README.md
└── .gitignore
Learning Lab Disclaimer

This repository is a personal Kubernetes and RAN automation learning project created to practice deployment, system integration, troubleshooting, rollout/rollback, operational validation and resilience concepts.

It does not represent production Kubernetes or production RAN experience.

The RAN environment and KPI data are synthetic.
