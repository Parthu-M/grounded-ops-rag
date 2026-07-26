# Nimbus Deployment Workflow.

Nimbus deploys the hosted service on Tuesdays and Thursdays. A release candidate must pass unit, integration, security, and migration tests before production deployment. Production rollout starts with a five-percent canary for 20 minutes. The rollout advances to 25 percent, 50 percent, and 100 percent only while error-rate and latency checks remain healthy.

An automatic rollback begins if the five-minute error rate exceeds two percent or p95 latency rises by more than 40 percent from baseline. Database migrations must be backward compatible with the previous application version. Destructive schema changes require a two-release expand-and-contract process.

Emergency fixes may be deployed on any day after approval by the incident commander and one code owner. Feature flags separate code deployment from customer activation. A flag that has reached 100 percent for 30 days must be removed from the codebase or assigned a documented exception.

