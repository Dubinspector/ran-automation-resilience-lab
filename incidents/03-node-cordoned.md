\# Incident 03 - Node Cordoned / Scheduling Failure



\## Symptom



A Deployment rollout stalled.



The existing Pod remained healthy:



\- READY: 1/1

\- STATUS: Running



The new Pod remained:



\- READY: 0/1

\- STATUS: Pending



\## Evidence



`kubectl get nodes` showed:



\- `desktop-control-plane` - Ready

\- `desktop-worker` - Ready,SchedulingDisabled



`kubectl describe pod` showed:



\- Node: `<none>`

\- Status: Pending

\- PodScheduled: False



Events showed:



`0/2 nodes are available: 1 node(s) had untolerated taint(s), 1 node(s) were unschedulable.`



\## Hypothesis



The new Pod cannot be scheduled because no suitable node is available.



Possible causes include:



\- worker node cordoned

\- insufficient CPU or memory

\- node selector mismatch

\- taints without matching tolerations



\## Investigation



The worker node had been cordoned:



`desktop-worker Ready,SchedulingDisabled`



The control-plane node was healthy but had a taint that the application Pod did not tolerate.



Therefore:



\- worker node could not accept new Pods

\- control-plane node was excluded by taint

\- scheduler had no valid placement



The existing Pod continued running because `cordon` prevents new scheduling but does not evict existing Pods.



\## Root Cause



The only worker node was cordoned.



The control-plane node was not eligible because of its taint.



As a result, the new ReplicaSet Pod could not be scheduled and remained Pending.



\## Fix



Uncordon the worker node:



`kubectl uncordon desktop-worker`



\## Verification



`kubectl get nodes` showed:



`desktop-worker Ready`



The pending Pod was then scheduled and became:



\- READY: 1/1

\- STATUS: Running



The previous Pod was terminated after the new Pod became Ready.



`kubectl rollout status deployment/ran-automation`



reported:



`deployment "ran-automation" successfully rolled out`



\## Prevention



\- Check node scheduling state before rollout.

\- Include `kubectl get nodes` in rollout pre-checks.

\- Investigate Pending Pods using `kubectl describe pod` and scheduler Events.

\- Do not start with application logs when the Pod has not been scheduled.

\- Monitor node capacity and scheduling constraints before deployment.

