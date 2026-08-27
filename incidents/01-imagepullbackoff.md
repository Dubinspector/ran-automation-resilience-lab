\# Incident 01 - ImagePullBackOff



\## Symptom



A new Kubernetes rollout did not complete.



The new Pod was created but remained unavailable:



\- READY: 0/1

\- STATUS: ErrImagePull

\- later: ImagePullBackOff



The previous application Pod remained Running and available.



\## Evidence



`kubectl get pods` showed:



\- existing v1.1 Pod: 1/1 Running

\- new Pod: 0/1 ErrImagePull



`kubectl describe pod` showed:



\- Image: `ran-automation-lab:v9.9`

\- State: Waiting

\- Reason: ErrImagePull

\- Ready: False



Events showed:



\- Failed to pull image `ran-automation-lab:v9.9`

\- repository does not exist or may require authorization

\- ErrImagePull

\- ImagePullBackOff



\## Hypothesis



The new Pod cannot start because Kubernetes cannot obtain the configured container image.



Possible causes include:



\- incorrect image tag

\- nonexistent image

\- registry authentication problem



\## Investigation



The Pod was successfully scheduled to `desktop-worker`.



Therefore scheduling was not the problem.



The container had no Container ID and never reached the Running state.



The Events section showed repeated failures while pulling:



`ran-automation-lab:v9.9`



The known working version was:



`ran-automation-lab:v1.1`



\## Root Cause



The Deployment referenced a nonexistent image tag:



`ran-automation-lab:v9.9`



Because the image was unavailable, kubelet could not create and start the container.



\## Fix



Rollback the Deployment:



`kubectl rollout undo deployment/ran-automation`



Then restore the source manifest to:



`image: ran-automation-lab:v1.1`



and apply it again.



\## Verification



`kubectl rollout status deployment/ran-automation`



reported:



`deployment "ran-automation" successfully rolled out`



`kubectl get pods` showed one healthy Pod:



\- READY: 1/1

\- STATUS: Running



The active Deployment image was verified as:



`ran-automation-lab:v1.1`



\## Prevention



\- Validate image names and tags before rollout.

\- Use immutable/versioned image tags.

\- Verify that the required image exists before deployment.

\- Keep the Kubernetes manifest consistent with the actual recovered cluster state.

\- Check Pod Events immediately when a container fails before attempting application-level troubleshooting.

