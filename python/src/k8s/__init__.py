from collections.abc import Callable
from functools import cache
from typing import Any

import kopf
from kubernetes import client
from kubernetes.client.exceptions import ApiException


@cache
def core() -> client.CoreV1Api:
    return client.CoreV1Api()


@cache
def networking() -> client.NetworkingV1Api:
    return client.NetworkingV1Api()


@cache
def rbac() -> client.RbacAuthorizationV1Api:
    return client.RbacAuthorizationV1Api()


def create_or_patch(
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
