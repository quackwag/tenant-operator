from collections.abc import Callable
from typing import Any

import kopf
from kubernetes import client
from kubernetes.client.exceptions import ApiException

from const import LIMIT_DEFAULT, LIMIT_DEFAULT_REQUEST, TENANT_LABEL
from k8s import core


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

    _create_or_patch(
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

    _create_or_patch(
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


def _create_or_patch(
    create: Callable[..., Any],
    patch: Callable[..., Any],
    name: str,
    ns: str,
    body: object,
    kind: str,
    logger: kopf.Logger,
) -> None:
    """Create the object, or patch it if it already exists (409 error)."""

    try:
        create(ns, body=body)
        logger.info("Created %s '%s' in '%s'.", kind, name, ns)
    except ApiException as e:
        if e.status != 409:
            raise
        patch(name, ns, body=body)
        logger.debug("Patched %s '%s' in '%s'.", kind, name, ns)
