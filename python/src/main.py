import json
import os
from datetime import UTC, datetime
from typing import Any

import kopf
from kubernetes import config

# import aws
from const import GROUP, PLURAL, REQUIRED_KEYS, REQUIRED_TIERS, VERSION
from k8s import namespace, network, quota, rbac


@kopf.on.startup()
def load_config(logger: kopf.Logger, **kwargs: Any) -> None:
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()


@kopf.on.startup()
def load_tiers(logger: kopf.Logger, memo: kopf.Memo, **kwargs: Any) -> None:
    path = os.environ["TIERS_CONFIG"]
    with open(path) as f:
        tiers = json.load(f)

    missing = REQUIRED_TIERS - tiers.keys()
    if missing:
        raise kopf.PermanentError(f"{path}: missing tiers {sorted(missing)}")
    for name in REQUIRED_TIERS:
        missing_keys = REQUIRED_KEYS - tiers[name].keys()
        if missing_keys:
            raise kopf.PermanentError(
                f"{path}: tier '{name}' is missing {sorted(missing_keys)}"
            )

    memo.tiers = tiers
    logger.info("Loaded tiers '%s' from '%s'", ", ".join(sorted(tiers)), path)


@kopf.on.create(GROUP, VERSION, PLURAL)
@kopf.on.update(GROUP, VERSION, PLURAL)
@kopf.on.resume(GROUP, VERSION, PLURAL)
@kopf.timer(GROUP, VERSION, PLURAL, interval=60)
def reconcile(
    body: kopf.Body,
    spec: kopf.Spec,
    name: str,
    memo: kopf.Memo,
    patch: kopf.Patch,
    logger: kopf.Logger,
    **kwargs: Any,
) -> None:
    conditions: list[dict[str, str]] = []

    try:
        ns = namespace.ensure(body, logger)
        conditions.append(_condition("NamespaceReady", True))
    except Exception as e:
        conditions.append(_condition("NamespaceReady", False, str(e)))
        conditions.append(_condition("Ready", False, "Namespace failed"))
        patch.status["conditions"] = conditions
        raise

    failed: list[str] = []
    for type_, step in [
        ("QuotaReady", lambda: quota.ensure(ns, spec, memo.tiers, logger, tenant=name)),
        ("NetworkReady", lambda: network.ensure(ns, spec, logger, tenant=name)),
        ("RBACReady", lambda: rbac.ensure(ns, spec, logger, tenant=name)),
        # aws.ensure(body, spec, logger)
    ]:
        try:
            step()  # type: ignore[no-untyped-call]
            conditions.append(_condition(type_, True))
        except Exception as e:
            logger.exception("%s failed", type_)
            conditions.append(_condition(type_, False, str(e)))
            failed.append(type_)

    conditions.append(_condition("Ready", not failed, ", ".join(failed)))
    patch.status["conditions"] = conditions
    if failed:
        raise kopf.TemporaryError(f"Failed: {', '.join(failed)}", delay=30)


# @kopf.on.delete(GROUP, VERSION, PLURAL)
# def delete_tenant(body, **kwargs):
# aws.delete(body)


def _condition(type_: str, ok: bool, message: str = "") -> dict[str, str]:
    return {
        "type": type_,
        "status": "True" if ok else "False",
        "reason": "Reconciled" if ok else "Failed",
        "message": message,
        "lastTransitionTime": datetime.now(UTC).isoformat(),
    }
