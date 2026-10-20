import json
import os
from typing import Any

import kopf
from kubernetes import config

# import aws
from const import GROUP, PLURAL, REQUIRED_KEYS, REQUIRED_TIERS, VERSION
from k8s import namespace, network, quota  # rbac


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
    logger: kopf.Logger,
    **kwargs: Any,
) -> None:
    ns = namespace.ensure(body, logger)
    quota.ensure(ns, spec, memo.tiers, logger, tenant=name)
    network.ensure(ns, spec, logger, tenant=name)
    # rbac.ensure(ns, spec, logger)
    # aws.ensure(body, spec, logger)


# @kopf.on.delete(GROUP, VERSION, PLURAL)
# def delete_tenant(body, **kwargs):
# aws.delete(body)
