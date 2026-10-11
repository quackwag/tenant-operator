import kopf
from const import NAMESPACE_PREFIX, TENANT_LABEL
from kubernetes import client
from kubernetes.client.exceptions import ApiException

from k8s import core


def ensure(body, logger) -> str:
    """Create the tenant's namespace, or confirm the existing one is ours.

    Safe to call repeatedly. Returns the namespace name.
    Raises kopf.PermanentError if the namespace belongs to someone else.
    """
    tenant = body["metadata"]["name"]
    name = f"{NAMESPACE_PREFIX}{tenant}"

    ns = client.V1Namespace(
        metadata=client.V1ObjectMeta(name=name, labels={TENANT_LABEL: tenant})
    )
    kopf.adopt(ns, owner=body)

    try:
        core().create_namespace(body=ns)
        logger.info("Created namespace '%s'.", name)
    except ApiException as e:
        if e.status != 409:
            raise
        existing = core().read_namespace(name)
        owners = existing.metadata.owner_references or []
        if not any(ref.uid == body["metadata"]["uid"] for ref in owners):
            raise kopf.PermanentError(
                f"Namespace '{name}' already exists and is not owned by this tenant."
            )
        labels = existing.metadata.labels or {}
        if labels.get(TENANT_LABEL) != tenant:
            patch = {"metadata": {"labels": {TENANT_LABEL: tenant}}}
            core().patch_namespace(name, patch)
            logger.info("Patched label '%s' on namespace '%s'.", TENANT_LABEL, name)
        else:
            logger.debug(
                "Namespace '%s' already exists and is owned by this tenant.", name
            )
    return name
