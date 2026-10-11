from typing import Any

import kopf
from kubernetes import config

# import aws
from const import GROUP, PLURAL, VERSION
from k8s import namespace  # network, quota, rbac


@kopf.on.startup()
def load_config(logger: kopf.Logger, **kwargs: Any) -> None:
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    logger.info("Kubernetes config loaded")


@kopf.on.create(GROUP, VERSION, PLURAL)
@kopf.on.update(GROUP, VERSION, PLURAL)
@kopf.on.resume(GROUP, VERSION, PLURAL)
@kopf.timer(GROUP, VERSION, PLURAL, interval=60)
def reconcile(
    body: kopf.Body, spec: kopf.Spec, logger: kopf.Logger, **kwargs: Any
) -> None:
    namespace.ensure(body, logger)
    # quota.ensure(ns, spec, logger)
    # network.ensure(ns, spec, logger)
    # rbac.ensure(ns, spec, logger)
    # aws.ensure(body, spec, logger)


# @kopf.on.delete(GROUP, VERSION, PLURAL)
# def delete_tenant(body, **kwargs):
# aws.delete(body)
