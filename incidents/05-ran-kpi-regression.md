\# Incident 05 - RAN KPI Regression with Automatic Rollback



\## Symptom



The Kubernetes application remained healthy:



\- Pod READY: 1/1

\- STATUS: Running

\- no container restart

\- readiness and liveness probes passed



However, after a simulated release change, RAN KPI validation failed.



The rollout workflow returned:



\- status: ROLLED\_BACK

\- attempted\_release: v1.1.0

\- active\_release: v1.0.0

\- failed\_cells: CELL-001



\## Evidence



Before the simulated change, CELL-001 baseline KPI values were:



\- PRB utilization: 54

\- SINR: 18 dB



The simulated new release changed CELL-001 to:



\- PRB utilization: 91

\- SINR: 11 dB



The validation logic compares post-change KPI values with the baseline.



Configured thresholds were:



\- PRB\_THRESHOLD: 20

\- SINR\_THRESHOLD: 5



The post-change validation detected CELL-001 as regressed.



At the same time:



`kubectl get pods`



still showed:



\- READY: 1/1

\- STATUS: Running



\## Hypothesis



The deployment is technically healthy at the Kubernetes level, but the release caused a functional or service-level regression in RAN KPI behavior.



Possible causes include:



\- configuration change negatively affecting RAN behavior

\- release logic causing higher PRB utilization

\- release logic causing lower SINR

\- regression not visible through Kubernetes probes



\## Investigation



Kubernetes health checks continued to pass.



The application process was running and reachable.



The failure was therefore not located in:



\- scheduling

\- image pull

\- container startup

\- Service routing

\- readiness

\- liveness



The RAN-aware post-change validation compared the current KPI values with the saved baseline.



For CELL-001:



PRB increase:



`91 - 54 = 37`



This exceeded the configured threshold of 20.



SINR drop:



`18 - 11 = 7`



This exceeded the configured threshold of 5.



Therefore the release failed the RAN-aware validation.



\## Root Cause



The simulated release introduced a RAN KPI regression on CELL-001.



Kubernetes health remained green because the application process itself was healthy.



The regression was only visible at the service/RAN validation layer.



\## Fix



The application rollout workflow automatically restored the baseline RAN state.



It also restored the simulated active release from:



`v1.1.0`



to:



`v1.0.0`



\## Verification



The rollout endpoint returned:



`status: ROLLED\_BACK`



with:



`failed\_cells: \["CELL-001"]`



The active release returned to:



`v1.0.0`



The Kubernetes Pod remained:



\- READY: 1/1

\- STATUS: Running



After rollback, RAN validation returned PASS.



\## Prevention



\- Do not use Kubernetes readiness alone as a release success criterion.

\- Capture a KPI baseline before rollout.

\- Perform post-change RAN-aware validation.

\- Define measurable regression thresholds.

\- Use canary rollout before full deployment.

\- Automatically rollback when service-level KPI validation fails.

\- Verify KPI recovery after rollback.



\## Key Lesson



Kubernetes deployment success does not guarantee service or RAN success.



A rollout can be technically healthy at the platform level while still producing unacceptable operational behavior.



This incident demonstrates why deployment validation must include both:



\- Kubernetes/platform health

\- RAN/service-level health



Note: the automatic rollback in this incident is implemented inside the learning-lab application and restores simulated RAN/release state. It is not an automatic Kubernetes `kubectl rollout undo`.

