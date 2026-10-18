import kopf
from kubernetes import client

from const import LIMIT_DEFAULT, LIMIT_DEFAULT_REQUEST, TENANT_LABEL
from k8s import core, create_or_patch


def ensure(
    ns: str,
    spec: kopf.Spec,
    tiers_preset: dict[str, dict[str, str]],
    logger: kopf.Logger,
    tenant: str,
) -> None:
    """Create the tenant's ResourceQuota and LimitRange, or patch them back to the spec."""

    hard = _merge(spec, tiers_preset)
    quota = client.V1ResourceQuota(
        metadata=client.V1ObjectMeta(name=tenant, labels={TENANT_LABEL: tenant}),
        spec=client.V1ResourceQuotaSpec(hard=hard),
    )

    create_or_patch(
        core().create_namespaced_resource_quota,
        core().patch_namespaced_resource_quota,
        tenant,
        ns,
        quota,
        "ResourceQuota",
        logger,
    )

    limit = client.V1LimitRange(
        metadata=client.V1ObjectMeta(name=tenant, labels={TENANT_LABEL: tenant}),
        spec=client.V1LimitRangeSpec(
            limits=[
                client.V1LimitRangeItem(
                    default=LIMIT_DEFAULT,
                    default_request=LIMIT_DEFAULT_REQUEST,
                    type="Container",
                )
            ]
        ),
    )

    create_or_patch(
        core().create_namespaced_limit_range,
        core().patch_namespaced_limit_range,
        tenant,
        ns,
        limit,
        "LimitRange",
        logger,
    )


def _merge(spec: kopf.Spec, tiers_preset: dict[str, dict[str, str]]) -> dict[str, str]:
    """Return the tier's quota values with any cpu or memory overrides applied."""
    resources = spec.get("resources", {})
    preset = tiers_preset[spec["tier"]]
    cpu = resources.get("cpu", preset["requests.cpu"])
    memory = resources.get("memory", preset["requests.memory"])
    overrides = {"requests.memory": memory, "requests.cpu": cpu}
    return preset | overrides
