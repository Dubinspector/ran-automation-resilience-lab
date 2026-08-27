\# Incident 02 - Service Selector Mismatch



\## Symptom



The application Pod was healthy and Running, but the Kubernetes Service had no endpoints.



`kubectl get pods` showed:



\- READY: 1/1

\- STATUS: Running



However, `kubectl get endpointslices` showed:



\- PORTS: `<unset>`

\- ENDPOINTS: `<unset>`



\## Evidence



`kubectl describe service ran-automation-service` showed:



`Selector: app=ran-automation-broken`



`kubectl get pods --show-labels` showed:



`app=ran-automation`



The Service selector did not match the Pod label.



\## Hypothesis



The Service is not routing traffic because it cannot select any Pod.



Possible causes include:



\- incorrect Service selector

\- incorrect Pod label

\- wrong namespace

\- Pods not Ready



\## Investigation



The Pod was Running and Ready.



The Service existed and had a valid ClusterIP.



The EndpointSlice was empty.



Comparing the Service selector and Pod labels showed:



Service:



`app=ran-automation-broken`



Pod:



`app=ran-automation`



\## Root Cause



The Service selector did not match the Pod label.



Because of the selector mismatch, Kubernetes could not associate the Service with the application Pod.



\## Fix



Restore the Service selector to:



`app: ran-automation`



Then apply the corrected manifest:



`kubectl apply -f .\\k8s\\service.yaml`



\## Verification



`kubectl get endpointslices` showed:



\- Port: 8000

\- Endpoint: `10.244.1.7`



Then traffic through the Service was verified using port-forward:



`kubectl port-forward service/ran-automation-service 8081:8000`



and:



`curl.exe "http://127.0.0.1:8081/cells"`



The API returned the three synthetic RAN cells.



\## Prevention



\- Keep Service selectors and Pod labels consistent.

\- Verify EndpointSlices after Service changes.

\- Do not assume that a Running Pod means network connectivity is working.

\- When a Service is unreachable, check the Service selector and endpoints before troubleshooting the application.

