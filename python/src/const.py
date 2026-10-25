GROUP = "platform.tenancy.io"
VERSION = "v1alpha1"
PLURAL = "tenants"
TENANT_LABEL = f"{GROUP}/tenant"
NAMESPACE_PREFIX = "tenant-"
PSA_LABELS = {
    "pod-security.kubernetes.io/enforce": "baseline",
    "pod-security.kubernetes.io/warn": "restricted",
}
REQUIRED_TIERS = {"small", "medium", "large"}
REQUIRED_KEYS = {
    "requests.cpu",
    "requests.memory",
    "requests.storage",
    "persistentvolumeclaims",
    "pods",
    "services.loadbalancers",
    "services.nodeports",
}
LIMIT_DEFAULT_REQUEST = {"cpu": "100m", "memory": "128Mi"}
LIMIT_DEFAULT = {"cpu": "500m", "memory": "512Mi"}
NETWORK_POLICY_NAME = "tenant-network"
NAMESPACE_NAME_LABEL = "kubernetes.io/metadata.name"
DNS_NAMESPACE = {NAMESPACE_NAME_LABEL: "kube-system"}
DNS_POD = {"k8s-app": "kube-dns"}
BINDING_ROLE_NAME = "tenant-binding"
BINDING_ROLE_MAP = {
    "owners": "tenant-admin",
    "members": "tenant-edit",
    "viewers": "view",
}
