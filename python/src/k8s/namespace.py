import kopf
from kubernetes import client
from kubernetes.client.exceptions import ApiException

from const import NAMESPACE_PREFIX, PSA_LABELS, TENANT_LABEL
from k8s import core


def ensure(body: kopf.Body, logger: kopf.Logger) -> str:
    """Create the tenant's namespace, or confirm the existing one is ours.

    Safe to call repeatedly. Returns the namespace name.
    Raises kopf.PermanentError if the namespace belongs to someone else.
    Patches the tenant label if it has been removed or changed.
    """
    tenant = body["metadata"]["name"]
    name = f"{NAMESPACE_PREFIX}{tenant}"
    labels = {TENANT_LABEL: tenant} | PSA_LABELS
    ns = client.V1Namespace(metadata=client.V1ObjectMeta(name=name, labels=labels))
    kopf.adopt(ns, owner=body)

    try:
        core().create_namespace(body=ns)
        logger.info("Created namespace '%s'.", name)
    except ApiException as e:
        if e.status != 409:
            raise
        _reconcile_existing(name, labels, body["metadata"]["uid"], logger)
    return name


def _reconcile_existing(
    name: str, labels: dict[str, str], uid: str, logger: kopf.Logger
) -> None:
    """Check an existing namespace is ours and patch its labels."""
    existing = core().read_namespace(name)
    assert existing.metadata is not None
    owners = existing.metadata.owner_references or []
    if not any(ref.uid == uid for ref in owners):
        raise kopf.PermanentError(
            f"Namespace '{name}' already exists and is not owned by this tenant."
        )

    current = existing.metadata.labels or {}
    if labels.items() <= current.items():
        logger.debug("Namespace '%s' is up to date.", name)
        return
    core().patch_namespace(name, {"metadata": {"labels": labels}})
    logger.info("Patched labels on namespace '%s'.", name)
