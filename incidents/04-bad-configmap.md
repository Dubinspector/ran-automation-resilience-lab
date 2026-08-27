\# Incident 04 - Bad ConfigMap / RAN Adapter Integration Failure



\## Symptom



The Kubernetes Pod remained healthy:



\- READY: 1/1

\- STATUS: Running

\- readiness probe passed



However, the application integration pre-check failed.



`GET /precheck` returned:



`status: FAIL`



with:



`ran\_adapter\_available: false`



\## Evidence



The Pod was healthy:



`kubectl get pods`



showed:



\- READY: 1/1

\- STATUS: Running



The environment variable inside the Pod was:



`RAN\_ADAPTER\_URL=http://ran-automation-broken:8000`



The pre-check returned:



\- ran\_adapter\_available: false

\- cells\_discovered: true

\- kpi\_baseline\_collected: true



\## Hypothesis



The application itself is running, but it cannot reach the configured RAN adapter endpoint.



Possible causes include:



\- incorrect Service DNS name

\- wrong port

\- Service unavailable

\- DNS/networking issue

\- incorrect ConfigMap value



\## Investigation



The Kubernetes Pod remained Ready.



The application API was reachable through the Service.



The failure was isolated to the RAN adapter connectivity check.



The ConfigMap contained an intentionally incorrect value:



`RAN\_ADAPTER\_URL: http://ran-automation-broken:8000`



The new Pod loaded this value after a Deployment restart.



\## Root Cause



The ConfigMap contained an incorrect RAN adapter hostname.



The application was healthy at the process and Kubernetes level, but integration with the configured dependency failed.



\## Fix



Restore the correct ConfigMap value:



`RAN\_ADAPTER\_URL: http://ran-automation-service:8000`



Apply the ConfigMap:



`kubectl apply -f .\\k8s\\configmap.yaml`



Restart the Deployment so the new Pod reloads environment variables:



`kubectl rollout restart deployment/ran-automation`



\## Verification



The new Pod loaded:



`RAN\_ADAPTER\_URL=http://ran-automation-service:8000`



`GET /precheck` then returned:



\- status: PASS

\- ran\_adapter\_available: true

\- cells\_discovered: true

\- kpi\_baseline\_collected: true



\## Prevention



\- Keep dependency endpoints in external configuration.

\- Validate ConfigMap values before rollout.

\- Include dependency connectivity in operational pre-checks.

\- Restart Pods when environment-variable based ConfigMaps change.

\- Do not treat Kubernetes readiness alone as proof that external integrations are healthy.

