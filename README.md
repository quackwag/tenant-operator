Python (kopf) implementation, Go version planned w/ crossplane

- Describe a team in one k8s custom resource
- The operator sets up their namespace, quotas, RBAC, network isolation and a scoped AWS IAM role and S3 buckets
- It syncs keeping these values correct after they're created and removes everything cleanly when the team is deleted
- The VPC and cluster come from my own terraform

