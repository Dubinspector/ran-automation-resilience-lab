\# Operations Runbook



\## Service unavailable



1\. Check Pods



`kubectl get pods`



2\. Check Deployment



`kubectl get deployments`



3\. Check recent Events



`kubectl get events --sort-by=.metadata.creationTimestamp`



4\. Inspect problematic Pod



`kubectl describe pod <pod-name>`



5\. Check application logs



`kubectl logs <pod-name>`



6\. Check Service



`kubectl describe service ran-automation-service`



7\. Check Service endpoints



`kubectl get endpointslices`



8\. Check Pod labels versus Service selector



`kubectl get pods --show-labels`



9\. Check configuration



`kubectl describe configmap ran-automation-config`



10\. Check application configuration inside the Pod



`kubectl exec deployment/ran-automation -- printenv`



11\. Check RAN integration



`GET /precheck`



12\. Check RAN KPI validation



`GET /validation`



13\. If a new Kubernetes release caused the incident



`kubectl rollout history deployment/ran-automation`



`kubectl rollout undo deployment/ran-automation`



14\. Verify rollout



`kubectl rollout status deployment/ran-automation`



15\. Final verification



\- Pod is 1/1 Running

\- Service has endpoint

\- `/precheck` returns PASS

\- `/validation` returns PASS

\- expected release/image is active



\## Troubleshooting principle



Follow:



Symptom  

→ Evidence  

→ Hypothesis  

→ Investigation  

→ Root Cause  

→ Fix  

→ Verification  

→ Prevention



Do not start with application logs if the failure is clearly in another layer.



Typical isolation path:



Client  

→ Network  

→ Service  

→ EndpointSlice  

→ Pod  

→ Container  

→ Application  

→ RAN dependency

